import math

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(title="VentureForge AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


def _sanitize_non_json_floats(value: object) -> object:
    """Starlette's default `JSONResponse` renders with `allow_nan=False` — strictly correct per
    the JSON spec, but it means a validation-error body that echoes back a rejected `NaN`/
    `Infinity` input (e.g. from `RevenueAssumptionsPatchRequest`'s `allow_inf_nan=False` fields)
    would otherwise crash the *error response itself* with an unrelated 500. Recursively replace
    any non-finite float in the error payload with its string form so the 422 can actually be
    returned.
    """
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {k: _sanitize_non_json_floats(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_non_json_floats(v) for v in value]
    return value


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    encoded = jsonable_encoder(exc.errors())
    return JSONResponse(status_code=422, content=_sanitize_non_json_floats(encoded))


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
