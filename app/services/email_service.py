"""Email service using Resend (free tier compatible)."""

import resend

from app.config import settings
from app.utils.security import generate_magic_link_token


class EmailService:
    """Service for sending transactional emails via Resend."""

    def __init__(self):
        self.resend = resend
        self.resend.api_key = settings.resend_api_key
        self.from_email = settings.email_from

    def _get_base_url(self) -> str:
        """Get frontend base URL for magic link."""
        # In production this would come from settings
        return "http://localhost:5173"

    async def send_magic_link(self, to_email: str, raw_token: str) -> dict:
        """Send magic link email to user."""
        magic_link = f"{self._get_base_url()}/auth/verify?token={raw_token}"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Inter', -apple-system, sans-serif; background: #0a0a0a; color: #fff; margin: 0; padding: 20px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #141414; border-radius: 8px; border: 1px solid #222; padding: 40px; }}
                h1 {{ color: #04ff24; margin: 0 0 20px; font-size: 24px; }}
                p {{ color: #ccc; line-height: 1.6; margin: 0 0 20px; }}
                a {{ display: inline-block; background: #04ff24; color: #000; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; }}
                .footer {{ margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>CinePhix</h1>
                <p>Click the button below to sign in to your account. This link expires in 15 minutes.</p>
                <a href="{magic_link}">Sign In to CinePhix</a>
                <p class="footer">If you didn't request this email, you can safely ignore it.</p>
            </div>
        </body>
        </html>
        """

        try:
            params = {
                "from": self.from_email,
                "to": to_email,
                "subject": "Your CinePhix Sign-In Link",
                "html": html_content,
            }
            return self.resend.Emails.send(params)
        except Exception as e:
            # Log error but don't fail - magic link can still be returned to user
            print(f"Failed to send email: {e}")
            return {"id": None, "error": str(e)}

    async def send_welcome_email(self, to_email: str, username: str) -> dict:
        """Send welcome email after registration."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Inter', -apple-system, sans-serif; background: #0a0a0a; color: #fff; margin: 0; padding: 20px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: #141414; border-radius: 8px; border: 1px solid #222; padding: 40px; }}
                h1 {{ color: #04ff24; margin: 0 0 20px; font-size: 24px; }}
                p {{ color: #ccc; line-height: 1.6; margin: 0 0 20px; }}
                .footer {{ margin-top: 30px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Welcome to CinePhix, {username}!</h1>
                <p>Your account is ready. Start discovering movies and TV shows, build your watchlist, and get personalized recommendations.</p>
                <p class="footer">— The CinePhix Team</p>
            </div>
        </body>
        </html>
        """

        try:
            params = {
                "from": self.from_email,
                "to": to_email,
                "subject": "Welcome to CinePhix!",
                "html": html_content,
            }
            return self.resend.Emails.send(params)
        except Exception as e:
            print(f"Failed to send welcome email: {e}")
            return {"id": None, "error": str(e)}