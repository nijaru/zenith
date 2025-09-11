"""
🔄 Advanced Background Processing - Redis-Powered Job Queues

This example demonstrates sophisticated background job processing:
- Redis-backed job queues with persistence
- Retry logic with exponential backoff for failed jobs  
- Job scheduling with cron-like expressions
- Multi-worker processes with supervision
- Comprehensive job status tracking and monitoring
- Production-ready distributed task processing

Prerequisites:
    pip install redis
    
Setup:
    # Start Redis first:
    redis-server
    
    # In one terminal, start the worker:
    python examples/14-advanced-background-processing.py worker
    
    # In another terminal, start the API:
    python examples/14-advanced-background-processing.py
    
    # Submit jobs via API:
    curl -X POST http://localhost:8014/jobs/email \
         -H "Content-Type: application/json" \
         -d '{"to": "user@example.com", "subject": "Hello"}'
"""

import asyncio
import sys
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

from zenith import Zenith, Router
from zenith.jobs import JobManager, JobQueue, Worker, job, schedule


# ============================================================================
# JOB DEFINITIONS - Using Global Decorators
# ============================================================================

@job(max_retries=3, retry_delay_secs=5)
async def send_email(to: str, subject: str, body: str) -> dict:
    """Background job to send an email."""
    print(f"📧 Sending email to {to}: {subject}")
    
    # Simulate email sending
    await asyncio.sleep(2)
    
    # Simulate occasional failures for retry demonstration
    import random
    if random.random() < 0.3:  # 30% chance of failure
        raise Exception("Email service temporarily unavailable")
    
    return {
        "sent_at": datetime.utcnow().isoformat(),
        "to": to,
        "subject": subject,
        "status": "sent"
    }


@job(max_retries=1)
async def process_image(image_url: str, sizes: list[str]) -> dict:
    """Background job to process images."""
    print(f"🖼️  Processing image: {image_url}")
    
    results = {}
    for size in sizes:
        await asyncio.sleep(0.5)  # Simulate processing
        results[size] = f"{image_url}_{size}.jpg"
        print(f"   ✅ Generated {size} version")
    
    return {"processed": results}


@schedule(cron="*/5 * * * *")  # Every 5 minutes
async def cleanup_old_sessions():
    """Scheduled job to clean up old sessions."""
    print(f"🧹 Running session cleanup at {datetime.utcnow()}")
    # Cleanup logic here
    cleaned_count = 42  # Simulated cleanup
    print(f"   Cleaned {cleaned_count} old sessions")
    return {"cleaned": cleaned_count}


@schedule(every=timedelta(hours=1))  # Every hour
async def generate_reports():
    """Scheduled job to generate reports."""
    print(f"📊 Generating reports at {datetime.utcnow()}")
    # Report generation logic here
    reports = ["daily_summary", "user_stats", "performance_metrics"]
    print(f"   Generated {len(reports)} reports")
    return {"reports_generated": reports}


# ============================================================================
# API SETUP
# ============================================================================

app = Zenith(
    title="Background Jobs Example",
    version="1.0.0"
)

# Get the global job manager (automatically initialized)
from zenith.jobs.manager import get_job_manager
job_manager = get_job_manager()


# ============================================================================
# API ENDPOINTS
# ============================================================================

class EmailRequest(BaseModel):
    to: str
    subject: str
    body: str = "This is a test email from Zenith jobs system."


class ImageRequest(BaseModel):
    image_url: str
    sizes: list[str] = ["thumbnail", "medium", "large"]


@app.post("/jobs/email")
async def submit_email_job(request: EmailRequest) -> dict:
    """Submit an email job to the queue."""
    # Use the .delay() method attached by the @job decorator
    job_id = await send_email.delay(
        request.to,
        request.subject,
        request.body
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Email job queued for {request.to}"
    }


@app.post("/jobs/image")
async def submit_image_job(request: ImageRequest) -> dict:
    """Submit an image processing job."""
    # Use the .delay() method attached by the @job decorator
    job_id = await process_image.delay(
        request.image_url,
        request.sizes
    )
    
    return {
        "job_id": job_id,
        "status": "queued",
        "message": f"Image processing queued for {len(request.sizes)} sizes"
    }


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict:
    """Get the status of a job."""
    status = await job_manager.get_job_status(job_id)
    result = await job_manager.get_job_result(job_id)
    
    return {
        "job_id": job_id,
        "status": status.value if status else "not_found",
        "result": result
    }


