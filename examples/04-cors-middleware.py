"""
CORS middleware example for Zenith.

Demonstrates how to enable cross-origin requests.
"""

from zenith import Zenith
from zenith.middleware import CORSMiddleware

# Create app with CORS for development
app = Zenith()

# Add CORS middleware - allows all origins in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],  # Common frontend dev ports
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
    max_age_secs=3600,
)


@app.get("/api/data")
async def get_data():
    """API endpoint accessible from browser."""
    return {"message": "This API supports CORS", "data": [1, 2, 3, 4, 5]}


@app.post("/api/users")
async def create_user(name: str, email: str):
    """Create user endpoint."""
    return {"id": 1, "name": name, "email": email}


@app.get("/health")
async def health():
    return {"status": "healthy", "cors": "enabled"}


if __name__ == "__main__":
    import uvicorn

    print("🌐 CORS-enabled API running at http://localhost:8004")
    print("Test from browser console:")
    print(
        "  fetch('http://localhost:8004/api/data').then(r => r.json()).then(console.log)"
    )
    uvicorn.run(app, host="127.0.0.1", port=8004, reload=False)
