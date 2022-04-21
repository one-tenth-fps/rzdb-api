import re
import aioodbc

import pyodbc
import uvicorn
import config
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.gzip import GZipMiddleware

dbpool = None
station_code_pattern = re.compile(r"(?:\d{1,6})")

app = FastAPI()
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
    request: Request, apiKey: str = "", stationCode: str = "0", searchRadius: int = 100, requestId: str = ""
):
    if searchRadius > config.CAR_SEARCH_RADIUS_LIMIT:
        raise HTTPException(
            status_code=config.BAD_REQUEST_STATUS,
            detail="searchRadius не должен превышать {0}".format(config.CAR_SEARCH_RADIUS_LIMIT),
        )

    if not station_code_pattern.fullmatch(stationCode):
        raise HTTPException(status_code=config.BAD_REQUEST_STATUS, detail="stationCode должен быть числом из 1-6 цифр")

    if len(requestId) > config.REQUEST_ID_LENGTH_LIMIT:
        raise HTTPException(
            status_code=config.BAD_REQUEST_STATUS,
            detail="requestId не должен быть длиннее {0} символов".format(config.REQUEST_ID_LENGTH_LIMIT),
        )

    async with dbpool.acquire() as db_conn:
        async with db_conn.cursor() as db_cursor:
            try:
                await db_cursor.execute(
                    "EXEC api.GetNearbyCars @StationCode=?, @Radius=?, @ApiKey=?, @RequestID=?, @ClientHost=?",
                    stationCode,
                    searchRadius,
                    apiKey[:1000],
                    requestId,
                    request.client.host,
                )
                db_response = await db_cursor.fetchone()
                return Response(
                    content=db_response.Result,
                    media_type="application/json",
                    status_code=config.BAD_REQUEST_STATUS if db_response.IsError else config.OK_STATUS,
                )
            except pyodbc.Error as e:
                error_message = e.args[0] if len(e.args) == 1 else e.args[1]
                raise HTTPException(status_code=config.BAD_REQUEST_STATUS, detail=error_message)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
