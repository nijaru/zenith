---
title: Testing API
description: Comprehensive testing utilities for Zenith applications
---

import { Code, Aside } from '@astrojs/starlight/components';

## Testing Overview

Zenith provides comprehensive testing utilities that make it easy to test your APIs, contexts, authentication, and integrations.

## TestClient

The `TestClient` provides an async HTTP client for testing your Zenith applications.

### Basic Usage

```python
from zenith.testing import TestClient
from zenith import Zenith
import pytest

app = Zenith()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.post("/items")
async def create_item(item: dict):
    return {"created": item}

@pytest.mark.asyncio
async def test_api_endpoints():
    async with TestClient(app) as client:
        # Test GET request
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}
        
        # Test POST request
        response = await client.post("/items", json={"name": "test"})
        assert response.status_code == 200
        assert response.json() == {"created": {"name": "test"}}
```

### HTTP Methods

```python
@pytest.mark.asyncio
async def test_all_methods():
    async with TestClient(app) as client:
        # GET request
        response = await client.get("/items")
        
        # POST request with JSON body
        response = await client.post("/items", json={"name": "test"})
        
        # PUT request
        response = await client.put("/items/1", json={"name": "updated"})
        
        # PATCH request
        response = await client.patch("/items/1", json={"name": "patched"})
        
        # DELETE request
        response = await client.delete("/items/1")
        
        # HEAD request
        response = await client.head("/items")
        
        # OPTIONS request
        response = await client.options("/items")
```

### Request Options

```python
@pytest.mark.asyncio
async def test_request_options():
    async with TestClient(app) as client:
        # With headers
        response = await client.get("/protected", headers={
            "Authorization": "Bearer token123",
            "X-Custom-Header": "value"
        })
        
        # With query parameters
        response = await client.get("/search", params={
            "q": "test",
            "limit": 10,
            "offset": 0
        })
        
        # With cookies
        response = await client.get("/", cookies={
            "session_id": "abc123"
        })
        
        # With timeout
        response = await client.get("/slow", timeout=30.0)
```

### File Uploads

```python
@pytest.mark.asyncio
async def test_file_upload():
    async with TestClient(app) as client:
        # Single file upload
        files = {
            "file": ("test.txt", b"file content", "text/plain")
        }
        response = await client.post("/upload", files=files)
        
        # Multiple files
        files = {
            "files": [
                ("file1.txt", b"content 1", "text/plain"),
                ("file2.txt", b"content 2", "text/plain")
            ]
        }
        response = await client.post("/upload-multiple", files=files)
        
        # Form data with files
        data = {"name": "test"}
        files = {"file": ("test.txt", b"content", "text/plain")}
        response = await client.post("/form-upload", data=data, files=files)
```

### Response Assertions

```python
@pytest.mark.asyncio
async def test_response_assertions():
    async with TestClient(app) as client:
        response = await client.get("/api/user/123")
        
        # Status code
        assert response.status_code == 200
        
        # Headers
        assert "Content-Type" in response.headers
        assert response.headers["Content-Type"] == "application/json"
        
        # JSON response
        data = response.json()
        assert data["id"] == 123
        assert data["name"] == "John Doe"
        
        # Text response
        text = response.text
        assert "Welcome" in text
        
        # Raw bytes
        content = response.content
        assert isinstance(content, bytes)
        
        # Cookies
        assert "session_id" in response.cookies
```

## Testing with Authentication

### MockAuth Context Manager

```python
from zenith.testing import TestClient, MockAuth
from zenith.auth import get_current_user

@app.get("/profile")
async def get_profile(user = Depends(get_current_user)):
    return {"user_id": user.id, "email": user.email}

@pytest.mark.asyncio
async def test_authenticated_endpoint():
    async with TestClient(app) as client:
        # Test without authentication (should fail)
        response = await client.get("/profile")
        assert response.status_code == 401
        
        # Test with mock authentication
        with MockAuth(user={"id": 123, "email": "test@example.com"}):
            response = await client.get("/profile")
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == 123
            assert data["email"] == "test@example.com"
```

### JWT Token Testing

```python
from zenith.auth import create_access_token

@pytest.mark.asyncio
async def test_with_jwt_token():
    # Create test token
    token = create_access_token({
        "sub": "test@example.com",
        "user_id": 123,
        "role": "admin"
    })
    
    async with TestClient(app) as client:
        response = await client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
```

### Role-Based Testing

```python
@pytest.mark.asyncio
async def test_role_based_access():
    async with TestClient(app) as client:
        # Test as regular user
        with MockAuth(user={"id": 1, "role": "user"}):
            response = await client.delete("/users/2")
            assert response.status_code == 403  # Forbidden
        
        # Test as admin
        with MockAuth(user={"id": 1, "role": "admin"}):
            response = await client.delete("/users/2")
            assert response.status_code == 204  # Success
```

