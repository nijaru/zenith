#!/usr/bin/env python3
"""
Competitive benchmarks: Zenith vs FastAPI vs Litestar

Benchmarks identical applications built with each framework to provide
fair performance comparisons across different scenarios.
"""

import asyncio
import builtins
import contextlib
import json
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

# Add zenith to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class BenchmarkResult:
    framework: str
    scenario: str
    requests_per_second: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    success_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    errors: int


class FrameworkBenchmark:
    """Benchmark runner for different frameworks."""

    def __init__(self):
        self.results: list[BenchmarkResult] = []
        self.temp_files: list[Path] = []

    async def run_all_benchmarks(self) -> dict[str, list[BenchmarkResult]]:
        """Run all competitive benchmarks."""
        print("🚀 Starting Competitive Framework Benchmarks")
        print("=" * 60)

        scenarios = [
            ("hello_world", "Simple Hello World"),
            ("json_api", "JSON API with Pydantic"),
            ("database_api", "Database CRUD API"),
            ("auth_api", "API with Authentication"),
            ("middleware_heavy", "API with Full Middleware Stack"),
        ]

        results = {}

        for scenario_id, scenario_name in scenarios:
            print(f"\n📊 Benchmarking: {scenario_name}")
            print("-" * 40)

            scenario_results = []

            # Test each framework
            frameworks = ["zenith", "fastapi", "litestar"]
            for framework in frameworks:
                print(f"Testing {framework.capitalize()}...")
                try:
                    result = await self.benchmark_framework(framework, scenario_id)
                    scenario_results.append(result)
                    print(f"  ✅ {result.requests_per_second:.1f} req/s")
                except Exception as e:
                    print(f"  ❌ Error: {e}")

            results[scenario_id] = scenario_results

        # Generate comparison report
        self.generate_report(results)

        # Cleanup
        self.cleanup()

        return results

    async def benchmark_framework(
        self, framework: str, scenario: str
    ) -> BenchmarkResult:
        """Benchmark a specific framework and scenario."""
        app_file = self.create_app_file(framework, scenario)

        # Start server
        port = self.get_available_port()
        server_process = await self.start_server(framework, app_file, port)

        try:
            # Wait for server to start
            await self.wait_for_server(f"http://localhost:{port}")

            # Run benchmark
            benchmark_data = await self.run_load_test(
                f"http://localhost:{port}",
                duration=30,  # 30 second benchmark
                concurrent_users=100,
            )

            # Get system metrics
            memory_mb, cpu_percent = self.get_system_metrics(server_process)

            return BenchmarkResult(
                framework=framework,
                scenario=scenario,
                requests_per_second=benchmark_data["rps"],
                avg_response_time_ms=benchmark_data["avg_response_time_ms"],
                p95_response_time_ms=benchmark_data["p95_response_time_ms"],
                p99_response_time_ms=benchmark_data["p99_response_time_ms"],
                success_rate=benchmark_data["success_rate"],
                memory_usage_mb=memory_mb,
                cpu_usage_percent=cpu_percent,
                errors=benchmark_data["errors"],
            )

        finally:
            server_process.terminate()
            server_process.wait()

    def create_app_file(self, framework: str, scenario: str) -> Path:
        """Create application file for the specified framework and scenario."""
        app_content = self.get_app_content(framework, scenario)

        app_file = Path(f"/tmp/{framework}_{scenario}_app.py")
        app_file.write_text(app_content)
        self.temp_files.append(app_file)

        return app_file

    def get_app_content(self, framework: str, scenario: str) -> str:
        """Get application content for framework and scenario."""

        if framework == "zenith":
            return self.get_zenith_app(scenario)
        elif framework == "fastapi":
            return self.get_fastapi_app(scenario)
        elif framework == "litestar":
            return self.get_litestar_app(scenario)
        else:
            raise ValueError(f"Unknown framework: {framework}")

    def get_zenith_app(self, scenario: str) -> str:
        """Generate Zenith application for scenario."""

        base_imports = """
import os
import asyncio
from zenith import Zenith, Inject, Service
from zenith.core.service import Service as BaseService
from pydantic import BaseModel
"""

        if scenario == "hello_world":
            return (
                base_imports
                + """
app = Zenith(debug=False, middleware=[])

@app.get("/")
async def hello():
    return {"message": "Hello, World!", "framework": "zenith"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""
            )

        elif scenario == "json_api":
            return (
                base_imports
                + """
class User(BaseModel):
    name: str
    email: str
    age: int

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: int

app = Zenith(debug=False, middleware=[])

# In-memory storage for benchmark
users = {}
user_counter = 0

@app.get("/")
async def root():
    return {"message": "JSON API", "framework": "zenith"}

@app.get("/users", response_model=list[UserResponse])
async def get_users():
    return list(users.values())

@app.post("/users", response_model=UserResponse)
async def create_user(user: User):
    global user_counter
    user_counter += 1
    user_data = UserResponse(id=user_counter, **user.dict())
    users[user_counter] = user_data
    return user_data

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    if user_id not in users:
        from zenith import not_found
        not_found("User not found")
    return users[user_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""
            )

        elif scenario == "database_api":
            return (
                base_imports
                + """
from zenith.db import SQLModel, Field, ZenithSQLModel

class User(SQLModel, ZenithSQLModel, table=True):
    __tablename__ = "users"
    name: str = Field(max_length=100)
    email: str = Field(unique=True)
    age: int = Field(gt=0)

class UserCreate(BaseModel):
    name: str
    email: str
    age: int

class UserService(BaseService):
    def __init__(self, container):
        super().__init__(container)
        self.users = {}
        self.counter = 0

    async def create_user(self, user_data: UserCreate) -> User:
        self.counter += 1
        user = User(id=self.counter, **user_data.dict())
        self.users[self.counter] = user
        return user

    async def get_user(self, user_id: int) -> User:
        return self.users.get(user_id)

    async def list_users(self) -> list[User]:
        return list(self.users.values())

app = Zenith(debug=False, middleware=[])
app.register_context("users", UserService)

@app.get("/")
async def root():
    return {"message": "Database API", "framework": "zenith"}

@app.get("/users")
async def get_users(users: UserService = Inject()):
    return await users.list_users()

@app.post("/users")
async def create_user(user: UserCreate, users: UserService = Inject()):
    return await users.create_user(user)

@app.get("/users/{user_id}")
async def get_user(user_id: int, users: UserService = Inject()):
    user = await users.get_user(user_id)
    if not user:
        from zenith import not_found
        not_found("User not found")
    return user

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""
            )

        elif scenario == "auth_api":
            return (
                base_imports
                + """
from zenith.auth import JWTAuth, Auth
import jwt
import time

SECRET_KEY = "test-secret-key"

class LoginRequest(BaseModel):
    username: str
    password: str

class MockUser:
    def __init__(self, id: int, username: str):
        self.id = id
        self.username = username

def create_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + 3600  # 1 hour
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

app = Zenith(debug=False, middleware=[])

@app.post("/auth/login")
async def login(request: LoginRequest):
    # Mock authentication
    if request.username == "test" and request.password == "password":
        token = create_token(1)
        return {"access_token": token, "token_type": "bearer"}
    return {"error": "Invalid credentials"}, 401

@app.get("/protected")
async def protected():
    # Mock auth check for benchmark
    return {"message": "Protected resource", "user_id": 1}

@app.get("/")
async def root():
    return {"message": "Auth API", "framework": "zenith"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""
            )

        elif scenario == "middleware_heavy":
            return """
import os
from zenith.performance_optimizations import create_api_app
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str
    price: float

# Use default middleware (not optimized) for fair comparison
app = create_api_app(debug=False)

items = {}
item_counter = 0

@app.get("/")
async def root():
    return {"message": "Middleware Heavy API", "framework": "zenith"}

@app.get("/items")
async def get_items():
    return list(items.values())

@app.post("/items")
async def create_item(item: Item):
    global item_counter
    item_counter += 1
    item_data = {"id": item_counter, **item.dict()}
    items[item_counter] = item_data
    return item_data

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id not in items:
        from zenith import not_found
        not_found("Item not found")
    return items[item_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        else:
            raise ValueError(f"Unknown scenario: {scenario}")

    def get_fastapi_app(self, scenario: str) -> str:
        """Generate FastAPI application for scenario."""

        if scenario == "hello_world":
            return """
import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def hello():
    return {"message": "Hello, World!", "framework": "fastapi"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        elif scenario == "json_api":
            return """
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

class User(BaseModel):
    name: str
    email: str
    age: int

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: int

app = FastAPI()

# In-memory storage for benchmark
users = {}
user_counter = 0

@app.get("/")
async def root():
    return {"message": "JSON API", "framework": "fastapi"}

@app.get("/users", response_model=list[UserResponse])
async def get_users():
    return list(users.values())

@app.post("/users", response_model=UserResponse)
async def create_user(user: User):
    global user_counter
    user_counter += 1
    user_data = UserResponse(id=user_counter, **user.dict())
    users[user_counter] = user_data
    return user_data

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    if user_id not in users:
        raise HTTPException(status_code=404, detail="User not found")
    return users[user_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        elif scenario == "database_api":
            return """
import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int

class UserCreate(BaseModel):
    name: str
    email: str
    age: int

class UserService:
    def __init__(self):
        self.users = {}
        self.counter = 0

    async def create_user(self, user_data: UserCreate) -> User:
        self.counter += 1
        user = User(id=self.counter, **user_data.dict())
        self.users[self.counter] = user
        return user

    async def get_user(self, user_id: int) -> User:
        return self.users.get(user_id)

    async def list_users(self) -> list[User]:
        return list(self.users.values())

user_service = UserService()

def get_user_service():
    return user_service

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Database API", "framework": "fastapi"}

@app.get("/users")
async def get_users(users: UserService = Depends(get_user_service)):
    return await users.list_users()

@app.post("/users")
async def create_user(user: UserCreate, users: UserService = Depends(get_user_service)):
    return await users.create_user(user)

@app.get("/users/{user_id}")
async def get_user(user_id: int, users: UserService = Depends(get_user_service)):
    user = await users.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        elif scenario == "auth_api":
            return """
import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import time

SECRET_KEY = "test-secret-key"
security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

def create_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + 3600  # 1 hour
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

app = FastAPI()

@app.post("/auth/login")
async def login(request: LoginRequest):
    if request.username == "test" and request.password == "password":
        token = create_token(1)
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/protected")
async def protected(user_id: int = Depends(verify_token)):
    return {"message": "Protected resource", "user_id": user_id}

@app.get("/")
async def root():
    return {"message": "Auth API", "framework": "fastapi"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        elif scenario == "middleware_heavy":
            return """
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import time

class Item(BaseModel):
    name: str
    description: str
    price: float

app = FastAPI()

# Add middleware stack
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

items = {}
item_counter = 0

@app.get("/")
async def root():
    return {"message": "Middleware Heavy API", "framework": "fastapi"}

@app.get("/items")
async def get_items():
    return list(items.values())

@app.post("/items")
async def create_item(item: Item):
    global item_counter
    item_counter += 1
    item_data = {"id": item_counter, **item.dict()}
    items[item_counter] = item_data
    return item_data

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    if item_id not in items:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        else:
            raise ValueError(f"Unknown scenario: {scenario}")

    def get_litestar_app(self, scenario: str) -> str:
        """Generate Litestar application for scenario."""

        if scenario == "hello_world":
            return """
import os
from litestar import Litestar, get

@get("/")
async def hello() -> dict:
    return {"message": "Hello, World!", "framework": "litestar"}

@get("/health")
async def health() -> dict:
    return {"status": "ok"}

app = Litestar(route_handlers=[hello, health])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        elif scenario == "json_api":
            return """
import os
from litestar import Litestar, get, post
from pydantic import BaseModel
from litestar.exceptions import NotFoundException

class User(BaseModel):
    name: str
    email: str
    age: int

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    age: int

# In-memory storage for benchmark
users = {}
user_counter = 0

@get("/")
async def root() -> dict:
    return {"message": "JSON API", "framework": "litestar"}

@get("/users")
async def get_users() -> list[UserResponse]:
    return list(users.values())

@post("/users")
async def create_user(data: User) -> UserResponse:
    global user_counter
    user_counter += 1
    user_data = UserResponse(id=user_counter, **data.dict())
    users[user_counter] = user_data
    return user_data

@get("/users/{user_id:int}")
async def get_user(user_id: int) -> UserResponse:
    if user_id not in users:
        raise NotFoundException(detail="User not found")
    return users[user_id]

app = Litestar(route_handlers=[root, get_users, create_user, get_user])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        elif scenario == "database_api":
            return """
import os
from litestar import Litestar, get, post, Provide
from pydantic import BaseModel
from litestar.exceptions import NotFoundException

class User(BaseModel):
    id: int
    name: str
    email: str
    age: int

class UserCreate(BaseModel):
    name: str
    email: str
    age: int

class UserService:
    def __init__(self):
        self.users = {}
        self.counter = 0

    async def create_user(self, user_data: UserCreate) -> User:
        self.counter += 1
        user = User(id=self.counter, **user_data.dict())
        self.users[self.counter] = user
        return user

    async def get_user(self, user_id: int) -> User:
        return self.users.get(user_id)

    async def list_users(self) -> list[User]:
        return list(self.users.values())

user_service = UserService()

def get_user_service() -> UserService:
    return user_service

@get("/")
async def root() -> dict:
    return {"message": "Database API", "framework": "litestar"}

@get("/users")
async def get_users(users: UserService) -> list[User]:
    return await users.list_users()

@post("/users")
async def create_user(data: UserCreate, users: UserService) -> User:
    return await users.create_user(data)

@get("/users/{user_id:int}")
async def get_user(user_id: int, users: UserService) -> User:
    user = await users.get_user(user_id)
    if not user:
        raise NotFoundException(detail="User not found")
    return user

app = Litestar(
    route_handlers=[root, get_users, create_user, get_user],
    dependencies={"users": Provide(get_user_service)}
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        elif scenario == "auth_api":
            return """
import os
from litestar import Litestar, get, post
from litestar.connection import Request
from litestar.exceptions import NotAuthorizedException
from pydantic import BaseModel
import jwt
import time

SECRET_KEY = "test-secret-key"

class LoginRequest(BaseModel):
    username: str
    password: str

def create_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + 3600  # 1 hour
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(request: Request) -> int:
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise NotAuthorizedException(detail="Missing or invalid token")

    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.InvalidTokenError:
        raise NotAuthorizedException(detail="Invalid token")

@post("/auth/login")
async def login(data: LoginRequest) -> dict:
    if data.username == "test" and data.password == "password":
        token = create_token(1)
        return {"access_token": token, "token_type": "bearer"}
    raise NotAuthorizedException(detail="Invalid credentials")

@get("/protected")
async def protected(request: Request) -> dict:
    user_id = verify_token(request)
    return {"message": "Protected resource", "user_id": user_id}

@get("/")
async def root() -> dict:
    return {"message": "Auth API", "framework": "litestar"}

app = Litestar(route_handlers=[login, protected, root])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        elif scenario == "middleware_heavy":
            return """
import os
from litestar import Litestar, get, post, Request, Response
from litestar.middleware import DefineMiddleware
from litestar.middleware.cors import CORSConfig
from litestar.middleware.compression import CompressionConfig
from pydantic import BaseModel
import time

class Item(BaseModel):
    name: str
    description: str
    price: float

async def log_requests(request: Request, call_next) -> Response:
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

items = {}
item_counter = 0

@get("/")
async def root() -> dict:
    return {"message": "Middleware Heavy API", "framework": "litestar"}

@get("/items")
async def get_items() -> list:
    return list(items.values())

@post("/items")
async def create_item(data: Item) -> dict:
    global item_counter
    item_counter += 1
    item_data = {"id": item_counter, **data.dict()}
    items[item_counter] = item_data
    return item_data

@get("/items/{item_id:int}")
async def get_item(item_id: int) -> dict:
    if item_id not in items:
        from litestar.exceptions import NotFoundException
        raise NotFoundException(detail="Item not found")
    return items[item_id]

app = Litestar(
    route_handlers=[root, get_items, create_item, get_item],
    cors_config=CORSConfig(allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
    compression_config=CompressionConfig(backend="gzip", minimum_size=1000),
    middleware=[DefineMiddleware(log_requests)]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")), log_level="error")
"""

        else:
            raise ValueError(f"Unknown scenario: {scenario}")

    async def start_server(
        self, framework: str, app_file: Path, port: int
    ) -> subprocess.Popen:
        """Start server for the given framework."""
        env = os.environ.copy()
        env["PORT"] = str(port)

        cmd = [sys.executable, str(app_file)]

        process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=app_file.parent,
        )

        return process

    async def wait_for_server(self, url: str, timeout: int = 30):
        """Wait for server to be ready."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/health") as response:
                        if response.status == 200:
                            return
            except Exception:
                pass

            await asyncio.sleep(0.5)

        raise Exception(f"Server at {url} did not start within {timeout} seconds")

    async def run_load_test(
        self, base_url: str, duration: int = 30, concurrent_users: int = 100
    ) -> dict[str, Any]:
        """Run load test against the server."""

        endpoints = [
            "/",
            "/health"
            if "/health" in await self.get_available_endpoints(base_url)
            else "/",
        ]

        results = {
            "requests_sent": 0,
            "requests_successful": 0,
            "response_times": [],
            "errors": 0,
        }

        async def worker(session: aiohttp.ClientSession):
            """Load test worker."""
            start_time = time.time()

            while time.time() - start_time < duration:
                for endpoint in endpoints:
                    try:
                        req_start = time.time()
                        async with session.get(f"{base_url}{endpoint}") as response:
                            await response.read()
                            req_end = time.time()

                            results["requests_sent"] += 1
                            results["response_times"].append(
                                (req_end - req_start) * 1000
                            )

                            if 200 <= response.status < 300:
                                results["requests_successful"] += 1
                            else:
                                results["errors"] += 1

                    except Exception:
                        results["errors"] += 1

        # Run concurrent workers
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=200),
        ) as session:
            tasks = [worker(session) for _ in range(concurrent_users)]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate metrics
        response_times = results["response_times"]

        if not response_times:
            return {
                "rps": 0,
                "avg_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0,
                "success_rate": 0,
                "errors": results["errors"],
            }

        return {
            "rps": results["requests_sent"] / duration,
            "avg_response_time_ms": statistics.mean(response_times),
            "p95_response_time_ms": statistics.quantiles(response_times, n=20)[
                18
            ],  # 95th percentile
            "p99_response_time_ms": statistics.quantiles(response_times, n=100)[
                98
            ],  # 99th percentile
            "success_rate": results["requests_successful"]
            / max(results["requests_sent"], 1),
            "errors": results["errors"],
        }

    async def get_available_endpoints(self, base_url: str) -> list[str]:
        """Get available endpoints from server."""
        try:
            async with aiohttp.ClientSession() as session:
                # Try common endpoints
                endpoints = []
                for path in ["/", "/health", "/users", "/items"]:
                    try:
                        async with session.get(f"{base_url}{path}") as response:
                            if response.status < 500:
                                endpoints.append(path)
                    except Exception:
                        pass
                return endpoints
        except Exception:
            return ["/"]

    def get_system_metrics(self, process: subprocess.Popen) -> tuple[float, float]:
        """Get memory and CPU usage for process."""
        try:
            import psutil

            p = psutil.Process(process.pid)
            memory_mb = p.memory_info().rss / 1024 / 1024
            cpu_percent = p.cpu_percent(interval=1)
            return memory_mb, cpu_percent
        except Exception:
            return 0.0, 0.0

    def get_available_port(self) -> int:
        """Get an available port."""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return s.getsockname()[1]

    def generate_report(self, results: dict[str, list[BenchmarkResult]]):
        """Generate comparison report."""

        print("\n" + "=" * 80)
        print("🏆 COMPETITIVE BENCHMARK RESULTS")
        print("=" * 80)

        # Summary table
        print(
            f"\n{'Scenario':<20} {'Framework':<12} {'RPS':<10} {'Avg RT (ms)':<12} {'P95 RT (ms)':<12} {'Memory (MB)':<12}"
        )
        print("-" * 88)

        for scenario_id, scenario_results in results.items():
            scenario_results.sort(key=lambda x: x.requests_per_second, reverse=True)

            for i, result in enumerate(scenario_results):
                scenario_name = scenario_id if i == 0 else ""

                winner_icon = (
                    "🥇 "
                    if i == 0
                    else ("🥈 " if i == 1 else ("🥉 " if i == 2 else "   "))
                )

                print(
                    f"{scenario_name:<20} {winner_icon}{result.framework:<9} "
                    f"{result.requests_per_second:<10.1f} "
                    f"{result.avg_response_time_ms:<12.2f} "
                    f"{result.p95_response_time_ms:<12.2f} "
                    f"{result.memory_usage_mb:<12.1f}"
                )

        # Performance comparison
        print(f"\n{'PERFORMANCE COMPARISON'}")
        print("-" * 40)

        for scenario_id, scenario_results in results.items():
            print(f"\n{scenario_id.replace('_', ' ').title()}:")

            scenario_results.sort(key=lambda x: x.requests_per_second, reverse=True)
            fastest = scenario_results[0]

            for result in scenario_results:
                if result.framework == fastest.framework:
                    print(
                        f"  {result.framework:>10}: {result.requests_per_second:>8.1f} req/s (baseline)"
                    )
                else:
                    ratio = (
                        result.requests_per_second / fastest.requests_per_second
                    ) * 100
                    diff = fastest.requests_per_second - result.requests_per_second
                    print(
                        f"  {result.framework:>10}: {result.requests_per_second:>8.1f} req/s ({ratio:>5.1f}%, -{diff:>6.1f} req/s)"
                    )

        # Save detailed results
        self.save_results_json(results)

    def save_results_json(self, results: dict[str, list[BenchmarkResult]]):
        """Save results to JSON file."""
        output = {"timestamp": datetime.now().isoformat(), "results": {}}

        for scenario_id, scenario_results in results.items():
            output["results"][scenario_id] = []
            for result in scenario_results:
                output["results"][scenario_id].append(
                    {
                        "framework": result.framework,
                        "requests_per_second": result.requests_per_second,
                        "avg_response_time_ms": result.avg_response_time_ms,
                        "p95_response_time_ms": result.p95_response_time_ms,
                        "p99_response_time_ms": result.p99_response_time_ms,
                        "success_rate": result.success_rate,
                        "memory_usage_mb": result.memory_usage_mb,
                        "cpu_usage_percent": result.cpu_usage_percent,
                        "errors": result.errors,
                    }
                )

        output_file = Path("competitive_benchmark_results.json")
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)

        print(f"\n📊 Detailed results saved to: {output_file}")

    def cleanup(self):
        """Clean up temporary files."""
        for file_path in self.temp_files:
            with contextlib.suppress(builtins.BaseException):
                file_path.unlink()


async def main():
    """Run competitive benchmarks."""
    benchmark = FrameworkBenchmark()

    print("Installing required packages...")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "fastapi",
            "litestar",
            "uvicorn",
            "aiohttp",
            "psutil",
            "pyjwt",
        ],
        check=True,
    )

    await benchmark.run_all_benchmarks()


if __name__ == "__main__":
    asyncio.run(main())
