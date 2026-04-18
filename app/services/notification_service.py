"""
Notification service — create notifications + broadcast via WebSocket.
Notification types: new_follower | review_liked | new_review_on_list | list_featured
"""

from app.models import Notification
from app.database import AsyncSession

# In-memory WebSocket connection registry: user_id -> list of WebSocket sessions
from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    """Tracks live WebSocket connections per user."""

    def __init__(self):
        # user_id -> [websocket, ...]
        self._connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        if user_id in self._connections:
            self._connections[user_id] = [
                ws for ws in self._connections[user_id] if ws != websocket
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]

    async def push(self, user_id: str, payload: dict) -> None:
        """Send JSON payload to all open connections of this user."""
        if user_id not in self._connections:
            return
        dead = []
        for ws in self._connections[user_id]:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        # Clean up dead connections
        for ws in dead:
            self._connections[user_id].remove(ws)

    @property
    def active_connections(self) -> int:
        return sum(len(v) for v in self._connections.values())


manager = ConnectionManager()


# Notification type constants
NT_NEW_FOLLOWER = "new_follower"
NT_REVIEW_LIKED = "review_liked"
NT_NEW_LIST = "new_review_on_list"
NT_LIST_FEATURED = "list_featured"


async def create_notification(
    db: AsyncSession,
    user_id: str,
    notification_type: str,
    data: dict | None = None,
) -> Notification:
    """
    Persist a notification to DB and push it via WebSocket to the user.
    Call this right after the triggering action (follow, vote, list create...).
    """
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        data=data or {},
    )
    db.add(notification)
    await db.flush()

    # Push via WebSocket in real-time
    from app.schemas.notification import NotificationResponse
    payload = NotificationResponse.model_validate(notification).model_dump(mode="json")
    await manager.push(user_id, {"type": "notification", "data": payload})

    return notification


async def notify_new_follower(
    db: AsyncSession,
    follower_id: str,
    following_id: str,
    follower_username: str,
) -> Notification:
    """Notify `following_id` that `follower_id` followed them."""
    return await create_notification(
        db,
        user_id=following_id,
        notification_type=NT_NEW_FOLLOWER,
        data={
            "follower_id": follower_id,
            "follower_username": follower_username,
        },
    )


async def notify_review_liked(
    db: AsyncSession,
    review_owner_id: str,
    liker_username: str,
    tmdb_id: int,
    media_type: str,
    review_id: int,
) -> Notification:
    """Notify review owner that someone found their review useful."""
    return await create_notification(
        db,
        user_id=review_owner_id,
        notification_type=NT_REVIEW_LIKED,
        data={
            "liker_username": liker_username,
            "tmdb_id": tmdb_id,
            "media_type": media_type,
            "review_id": review_id,
        },
    )


async def notify_list_created(
    db: AsyncSession,
    list_owner_id: str,
    list_id: int,
    list_name: str,
) -> Notification:
    """Notify user when one of their lists gets featured."""
    return await create_notification(
        db,
        user_id=list_owner_id,
        notification_type=NT_LIST_FEATURED,
        data={
            "list_id": list_id,
            "list_name": list_name,
        },
    )
