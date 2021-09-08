import os
import pyodbc
import uvicorn
import re
from fastapi import FastAPI, Response, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv

ERROR_STATUS = 400
OK_STATUS = 200
SEARCH_RADIUS_LIMIT = 500
REQUEST_ID_LIMIT = 1000
STATION_CODE_PATTERN = r'\d{1,6}'

load_dotenv()
db_driver = os.getenv('db_driver')
db_server = os.getenv('db_server')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password') 
db_database = os.getenv('db_database')

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/getNearbyCars")
async def getNearbyCars(request: Request, apiKey: str = '', stationCode: str = '0', searchRadius: int = 100, requestId: str = ''):
    if searchRadius > SEARCH_RADIUS_LIMIT:
        raise HTTPException(status_code=ERROR_STATUS, detail='searchRadius не должен превышать {0}'.format(SEARCH_RADIUS_LIMIT))

    if not re.fullmatch(STATION_CODE_PATTERN, stationCode):
        raise HTTPException(status_code=ERROR_STATUS, detail='stationCode должен быть числом из 1-6 цифр')

    if len(requestId) > REQUEST_ID_LIMIT:
        raise HTTPException(status_code=ERROR_STATUS, detail='requestId не должен быть длиннее {0} символов'.format(REQUEST_ID_LIMIT))
    
    db_conn = pyodbc.connect('DRIVER='+db_driver+';SERVER='+db_server+';DATABASE='+db_database+';UID='+db_user+';PWD='+db_password, autocommit=True)
    db_cursor = db_conn.cursor()
    db_params = (stationCode, searchRadius, apiKey[:1000], requestId, request.client.host)
    try:
        db_cursor.execute('EXEC api.GetNearbyCars ?, ?, ?, ?, ?', db_params)
        db_response = db_cursor.fetchone()
        return Response(content=db_response.Result, media_type='application/json', status_code=ERROR_STATUS if db_response.IsError else OK_STATUS)
    except pyodbc.Error as e:
        error_message = e.args[0] if len(e.args) == 1 else e.args[1]
        raise HTTPException(status_code=ERROR_STATUS, detail=error_message)
    finally:
        db_cursor.close()
        db_conn.close()

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)