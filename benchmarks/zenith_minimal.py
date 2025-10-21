"""Truly minimal Zenith benchmark application - no middleware."""

import os

# Set required env var
os.environ["SECRET_KEY"] = "benchmark-secret-key-for-testing"

from zenith import Zenith

# App with no middleware for fair benchmarking
app = Zenith(debug=False, middleware=[])


@app.get("/")
async def hello_world():
    return {"message": "Hello, World!"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100, log_level="error")
