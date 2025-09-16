"""
Background Task Management Example

This example demonstrates how Zenith's background task system addresses
the production issues identified in yt-text application:

1. Automatic task lifecycle management
2. Error handling and retry logic
3. Progress tracking and monitoring
4. Clean shutdown and resource cleanup

Before: Manual asyncio.Task management with memory leaks
After: Production-ready background processing
"""

import asyncio
import time
from uuid import UUID

from zenith import (
    Zenith,
    BackgroundTaskManager,
    JobQueue,
    Job,
    JobStatus,
    background_task
)

# Create Zenith app
app = Zenith(debug=True)

# Initialize background systems
task_manager = BackgroundTaskManager(max_concurrent_tasks=5)
job_queue = JobQueue(max_workers=3)


# ============================================================================
# PROBLEM 1: Manual asyncio.Task management (yt-text pain point)
# ============================================================================

# ❌ OLD WAY (yt-text pattern - error prone):
"""
class TranscriptionManager:
    def __init__(self):
        self._background_tasks: dict[UUID, asyncio.Task] = {}

    async def start_transcription(self, job_id: UUID):
        # Manual task creation - no error handling
        task = asyncio.create_task(self._process_job_background(job_id))
        self._background_tasks[job_id] = task  # Memory leak potential

    # Manual cleanup required, often forgotten
"""

# ✅ NEW WAY (Zenith v0.3.0):
@background_task(name="video_transcription", timeout=300)
async def process_video_transcription(video_url: str, quality: str = "medium"):
    """
    Process video transcription with automatic error handling and cleanup.

    The @background_task decorator provides:
    - Automatic error logging
    - Timeout handling
    - Memory cleanup
    - Task tracking
    """
    print(f"🎥 Starting transcription: {video_url} (quality: {quality})")

    # Simulate video processing
    for i in range(5):
        await asyncio.sleep(1)
        print(f"📝 Transcription progress: {(i+1)*20}%")

    return {
        "video_url": video_url,
        "transcript": f"Transcribed content for {video_url}",
        "duration": 5.0,
        "word_count": 150
    }


# ============================================================================
# PROBLEM 2: No job persistence or retry logic (yt-text need)
# ============================================================================

async def video_download_job(data: dict, job: Job) -> dict:
    """
    Download video job with progress tracking and retry capability.

    This addresses yt-text's need for:
    - Job persistence across restarts
    - Automatic retry on failure
    - Progress tracking
    - Error recovery
    """
    video_url = data.get("url")
    print(f"📺 Downloading video: {video_url}")

    # Simulate download with progress updates
    for i in range(10):
        if i == 7:
            # Simulate occasional network error (will trigger retry)
            import random
            if random.random() < 0.3:  # 30% chance of failure
                raise Exception("Network timeout during download")

        await asyncio.sleep(0.5)
        job.progress = (i + 1) / 10
        print(f"⬇️  Download progress: {job.progress:.1%}")

        # Update job progress in backend
        await job_queue.backend.update_job(job)

    return {
        "video_url": video_url,
        "file_path": f"/tmp/{video_url.split('/')[-1]}.mp4",
        "size_mb": 25.4,
        "format": "mp4"
    }


async def transcription_job(data: dict, job: Job) -> dict:
    """
    Transcription job with comprehensive error handling.

    Addresses yt-text production needs:
    - Long-running job support
    - Detailed error reporting
    - Resource management
    """
    file_path = data.get("file_path")
    model = data.get("model", "whisper-large")

    print(f"🎙️  Starting transcription: {file_path} (model: {model})")

    try:
        # Simulate transcription processing
        for i in range(8):
            await asyncio.sleep(0.7)
            job.progress = (i + 1) / 8
            print(f"🔤 Transcription progress: {job.progress:.1%}")

            # Update job progress
            await job_queue.backend.update_job(job)

        return {
            "file_path": file_path,
            "model": model,
            "transcript": "This is the transcribed text content...",
            "confidence": 0.94,
            "word_count": 847,
            "processing_time": 5.6
        }

    except Exception as e:
        # Enhanced error reporting for debugging
        error_context = {
            "file_path": file_path,
            "model": model,
            "progress": job.progress,
            "retry_count": job.retry_count
        }
        print(f"❌ Transcription failed: {str(e)}")
        print(f"🔍 Error context: {error_context}")
        raise


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/transcribe/simple")
async def simple_transcription(video_url: str, quality: str = "medium"):
    """
    Simple background task example.

    Uses BackgroundTaskManager for fire-and-forget tasks.
    """
    task_id = await task_manager.add_task(
        process_video_transcription,
        video_url,
        quality,
        name=f"transcribe_{video_url.split('/')[-1]}"
    )

    return {
        "message": "Transcription started",
        "task_id": str(task_id),
        "status_url": f"/transcribe/simple/{task_id}/status"
    }


