"""
Routing mixin for Zenith applications.

Contains HTTP verb decorators and route management methods.
"""


class RoutingMixin:
    """Mixin for HTTP routing decorator methods."""

    def get(self, path: str, **kwargs):
        """Register a GET route."""
        return self._app_router.get(path, **kwargs)

    def post(self, path: str, **kwargs):
        """Register a POST route."""
        return self._app_router.post(path, **kwargs)

    def put(self, path: str, **kwargs):
        """Register a PUT route."""
        return self._app_router.put(path, **kwargs)

    def patch(self, path: str, **kwargs):
        """Register a PATCH route."""
        return self._app_router.patch(path, **kwargs)

    def delete(self, path: str, **kwargs):
        """Register a DELETE route."""
        return self._app_router.delete(path, **kwargs)

    def head(self, path: str, **kwargs):
        """Register a HEAD route."""
        return self._app_router.head(path, **kwargs)

    def options(self, path: str, **kwargs):
        """Register an OPTIONS route."""
        return self._app_router.options(path, **kwargs)

    def websocket(self, path: str, **kwargs):
        """Register a WebSocket route."""
        return self._app_router.websocket(path, **kwargs)

    def route(self, path: str, methods: list[str], **kwargs):
        """Register a route with multiple HTTP methods."""
        return self._app_router.route(path, methods, **kwargs)

    def template(self, template_name: str, **template_kwargs):
        """Template response decorator."""
        return self._app_router.template(template_name, **template_kwargs)

    def negotiate(self, template_name: str | None = None, **template_kwargs):
        """Content negotiation decorator."""
        return self._app_router.negotiate(template_name, **template_kwargs)
