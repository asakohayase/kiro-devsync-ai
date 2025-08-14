"""Main FastAPI application for DevSync AI."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from typing import Callable

from devsync_ai.config import settings
from devsync_ai.api.routes import api_router
from devsync_ai.webhooks.routes import webhook_router


# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Smart release coordination tool that automates communication and coordination tasks within software teams",
        debug=settings.debug,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Add middleware
    setup_middleware(app)

    # Add routes
    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(webhook_router, prefix="/webhooks")

    # Add event handlers
    setup_event_handlers(app)

    return app


def setup_middleware(app: FastAPI) -> None:
    """Configure application middleware."""

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else ["https://your-domain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted host middleware
    if not settings.debug:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[
                "kiro-devsync-ai.onrender.com",
                "*.onrender.com",
                "localhost",
                "testserver",
            ],
        )

    # Request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next: Callable):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable):
        logger.info(f"{request.method} {request.url}")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response


def setup_event_handlers(app: FastAPI) -> None:
    """Configure application event handlers."""

    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup."""
        logger.info(f"Starting {settings.app_name} v{settings.app_version}")

        # Start JIRA sync scheduler
        try:
            from devsync_ai.scheduler.jira_sync import start_scheduler

            await start_scheduler()
            logger.info("JIRA sync scheduler started")
        except Exception as e:
            logger.error(f"Failed to start JIRA sync scheduler: {e}")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up resources on shutdown."""
        logger.info(f"Shutting down {settings.app_name}")

        # Stop JIRA sync scheduler
        try:
            from devsync_ai.scheduler.jira_sync import stop_scheduler

            await stop_scheduler()
            logger.info("JIRA sync scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop JIRA sync scheduler: {e}")


# Create the application instance
app = create_app()


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "path": str(request.url),
            }
        },
    )


if __name__ == "__main__":
    import uvicorn
    import os

    # Use PORT from environment (for Render) or fall back to settings
    port = int(os.environ.get("PORT", settings.api_port))

    uvicorn.run(
        "devsync_ai.main:app",
        host="0.0.0.0",  # Bind to all interfaces for deployment
        port=port,
        reload=settings.debug,
    )
