---
title: Context System
description: Organize business logic with clean contexts
---

import { Aside, Code } from '@astrojs/starlight/components';

## What are Contexts?

Contexts are Zenith's way of organizing business logic. They provide a clean separation between your domain logic and web layer, making your code more maintainable, testable, and reusable.

<Aside type="note">
  **Think of Contexts as service layers** that encapsulate all business logic related to a specific domain area of your application.
</Aside>

## Why Use Contexts?

### Traditional Approach (Without Contexts)

```python
# ❌ Business logic mixed with web layer
@app.post("/users")
async def create_user(user_data: UserCreate, db: Session):
    # Validation logic
    if len(user_data.password) < 8:
        raise HTTPException(400, "Password too short")
    
    # Check if email exists
    existing = db.query(User).filter_by(email=user_data.email).first()
    if existing:
        raise HTTPException(400, "Email already exists")
    
    # Hash password
    password_hash = bcrypt.hashpw(user_data.password.encode(), bcrypt.gensalt())
    
    # Create user
    user = User(
        email=user_data.email,
        password_hash=password_hash
    )
    db.add(user)
    db.commit()
    
    # Send welcome email
    send_email(user.email, "Welcome!")
    
    # Log event
    logger.info(f"User created: {user.email}")
    
    return user
```

### Zenith Approach (With Contexts)

```python
# ✅ Clean separation of concerns
class UserContext(Context):
    """Encapsulates all user-related business logic."""
    
    async def create_user(self, user_data: UserCreate) -> User:
        await self._validate_password(user_data.password)
        await self._ensure_email_unique(user_data.email)
        
        user = await self._save_user(user_data)
        await self._send_welcome_email(user)
        await self._log_user_creation(user)
        
        return user

# Route handler stays simple
@app.post("/users")
async def create_user(
    user_data: UserCreate,
    users: UserContext = Depends()
) -> User:
    return await users.create_user(user_data)
```

## Creating Contexts

### Basic Context

```python
from zenith import Context
from typing import List, Optional

class ProductContext(Context):
    """Handles all product-related business logic."""
    
    async def list_products(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Product]:
        """List products with optional filtering."""
        query = select(Product)
        if category:
            query = query.where(Product.category == category)
        
        products = await self.db.exec(query.limit(limit))
        return products.all()
    
    async def get_product(self, product_id: int) -> Optional[Product]:
        """Get a single product by ID."""
        return await self.db.get(Product, product_id)
    
    async def create_product(self, data: ProductCreate) -> Product:
        """Create a new product."""
        product = Product(**data.dict())
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        return product
    
    async def update_stock(self, product_id: int, quantity: int) -> Product:
        """Update product stock level."""
        product = await self.get_product(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")
        
        product.stock_quantity = quantity
        product.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(product)
        
        # Emit event for other systems
        await self.events.emit("product.stock_updated", {
            "product_id": product_id,
            "new_quantity": quantity
        })
        
        return product
```

### Context with Dependencies

Contexts can depend on other contexts and services:

```python
class OrderContext(Context):
    """Handles order processing logic."""
    
    def __init__(
        self,
        products: ProductContext = Depends(),
        payments: PaymentContext = Depends(),
        notifications: NotificationService = Depends()
    ):
        super().__init__()
        self.products = products
        self.payments = payments
        self.notifications = notifications
    
    async def create_order(self, order_data: OrderCreate) -> Order:
        """Create a new order with full processing."""
        # Validate products exist and have stock
        for item in order_data.items:
            product = await self.products.get_product(item.product_id)
            if not product:
                raise ValueError(f"Product {item.product_id} not found")
            if product.stock_quantity < item.quantity:
                raise ValueError(f"Insufficient stock for {product.name}")
        
        # Calculate totals
        total = await self._calculate_total(order_data.items)
        
        # Process payment
        payment = await self.payments.process_payment(
            amount=total,
            payment_method=order_data.payment_method
        )
        
        # Create order
        order = Order(
            customer_id=order_data.customer_id,
            items=order_data.items,
            total=total,
            payment_id=payment.id,
            status=OrderStatus.CONFIRMED
        )
        
        self.db.add(order)
        await self.db.commit()
        
        # Update stock
        for item in order_data.items:
            await self.products.update_stock(
                item.product_id,
                -item.quantity
            )
        
        # Send confirmation
        await self.notifications.send_order_confirmation(order)
        
        return order
```

## Context Patterns

### Repository Pattern

Separate data access from business logic:

```python
class UserRepository:
    """Data access layer for users."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def find_by_email(self, email: str) -> Optional[User]:
        statement = select(User).where(User.email == email)
        return await self.db.exec(statement).first()
    
    async def find_by_id(self, user_id: int) -> Optional[User]:
        return await self.db.get(User, user_id)
    
    async def save(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

class UserContext(Context):
    """Business logic layer for users."""
    
    def __init__(self, repo: UserRepository = Depends()):
        self.repo = repo
    
    async def get_user_by_email(self, email: str) -> User:
        user = await self.repo.find_by_email(email)
        if not user:
            raise UserNotFoundError(f"No user with email {email}")
        return user
```

### Event-Driven Contexts

Contexts can emit and listen to events:

