"""
APScheduler setup.
Jobs:
  - Daily refill gap detection
  - 48h no-reply campaign retry
"""
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def start_scheduler():
    """Register all jobs and start the scheduler."""
    # Daily at 08:00 UTC
    scheduler.add_job(
        _run_refill_detection,
        CronTrigger(hour=8, minute=0),
        id="daily_refill_detection",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Every hour — check for 48h no-reply campaigns
    scheduler.add_job(
        _run_no_reply_check,
        IntervalTrigger(hours=1),
        id="no_reply_check",
        replace_existing=True,
        misfire_grace_time=600,
    )

    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


def _run_refill_detection():
    """Triggered daily — detect overdue medications and fire nudge campaigns."""
    logger.info("Running daily refill gap detection ...")
    try:
        from app.services.refill_gap_service import detect_and_trigger
        results = detect_and_trigger()
        logger.info("Refill detection results: %s", results)
    except Exception as exc:
        logger.error("Refill gap detection failed: %s", exc)


def _run_no_reply_check():
    """Check for campaigns in 'sent' state with no reply for 48+ hours."""
    logger.info("Running 48h no-reply check ...")
    try:
        from app.core.database import SessionLocal
        from app.models.models import NudgeCampaign
        from app.services.nudge_campaign_service import retry_or_escalate

        db = SessionLocal()
        threshold = datetime.utcnow() - timedelta(hours=48)
        stale_campaigns = (
            db.query(NudgeCampaign)
            .filter(
                NudgeCampaign.status == "sent",
                NudgeCampaign.last_sent_at <= threshold,
            )
            .all()
        )
        for campaign in stale_campaigns:
            try:
                retry_or_escalate(db, campaign)
            except Exception as exc:
                logger.error("Error retrying campaign %s: %s", campaign.id, exc)
        db.close()
    except Exception as exc:
        logger.error("No-reply check failed: %s", exc)
