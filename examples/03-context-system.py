"""
🏗️ Context System - Business Logic Organization

This example demonstrates Zenith's unique Context system:
- Organizing business logic in Context classes
- Clean dependency injection with Context()
- Separation of concerns between routes and business logic
- Event-driven communication between contexts

Run with: python examples/03-context-system.py
Then visit: http://localhost:8003
"""

from datetime import datetime
from typing import List
from zenith import Context, Zenith, Router, Service
from zenith.db import SQLModel, Field

app = Zenith(debug=True)

# ============================================================================
# SQLMODEL MODELS - Modern Unified Approach
# ============================================================================

class ProductBase(SQLModel):
    """Base model for product fields."""
    name: str = Field(min_length=1, max_length=200, description="Product name")
    price: float = Field(gt=0, description="Product price")
    category: str = Field(min_length=1, max_length=100, description="Product category")
    stock: int = Field(ge=0, description="Stock quantity")

class Product(ProductBase):
    """Product model with ID and timestamps."""
    id: int
    created_at: datetime

class ProductCreate(ProductBase):
    """Model for creating products."""
    pass

class OrderBase(SQLModel):
    """Base model for order fields."""
    product_id: int = Field(description="ID of the product being ordered")
    quantity: int = Field(gt=0, description="Quantity to order")

class Order(OrderBase):
    """Order model with ID, total, and timestamp."""
    id: int
    total: float = Field(description="Total order amount")
    created_at: datetime

class OrderCreate(OrderBase):
    """Model for creating orders."""
    pass

# ============================================================================
# BUSINESS LOGIC CONTEXTS - Clean Architecture
# ============================================================================

class ProductService(Service):
    """Product management business logic with modern patterns."""
    
    def __init__(self, container):
        super().__init__(container)
        # In-memory storage for demo (in real apps, use repository pattern)
        self.products = [
            Product(
                id=1, 
                name="Laptop", 
                price=999.99, 
                category="Electronics", 
                stock=10,
                created_at=datetime(2025, 1, 1, 10, 0, 0)
            ),
            Product(
                id=2, 
                name="Coffee Mug", 
                price=12.99, 
                category="Home", 
                stock=25,
                created_at=datetime(2025, 1, 1, 11, 0, 0)
            )
        ]
        self.next_id = 3
    
    async def list_products(self, category: str | None = None) -> List[Product]:
        """List all products, optionally filtered by category."""
        products = self.products
        if category:
            products = [p for p in products if p.category.lower() == category.lower()]
        return products
    
    async def get_product(self, product_id: int) -> Product | None:
        """Get product by ID."""
        return next((p for p in self.products if p.id == product_id), None)
    
    async def create_product(self, product_data: ProductCreate) -> Product:
        """Create a new product."""
        new_product = Product(
            id=self.next_id,
            **product_data.model_dump(),
            created_at=datetime.utcnow()
        )
        
        self.products.append(new_product)
        self.next_id += 1
        
        # Emit event for other contexts
        await self.emit("product.created", {"product_id": new_product.id, "name": new_product.name})
        
        return new_product
    
    async def update_stock(self, product_id: int, quantity_change: int) -> bool:
        """Update product stock (positive = add, negative = remove)."""
        product = next((p for p in self.products if p.id == product_id), None)
        if not product:
            return False
        
        new_stock = product.stock + quantity_change
        if new_stock < 0:
            return False  # Insufficient stock
        
        old_stock = product.stock
        product.stock = new_stock
        
        # Emit stock update event
        await self.emit("product.stock_updated", {
            "product_id": product_id,
            "old_stock": old_stock,
            "new_stock": new_stock
        })
        
        return True


class OrderService(Service):
    """Order management business logic with modern patterns."""
    
    def __init__(self, container):
        super().__init__(container)
        self.orders: List[Order] = []
        self.next_id = 1
        
        # Subscribe to product events
        self.subscribe("product.created", self.on_product_created)
    
    async def create_order(self, order_data: OrderCreate, products: ProductService) -> Order | None:
        """Create a new order."""
        # Get product details
        product = await products.get_product(order_data.product_id)
        if not product:
            raise ValueError(f"Product {order_data.product_id} not found")
        
        # Check stock and update
        if not await products.update_stock(order_data.product_id, -order_data.quantity):
            raise ValueError("Insufficient stock")
        
        # Create order
        total = product.price * order_data.quantity
        new_order = Order(
            id=self.next_id,
            product_id=order_data.product_id,
            quantity=order_data.quantity,
            total=total,
            created_at=datetime.utcnow()
        )
        
        self.orders.append(new_order)
        self.next_id += 1
        
        # Emit order created event
        await self.emit("order.created", {
            "order_id": new_order.id,
            "product_id": order_data.product_id,
            "total": total
        })
        
        return new_order
    
    async def list_orders(self) -> List[Order]:
        """List all orders."""
        return self.orders
    
    def on_product_created(self, data):
        """Handle product created event."""
        print(f"📦 New product created: {data['name']} (ID: {data['product_id']})")