```python
class NotificationContext(Context):
    """Handles notification logic."""
    
    async def on_startup(self):
        """Subscribe to events on startup."""
        self.events.subscribe("user.created", self.send_welcome_email)
        self.events.subscribe("order.completed", self.send_order_email)
        self.events.subscribe("payment.failed", self.send_payment_failed_email)
    
    async def send_welcome_email(self, event: Event):
        """Send welcome email when user is created."""
        user = event.data
        await self.email_service.send(
            to=user.email,
            subject="Welcome to our platform!",
            template="welcome",
            context={"user": user}
        )
```

## Testing Contexts

Contexts are easy to test in isolation:

```python
import pytest
from zenith.testing import TestContext

@pytest.mark.asyncio
async def test_user_creation():
    """Test user creation logic."""
    async with TestContext(UserContext) as users:
        # Test data
        user_data = UserCreate(
            email="test@example.com",
            password="securepassword123",
            name="Test User"
        )
        
        # Create user
        user = await users.create_user(user_data)
        
        # Assertions
        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.id is not None
        
        # Verify password is hashed
        assert user.password_hash != "securepassword123"

@pytest.mark.asyncio
async def test_duplicate_email():
    """Test that duplicate emails are rejected."""
    async with TestContext(UserContext) as users:
        # Create first user
        await users.create_user(UserCreate(
            email="test@example.com",
            password="password123",
            name="First User"
        ))
        
        # Try to create second user with same email
        with pytest.raises(ValueError, match="already exists"):
            await users.create_user(UserCreate(
                email="test@example.com",
                password="password456",
                name="Second User"
            ))
```

## Advanced Patterns

### Context Composition

Combine multiple contexts for complex operations:

```python
class CheckoutContext(Context):
    """Orchestrates the checkout process."""
    
    def __init__(
        self,
        cart: CartContext = Depends(),
        inventory: InventoryContext = Depends(),
        payment: PaymentContext = Depends(),
        shipping: ShippingContext = Depends(),
        email: EmailContext = Depends()
    ):
        super().__init__()
        self.cart = cart
        self.inventory = inventory
        self.payment = payment
        self.shipping = shipping
        self.email = email
    
    async def process_checkout(
        self,
        user_id: int,
        payment_info: PaymentInfo,
        shipping_info: ShippingInfo
    ) -> Order:
        """Complete checkout process."""
        async with self.db.transaction():
            # Get cart items
            cart_items = await self.cart.get_items(user_id)
            
            # Reserve inventory
            reservations = await self.inventory.reserve_items(cart_items)
            
            try:
                # Process payment
                payment = await self.payment.charge(
                    amount=self.calculate_total(cart_items),
                    payment_info=payment_info
                )
                
                # Create order
                order = await self.create_order(
                    user_id=user_id,
                    items=cart_items,
                    payment_id=payment.id
                )
                
                # Schedule shipping
                shipment = await self.shipping.schedule(
                    order=order,
                    shipping_info=shipping_info
                )
                
                # Clear cart
                await self.cart.clear(user_id)
                
                # Send confirmation
                await self.email.send_order_confirmation(order)
                
                return order
                
            except PaymentFailedError:
                # Release inventory reservations
                await self.inventory.release_reservations(reservations)
                raise
```

### Context Middleware

Add cross-cutting concerns to all context methods:

```python
class AuditedContext(Context):
    """Base context with audit logging."""
    
    async def __call__(self, method_name: str, *args, **kwargs):
        """Log all context method calls."""
        start_time = time.time()
        user = self.request.user if hasattr(self.request, 'user') else None
        
        try:
            result = await super().__call__(method_name, *args, **kwargs)
            
            # Log success
            await self.audit_log.create(
                user_id=user.id if user else None,
                action=f"{self.__class__.__name__}.{method_name}",
                status="success",
                duration=time.time() - start_time
            )
            
            return result
            
        except Exception as e:
            # Log failure
            await self.audit_log.create(
                user_id=user.id if user else None,
                action=f"{self.__class__.__name__}.{method_name}",
                status="error",
                error=str(e),
                duration=time.time() - start_time
            )
            raise
```

## Best Practices

<Aside type="tip" title="Context Best Practices">
  1. **Single Responsibility** - Each context should handle one domain area
  2. **Business Logic Only** - Keep HTTP concerns out of contexts
  3. **Dependency Injection** - Use DI for database, services, and other contexts
  4. **Error Handling** - Throw domain exceptions, let routes handle HTTP errors
  5. **Testing** - Test contexts independently from web layer
</Aside>

### Do's ✅

- Keep contexts focused on a single domain
- Use type hints for all methods
- Write comprehensive tests for context logic
- Use dependency injection for flexibility
- Document complex business rules

### Don'ts ❌

- Don't import web framework code in contexts
- Don't handle HTTP errors in contexts
- Don't make contexts too large (split if needed)
- Don't mix different domain concerns
- Don't bypass contexts for business logic

## Next Steps

- Learn about [Dependency Injection](/concepts/dependency-injection)
- Explore [Testing Contexts](/features/testing#context-testing)
- See [Real-world Examples](https://github.com/nijaru/zenith/tree/main/examples)