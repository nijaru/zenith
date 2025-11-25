"""Development mode app for benchmarking (minimal middleware)."""

import os

os.environ["ZENITH_ENV"] = "development"
os.environ["SECRET_KEY"] = "benchmarksecretkey12345678901234"

from zenith import Zenith

app = Zenith(debug=False)  # No debug to skip RequestLogging


@app.get("/")
async def hello():
    return {"message": "Hello, World!"}


@app.get("/json")
async def json_response():
    return {
        "users": [
            {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"}
            for i in range(10)
        ],
        "total": 10,
        "page": 1,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8203, log_level="warning")
