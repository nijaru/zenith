"""
🌐 Frontend Serving - Complete Guide

This example demonstrates Zenith's frontend serving capabilities for 
building full-stack applications with modern SPAs.

Features:
- app.spa() - Intelligent SPA serving with framework detection
- app.static() - Traditional static file serving
- Zero-configuration auto-detection
- Production-ready caching and optimization

Run with: python examples/18-frontend-serving-dx.py
"""

from zenith import Zenith, Service, Context
from pydantic import BaseModel

app = Zenith(title="Frontend Serving DX Demo")

# ============================================================================
# API ROUTES - Your backend logic
# ============================================================================

class User(BaseModel):
    id: int
    name: str
    email: str

class UserService(Service):
    def __init__(self):
        self.users = [
            User(id=1, name="Alice", email="alice@example.com"),
            User(id=2, name="Bob", email="bob@example.com"),
        ]
    
    async def get_users(self):
        return self.users

@app.get("/api/users")
async def get_users(users: UserService = Context()):
    return await users.get_users()

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

# ============================================================================
# NEW CLEAN API - Simple and Intuitive
# ============================================================================

# 🎯 SPA Serving (Most Common Use Case)
# app.spa()              # Auto-detect dist/ or build/
# app.spa("solidjs")     # Framework-specific: uses dist/  
# app.spa("react")       # Framework-specific: uses build/
# app.spa("dist")        # Custom directory

# 🎯 Static File Serving (Traditional Assets)
# app.static()                    # /static/ -> ./static/
# app.static("/assets", "public") # /assets/ -> ./public/

# 🎯 Production Configuration
# app.spa("dist", max_age=86400)  # Long caching

# ============================================================================
# CURRENT API - Production-Ready Frontend Serving
# ============================================================================

# ✨ SPA Serving - Smart, framework-aware
# app.spa()              # Auto-detect dist/ or build/
# app.spa("solidjs")     # Framework: uses dist/
# app.spa("react")       # Framework: uses build/
# app.spa("my-build")    # Custom directory
# app.spa("dist", max_age=86400)  # Production caching

# 📁 Static Files - Traditional assets
# app.static()                    # /static/ -> ./static/
# app.static("/assets", "public") # /assets/ -> ./public/

# ============================================================================
# EXAMPLES - Clean New API
# ============================================================================

if __name__ == "__main__":
    print("🌐 Frontend Serving - Clean API Design")
    print("=" * 50)
    
    # Choose ONE of these approaches:
    
    # Option 1: Auto-detection (recommended)
    print("🎯 Using auto-detection...")
    app.spa()  # Auto-detects dist/ or build/
    
    # Option 2: Framework-specific
    # print("🎯 Using SolidJS config...")  
    # app.spa("solidjs")  # Uses dist/
    
    # Option 3: Custom directory
    # print("🎯 Using custom directory...")
    # app.spa("my-build")
    
    # Option 4: Production with caching
    # print("🎯 Using production config...")
    # app.spa("dist", max_age=86400)
    
    print(f"📍 Server: http://localhost:8018")
    print(f"📖 API Docs: http://localhost:8018/docs") 
    print(f"🔗 API Test: http://localhost:8018/api/users")
    
    print("\n✨ Clean API Design:")
    print("   • app.spa() - Short, intuitive, industry-standard")
    print("   • Smart framework detection and auto-detection")  
    print("   • Separate concerns: spa() vs static()")
    print("   • Zero configuration required")
    print("   • Production optimizations built-in")
    
    print("\n🏗️ Usage Examples:")
    print("   Auto:     app.spa()            # Detects dist/ or build/")
    print("   SolidJS:  app.spa('solidjs')   # Uses dist/ automatically")
    print("   React:    app.spa('react')     # Uses build/ automatically") 
    print("   Custom:   app.spa('my-build')  # Any directory")
    print("   Static:   app.static()         # Traditional /static/ assets")
    
    app.run(host="127.0.0.1", port=8018)