from fastapi import Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("server")


async def globalExceptionHandler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"code": -1, "msg": str(exc), "data": None},
    )