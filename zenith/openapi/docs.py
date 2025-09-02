"""
Documentation routes for serving OpenAPI spec and interactive documentation.

Provides Swagger UI and ReDoc interfaces for API documentation.
"""

from starlette.responses import HTMLResponse, JSONResponse

from zenith.core.routing import Router

from .generator import generate_openapi_spec


def setup_docs_routes(
    routers: list[Router],
    title: str = "Zenith API",
    version: str = "1.0.0",
    description: str = "API built with Zenith framework",
    docs_url: str = "/docs",
    redoc_url: str = "/redoc",
    openapi_url: str = "/openapi.json",
    servers: list[dict[str, str]] | None = None,
) -> Router:
    """
    Setup documentation routes for OpenAPI spec and interactive docs.

    Args:
        routers: List of application routers to document
        title: API title
        version: API version
        description: API description
        docs_url: URL for Swagger UI (set to None to disable)
        redoc_url: URL for ReDoc (set to None to disable)
        openapi_url: URL for OpenAPI JSON spec
        servers: Server configurations

    Returns:
        Router with documentation routes
    """

    docs_router = Router()

    # Generate OpenAPI spec
    spec = generate_openapi_spec(
        routers=routers,
        title=title,
        version=version,
        description=description,
        servers=servers,
    )

    @docs_router.get(openapi_url)
    async def get_openapi_spec():
        """Get the OpenAPI specification."""
        return JSONResponse(spec)

    if docs_url:

        @docs_router.get(docs_url)
        async def swagger_ui():
            """Serve Swagger UI for API documentation."""
            return HTMLResponse(
                _get_swagger_ui_html(title=title, openapi_url=openapi_url)
            )

    if redoc_url:

        @docs_router.get(redoc_url)
        async def redoc():
            """Serve ReDoc for API documentation."""
            return HTMLResponse(_get_redoc_html(title=title, openapi_url=openapi_url))

    return docs_router


def _get_swagger_ui_html(title: str, openapi_url: str) -> str:
    """Generate Swagger UI HTML page."""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - Swagger UI</title>
        <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css" />
        <style>
            html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
            *, *:before, *:after {{ box-sizing: inherit; }}
            body {{ margin:0; background: #fafafa; }}
            .swagger-ui .topbar {{ display: none; }}
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js"></script>
        <script src="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-standalone-preset.js"></script>
        <script>
            const ui = SwaggerUIBundle({{
                url: '{openapi_url}',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            }});
        </script>
    </body>
    </html>
    """


def _get_redoc_html(title: str, openapi_url: str) -> str:
    """Generate ReDoc HTML page."""

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{title} - ReDoc</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <style>
            body {{ margin: 0; padding: 0; }}
            redoc {{ display: block; }}
        </style>
    </head>
    <body>
        <redoc spec-url='{openapi_url}'></redoc>
        <script src="https://unpkg.com/redoc@2.0.0/bundles/redoc.standalone.js"></script>
    </body>
    </html>
    """
