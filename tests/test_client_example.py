"""
Test example using Zenith TestClient.
"""

import pytest
from zenith import Zenith
from zenith.testing import TestClient

# Create simple app for testing
app = Zenith(debug=True)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    return {"item_id": item_id, "name": f"Item {item_id}"}


# Async test
@pytest.mark.asyncio
async def test_async_client():
    """Test using async TestClient."""
    async with TestClient(app) as client:
        # Test root endpoint
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}
        
        # Test parametrized endpoint
        response = await client.get("/items/42")
        assert response.status_code == 200
        assert response.json() == {"item_id": 42, "name": "Item 42"}


# Sync test (if using SyncTestClient)
def test_sync_client():
    """Test using sync TestClient (for non-async tests)."""
    from zenith.testing import SyncTestClient
    
    client = SyncTestClient(app)  # Pass the Zenith app directly
    
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
    
    response = client.get("/items/123")
    assert response.status_code == 200
    assert response.json()["item_id"] == 123


if __name__ == "__main__":
    # Run async test manually
    import asyncio
    asyncio.run(test_async_client())
    print("✅ Async test passed")
    
    # Run sync test
    test_sync_client()
    print("✅ Sync test passed")