## Context Testing

Test business logic independently of HTTP endpoints.

### TestContext

```python
from zenith.testing import TestContext
from app.contexts.users import UserContext
from app.models.user import UserCreate

@pytest.mark.asyncio
async def test_user_context():
    async with TestContext(UserContext) as users:
        # Test user creation
        user_data = UserCreate(
            email="test@example.com",
            name="Test User",
            password="securepass123"
        )
        
        user = await users.create_user(user_data)
        
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.id is not None
        
        # Test user retrieval
        found_user = await users.get_user_by_email("test@example.com")
        assert found_user is not None
        assert found_user.id == user.id
```

### Context with Dependencies

```python
from unittest.mock import Mock, AsyncMock
from app.contexts.orders import OrderContext
from app.services.email import EmailService
from app.services.payment import PaymentService

@pytest.mark.asyncio
async def test_order_context_with_mocks():
    # Create mock services
    mock_email = Mock(spec=EmailService)
    mock_email.send_order_confirmation = AsyncMock()
    
    mock_payment = Mock(spec=PaymentService)
    mock_payment.process_payment = AsyncMock(return_value={
        "id": "pay_123",
        "status": "completed"
    })
    
    # Test with mocked dependencies
    async with TestContext(OrderContext, {
        'email_service': mock_email,
        'payment_service': mock_payment
    }) as orders:
        order_data = OrderCreate(
            items=[{"product_id": 1, "quantity": 2}],
            total=29.99
        )
        
        order = await orders.create_order(order_data, user_id=123)
        
        assert order.total == 29.99
        assert order.user_id == 123
        
        # Verify mocks were called
        mock_payment.process_payment.assert_called_once()
        mock_email.send_order_confirmation.assert_called_once()
```

### Database Testing

```python
import pytest
from zenith.testing import TestContext
from zenith.db import create_engine, SQLModel

@pytest.fixture
async def test_db():
    """Create test database."""
    engine = create_engine("sqlite:///:memory:")  # In-memory database
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.mark.asyncio
async def test_user_persistence(test_db):
    async with TestContext(UserContext, db_engine=test_db) as users:
        # Create user
        user = await users.create_user(UserCreate(
            email="test@example.com",
            name="Test User"
        ))
        
        # Verify persistence
        found_user = await users.get_user(user.id)
        assert found_user.email == "test@example.com"
        
        # Test update
        updated = await users.update_user(user.id, {"name": "Updated Name"})
        assert updated.name == "Updated Name"
        
        # Test deletion
        deleted = await users.delete_user(user.id)
        assert deleted is True
        
        # Verify deletion
        not_found = await users.get_user(user.id)
        assert not_found is None
```

## WebSocket Testing

```python
from zenith.testing import TestClient

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")

@pytest.mark.asyncio
async def test_websocket():
    async with TestClient(app) as client:
        async with client.websocket_connect("/ws") as websocket:
            # Send message
            await websocket.send_text("Hello WebSocket")
            
            # Receive response
            response = await websocket.receive_text()
            assert response == "Echo: Hello WebSocket"
            
            # Send JSON
            await websocket.send_json({"type": "message", "data": "test"})
            response_data = await websocket.receive_json()
            assert "Echo:" in str(response_data)
```

## Fixtures and Test Utilities

### Common Test Fixtures

```python
import pytest
from zenith.testing import TestClient
from app.main import app
from app.models.user import User
from app.contexts.users import UserContext

@pytest.fixture
async def client():
    """Test client fixture."""
    async with TestClient(app) as c:
        yield c

@pytest.fixture
async def test_user():
    """Create test user."""
    async with TestContext(UserContext) as users:
        user = await users.create_user(UserCreate(
            email="test@example.com",
            name="Test User",
            password="password123"
        ))
        yield user
        # Cleanup happens automatically

@pytest.fixture
async def auth_headers(test_user):
    """Create authentication headers for test user."""
    token = create_access_token({
        "sub": test_user.email,
        "user_id": test_user.id
    })
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_with_fixtures(client, test_user, auth_headers):
    """Test using fixtures."""
    response = await client.get("/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
```

### Test Data Factories

