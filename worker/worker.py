
import os
from pathlib import Path

# --------------------------------------------------
# Prometheus multiprocess configuration
# Must execute before importing application modules.
# --------------------------------------------------

PROMETHEUS_DIR = (
    Path(__file__).resolve().parents[1]
    / "storage"
    / "prometheus"
)

PROMETHEUS_DIR.mkdir(parents=True, exist_ok=True)

os.environ["PROMETHEUS_MULTIPROC_DIR"] = str(PROMETHEUS_DIR)


# --------------------------------------------------
# Application imports
# --------------------------------------------------

from rq import SimpleWorker

from config.logging_config import configure_logging, get_logger
from observability.metrics import ACTIVE_WORKERS
from observability.tracing import configure_tracing, shutdown_tracing
from services.queue_service import get_queue, get_redis_connection

configure_logging()
logger = get_logger(__name__)


def run_worker() -> None:
    worker_name = os.getenv(
        "RQ_WORKER_NAME",
        f"petition-worker-{os.getpid()}",
    )

    try:
        configure_tracing()

        redis_connection = get_redis_connection()
        queue = get_queue()

        worker = SimpleWorker(
            [queue],
            connection=redis_connection,
            name=worker_name,
        )

        ACTIVE_WORKERS.inc()

        logger.info(
            "worker_starting",
            worker_name=worker_name,
            queue_name=queue.name,
            worker_type="SimpleWorker",
        )

        worker.work(with_scheduler=False)

    except KeyboardInterrupt:
        logger.info("worker_shutdown_requested")

    except Exception:
        logger.exception("worker_failed")
        raise

    finally:
        ACTIVE_WORKERS.dec()
        shutdown_tracing()

        logger.info(
            "worker_stopped",
            worker_name=worker_name,
        )


if __name__ == "__main__":
    run_worker()
