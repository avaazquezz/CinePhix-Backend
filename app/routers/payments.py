"""
Stripe Payments router — recurring subscription checkout for Pro plans.
4 plans: monthly (€4.99), quarterly (€12.99), 6m (€22.99), annual (€39.99)
"""

from datetime import datetime, timedelta, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.dependencies import CurrentUser, OptionalUser
from app.models import UserPro
from app.models.user import User

router = APIRouter(prefix="/payments", tags=["payments"])

# Stripe price IDs (recurring — must be configured as recurring prices in Stripe Dashboard)
STRIPE_PRICE_IDS = {
    "pro_monthly": "price_1TNYfz4fVdVPl5MMkGzgjAXn",
    "pro_quarterly": "price_1TNYfz4fVdVPl5MMDnfqznXd",
    "pro_6months": "price_1TNYfz4fVdVPl5MMjmswrQBA",
    "pro_annual": "price_1TNYg04fVdVPl5MMh8pEVqtt",
}

# Duration mapping: plan_name → months
PLAN_DURATION = {
    "pro_monthly": 1,
    "pro_quarterly": 3,
    "pro_6months": 6,
    "pro_annual": 12,
}


def _grant_pro_access(plan_type: str):
    now = datetime.now(timezone.utc)
    months = PLAN_DURATION.get(plan_type, 1)
    expires = now + timedelta(days=months * 30)
    return now, expires


def _stripe_error_detail(exc: stripe.error.StripeError) -> str:
    for attr in ("user_message", "_message", "message"):
        val = getattr(exc, attr, None)
        if val:
            return str(val)
    return str(exc)


async def _create_checkout_session_impl(current_user: User, plan: str) -> dict:
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key

    if plan not in STRIPE_PRICE_IDS:
        raise HTTPException(status_code=400, detail="Unknown plan")

    price_id = STRIPE_PRICE_IDS[plan]
    success_url = f"{settings.frontend_url}/CinePhix/profile?pro=success"
    cancel_url = f"{settings.frontend_url}/CinePhix/profile?pro=cancelled"

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            customer_email=current_user.email,
            metadata={
                "user_id": str(current_user.id),
                "plan": plan,
            },
            allow_promotion_codes=True,
            billing_address_collection="required",
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.error.AuthenticationError:
        raise HTTPException(
            status_code=502,
            detail="Stripe rejected the API key. Use a secret key from the same Stripe mode as your Price IDs.",
        )
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {_stripe_error_detail(e)}")


@router.post("/create-checkout-session")
async def create_checkout_session(
    current_user: CurrentUser,
    plan: str = Query(..., description="pro_monthly | pro_quarterly | pro_6months | pro_annual"),
):
    return await _create_checkout_session_impl(current_user, plan)


@router.post("/pay_plan_pro_monthly", include_in_schema=False)
async def pay_plan_pro_monthly(current_user: CurrentUser):
    return await _create_checkout_session_impl(current_user, "pro_monthly")


@router.post("/pay_plan_pro_quarterly", include_in_schema=False)
async def pay_plan_pro_quarterly(current_user: CurrentUser):
    return await _create_checkout_session_impl(current_user, "pro_quarterly")


@router.post("/pay_plan_pro_6months", include_in_schema=False)
async def pay_plan_pro_6months(current_user: CurrentUser):
    return await _create_checkout_session_impl(current_user, "pro_6months")


@router.post("/pay_plan_pro_annual", include_in_schema=False)
async def pay_plan_pro_annual(current_user: CurrentUser):
    return await _create_checkout_session_impl(current_user, "pro_annual")


@router.get("/pro-status")
async def pro_status(
    current_user: OptionalUser,
    db=Depends(get_db),
):
    if current_user is None:
        return {"pro": False, "plan": None, "expires_at": None}

    result = await db.execute(
        select(UserPro).where(UserPro.user_id == current_user.id)
    )
    pro = result.scalar_one_or_none()

    if not pro or not pro.is_active:
        return {"pro": False, "plan": None, "expires_at": None}

    return {
        "pro": True,
        "plan": pro.plan_type,
        "granted_at": pro.granted_at.isoformat() if pro.granted_at else None,
        "expires_at": pro.expires_at.isoformat() if pro.expires_at else None,
        "subscription_id": pro.stripe_subscription_id,
    }


