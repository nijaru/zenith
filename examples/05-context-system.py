"""
🏗️ Modern Database Patterns - Modern Business Logic

This example demonstrates Zenith's Modern DX features:
- Enhanced Model with database operations
- Enhanced dependency injection with clean shortcuts
- Modern query patterns and automatic session management
- Zero-config setup with intelligent defaults

Run with: python examples/03-context-system.py
Then visit: http://localhost:8003
"""

from datetime import datetime

from zenith import Router, Zenith
from zenith.db import (
    Field,
)
from zenith.db import (
    ZenithModel as Model,
)  # Enhanced model with where/find/create methods

# 🎯 Zero-config setup - just works!
app = Zenith()

# ============================================================================
# MODERN MODELS - Intuitive Database Operations
# ============================================================================


class Product(Model, table=True):
    """Modern Product model with database operations."""

    id: int | None = Field(primary_key=True)
    name: str = Field(min_length=1, max_length=200, description="Product name")
    price: float = Field(gt=0, description="Product price")
    category: str = Field(min_length=1, max_length=100, description="Product category")
    stock: int = Field(ge=0, description="Stock quantity")
    created_at: datetime | None = Field(default_factory=datetime.utcnow)


class Order(Model, table=True):
    """Modern Order model with database operations."""

    id: int | None = Field(primary_key=True)
    product_id: int = Field(description="ID of the product being ordered")
    quantity: int = Field(gt=0, description="Quantity to order")
    total: float = Field(description="Total order amount")
    created_at: datetime | None = Field(default_factory=datetime.utcnow)


# ============================================================================
# SAMPLE DATA - Create via API calls or add startup event handler
# ============================================================================

# Sample products data for testing (create via POST /api/v1/products)
SAMPLE_PRODUCTS = [
    {
        "name": "Laptop",
        "price": 999.99,
        "category": "Electronics",
        "stock": 10,
    },
    {
        "name": "Coffee Mug",
        "price": 12.99,
        "category": "Home",
        "stock": 25,
    },
    {
        "name": "Wireless Mouse",
        "price": 29.99,
        "category": "Electronics",
        "stock": 15,
    },
]

# ============================================================================
# ROUTER GROUPING FOR API ORGANIZATION
# ============================================================================

# API v1 router for versioned endpoints
api_v1 = Router(prefix="/api/v1")

# Products router
products_router = Router(prefix="/products")

# Orders router
orders_router = Router(prefix="/orders")

# ============================================================================
# ROOT ROUTES
# ============================================================================


@app.get("/")
async def root():
    """API overview showcasing Modern DX and Router grouping."""
    return {
        "message": "Modern Database Patterns 🏗️",
        "concept": "Database database operations with zero-config setup",
        "benefits": [
            "85% less boilerplate code",
            "Modern query patterns: User.where().order_by().limit()",
            "Automatic session management",
            "Enhanced dependency injection with DB shortcut",
            "Zero-config setup with intelligent defaults",
        ],
        "endpoints": {
            "products": "/api/v1/products",
            "orders": "/api/v1/orders",
        },
        "features": [
            "Enhanced Model with clean patterns",
            "Router grouping",
            "Enhanced dependency injection",
            "Automatic 404 handling",
        ],
    }


# ============================================================================
# API ROUTES WITH MODERN DATABASE OPERATIONS
# ============================================================================


@products_router.get("/", response_model=list[Product])
async def list_products(category: str | None = None) -> list[Product]:
    """List products with Modern query patterns."""
    if category:
        # Clean: Product.where(category=category) - synchronous chaining
        query = Product.where(category=category)
        products = await query.order_by("-created_at").all()
    else:
        # Clean: Product.all() - get all products
        products = await Product.order_by("-created_at").all()
    return products


@products_router.post("/", response_model=Product)
async def create_product(product_data: dict) -> Product:
    """Create product using Modern patterns."""
    # Clean: Product.create() - no session management!
    product = await Product.create(**product_data)
    return product


@products_router.get("/{product_id}", response_model=Product)
async def get_product(product_id: int) -> Product:
    """Get product by ID with automatic 404 handling."""
    # Clean: automatic 404 if not found
    product = await Product.find_or_404(product_id)
    return product


@orders_router.get("/", response_model=list[Order])
async def list_orders() -> list[Order]:
    """List all orders with Modern patterns."""
    # Clean: Order.all() with automatic ordering
    orders = await Order.order_by("-created_at").all()
    return orders


@orders_router.post("/", response_model=Order)
async def create_order(order_data: dict) -> Order:
    """Create order with Modern business logic."""
    product_id = order_data["product_id"]
    quantity = order_data["quantity"]

    # Clean: Product.find_or_404()
    product = await Product.find_or_404(product_id)

    # Check stock
    if product.stock < quantity:
        raise ValueError("Insufficient stock")

    # Calculate total
    total = product.price * quantity

    # Clean: Order.create()
    order = await Order.create(product_id=product_id, quantity=quantity, total=total)

    # Update product stock
    await product.update(stock=product.stock - quantity)

    return order


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "example": "03-modern-patterns",
        "patterns": ["Modern DX", "Enhanced Model", "Router grouping", "Enhanced DI"],
    }


# ============================================================================
# INCLUDE ROUTERS IN API STRUCTURE
# ============================================================================

# Include feature routers in API v1
api_v1.include_router(products_router)
api_v1.include_router(orders_router)

# Include API v1 in main app
app.include_router(api_v1)

if __name__ == "__main__":
    print("🏗️ Starting Modern Database Patterns Example")
    print("📍 Server will start at: http://localhost:8003")
    print()
    print("🧪 Try these Modern requests:")
    print("   GET /api/v1/products")
    print("   GET /api/v1/products?category=Electronics")
    print(
        '   POST /api/v1/products {"name": "Tablet", "price": 299.99, "category": "Electronics", "stock": 5}'
    )
    print('   POST /api/v1/orders {"product_id": 1, "quantity": 2}')
    print("   GET /api/v1/orders")
    print("   GET /api/v1/products/1")
    print()
    print("💡 Modern DX Features:")
    print("   • Enhanced Model with database operations")
    print("   • Product.where(category='Electronics').order_by('-created_at').all()")
    print("   • Product.find_or_404(id) - automatic 404 handling")
    print("   • Product.create(**data) - no session management")
    print("   • No session management - ZenithModel handles it automatically")
    print("   • Zero-config setup with intelligent defaults")
    print("   • Router grouping for API organization")
    print()
    print("📝 To add sample data, POST to /api/v1/products with:")
    print("   ", SAMPLE_PRODUCTS[0])
    print()

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8003)
