"""
🗂️ Router Grouping Example - Clean API Organization

This example demonstrates Zenith's router grouping capabilities for organizing
large APIs with clean URL structures, shared middleware, and API versioning.

Key Features Demonstrated:
- Nested router patterns for API organization
- API versioning with router prefixes
- Shared middleware and dependencies per router group
- Tag-based OpenAPI documentation organization
- Clean separation of concerns

Run with: python examples/15-router-grouping.py
"""

from pydantic import BaseModel

from zenith import Auth, Inject, Router, Service, Zenith

# ============================================================================
# MODELS
# ============================================================================


class Product(BaseModel):
    """Product model."""

    id: int
    name: str
    price: float
    category: str
    in_stock: bool = True


class User(BaseModel):
    """User model."""

    id: int
    username: str
    email: str
    role: str = "user"


class Order(BaseModel):
    """Order model."""

    id: int
    user_id: int
    product_id: int
    quantity: int
    total: float
    status: str = "pending"


# ============================================================================
# CONTEXTS (Business Logic)
# ============================================================================


class ProductService(Service):
    """Product management business logic."""

    async def list_products(self, category: str | None = None) -> list[Product]:
        """List products, optionally filtered by category."""
        products = [
            Product(id=1, name="Laptop", price=999.99, category="Electronics"),
            Product(id=2, name="Mouse", price=29.99, category="Electronics"),
            Product(id=3, name="Coffee Mug", price=12.99, category="Kitchen"),
            Product(id=4, name="Notebook", price=4.99, category="Office"),
        ]

        if category:
            return [p for p in products if p.category.lower() == category.lower()]
        return products

    async def get_product(self, product_id: int) -> Product | None:
        """Get product by ID."""
        products = await self.list_products()
        return next((p for p in products if p.id == product_id), None)


class UserService(Service):
    """User management business logic."""

    async def list_users(self) -> list[User]:
        """List all users."""
        return [
            User(id=1, username="alice", email="alice@example.com", role="admin"),
            User(id=2, username="bob", email="bob@example.com"),
            User(id=3, username="charlie", email="charlie@example.com"),
        ]

    async def get_user(self, user_id: int) -> User | None:
        """Get user by ID."""
        users = await self.list_users()
        return next((u for u in users if u.id == user_id), None)


class OrderService(Service):
    """Order management business logic."""

    async def list_orders(self, user_id: int | None = None) -> list[Order]:
        """List orders, optionally filtered by user."""
        orders = [
            Order(id=1, user_id=1, product_id=1, quantity=1, total=999.99),
            Order(id=2, user_id=2, product_id=2, quantity=2, total=59.98),
            Order(id=3, user_id=1, product_id=3, quantity=3, total=38.97),
        ]

        if user_id:
            return [o for o in orders if o.user_id == user_id]
        return orders

    async def create_order(self, user_id: int, product_id: int, quantity: int) -> Order:
        """Create a new order."""
        # In a real app, this would calculate price and save to database
        return Order(
            id=99,
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            total=99.99 * quantity,
            status="confirmed",
        )


# ============================================================================
# ROUTER GROUPS
# ============================================================================

# Create the main application
app = Zenith()

# Register contexts
app.register_context("products", ProductContext)
app.register_context("users", UserContext)
app.register_context("orders", OrderContext)


# ----------------------------------------------------------------------------
# API Version 1 Router Group
# ----------------------------------------------------------------------------

api_v1 = Router(prefix="/api/v1")


# Products router within v1
products_v1 = Router(prefix="/products")  # tags=["products-v1"])


@products_v1.get("/", response_model=list[Product])
async def list_products_v1(
    category: str | None = None, products: ProductContext = Inject()
) -> list[Product]:
    """List all products (v1)."""
    return await products.list_products(category)


