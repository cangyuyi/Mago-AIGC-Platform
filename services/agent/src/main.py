"""Mago Agent Service - FastAPI Application Entry Point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import agent as agent_router
from src.api.routes import hitl as hitl_router
from src.api.routes import knowledge as knowledge_router
from src.api.routes import trends as trends_router
from src.common.logger import get_logger, setup_logging
from src.config import get_settings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging("DEBUG" if settings.debug else "INFO")

    # Initialize observability (Langfuse + OpenTelemetry)
    try:
        from src.observability import setup_langfuse, setup_tracing

        setup_langfuse()
        setup_tracing(
            service_name="mago-agent",
            sample_rate=1.0 if settings.debug else 0.1,
        )
        logger.info("observability_initialized")
    except Exception as e:
        logger.warning(f"observability_init_failed (non-critical): {e}")

    logger.info(
        "agent_service_starting",
        app=settings.app_name,
        version=settings.app_version,
        env=settings.environment,
        host=settings.host,
        port=settings.port,
    )

    from src.llm.gateway import get_llm_gateway

    _ = get_llm_gateway()

    if not settings.openai_api_key and not settings.anthropic_api_key and not settings.google_api_key:
        logger.warning("No LLM API keys configured! Agent will run in offline/demo mode.")

    # Initialize the ARQ pool separately from the JSON cache. The API uses
    # this pool only to enqueue durable jobs; the dedicated worker executes
    # them and writes task status back to Redis.
    app.state.arq_pool = None
    try:
        from arq import create_pool
        from arq.connections import RedisSettings

        arq_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        try:
            await arq_pool.ping()
        except Exception:
            arq_pool.close()
            raise
        app.state.arq_pool = arq_pool
        logger.info("arq_queue_connected")
    except Exception as e:
        logger.warning(f"arq_queue_unavailable (non-critical for development): {e}")
        app.state.arq_pool = None

    # Initialize Redis cache if available
    try:
        from src.common.cache import get_cache

        cache = get_cache(settings.redis_url)
        if await cache.ping():
            app.state.cache = cache
            logger.info("redis_cache_connected")
        else:
            app.state.cache = None
            logger.warning("redis_cache_unavailable (ping failed)")
    except Exception as e:
        logger.warning(f"redis_cache_unavailable (non-critical): {e}")
        app.state.cache = None

    # Start crawl scheduler
    try:
        from src.scheduler import CrawlScheduler

        scheduler = CrawlScheduler(arq_pool=app.state.arq_pool)
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("crawl_scheduler_started")
    except Exception as e:
        logger.warning(f"crawl_scheduler_failed: {e}")

    logger.info("agent_service_ready")
    yield

    # Shutdown: flush observability data
    try:
        from src.observability.langfuse_setup import flush_langfuse

        flush_langfuse()
    except Exception:
        pass

    # Shutdown scheduler
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()

    if getattr(app.state, "arq_pool", None) is not None:
        try:
            app.state.arq_pool.close()
        except Exception as e:
            logger.warning(f"arq_queue_close_failed: {e}")

    if getattr(app.state, "cache", None) is not None:
        try:
            await app.state.cache.close()
        except Exception as e:
            logger.warning(f"redis_cache_close_failed: {e}")

    logger.info("agent_service_shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Mago Agent Platform - AI Creative Brain",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    # Security middleware first (before CORS)
    from src.api.middleware.security import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware)

    origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
    # Credentials cannot be safely combined with a wildcard origin. Keep a
    # conservative local fallback if the setting is accidentally blank.
    if not origins:
        origins = ["http://localhost:3000", "http://localhost"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
        max_age=3600,
    )

    # Request ID middleware
    from src.api.middleware.request_id import RequestIDMiddleware

    app.add_middleware(RequestIDMiddleware)

    if settings.agent_auth_enabled:
        import jwt
        from fastapi.responses import JSONResponse

        @app.middleware("http")
        async def agent_auth_middleware(request, call_next):
            public_paths = {
                "/",
                "/health",
                "/api/v1/agent/health",
                "/metrics",
                "/docs",
                "/redoc",
                "/openapi.json",
            }
            if request.url.path in public_paths or request.method == "OPTIONS":
                return await call_next(request)
            authorization = request.headers.get("Authorization", "")
            if not authorization.startswith("Bearer ") or not settings.jwt_secret:
                return JSONResponse({"detail": "missing or invalid authorization header"}, status_code=401)
            try:
                claims = jwt.decode(
                    authorization[7:],
                    settings.jwt_secret,
                    algorithms=["HS256"],
                    issuer="mago-agent",
                    options={"require": ["exp", "iat", "iss", "sub"]},
                )
                if claims.get("token_type") != "access" or not claims.get("user_id"):
                    raise jwt.InvalidTokenError("invalid access token")
                request.state.user_id = claims["user_id"]
                request.state.user_role = claims.get("role", "user")
            except jwt.PyJWTError:
                return JSONResponse({"detail": "invalid or expired token"}, status_code=401)
            return await call_next(request)

    # Root health for Nginx/load balancer
    @app.get("/health", tags=["health"])
    async def root_health():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "ok",
        }

    # Metrics endpoint (for Prometheus scraping)
    @app.get("/metrics", tags=["monitoring"])
    async def metrics():
        from fastapi.responses import PlainTextResponse

        # Basic Prometheus-format metrics (can be extended with prometheus-client)
        return PlainTextResponse(
            "# HELP mago_agent_info Agent service info\n"
            "# TYPE mago_agent_info gauge\n"
            f'mago_agent_info{{version="{settings.app_version}"}} 1\n'
        )

    # Agent API routes
    app.include_router(agent_router.router)

    # Trend Intelligence routes
    app.include_router(trends_router.router)
    app.include_router(knowledge_router.router)
    app.include_router(hitl_router.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
