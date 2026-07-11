from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(title="VentureForge AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins.split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(OperationalError)
async def database_unavailable_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """Turn a raw driver connection error into a clear, actionable response instead of a bare 500.

    Never includes the raw driver exception (which can contain the connection string) in the
    response body — only a fixed, safe message pointing at DATABASE_URL and the setup docs.
    """
    return JSONResponse(
        status_code=503,
        content={
            "detail": (
                "Database unavailable. Check that PostgreSQL is running and DATABASE_URL is "
                "correct (see README.md, 'Local Setup', step 3)."
            )
        },
    )
