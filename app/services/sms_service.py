"""
SMS Service - Handles all SMS operations via Twilio.
"""
from typing import Dict, Optional
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


class SMSService:
    """Handles all SMS operations via Twilio."""

    def __init__(self):
        self._client = None
        self._from_number = None

    def _get_client(self):
        """Lazy initialization of Twilio client."""
        if self._client is None:
            settings = get_settings()
            if settings.twilio_account_sid and settings.twilio_auth_token:
                from twilio.rest import Client
                self._client = Client(
                    settings.twilio_account_sid,
                    settings.twilio_auth_token
                )
                self._from_number = settings.twilio_phone_number
            else:
                logger.warning("Twilio credentials not configured")
        return self._client

    def is_configured(self) -> bool:
        """Check if Twilio is properly configured."""
        settings = get_settings()
        return bool(
            settings.twilio_account_sid and
            settings.twilio_auth_token and
            settings.twilio_phone_number
        )

    def send_sms(
        self,
        to_number: str,
        message: str,
        user_id: Optional[str] = None,
        message_type: Optional[str] = None
    ) -> Dict:
        """
        Send SMS via Twilio.

        Args:
            to_number: Destination phone number in E.164 format
            message: Message body
            user_id: Optional user ID for logging
            message_type: Type of message (verification, reminder, etc.)

        Returns:
            Dict with success status and message SID or error
        """
        client = self._get_client()
        if not client:
            logger.error("Twilio client not available")
            return {"success": False, "error": "SMS service not configured"}

        try:
            from twilio.base.exceptions import TwilioRestException

            response = client.messages.create(
                body=message,
                from_=self._from_number,
                to=to_number
            )

            logger.info(
                f"SMS sent to {self._mask_phone(to_number)} "
                f"[{message_type or 'unknown'}] SID: {response.sid}"
            )

            return {
                "success": True,
                "sid": response.sid,
                "status": response.status
            }

        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return {"success": False, "error": str(e)}

    def send_verification_code(self, to_number: str, code: str) -> Dict:
        """Send phone verification code."""
        message = f"Your Dose verification code is: {code}\n\nIt expires in 10 minutes."
        return self.send_sms(
            to_number=to_number,
            message=message,
            message_type="verification"
        )

    def send_reminder(
        self,
        to_number: str,
        user_name: str,
        time_of_day: str,
        supplements: list
    ) -> Dict:
        """
        Send supplement reminder.

        Args:
            to_number: User's phone number
            user_name: User's first name
            time_of_day: "morning" or "evening"
            supplements: List of supplement dicts with 'name' key
        """
        message = self.build_reminder_message(user_name, time_of_day, supplements)
        return self.send_sms(
            to_number=to_number,
            message=message,
            message_type=f"{time_of_day}_reminder"
        )

    def build_reminder_message(
        self,
        user_name: str,
        time_of_day: str,
        supplements: list
    ) -> str:
        """Build personalized reminder message."""
        # Get first name
        first_name = user_name.split()[0] if user_name else "there"

        # Format supplement names (limit to 3 for SMS length)
        supp_names = [s.get("name", s.get("supplement_name", "Unknown")) for s in supplements[:3]]
        supp_text = ", ".join(supp_names)

        if len(supplements) > 3:
            supp_text += f" +{len(supplements) - 3} more"

        # Build message based on time
        if time_of_day == "morning":
            greeting = f"Good morning, {first_name}!"
        else:
            greeting = f"Evening reminder, {first_name}!"

        return f"{greeting}\n\nTime for your supplements: {supp_text}\n\n- Dose"

    def _mask_phone(self, phone: str) -> str:
        """Mask phone number for logging."""
        if phone and len(phone) > 6:
            return phone[:3] + "***" + phone[-4:]
        return "***"


# Singleton instance
sms_service = SMSService()
