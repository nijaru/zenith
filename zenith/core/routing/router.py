"""
Modern Router implementation with clean separation of concerns.

Focuses purely on route registration and building. Execution, dependency
injection, and response handling are delegated to specialized services.
"""

from collections.abc import Callable

from starlette.middleware import Middleware
from starlette.routing import Route, WebSocketRoute
from starlette.routing import Router as StarletteRouter

from .executor import RouteExecutor
from .specs import RouteSpec


class Router:
    """
    Modern router with clean architecture.

    Responsibilities:
    - Route registration via decorators
    - Building Starlette router for ASGI
    - Route organization and prefixing

    Does NOT handle:
    - Route execution (delegated to RouteExecutor)
    - Dependency injection (delegated to DependencyResolver)
    - Response processing (delegated to ResponseProcessor)
    """

    __slots__ = ("_app", "executor", "middleware", "prefix", "routes")

    def __init__(self, prefix: str = "", middleware: list[Middleware] | None = None):
        self.prefix = prefix
        self.middleware = middleware or []
        self.routes: list[RouteSpec] = []
        self.executor = RouteExecutor()
        self._app = None  # Will be set by Application

    def route(
        self,
        path: str,
        methods: list[str],
        name: str | None = None,
        middleware: list[Middleware] | None = None,
        response_model: type | None = None,
        response_class: type | None = None,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ):
        """Register a route with the given methods."""

        def decorator(handler: Callable) -> Callable:
            route_spec = RouteSpec(
                path=self.prefix + path,
                methods=methods,
                handler=handler,
                name=name,
                middleware=middleware,
                response_model=response_model,
                response_class=response_class,
                summary=summary,
                description=description,
                tags=tags,
            )
            self.routes.append(route_spec)
            return handler

        return decorator

    # HTTP method decorators
    def get(self, path: str, **kwargs):
        """GET route decorator."""
        return self.route(path, ["GET"], **kwargs)

    def post(self, path: str, **kwargs):
        """POST route decorator."""
        return self.route(path, ["POST"], **kwargs)

    def put(self, path: str, **kwargs):
        """PUT route decorator."""
        return self.route(path, ["PUT"], **kwargs)

    def patch(self, path: str, **kwargs):
        """PATCH route decorator."""
        return self.route(path, ["PATCH"], **kwargs)

    def delete(self, path: str, **kwargs):
        """DELETE route decorator."""
        return self.route(path, ["DELETE"], **kwargs)

    def head(self, path: str, **kwargs):
        """HEAD route decorator."""
        return self.route(path, ["HEAD"], **kwargs)

    def options(self, path: str, **kwargs):
        """OPTIONS route decorator."""
        return self.route(path, ["OPTIONS"], **kwargs)

    def websocket(self, path: str, **kwargs):
        """WebSocket route decorator."""

        def decorator(handler: Callable) -> Callable:
            from zenith.web.websockets import WebSocket

            async def websocket_endpoint(websocket_raw):
                websocket = WebSocket(websocket_raw)
                await handler(websocket)

            route_spec = RouteSpec(
                path=self.prefix + path,
                methods=["WEBSOCKET"],
                handler=handler,
                raw_handler=websocket_endpoint,
                **kwargs,
            )
            self.routes.append(route_spec)
            return handler

        return decorator

    def include_router(self, router: "Router", prefix: str = "") -> None:
        """Include routes from another router."""
        combined_prefix = self.prefix + prefix

        for route_spec in router.routes:
            # Create a new route spec with the combined prefix
            new_route_spec = RouteSpec(
                path=combined_prefix + route_spec.path,
                methods=route_spec.methods,
                handler=route_spec.handler,
                raw_handler=route_spec.raw_handler,
                name=route_spec.name,
                middleware=route_spec.middleware,
                response_model=route_spec.response_model,
                summary=route_spec.summary,
                description=route_spec.description,
                tags=route_spec.tags,
            )
            self.routes.append(new_route_spec)

    def build_starlette_router(self) -> StarletteRouter:
        """Build Starlette router from registered routes."""
        starlette_routes = []

        for route_spec in self.routes:
            if route_spec.methods == ["WEBSOCKET"]:
                # WebSocket routes
                websocket_route = WebSocketRoute(
                    route_spec.path,
                    endpoint=route_spec.raw_handler,
                    name=route_spec.name,
                )
                starlette_routes.append(websocket_route)
            else:
                # HTTP routes - delegate execution to RouteExecutor
                def create_endpoint(spec):
                    async def endpoint(request):
                        return await self.executor.execute_route(
                            request, spec, self._app
                        )

                    return endpoint

                starlette_route = Route(
                    route_spec.path,
                    endpoint=create_endpoint(route_spec),
                    methods=route_spec.methods,
                    name=route_spec.name,
                )
                starlette_routes.append(starlette_route)

        # Note: Mount routes are now handled at the Zenith application level
        # in _build_starlette_app() to ensure they're properly included

        return StarletteRouter(routes=starlette_routes, middleware=self.middleware)
