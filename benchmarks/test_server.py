#!/usr/bin/env python
"""Test if benchmark servers can start."""

import asyncio
import subprocess
import time
import httpx

async def test_server_startup(name: str, script: str, port: int):
    """Test if a server can start and respond."""
    print(f"\nTesting {name} on port {port}...")
    
    # Start server
    proc = subprocess.Popen(
        ["python", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for startup
    await asyncio.sleep(3)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://127.0.0.1:{port}/", timeout=2)
            print(f"✅ {name}: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ {name}: {type(e).__name__}: {e}")
        
        # Get process output
        if proc.poll() is None:
            # Still running
            print(f"   Process is still running (PID: {proc.pid})")
        else:
            # Exited
            stdout, stderr = proc.communicate()
            print(f"   Process exited with code: {proc.returncode}")
            if stdout:
                print(f"   STDOUT: {stdout.decode()[:200]}")
            if stderr:
                print(f"   STDERR: {stderr.decode()[:200]}")
    
    finally:
        # Cleanup
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()

async def main():
    print("Testing benchmark servers...")
    
    # Test each server
    await test_server_startup("Zenith", "zenith_minimal.py", 8000)
    await test_server_startup("FastAPI", "fastapi_app.py", 8001) 
    await test_server_startup("Flask", "flask_app.py", 8002)

if __name__ == "__main__":
    asyncio.run(main())