@app.get("/jobs")
async def list_jobs(status: Optional[str] = None) -> dict:
    """List all jobs, optionally filtered by status."""
    jobs = await job_manager.queue.list_jobs(status=status)
    
    return {
        "total": len(jobs),
        "jobs": jobs
    }


@app.post("/jobs/scheduled")
async def schedule_email_later(
    request: EmailRequest, 
    delay_minutes: int = 5
) -> dict:
    """Schedule an email to be sent after a delay."""
    # Use the global job manager to enqueue with a delay
    job_id = await job_manager.enqueue(
        "send_email",
        request.to,
        request.subject, 
        request.body,
        delay=timedelta(minutes=delay_minutes)
    )
    
    return {
        "job_id": job_id,
        "status": "scheduled",
        "message": f"Email scheduled to send in {delay_minutes} minutes"
    }


@app.get("/")
async def root() -> dict:
    """Root endpoint with usage instructions."""
    return {
        "message": "Zenith Background Jobs Example",
        "features": [
            "Redis-backed job queue",
            "Retry logic with exponential backoff",
            "Job scheduling (cron and delay)",
            "Worker process management",
            "Job status tracking"
        ],
        "endpoints": {
            "POST /jobs/email": "Submit an email job",
            "POST /jobs/image": "Submit an image processing job",
            "POST /jobs/scheduled": "Schedule an email for later",
            "GET /jobs/{job_id}": "Get job status",
            "GET /jobs": "List all jobs"
        },
        "setup": [
            "1. Start Redis: redis-server",
            "2. Start worker: python examples/16-background-jobs.py worker",
            "3. Start API: python examples/16-background-jobs.py",
            "4. Submit jobs via the API endpoints"
        ]
    }


# ============================================================================
# WORKER PROCESS
# ============================================================================

async def run_worker():
    """Run the background worker process."""
    print("🚀 Starting Zenith job worker...")
    print("📡 Connecting to Redis...")
    
    # Create worker with the global job manager's queue
    worker = Worker(
        queue=job_manager.queue,
        concurrency=4  # Process up to 4 jobs concurrently
    )
    
    print("✅ Worker ready, waiting for jobs...")
    print("   Registered jobs:", list(job_manager.jobs.keys()))
    print("   Press Ctrl+C to stop")
    
    try:
        # Start the worker - it will process jobs from the queue
        await worker.run()
    except KeyboardInterrupt:
        print("\n👋 Shutting down worker...")


# ============================================================================
# SCHEDULER PROCESS
# ============================================================================

async def run_scheduler():
    """Run the job scheduler for recurring tasks."""
    from zenith.jobs.scheduler import get_scheduler
    
    print("⏰ Starting Zenith job scheduler...")
    scheduler = get_scheduler()
    
    print("✅ Scheduler ready, managing recurring jobs...")
    print("   Press Ctrl+C to stop")
    
    try:
        await scheduler.run()
    except KeyboardInterrupt:
        print("\n👋 Shutting down scheduler...")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "worker":
            # Run as worker
            asyncio.run(run_worker())
        elif command == "scheduler":
            # Run as scheduler
            asyncio.run(run_scheduler())
        elif command == "all":
            # Run worker and scheduler together
            async def run_all():
                await asyncio.gather(
                    run_worker(),
                    run_scheduler()
                )
            asyncio.run(run_all())
        else:
            print("Unknown command. Use: worker, scheduler, or all")
            sys.exit(1)
    else:
        # Run as API server
        import uvicorn
        print("🚀 Starting Zenith Jobs API")
        print("📍 API available at: http://localhost:8000")
        print("📖 Docs at: http://localhost:8000/docs")
        print("\n⚠️  Make sure Redis is running and start workers separately!")
        print("\nWorker commands:")
        print("  python examples/16-background-jobs.py worker")
        print("  python examples/16-background-jobs.py scheduler") 
        print("  python examples/16-background-jobs.py all")
        uvicorn.run(app, host="0.0.0.0", port=8000)