@products_v1.get("/{product_id}", response_model=Product)
async def get_product_v1(
    product_id: int, products: ProductContext = Inject()
) -> Product:
    """Get product by ID (v1)."""
    product = await products.get_product(product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")
    return product


# Users router within v1
users_v1 = Router(prefix="/users")  # tags=["users-v1"])


@users_v1.get("/", response_model=list[User])
async def list_users_v1(users: UserContext = Inject()) -> list[User]:
    """List all users (v1)."""
    return await users.list_users()


@users_v1.get("/{user_id}", response_model=User)
async def get_user_v1(user_id: int, users: UserContext = Inject()) -> User:
    """Get user by ID (v1)."""
    user = await users.get_user(user_id)
    if not user:
        raise ValueError(f"User {user_id} not found")
    return user


# Include sub-routers in v1
api_v1.include_router(products_v1)
api_v1.include_router(users_v1)


# ----------------------------------------------------------------------------
# API Version 2 Router Group (with enhanced features)
# ----------------------------------------------------------------------------

api_v2 = Router(prefix="/api/v2")  # tags=["v2"])


# Products router within v2 (enhanced)
products_v2 = Router(prefix="/products")  # tags=["products-v2"])


@products_v2.get("/", response_model=list[Product])
async def list_products_v2(
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    products: ProductContext = Inject(),
) -> list[Product]:
    """List products with advanced filtering (v2)."""
    result = await products.list_products(category)

    # Additional v2 filtering
    if min_price is not None:
        result = [p for p in result if p.price >= min_price]
    if max_price is not None:
        result = [p for p in result if p.price <= max_price]

    return result


@products_v2.get("/{product_id}", response_model=Product)
async def get_product_v2(
    product_id: int, include_related: bool = False, products: ProductContext = Inject()
) -> dict:
    """Get product with optional related data (v2)."""
    product = await products.get_product(product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")

    response = product.model_dump()

    if include_related:
        # In v2, we can include related data
        response["reviews"] = [
            {"rating": 5, "comment": "Great product!"},
            {"rating": 4, "comment": "Good value"},
        ]
        response["similar_products"] = [2, 3]

    return response


# Orders router within v2 (new in v2)
orders_v2 = Router(prefix="/orders")  # tags=["orders-v2"])


@orders_v2.get("/", response_model=list[Order])
async def list_orders_v2(
    user_id: int | None = None, orders: OrderContext = Inject()
) -> list[Order]:
    """List orders (v2)."""
    return await orders.list_orders(user_id)


@orders_v2.post("/", response_model=Order)
async def create_order_v2(
    product_id: int,
    quantity: int = 1,
    orders: OrderContext = Inject(),
    current_user: dict = Auth(required=False),  # Mock auth for demo
) -> Order:
    """Create a new order (v2)."""
    # In a real app, current_user would come from authentication
    user_id = 1  # Mock user ID
    return await orders.create_order(user_id, product_id, quantity)


# Include sub-routers in v2
api_v2.include_router(products_v2)
api_v2.include_router(orders_v2)


# ----------------------------------------------------------------------------
# Admin Router Group (separate from API versions)
# ----------------------------------------------------------------------------

admin = Router(prefix="/admin")  # tags=["admin"])


@admin.get("/stats")
async def admin_stats(
    products: ProductContext = Inject(),
    users: UserContext = Inject(),
    orders: OrderContext = Inject(),
) -> dict:
    """Get admin statistics."""
    return {
        "total_products": len(await products.list_products()),
        "total_users": len(await users.list_users()),
        "total_orders": len(await orders.list_orders()),
        "api_versions": ["v1", "v2"],
    }


@admin.get("/health")
async def admin_health() -> dict:
    """Admin health check endpoint."""
    return {
        "status": "healthy",
        "service": "admin",
        "checks": {
            "database": "ok",
            "cache": "ok",
            "queue": "ok",
        },
    }


# ----------------------------------------------------------------------------
# Public Router (no prefix, public endpoints)
# ----------------------------------------------------------------------------

public = Router()  # No prefix for public endpoints


@public.get("/")
async def root() -> dict:
    """API root endpoint."""
    return {
        "name": "E-Commerce API",
        "version": "2.0.0",
        "endpoints": {
            "api_v1": "/api/v1",
            "api_v2": "/api/v2",
            "admin": "/admin",
            "docs": "/docs",
        },
    }


@public.get("/health")
async def health() -> dict:
    """Public health check."""
    return {"status": "healthy"}


# ============================================================================
# INCLUDE ALL ROUTERS IN MAIN APP
# ============================================================================

# The order matters - routers are matched in the order they're included
app.include_router(public)  # Public endpoints (no prefix)
app.include_router(api_v1)  # API v1 endpoints
app.include_router(api_v2)  # API v2 endpoints
app.include_router(admin)  # Admin endpoints


# ============================================================================
# MIDDLEWARE CONFIGURATION (can be per-router or global)
# ============================================================================

# Global middleware
app.add_cors(allow_origins=["*"])
# app.add_compression()  # Would add compression if available

# You could also add middleware to specific routers:
# api_v2.add_middleware(RateLimitMiddleware, limit="100/minute")
# admin.add_middleware(AuthMiddleware, required_role="admin")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("🗂️ Router Grouping Example")
    print("=" * 60)
    print("\n📍 Server starting at: http://localhost:8015")
    print("\n🔗 Available endpoints:")
    print("\n  Public:")
    print("    GET /              - API root")
    print("    GET /health        - Health check")
    print("\n  API v1:")
    print("    GET /api/v1/products      - List products")
    print("    GET /api/v1/products/{id} - Get product")
    print("    GET /api/v1/users         - List users")
    print("    GET /api/v1/users/{id}    - Get user")
    print("\n  API v2 (enhanced):")
    print("    GET /api/v2/products      - List with filtering")
    print("    GET /api/v2/products/{id} - Get with related data")
    print("    GET /api/v2/orders        - List orders")
    print("    POST /api/v2/orders       - Create order")
    print("\n  Admin:")
    print("    GET /admin/stats   - Admin statistics")
    print("    GET /admin/health  - Admin health check")
    print("\n📖 Interactive docs: http://localhost:8015/docs")
    print("\n💡 Benefits of Router Grouping:")
    print("  • Clean URL organization")
    print("  • API versioning support")
    print("  • Shared middleware per group")
    print("  • Better code organization")
    print("  • Easier testing and maintenance")

    app.run(host="127.0.0.1", port=8015, reload=True)