@app.get("/transcribe/simple/{task_id}/status")
async def get_simple_task_status(task_id: UUID):
    """Get status of a simple background task."""
    status = await task_manager.get_task_status(task_id)
    return status


@app.post("/transcribe/job")
async def create_transcription_job(video_url: str, model: str = "whisper-large"):
    """
    Create a comprehensive transcription job.

    Uses JobQueue for persistent jobs with retry logic.
    """
    # Step 1: Queue video download job
    download_job_id = await job_queue.enqueue_job(
        "video_download",
        data={"url": video_url},
        max_retries=3,
        metadata={"user_id": "demo_user", "priority": "normal"}
    )

    print(f"📋 Queued download job: {download_job_id}")

    return {
        "message": "Transcription pipeline started",
        "download_job_id": str(download_job_id),
        "status_url": f"/transcribe/job/{download_job_id}/status"
    }


@app.get("/transcribe/job/{job_id}/status")
async def get_job_status(job_id: UUID):
    """Get comprehensive job status with progress and error details."""
    job = await job_queue.get_job_status(job_id)

    if not job:
        return {"error": "Job not found"}

    return {
        "id": str(job.id),
        "name": job.name,
        "status": job.status,
        "progress": job.progress,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "retry_count": job.retry_count,
        "max_retries": job.max_retries,
        "error": job.error,
        "result": job.result,
        "metadata": job.metadata
    }


@app.get("/transcribe/jobs")
async def list_jobs(status: JobStatus = None):
    """List all jobs with optional status filtering."""
    jobs = await job_queue.backend.list_jobs(status)

    return {
        "jobs": [
            {
                "id": str(job.id),
                "name": job.name,
                "status": job.status,
                "progress": job.progress,
                "created_at": job.created_at,
                "error": job.error
            }
            for job in jobs
        ],
        "total": len(jobs)
    }


@app.get("/transcribe/tasks")
async def list_tasks():
    """List all running background tasks."""
    tasks = await task_manager.list_tasks()
    return {"tasks": tasks, "total": len(tasks)}


# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

@app.on_event("startup")
async def startup():
    """
    Application startup with proper background system initialization.

    This ensures clean resource management that yt-text was missing.
    """
    print("🚀 Starting Zenith application with background processing...")

    # Register job handlers
    job_queue.register_handler("video_download", video_download_job)
    job_queue.register_handler("transcription", transcription_job)

    # Start background systems
    await task_manager.start()
    await job_queue.start_workers()

    print("✅ Background processing systems ready")


@app.on_event("shutdown")
async def shutdown():
    """
    Clean application shutdown with proper resource cleanup.

    This prevents the resource leaks that yt-text experienced.
    """
    print("🛑 Shutting down background processing systems...")

    # Graceful shutdown of all background systems
    await job_queue.stop_workers()
    await task_manager.stop()

    print("✅ Clean shutdown completed")


# ============================================================================
# DEVELOPMENT & MONITORING
# ============================================================================

@app.get("/")
async def root():
    """Application overview with system status."""
    return {
        "message": "Zenith Background Task Demo",
        "features": [
            "Automatic task lifecycle management",
            "Job persistence with retry logic",
            "Progress tracking and monitoring",
            "Clean shutdown and resource cleanup",
            "Production-ready error handling"
        ],
        "endpoints": {
            "simple_transcription": "POST /transcribe/simple",
            "job_transcription": "POST /transcribe/job",
            "list_jobs": "GET /transcribe/jobs",
            "list_tasks": "GET /transcribe/tasks"
        },
        "improvements_over_yt_text": [
            "❌ Manual asyncio.Task dict → ✅ BackgroundTaskManager",
            "❌ No error handling → ✅ Automatic retry with backoff",
            "❌ Memory leaks → ✅ Automatic cleanup",
            "❌ No progress tracking → ✅ Real-time progress updates",
            "❌ Manual lifecycle → ✅ Startup/shutdown hooks"
        ]
    }


if __name__ == "__main__":
    import uvicorn

    print("🎯 Starting Zenith Background Task Demo")
    print("📖 This addresses all yt-text production pain points:")
    print("   • Automatic task management")
    print("   • Job persistence and retry logic")
    print("   • Progress tracking")
    print("   • Clean resource management")
    print()
    print("🌐 Visit http://localhost:8000 for API overview")
    print("🔧 Try the endpoints to see background processing in action!")

    uvicorn.run(app, host="127.0.0.1", port=8000)