@router.post("/customer-portal")
async def customer_portal(
    current_user: CurrentUser,
    db=Depends(get_db),
):
    """Redirect to Stripe customer portal for subscription management (cancel, upgrade, etc.)."""
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key

    # Get user's subscription ID
    result = await db.execute(
        select(UserPro).where(UserPro.user_id == current_user.id)
    )
    pro = result.scalar_one_or_none()

    if not pro or not pro.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription found")

    try:
        session = stripe.billing_portal.Session.create(
            customer=pro.stripe_subscription_id,
            return_url=f"{settings.frontend_url}/CinePhix/profile",
        )
        return {"portal_url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {_stripe_error_detail(e)}")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db=Depends(get_db),
):
    if not settings.stripe_secret_key:
        raise HTTPException(status_code=500, detail="Stripe not configured")

    stripe.api_key = settings.stripe_secret_key
    webhook_secret = settings.stripe_webhook_secret

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")

    body = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(body, sig, webhook_secret)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"]["user_id"]
        plan = session["metadata"]["plan"]
        subscription_id = session.get("subscription")
        granted, expires = _grant_pro_access(plan)

        result = await db.execute(select(UserPro).where(UserPro.user_id == user_id))
        existing = result.scalar_one_or_none()

        if existing:
            existing.plan_type = plan
            existing.stripe_session_id = session.get("id")
            existing.stripe_subscription_id = subscription_id
            existing.granted_at = granted
            existing.expires_at = expires
        else:
            pro = UserPro(
                user_id=user_id,
                plan_type=plan,
                stripe_session_id=session.get("id"),
                stripe_subscription_id=subscription_id,
                granted_at=granted,
                expires_at=expires,
                created_at=datetime.now(timezone.utc),
            )
            db.add(pro)

        await db.commit()

    # Handle subscription renewals — extend expiry on each successful invoice
    elif event["type"] == "invoice.paid":
        invoice = event["data"]["object"]
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return {"received": True}

        result = await db.execute(
            select(UserPro).where(UserPro.stripe_subscription_id == subscription_id)
        )
        pro = result.scalar_one_or_none()
        if pro:
            months = PLAN_DURATION.get(pro.plan_type, 1)
            pro.expires_at = datetime.now(timezone.utc) + timedelta(days=months * 30)
            pro.granted_at = datetime.now(timezone.utc)
            await db.commit()

    # Handle subscription cancellation — revoke pro access immediately
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        subscription_id = subscription.get("id")

        result = await db.execute(
            select(UserPro).where(UserPro.stripe_subscription_id == subscription_id)
        )
        pro = result.scalar_one_or_none()
        if pro:
            pro.expires_at = datetime.now(timezone.utc)
            await db.commit()

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        subscription_id = subscription.get("id")
        status = subscription.get("status")

        result = await db.execute(
            select(UserPro).where(UserPro.stripe_subscription_id == subscription_id)
        )
        pro = result.scalar_one_or_none()
        if pro:
            if status in ("canceled", "unpaid", "past_due"):
                pro.expires_at = datetime.now(timezone.utc)
            await db.commit()

    return {"received": True}


@router.post("/grant-pro")
async def grant_pro_admin(
    plan: str = Query(..., description="pro_monthly | pro_quarterly | pro_6months | pro_annual"),
    user_id: str = Query(...),
    db=Depends(get_db),
):
    if plan not in PLAN_DURATION:
        raise HTTPException(status_code=400, detail="Invalid plan")

    granted, expires = _grant_pro_access(plan)

    result = await db.execute(select(UserPro).where(UserPro.user_id == user_id))
    existing = result.scalar_one_or_none()

    if existing:
        existing.plan_type = plan
        existing.granted_at = granted
        existing.expires_at = expires
    else:
        pro = UserPro(
            user_id=user_id,
            plan_type=plan,
            granted_at=granted,
            expires_at=expires,
            created_at=datetime.now(timezone.utc),
        )
        db.add(pro)

    await db.commit()
    return {"ok": True, "expires_at": expires.isoformat()}
