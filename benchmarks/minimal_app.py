"""Minimal app without default middleware for comparison."""

import os

os.environ["ZENITH_ENV"] = "production"
os.environ["SECRET_KEY"] = "benchmarksecretkey12345678901234"

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def hello(request):
    return JSONResponse({"message": "Hello, World!"})


app = Starlette(routes=[Route("/", hello)])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8202, log_level="warning")
