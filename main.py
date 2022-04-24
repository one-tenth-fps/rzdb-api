import logging
import time

import aioodbc
import pyodbc
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.exception_handlers import (http_exception_handler,
                                        request_validation_exception_handler)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

import config

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
    filename="main.log",
    encoding="utf-8",
)

dbpool = None
station_code_pattern = r"^(?:\d{1,6})$"

app = FastAPI(docs_url=None, redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.on_event("startup")
async def startup():
    global dbpool
    dbpool = await aioodbc.create_pool(minsize=1, maxsize=10, dsn=config.DB_CONNECTION_STRING, autocommit=True)


@app.on_event("shutdown")
async def shutdown():
    dbpool.close()
    await dbpool.wait_closed()


@app.get("/getNearbyCars")
async def getNearbyCars(
    request: Request,
    apiKey: str = Query(..., max_length=config.API_KEY_LENGTH_LIMIT),
    stationCode: str = Query(..., regex=station_code_pattern),
    searchRadius: int | None = Query(100, le=config.CAR_SEARCH_RADIUS_LIMIT),
    requestId: str | None = Query(None, max_length=config.REQUEST_ID_LENGTH_LIMIT),
):
    async with dbpool.acquire() as db_conn:
        async with db_conn.cursor() as db_cursor:
            try:
                await db_cursor.execute(
                    "EXEC api.GetNearbyCars @StationCode=?, @Radius=?, @ApiKey=?, @RequestID=?, @ClientHost=?",
                    stationCode,
                    searchRadius,
                    apiKey,
                    requestId,
                    request.client.host,
                )
                db_response = await db_cursor.fetchone()
                return return_json(db_response.Result, db_response.IsError)
            except pyodbc.Error as e:
                raise_on_pyodbc_error(e)


@app.post("/getCarDocTurnover")
async def getCarDocTurnover(
    request: Request,
    apiKey: str = Query(..., max_length=config.API_KEY_LENGTH_LIMIT),
):
    body = await request.body()
    try:
        body_str = body.decode()
    except UnicodeDecodeError:
        raise_http_exception("UTF-8 expected")

    async with dbpool.acquire() as db_conn:
        async with db_conn.cursor() as db_cursor:
            try:
                await db_cursor.execute("EXEC api.GetCarDocTurnover @RequestJSON=?, @ApiKey=?", body_str, apiKey)
                db_response = await db_cursor.fetchone()
                return return_json(db_response.Result, db_response.IsError)
            except pyodbc.Error as e:
                raise_on_pyodbc_error(e)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.monotonic()
    response = await call_next(request)
    process_time = time.monotonic() - start_time
    logging.info(f"{request.client.host} {request.method} {request.url} {process_time:.2f}ms {response.status_code}")
    return response


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc):
    logging.error(f"{repr(exc)}")
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logging.error(f"{repr(exc)}")
    return await request_validation_exception_handler(request, exc)


def return_json(content: str, IsError: bool):
    logging.info(f"{len(content)} bytes sent")
    return Response(
        content=content,
        media_type="application/json",
        status_code=config.BAD_REQUEST_STATUS if IsError else config.OK_STATUS,
    )


def raise_http_exception(detail: str):
    logging.error(detail)
    raise HTTPException(status_code=config.BAD_REQUEST_STATUS, detail=detail)


def raise_on_pyodbc_error(exc: pyodbc.Error):
    error_message = exc.args[0] if len(exc.args) == 1 else exc.args[1]
    raise_http_exception(error_message)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
