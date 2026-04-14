"""
Scheduler worker entry point.

Used by the dedicated ECS `scheduler-service` task (SCHEDULER_ENABLED=true).
The API service runs with SCHEDULER_ENABLED=false so jobs do not duplicate
when the API scales to multiple tasks.

Usage:
    python -m app.worker
"""
import logging
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def _shutdown(signum, frame):  # pragma: no cover
    logger.info("Scheduler worker received signal %s — shutting down", signum)
    from app.core.scheduler import stop_scheduler
    stop_scheduler()
    sys.exit(0)


if __name__ == "__main__":
    from app.core.config import settings

    if not settings.SCHEDULER_ENABLED:
        logger.error(
            "SCHEDULER_ENABLED is false — worker must run with SCHEDULER_ENABLED=true"
        )
        sys.exit(1)

    from app.core.database import Base, engine
    from app.core.scheduler import start_scheduler

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Starting scheduler worker")
    start_scheduler()

    # Block the main thread so the BackgroundScheduler threads keep running
    signal.pause()
