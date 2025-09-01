# Immediate TODO: Fix The Foundation
*What needs to happen RIGHT NOW to make Zenith real*

## 🚨 Critical Fixes (This Week)

### 1. Database Integration (Most Critical)
```python
# Current (Embarrassing)
class Accounts(Context):
    def __init__(self):
        self._users = {}  # This is a toy

# Needed (Real Framework)  
class Accounts(Context):
    async def create_user(self, data: UserCreate) -> User:
        async with self.db.session() as session:
            user = User(**data.model_dump())
            session.add(user)
            await session.commit()
            return user
```

**Tasks:**
- [ ] Integrate SQLAlchemy 2.0 with our DI system
- [ ] Add database configuration to Config
- [ ] Create base Context class with database access
- [ ] Update Accounts context to use real database
- [ ] Add migration support (Alembic)

### 2. Simplify Over-Engineering
```python
# Remove Supervisor complexity
# Current: 200+ lines of Erlang-inspired supervision
# Needed: Simple background task management (20 lines)

class Application:
    def __init__(self):
        # DELETE: self.supervisor = Supervisor()
        self.tasks = []  # Simple task tracking
```

**Tasks:**
- [ ] Remove supervisor.py or simplify to 20 lines
- [ ] Remove supervisor from Application
- [ ] Keep simple task management for background jobs

### 3. Fix Authentication Stub
```python
# Current: Auth() returns mock data
@app.get("/protected")
async def protected(current_user: dict = Auth()):
    return {"user": current_user}  # Returns fake user

# Needed: Real authentication
@app.get("/protected")  
async def protected(current_user: User = Auth()):
    return {"user": current_user}  # Returns real authenticated user
```

**Tasks:**
- [ ] Implement JWT token generation
- [ ] Create login/logout endpoints
- [ ] Make Auth() dependency actually validate tokens
- [ ] Add permission checking

### 4. Fix Routing Edge Cases
```python
# Current: Basic routing works but missing:
# - Error handling
# - Middleware support  
# - Response models
# - OpenAPI generation
```

**Tasks:**
- [ ] Add exception handlers
- [ ] Implement middleware system
- [ ] Fix response model serialization
- [ ] Add OpenAPI/Swagger generation

---

## 📝 Linear Items Update

### Delete These:
- **ZEN-4: Build LiveView Engine** → DELETE (not suitable for Python)
- **ZEN-5: Implement Channel System** → DELETE (overengineered)

### Rename These:
- **ZEN-2: Build Basic Routing System** → "Complete Database Integration"
- **ZEN-3: Implement Context System** → "Fix Routing & Add Middleware"
- **ZEN-6: Design Database Layer** → "Build Authentication System"

### Add These:
- **ZEN-7: Testing Framework** (NEW)
- **ZEN-8: Documentation Generation** (NEW)
- **ZEN-9: Performance Benchmarks** (NEW)

---

## 🎯 Success Criteria for MVP

### Can someone build a real API?
```python
# This should work end-to-end
@app.post("/api/orders")
async def create_order(
    order: OrderCreate,
    current_user: User = Auth(),
    orders: Orders = Context()
) -> Order:
    # Real database transaction
    async with Transaction():
        order = await orders.create(order, user=current_user)
        await orders.send_confirmation_email(order)
    return order
```

### Can they test it?
```python
async def test_order_creation():
    async with TestClient(app) as client:
        # Login
        token = await client.login("user@example.com", "password")
        
        # Create order
        response = await client.post("/api/orders", 
            json={"items": [...]},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 201
```

### Can they deploy it?
```dockerfile
FROM python:3.11
COPY . /app
WORKDIR /app
RUN pip install -e .
CMD ["zen", "server", "--prod"]
```

---

## 🚀 Week-by-Week Plan

### Week 1: Database Foundation
- Monday-Tuesday: SQLAlchemy integration
- Wednesday-Thursday: Update contexts to use database
- Friday: Add migrations, test with real data

### Week 2: Core Features
- Monday-Tuesday: Fix authentication
- Wednesday-Thursday: Add middleware system
- Friday: Error handling and logging

### Week 3: Developer Experience  
- Monday-Tuesday: Testing utilities
- Wednesday-Thursday: OpenAPI generation
- Friday: Documentation and examples

### Week 4: Production Ready
- Monday-Tuesday: Performance benchmarks
- Wednesday-Thursday: Deployment guide
- Friday: First release (0.1.0)

---

## ⚠️ What NOT to Do

1. **Don't add more features** - Fix what we have first
2. **Don't refactor everything** - Incremental improvements
3. **Don't overthink** - Simple solutions first
4. **Don't build what exists** - Use SQLAlchemy, don't build ORM
5. **Don't promise LiveView** - It's not happening in Python

---

## ✅ Definition of Done for MVP

- [ ] Real database integration works
- [ ] Authentication actually authenticates
- [ ] Can build a TODO API in 50 lines of code
- [ ] Tests can be written easily
- [ ] Deploys to Docker without issues
- [ ] Benchmarks show reasonable performance
- [ ] Documentation explains the WHY not just HOW
- [ ] One real user has built something with it

---

*Ship something people can use, not something that sounds impressive.*