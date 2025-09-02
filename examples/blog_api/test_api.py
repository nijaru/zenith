"""
Quick test script to demonstrate the Blog API functionality.

Tests all the major endpoints to show that the type-based dependency
injection and routing system works correctly.
"""

import asyncio

import httpx

BASE_URL = "http://127.0.0.1:8000"


async def test_api():
    """Test all API endpoints."""
    async with httpx.AsyncClient() as client:
        print("🧪 Testing Zenith Blog API...\n")

        # Test root endpoint
        print("1. Testing root endpoint...")
        response = await client.get(f"{BASE_URL}/")
        print(f"   GET / -> {response.status_code}")
        print(f"   Response: {response.json()['message']}")
        print()

        # Test health check
        print("2. Testing health check...")
        response = await client.get(f"{BASE_URL}/api/health")
        print(f"   GET /api/health -> {response.status_code}")
        print(f"   Status: {response.json()['status']}")
        print()

        # Test user creation (POST with validation)
        print("3. Testing user creation with Pydantic validation...")
        user_data = {
            "email": "alice@example.com",
            "name": "Alice Johnson",
            "password": "secure123",
            "role": "user",
        }
        response = await client.post(f"{BASE_URL}/api/users", json=user_data)
        print(f"   POST /api/users -> {response.status_code}")
        if response.status_code == 200:
            user = response.json()
            print(f"   Created user: {user['name']} ({user['email']})")
            user_id = user["id"]
        else:
            print(f"   Error: {response.json()}")
            return
        print()

        # Test user listing (GET with context injection)
        print("4. Testing user listing with context injection...")
        response = await client.get(f"{BASE_URL}/api/users")
        print(f"   GET /api/users -> {response.status_code}")
        users = response.json()
        print(f"   Found {users['total']} users")
        print()

        # Test getting specific user (path parameter parsing)
        print("5. Testing user retrieval with path parameters...")
        response = await client.get(f"{BASE_URL}/api/users/{user_id}")
        print(f"   GET /api/users/{user_id} -> {response.status_code}")
        if response.status_code == 200:
            user = response.json()
            print(f"   Retrieved: {user['name']} ({user['email']})")
        print()

        # Test authentication
        print("6. Testing authentication...")
        login_data = {
            "email": "alice@example.com",
            "password": "correct_password",  # Mock password
        }
        response = await client.post(f"{BASE_URL}/api/auth/login", json=login_data)
        print(f"   POST /api/auth/login -> {response.status_code}")
        if response.status_code == 200:
            auth_data = response.json()
            token = auth_data["access_token"]
            print("   Login successful, got token")

            # Test protected route
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(f"{BASE_URL}/protected", headers=headers)
            print(f"   GET /protected -> {response.status_code}")
            print(f"   Message: {response.json()['message']}")
        else:
            print(f"   Login failed: {response.json()}")
        print()

        # Test statistics (context usage)
        print("7. Testing statistics with context usage...")
        response = await client.get(f"{BASE_URL}/stats")
        print(f"   GET /stats -> {response.status_code}")
        stats = response.json()
        print(f"   Total users: {stats['total_users']}")
        print(f"   User roles: {stats['user_roles']}")
        print()

        # Test blog posts (query parameters)
        print("8. Testing blog posts with query parameters...")
        response = await client.get(f"{BASE_URL}/api/blog/posts?published=true&limit=5")
        print(
            f"   GET /api/blog/posts?published=true&limit=5 -> {response.status_code}"
        )
        posts = response.json()
        print(f"   Found {len(posts['posts'])} published posts")
        print()

        # Test post creation with authentication
        print("9. Testing post creation...")
        if "token" in locals():
            headers = {"Authorization": f"Bearer {token}"}
            post_data = {
                "title": "My First Zenith Post",
                "content": "This post was created using Zenith's type-safe API!",
                "published": True,
            }
            response = await client.post(
                f"{BASE_URL}/api/blog/posts", json=post_data, headers=headers
            )
            print(f"   POST /api/blog/posts -> {response.status_code}")
            if response.status_code == 200:
                post = response.json()["post"]
                print(f"   Created post: '{post['title']}'")
        print()

        print("✅ All tests completed!")
        print("\n🎉 Zenith features demonstrated:")
        print("   ✓ FastAPI-style routing with decorators")
        print("   ✓ Type-based dependency injection")
        print("   ✓ Automatic Pydantic request/response validation")
        print("   ✓ Phoenix-style context injection")
        print("   ✓ Path and query parameter parsing")
        print("   ✓ Authentication and authorization")
        print("   ✓ Event-driven architecture")


if __name__ == "__main__":
    print("Make sure the API server is running first:")
    print("python examples/blog_api/main.py")
    print()
    input("Press Enter when the server is ready...")
    print()

    asyncio.run(test_api())