class AnalyticsService(Service):
    """Analytics and reporting with event tracking."""
    
    def __init__(self, container):
        super().__init__(container)
        self.events = []
        
        # Subscribe to all events
        self.subscribe("product.created", self.track_event)
        self.subscribe("product.stock_updated", self.track_event)
        self.subscribe("order.created", self.track_event)
    
    def track_event(self, data):
        """Track all events for analytics."""
        self.events.append({
            "timestamp": datetime.utcnow(),
            "data": data
        })
        print(f"📊 Analytics: Tracked event with data: {data}")
    
    async def get_stats(self) -> dict:
        """Get basic analytics."""
        return {
            "total_events": len(self.events),
            "recent_events": self.events[-5:] if self.events else []
        }


# Register services for dependency injection
app.register_context("products", ProductService)
app.register_context("orders", OrderService)
app.register_context("analytics", AnalyticsService)

# ============================================================================
# ROUTER GROUPING FOR API ORGANIZATION
# ============================================================================

# API v1 router for versioned endpoints
api_v1 = Router(
    prefix="/api/v1"
)

# Products router
products_router = Router(
    prefix="/products"
)

# Orders router  
orders_router = Router(
    prefix="/orders"
)

# Analytics router
analytics_router = Router(
    prefix="/analytics"
)

# ============================================================================
# ROOT ROUTES
# ============================================================================

@app.get("/")
async def root():
    """API overview showcasing Context system and Router grouping."""
    return {
        "message": "Context System Example 🏗️",
        "concept": "Business logic organized in Context classes with Router grouping",
        "benefits": [
            "Clean separation of concerns",
            "Easy testing of business logic",
            "Event-driven architecture",
            "Dependency injection without boilerplate",
            "Organized API structure with Router grouping"
        ],
        "endpoints": {
            "products": "/api/v1/products",
            "orders": "/api/v1/orders", 
            "analytics": "/api/v1/analytics"
        },
        "features": [
            "SQLModel unified models",
            "Router grouping",
            "Context system",
            "Event-driven communication"
        ]
    }

# ============================================================================
# API ROUTES WITH ROUTER GROUPING
# ============================================================================

@products_router.get("/", response_model=List[Product])
async def list_products(
    category: str | None = None,
    products: ProductService = Context()
) -> List[Product]:
    """List products, optionally filtered by category."""
    return await products.list_products(category)

@products_router.post("/", response_model=Product)
async def create_product(
    product_data: ProductCreate,
    products: ProductService = Context()
) -> Product:
    """Create a new product."""
    return await products.create_product(product_data)

@products_router.get("/{product_id}", response_model=Product)
async def get_product(
    product_id: int,
    products: ProductService = Context()
) -> Product:
    """Get product by ID."""
    product = await products.get_product(product_id)
    if not product:
        raise ValueError(f"Product {product_id} not found")
    return product

@orders_router.get("/", response_model=List[Order])
async def list_orders(orders: OrderService = Context()) -> List[Order]:
    """List all orders."""
    return await orders.list_orders()

@orders_router.post("/", response_model=Order)
async def create_order(
    order_data: OrderCreate,
    orders: OrderService = Context(),
    products: ProductService = Context()
) -> Order:
    """Create a new order."""
    return await orders.create_order(order_data, products)

@analytics_router.get("/")
async def get_analytics(analytics: AnalyticsService = Context()):
    """Get analytics data showing event tracking."""
    return await analytics.get_stats()

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy", 
        "example": "03-context-system",
        "patterns": ["Context system", "Router grouping", "SQLModel"]
    }

# ============================================================================
# INCLUDE ROUTERS IN API STRUCTURE
# ============================================================================

# Include feature routers in API v1
api_v1.include_router(products_router)
api_v1.include_router(orders_router)
api_v1.include_router(analytics_router)

# Include API v1 in main app
app.include_router(api_v1)

if __name__ == "__main__":
    print("🏗️ Starting Context System Example")
    print("📍 Server will start at: http://localhost:8003")
    print()
    print("🧪 Try these requests:")
    print("   GET /api/v1/products")
    print("   GET /api/v1/products?category=Electronics")
    print('   POST /api/v1/products {"name": "Tablet", "price": 299.99, "category": "Electronics", "stock": 5}')
    print('   POST /api/v1/orders {"product_id": 1, "quantity": 2}')
    print("   GET /api/v1/orders")
    print("   GET /api/v1/analytics")
    print()
    print("💡 Key Concepts:")
    print("   • Business logic in Context classes")
    print("   • Clean dependency injection with Context()")
    print("   • Event-driven communication between contexts")
    print("   • Router grouping for API organization")
    print("   • SQLModel unified models")
    print("   • Routes focused purely on HTTP concerns")
    print()
    
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8003)