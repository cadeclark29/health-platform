"""
Scheduler Service - Handles scheduled SMS reminders using APScheduler.
"""
from datetime import datetime
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

from app.db.database import SessionLocal
from app.models import User
from app.services.sms_service import sms_service

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


def get_reminder_time(user: User, period: str) -> str:
    """
    Calculate the reminder time for a user.

    Priority:
    1. Custom override time (custom_morning_time/custom_evening_time)
    2. User's wake_time/bedtime
    3. Default times (07:00 morning, 21:00 evening)
    """
    prefs = user.notification_preferences or {}

    if period == "morning":
        custom = prefs.get("custom_morning_time")
        if custom:
            return custom
        return user.wake_time or "07:00"
    else:
        custom = prefs.get("custom_evening_time")
        if custom:
            return custom
        # Default evening to 30 min before bedtime or 21:00
        bedtime = user.bedtime or "21:30"
        try:
            hours, minutes = map(int, bedtime.split(":"))
            total_minutes = hours * 60 + minutes - 30  # 30 min before bed
            if total_minutes < 0:
                total_minutes += 24 * 60
            result_hours = (total_minutes // 60) % 24
            result_minutes = total_minutes % 60
            return f"{result_hours:02d}:{result_minutes:02d}"
        except:
            return "21:00"


async def check_and_send_reminders():
    """
    Main scheduler job that runs every minute.
    Checks all users and sends reminders if their scheduled time matches.
    """
    if not sms_service.is_configured():
        return

    db = SessionLocal()
    try:
        # Get all users with verified phones
        users = db.query(User).filter(
            User.phone_verified == True,
            User.phone_number.isnot(None)
        ).all()

        for user in users:
            await process_user_reminders(user, db)

    except Exception as e:
        logger.error(f"Scheduler error: {e}")
    finally:
        db.close()


async def process_user_reminders(user: User, db):
    """Process reminder checks for a single user."""
    prefs = user.notification_preferences or {}

    # Skip if SMS not enabled
    if not prefs.get("sms_enabled", False):
        return

    # Get user's current time
    try:
        user_tz = pytz.timezone(user.timezone or "America/New_York")
    except:
        user_tz = pytz.timezone("America/New_York")

    user_now = datetime.now(user_tz)
    current_time_str = user_now.strftime("%H:%M")

    # Check morning reminder
    if prefs.get("morning_reminder", True):
        morning_time = get_reminder_time(user, "morning")
        if current_time_str == morning_time:
            await send_user_reminder(user, "morning", db)

    # Check evening reminder
    if prefs.get("evening_reminder", True):
        evening_time = get_reminder_time(user, "evening")
        if current_time_str == evening_time:
            await send_user_reminder(user, "evening", db)


async def send_user_reminder(user: User, time_of_day: str, db):
    """Send a supplement reminder to a user."""
    try:
        # Get user's active supplements
        supplements = [
            s.to_dict() for s in user.supplement_starts
            if s.end_date is None
        ]

        if not supplements:
            logger.info(f"No active supplements for user {user.id}")
            return

        # Send the reminder
        result = sms_service.send_reminder(
            to_number=user.phone_number,
            user_name=user.name,
            time_of_day=time_of_day,
            supplements=supplements
        )

        if result["success"]:
            logger.info(f"Sent {time_of_day} reminder to user {user.id}")
        else:
            logger.error(f"Failed to send reminder to user {user.id}: {result.get('error')}")

    except Exception as e:
        logger.error(f"Error sending reminder to user {user.id}: {e}")


def start_scheduler():
    """Initialize and start the scheduler."""
    if not sms_service.is_configured():
        logger.warning("Twilio not configured - SMS scheduler disabled")
        return

    # Run every minute to check for due reminders
    scheduler.add_job(
        check_and_send_reminders,
        CronTrigger(minute="*"),
        id="sms_reminder_check",
        replace_existing=True
    )
    scheduler.start()
    logger.info("SMS reminder scheduler started")


def shutdown_scheduler():
    """Gracefully shutdown the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("SMS reminder scheduler stopped")
