---
title: Hello World Example
description: Your first Zenith application
---

import { Code } from '@astrojs/starlight/components';

## Minimal Zenith Application

The simplest possible Zenith application:

```python
from zenith import Zenith

app = Zenith()

@app.get("/")
async def hello():
    return {"message": "Hello, World!"}
```

## Run the Application

```bash
# Save as app.py
# Run with:
uvicorn app:app --reload

# Or use the Zenith CLI:
zen server --reload
```

Visit `http://localhost:8000` to see your API in action!

## Interactive Documentation

Zenith automatically generates interactive API documentation. Visit:
- `http://localhost:8000/docs` - Swagger UI
- `http://localhost:8000/redoc` - ReDoc

## Adding More Routes

```python
from zenith import Zenith
from datetime import datetime

app = Zenith()

@app.get("/")
async def hello():
    return {"message": "Hello, World!"}

@app.get("/time")
async def current_time():
    return {"time": datetime.utcnow()}

@app.get("/greet/{name}")
async def greet(name: str):
    return {"message": f"Hello, {name}!"}
```

## With Configuration

```python
from zenith import Zenith

app = Zenith(
    title="My First API",
    version="1.0.0",
    description="Learning Zenith Framework"
)

@app.get("/", tags=["General"])
async def hello():
    """
    Say hello to the world.
    
    This endpoint returns a simple greeting message.
    """
    return {"message": "Hello, World!"}

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """Check if the service is healthy."""
    return {"status": "healthy"}
```

## Complete Example

Find the complete example at:
[github.com/nijaru/zenith/examples/00-hello-world.py](https://github.com/nijaru/zenith/tree/main/examples/00-hello-world.py)