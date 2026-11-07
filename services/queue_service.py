from redis import Redis
from rq import Queue

from config.settings import get_settings

settings = get_settings()


def get_redis_connection() -> Redis:
    """Create a Redis connection using application settings."""
    return Redis.from_url(
        settings.redis_url,
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )


def get_queue() -> Queue:
    """Return the petition-processing RQ queue."""
    connection = get_redis_connection()

    return Queue(
        name=settings.redis_queue_name,
        connection=connection,
        default_timeout=settings.llm_timeout_seconds * 3,
    )


def enqueue_petition(run_id: str, petition_id: str) -> str:
    """Submit a petition-processing job to the background queue."""
    queue = get_queue()

    job = queue.enqueue(
        "worker.tasks.process_petition",
        run_id,
        petition_id,
        job_timeout=settings.llm_timeout_seconds * 3,
        result_ttl=86400,
        failure_ttl=604800,
    )

    return job.id


def get_job_status(job_id: str) -> dict:
    """Retrieve the status of a queued job."""
    connection = get_redis_connection()

    from rq.job import Job

    try:
        job = Job.fetch(job_id, connection=connection)

        return {
            "job_id": job.id,
            "status": job.get_status(),
            "result": job.result,
            "error": job.exc_info,
        }

    except Exception:
        return {
            "job_id": job_id,
            "status": "not_found",
            "result": None,
            "error": None,
        }