```python
from dataclasses import dataclass
from typing import Optional
import random
import string

class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def random_email() -> str:
        """Generate random email."""
        username = ''.join(random.choices(string.ascii_lowercase, k=8))
        return f"{username}@example.com"
    
    @staticmethod
    def create_user_data(
        email: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs
    ) -> UserCreate:
        """Create user test data."""
        return UserCreate(
            email=email or TestDataFactory.random_email(),
            name=name or "Test User",
            password="password123",
            **kwargs
        )
    
    @staticmethod
    def create_post_data(
        title: Optional[str] = None,
        **kwargs
    ) -> PostCreate:
        """Create post test data."""
        return PostCreate(
            title=title or f"Test Post {random.randint(1, 1000)}",
            content="This is test content for the post.",
            **kwargs
        )

@pytest.mark.asyncio
async def test_with_factory_data():
    async with TestContext(UserContext) as users:
        # Create multiple test users
        for _ in range(5):
            user_data = TestDataFactory.create_user_data()
            user = await users.create_user(user_data)
            assert user.email.endswith("@example.com")
```

## Error Testing

```python
@pytest.mark.asyncio
async def test_error_handling():
    async with TestClient(app) as client:
        # Test 404 error
        response = await client.get("/nonexistent")
        assert response.status_code == 404
        
        # Test validation error
        response = await client.post("/users", json={
            "email": "invalid-email",  # Invalid format
            "name": ""  # Empty name
        })
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data
        
        # Test authentication error
        response = await client.get("/protected")
        assert response.status_code == 401
        
        # Test authorization error
        with MockAuth(user={"id": 1, "role": "user"}):
            response = await client.delete("/admin/users/1")
            assert response.status_code == 403

@pytest.mark.asyncio
async def test_context_error_handling():
    async with TestContext(UserContext) as users:
        # Test duplicate email error
        user_data = TestDataFactory.create_user_data()
        await users.create_user(user_data)
        
        with pytest.raises(ValueError, match="Email already registered"):
            await users.create_user(user_data)  # Same email
        
        # Test not found error
        user = await users.get_user(99999)  # Non-existent ID
        assert user is None
```

## Performance Testing

```python
import time
import asyncio

@pytest.mark.asyncio
async def test_endpoint_performance():
    async with TestClient(app) as client:
        # Test response time
        start_time = time.time()
        response = await client.get("/api/data")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second

@pytest.mark.asyncio
async def test_concurrent_requests():
    async with TestClient(app) as client:
        # Test multiple concurrent requests
        async def make_request():
            return await client.get("/api/data")
        
        # Make 10 concurrent requests
        start_time = time.time()
        responses = await asyncio.gather(*[make_request() for _ in range(10)])
        end_time = time.time()
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Should handle concurrency well
        assert (end_time - start_time) < 5.0  # All 10 requests within 5 seconds
```

## Integration Testing

```python
import pytest
from zenith.testing import TestClient
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_full_user_workflow():
    """Test complete user registration and login flow."""
    async with TestClient(app) as client:
        # Register user
        register_data = {
            "email": "newuser@example.com",
            "name": "New User",
            "password": "securepass123"
        }
        response = await client.post("/auth/register", json=register_data)
        assert response.status_code == 201
        user_data = response.json()
        
        # Login
        login_data = {
            "email": "newuser@example.com",
            "password": "securepass123"
        }
        response = await client.post("/auth/login", json=login_data)
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        
        # Use token to access protected endpoint
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        response = await client.get("/profile", headers=headers)
        assert response.status_code == 200
        profile_data = response.json()
        assert profile_data["email"] == "newuser@example.com"

@pytest.mark.asyncio
async def test_external_service_integration():
    """Test integration with external services."""
    with patch('app.services.email.EmailService.send_email') as mock_send:
        mock_send.return_value = AsyncMock()
        
        async with TestClient(app) as client:
            # Test endpoint that sends email
            response = await client.post("/auth/forgot-password", json={
                "email": "test@example.com"
            })
            
            assert response.status_code == 200
            # Verify external service was called
            mock_send.assert_called_once()
```

## Test Configuration

### pytest.ini

```ini
[tool:pytest]
addopts = 
    -v
    --tb=short
    --asyncio-mode=auto
    --cov=app
    --cov-report=html
    --cov-report=term-missing
testpaths = tests
python_files = test_*.py
python_functions = test_*
python_classes = Test*
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    auth: marks tests that require authentication
```

### Test Environment

```python
# conftest.py
import pytest
import os
from zenith.testing import TestClient
from app.main import create_app

# Set test environment
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

@pytest.fixture(scope="session")
async def app():
    """Create test application."""
    return create_app(testing=True)

@pytest.fixture
async def client(app):
    """Create test client."""
    async with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
async def setup_test_database():
    """Set up clean database for each test."""
    # Setup code
    yield
    # Cleanup code
```

<Aside type="tip">
  **Testing Strategy**: Use unit tests for contexts, integration tests for full workflows, and mocks for external services to create a comprehensive test suite.
</Aside>

Zenith's testing utilities provide everything you need to thoroughly test your applications, from individual functions to complete user workflows. The async-first design ensures your tests accurately reflect real-world usage patterns.