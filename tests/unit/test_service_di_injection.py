"""
Test new constructor injection pattern for Services.

Tests that Services can have dependencies auto-injected via constructor.
"""

import pytest

from zenith import Inject, Service, Zenith
from zenith.testing import TestClient


# Simple services for testing
class ProductService(Service):
    """Service with no dependencies."""

    async def get_product(self, product_id: int):
        return {"id": product_id, "name": f"Product {product_id}"}


class PaymentService(Service):
    """Service with no dependencies."""

    async def charge(self, amount: float):
        return {"amount": amount, "status": "charged"}


class OrderService(Service):
    """Service with constructor-injected dependencies."""

    def __init__(self, products: ProductService, payments: PaymentService):
        self.products = products
        self.payments = payments

    async def create_order(self, product_id: int, amount: float):
        product = await self.products.get_product(product_id)
        payment = await self.payments.charge(amount)
        return {"product": product, "payment": payment, "status": "created"}


@pytest.mark.asyncio
class TestConstructorInjection:
    """Test constructor injection for Services."""

    async def test_simple_service_no_dependencies(self):
        """Test service with no dependencies works."""
        app = Zenith(debug=True)

        @app.get("/product/{product_id}")
        async def get_product(product_id: int, products: ProductService = Inject()):
            return await products.get_product(product_id)

        async with TestClient(app) as client:
            response = await client.get("/product/123")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 123
            assert data["name"] == "Product 123"

    async def test_service_with_constructor_dependencies(self):
        """Test service with constructor-injected dependencies."""
        app = Zenith(debug=True)

        @app.post("/orders")
        async def create_order(
            product_id: int, amount: float, orders: OrderService = Inject()
        ):
            return await orders.create_order(product_id, amount)

        async with TestClient(app) as client:
            response = await client.post(
                "/orders", params={"product_id": 456, "amount": 99.99}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["product"]["id"] == 456
            assert data["payment"]["amount"] == 99.99
            assert data["status"] == "created"

    async def test_nested_service_dependencies(self):
        """Test that service dependencies are resolved recursively."""
        app = Zenith(debug=True)

        # This should work because:
        # 1. OrderService depends on ProductService and PaymentService
        # 2. Framework creates ProductService and PaymentService first
        # 3. Then creates OrderService with those injected

        @app.get("/test")
        async def test_endpoint(orders: OrderService = Inject()):
            # Verify dependencies were injected
            assert orders.products is not None
            assert orders.payments is not None
            assert isinstance(orders.products, ProductService)
            assert isinstance(orders.payments, PaymentService)
            return {"status": "ok"}

        async with TestClient(app) as client:
            response = await client.get("/test")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

    async def test_request_context_in_service(self):
        """Test that services can access request context."""
        app = Zenith(debug=True)

        class AuditService(Service):
            async def get_request_info(self):
                if self.request:
                    return {
                        "has_request": True,
                        "method": self.request.method,
                        "path": self.request.url.path,
                    }
                return {"has_request": False}

        @app.get("/audit")
        async def audit_endpoint(audit: AuditService = Inject()):
            return await audit.get_request_info()

        async with TestClient(app) as client:
            response = await client.get("/audit")
            assert response.status_code == 200
            data = response.json()
            assert data["has_request"] is True
            assert data["method"] == "GET"
            assert data["path"] == "/audit"


@pytest.mark.asyncio
class TestManualServiceUsage:
    """Test that services still work outside of DI context."""

    async def test_manual_instantiation(self):
        """Test creating service manually (for tests, CLI, etc)."""
        products = ProductService()
        payments = PaymentService()
        orders = OrderService(products, payments)

        result = await orders.create_order(789, 49.99)
        assert result["product"]["id"] == 789
        assert result["payment"]["amount"] == 49.99
        assert result["status"] == "created"

    async def test_service_without_request_context(self):
        """Test that services work without request context."""

        class MyService(Service):
            async def do_something(self):
                # Should work even without request
                return {"has_request": self.request is not None}

        service = MyService()
        result = await service.do_something()
        assert result["has_request"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
