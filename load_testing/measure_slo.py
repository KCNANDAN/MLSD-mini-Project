import argparse
import asyncio
from datetime import datetime, timezone
import json
import statistics
import time
from uuid import uuid4
from pathlib import Path
from typing import Any

from database.connection import SessionLocal
from database.models import ProcessingRun
from services.petition_service import PetitionService
from worker.tasks import _process_petition_async


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_PATH = PROJECT_ROOT / "storage" / "slo_benchmark_report.json"


def generate_synthetic_petition(index: int) -> dict[str, Any]:
    categories = [
        "attendance",
        "re_evaluation",
        "medical_leave",
        "grade_grievance",
        "re_registration",
    ]
    category = categories[index % len(categories)]
    return {
        "student_reference": f"SLO-BENCH-{index:04d}-{uuid4().hex[:6]}",
        "petition_type": category,
        "admission_batch": "2024",
        "semester": (index % 8) + 1,
        "description": f"Performance and SLO validation benchmark petition #{index}.",
        "additional_details": {
            "attendance_percentage": 70 + (index % 15),
            "medical_grounds": bool(index % 2 == 0),
            "benchmark_batch": True,
        },
    }


async def simulate_worker_queue(
    petitions: list[dict[str, Any]],
    num_workers: int = 3,
) -> list[dict[str, Any]]:
    """
    Simulate multi-worker queue execution and measure end-to-end processing latency.
    """
    service = PetitionService()
    submitted_jobs = []

    # 1. Enqueue all petitions
    enqueue_start = time.perf_counter()
    for petition in petitions:
        submission = service.submit_petition(petition)
        submitted_jobs.append({
            "run_id": submission["run_id"],
            "submitted_at": time.time(),
        })

    enqueue_duration = time.perf_counter() - enqueue_start

    # 2. Process concurrently with N worker coroutines simulating simultaneous workers
    queue = asyncio.Queue()
    for job in submitted_jobs:
        await queue.put(job)

    results = []
    worker_timeline = {f"worker-{i+1}": 0 for i in range(num_workers)}

    async def worker_loop(worker_id: str):
        while not queue.empty():
            try:
                job = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            run_id = job["run_id"]
            start_proc = time.perf_counter()

            # Retrieve petition_id from database
            with SessionLocal() as db:
                run = db.query(ProcessingRun).filter_by(run_id=run_id).first()
                petition_id = run.petition_id

            try:
                outcome = await _process_petition_async(run_id, petition_id)
                status = outcome.get("routing_recommendation", "completed")
                is_success = True
                error_msg = None
            except Exception as exc:
                status = "failed"
                is_success = False
                error_msg = str(exc)

            proc_duration = time.perf_counter() - start_proc
            total_e2e_duration = time.time() - job["submitted_at"]
            worker_timeline[worker_id] += 1

            results.append({
                "run_id": run_id,
                "worker_id": worker_id,
                "processing_seconds": proc_duration,
                "e2e_seconds": total_e2e_duration,
                "status": status,
                "success": is_success,
                "error": error_msg,
            })
            queue.task_done()

    worker_tasks = [
        asyncio.create_task(worker_loop(f"worker-{i+1}"))
        for i in range(num_workers)
    ]
    await asyncio.gather(*worker_tasks)

    return results


def calculate_slo_metrics(
    results: list[dict[str, Any]],
    total_time: float,
    num_workers: int,
) -> dict[str, Any]:
    latencies = [r["e2e_seconds"] for r in results]
    success_count = sum(1 for r in results if r["success"])
    failure_count = len(results) - success_count

    if not latencies:
        return {}

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    def percentile(p: float) -> float:
        k = (n - 1) * p
        f = int(k)
        c = min(f + 1, n - 1)
        d0 = sorted_latencies[f] * (c - k)
        d1 = sorted_latencies[c] * (k - f)
        return round(d0 + d1, 4)

    p50 = percentile(0.50)
    p90 = percentile(0.90)
    p95 = percentile(0.95)
    p99 = percentile(0.99)
    mean_lat = round(statistics.mean(latencies), 4)

    throughput = round(len(results) / total_time, 2) if total_time > 0 else 0

    # Worker load distribution
    worker_counts = {}
    for r in results:
        wid = r["worker_id"]
        worker_counts[wid] = worker_counts.get(wid, 0) + 1

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_petitions": len(results),
        "workers_configured": num_workers,
        "worker_distribution": worker_counts,
        "simultaneous_workers_verified": len(worker_counts) == num_workers,
        "successful_petitions": success_count,
        "failed_petitions": failure_count,
        "success_rate_percent": round((success_count / len(results)) * 100, 2),
        "total_benchmark_duration_seconds": round(total_time, 3),
        "throughput_petitions_per_second": throughput,
        "latency_slo_seconds": {
            "min": round(min(latencies), 4),
            "max": round(max(latencies), 4),
            "mean": mean_lat,
            "p50": p50,
            "p90": p90,
            "p95": p95,
            "p99": p99,
        },
        "target_p95_slo_seconds": 30.0,
        "meets_p95_slo": p95 <= 30.0,
    }


def main():
    parser = argparse.ArgumentParser(description="End-to-end performance and SLO benchmark.")
    parser.add_argument("--count", type=int, default=30, help="Number of petitions to benchmark.")
    parser.add_argument("--workers", type=int, default=3, help="Simultaneous workers count.")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH, help="Output JSON path.")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("ACADEMIC PETITION TRIAGE — MULTI-WORKER & SLO BENCHMARK")
    print("=" * 60)
    print(f"Generating {args.count} synthetic petitions across {args.workers} workers...")

    petitions = [generate_synthetic_petition(i) for i in range(args.count)]

    start_time = time.perf_counter()
    results = asyncio.run(simulate_worker_queue(petitions, num_workers=args.workers))
    total_time = time.perf_counter() - start_time

    metrics = calculate_slo_metrics(results, total_time, args.workers)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("\nBenchmark Results Summary:")
    print("-" * 60)
    print(f"Total petitions:       {metrics['total_petitions']}")
    print(f"Workers running:       {metrics['workers_configured']} ({metrics['worker_distribution']})")
    print(f"Success rate:          {metrics['success_rate_percent']}%")
    print(f"Total time:            {metrics['total_benchmark_duration_seconds']}s")
    print(f"Throughput:            {metrics['throughput_petitions_per_second']} petitions/sec")
    print(f"Mean processing time:  {metrics['latency_slo_seconds']['mean']}s")
    print(f"p50 latency:           {metrics['latency_slo_seconds']['p50']}s")
    print(f"p90 latency:           {metrics['latency_slo_seconds']['p90']}s")
    print(f"p95 latency:           {metrics['latency_slo_seconds']['p95']}s (Target: <=30.0s) -> {'PASSED' if metrics['meets_p95_slo'] else 'FAILED'}")
    print(f"p99 latency:           {metrics['latency_slo_seconds']['p99']}s")
    print("-" * 60)
    print(f"Report saved to: {args.output}\n")


if __name__ == "__main__":
    main()
