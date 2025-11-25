"""
Background tasks example for Zenith.

Demonstrates async background task execution.
"""

import asyncio
from datetime import datetime

from pydantic import BaseModel

from zenith import BackgroundTasks, Zenith, background_task

# Create app
app = Zenith()

# Simulated email queue
email_queue = []


# Request models
class RegisterRequest(BaseModel):
    email: str
    name: str


class NewsletterRequest(BaseModel):
    subject: str


# Background task functions
@background_task
async def send_email(to: str, subject: str, body: str):
    """Simulate sending an email (runs in background)."""
    print(f"📧 Sending email to {to}...")
    await asyncio.sleep(2)  # Simulate email API call
    email_queue.append(
        {
            "to": to,
            "subject": subject,
            "body": body,
            "sent_at": datetime.now().isoformat(),
        }
    )
    print(f"Email sent to {to}")


@background_task
async def process_analytics(event: str, data: dict):
    """Process analytics event in background."""
    print(f"[*] Processing analytics: {event}")
    await asyncio.sleep(1)  # Simulate processing
    print(f"Analytics processed: {event}")


@background_task
def cleanup_temp_files(pattern: str):
    """Clean up temporary files (sync task)."""
    print(f"🗑️ Cleaning up files matching: {pattern}")
    # In real app, would delete files here
    print("Cleanup completed")


# Routes
@app.post("/register")
async def register_user(
    data: RegisterRequest, background: BackgroundTasks = BackgroundTasks()
) -> dict:
    """Register user and send welcome email in background."""
    # Create user (simplified)
    user = {
        "id": 1,
        "email": data.email,
        "name": data.name,
        "created_at": datetime.now().isoformat(),
    }

    # Queue welcome email
    background.add_task(
        send_email,
        to=data.email,
        subject="Welcome to Zenith!",
        body=f"Hi {data.name}, welcome to our platform!",
    )

    # Queue analytics
    background.add_task(
        process_analytics,
        event="user_registered",
        data={"user_id": user["id"], "email": data.email},
    )

    # Return immediately (tasks run after response)
    return {"message": "Registration successful", "user": user}


@app.post("/send-newsletter")
async def send_newsletter(
    data: NewsletterRequest, background: BackgroundTasks = BackgroundTasks()
) -> dict:
    """Send newsletter to all users in background."""
    # Mock user list
    users = ["user1@example.com", "user2@example.com", "user3@example.com"]

    # Queue emails for all users
    for email in users:
        background.add_task(
            send_email,
            to=email,
            subject=data.subject,
            body="Check out our latest updates!",
        )

    return {"message": f"Newsletter queued for {len(users)} users", "count": len(users)}


@app.post("/cleanup")
async def trigger_cleanup(
    pattern: str = "*.tmp", background: BackgroundTasks = BackgroundTasks()
) -> dict:
    """Trigger cleanup in background."""
    background.add_task(cleanup_temp_files, pattern=pattern)

    return {"message": f"Cleanup queued for pattern: {pattern}"}


@app.get("/email-queue")
async def get_email_queue() -> dict:
    """Check email queue (for demo purposes)."""
    return {
        "total_sent": len(email_queue),
        "emails": email_queue[-5:],  # Last 5 emails
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "background_tasks": "enabled"}


if __name__ == "__main__":
    import uvicorn

    print("Background Tasks Example")
    print("Try these endpoints:")
    print("  POST /register - Register user and send email in background")
    print("  POST /send-newsletter - Send newsletter to multiple users")
    print("  POST /cleanup - Trigger file cleanup")
    print("  GET /email-queue - Check sent emails")
    uvicorn.run(
        "background_tasks_example:app", host="127.0.0.1", port=8005, reload=True
    )
