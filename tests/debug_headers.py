"""
Debug rate limiting header addition
"""
import asyncio
from zenith import Zenith
from zenith.middleware.rate_limit import RateLimit, RateLimitConfig, RateLimitMiddleware
from zenith.testing import TestClient


class DebugRateLimitMiddleware(RateLimitMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        print(f"Rate limit middleware called for {scope.get('path')}")
        print(f"Exempt IPs configured: {self.exempt_ips}")
        print(f"Client IP: {self._get_client_ip_asgi(scope)}")

        # Skip rate limiting for exempt requests
        if self._should_exempt_asgi(scope):
            print("Request is exempt")
            await self.app(scope, receive, send)
            return

        # Get applicable rate limits
        limits = self._get_applicable_limits_asgi(scope)
        print(f"Applicable limits: {limits}")

        # Check rate limits
        (
            allowed,
            violated_limit,
            current_count,
            limit_count,
        ) = await self._check_rate_limits_asgi(scope, limits)

        print(f"Rate check: allowed={allowed}, current={current_count}, limit={limit_count}")

        if not allowed:
            print("Request blocked by rate limit")
            error_response = self._create_error_response_asgi(
                violated_limit, current_count, limit_count, scope
            )
            await error_response(scope, receive, send)
            return

        print(f"Request allowed, include_headers={self.include_headers}")

        # Wrap send to add rate limit headers to successful responses
        async def send_wrapper(message):
            print(f"send_wrapper called with message type: {message['type']}")
            if (
                message["type"] == "http.response.start"
                and self.include_headers
                and limits
            ):
                print("Adding rate limit headers")
                # Use the most restrictive limit for headers
                most_restrictive = min(limits, key=lambda l: l.requests / l.window)
                print(f"Most restrictive limit: {most_restrictive}")
                key = self._get_rate_limit_key_asgi(scope, most_restrictive)
                current = await self.storage.get_count(key)
                print(f"Current count: {current}")

                response_headers = list(message.get("headers", []))
                print(f"Original headers count: {len(response_headers)}")
                response_headers.extend(
                    [
                        (
                            b"x-ratelimit-limit",
                            str(most_restrictive.requests).encode("latin-1"),
                        ),
                        (
                            b"x-ratelimit-window",
                            str(most_restrictive.window).encode("latin-1"),
                        ),
                        (
                            b"x-ratelimit-remaining",
                            str(max(0, most_restrictive.requests - current)).encode(
                                "latin-1"
                            ),
                        ),
                    ]
                )
                print(f"Headers after adding rate limit: {len(response_headers)}")
                message["headers"] = response_headers
            else:
                print(f"Not adding headers: response_start={message['type'] == 'http.response.start'}, include_headers={self.include_headers}, has_limits={bool(limits)}")

            await send(message)

        await self.app(scope, receive, send_wrapper)


async def debug_headers():
    app = Zenith()

    # Remove auto-added rate limiting
    app.middleware = [m for m in app.middleware if m.cls != RateLimitMiddleware]

    # Add our debug rate limiting with no exempt IPs
    rate_limits = [RateLimit(requests=2, window=60, per="ip")]
    app.add_middleware(
        DebugRateLimitMiddleware,
        default_limits=rate_limits,
        exempt_ips=[]  # Don't exempt localhost for testing
    )

    @app.get("/test")
    async def test_endpoint():
        return {"message": "success"}

    async with TestClient(app) as client:
        print("\n--- Making request ---")
        response = await client.get("/test")
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")


if __name__ == "__main__":
    asyncio.run(debug_headers())