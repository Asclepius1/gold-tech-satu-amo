from datetime import datetime
from fastapi import FastAPI, HTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.responses import PlainTextResponse

import contextlib
import re
import httpx
import requests
import logging
import codecs

from dotenv import load_dotenv
import os
load_dotenv()


API_TOKEN_SATU = os.getenv("API_TOKEN_SATU")
API_TOKEN_AMO = os.getenv("API_TOKEN_AMO")
API_URL_SATU = os.getenv("API_URL_SATU")
API_URL_AMO = os.getenv("API_URL_AMO")
PIPLINE = int(os.getenv("PIPLINE"))

log_file = codecs.open('app.log', 'a+', 'utf-8')
logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    stream=log_file)

def post_request_amo(data: list[dict[str, int|str|dict[str,str]]]) -> dict:
    try:
        url = API_URL_AMO
        headers = {"Authorization": f"Bearer {API_TOKEN_AMO}"}
        response = requests.post(url, headers=headers, json=data).json()
        logging.info(f"Запрос в амо отправлен успешно:\n{response}\n")
        return response
    except httpx.HTTPStatusError as exc:
        logging.warning("Запрос в амо отправлен не корректно!")
        raise HTTPException(status_code=exc.response.status_code, detail=f"Ошибка запроса: {exc}") 
    



def task() -> None:

    headers = {"Authorization": f"Bearer {API_TOKEN_SATU}"}

    with open('last_date.txt', 'a+') as f:
        f.seek(0)
        date = f.read()
        if not date:
            date = datetime.now()
        else:
            date = datetime.strptime(date.strip(), "%Y.%m.%dT%H:%M")
        f.truncate(0)
        f.write(datetime.now().strftime("%Y.%m.%dT%H:%M"))
        logging.info(f"Смена даты для выгрузки на {f.read()}")

    params = {
        # 'limit': 10,
        'date_from': date,
        'status': 'pending',
    }
    
    with httpx.Client() as client:
        try:
            response = client.get(API_URL_SATU, headers=headers, params=params)
            response.raise_for_status() 
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Ошибка запроса: {exc}")
        
        raw_datas: list[dict[str, str|dict[str,str]]] = response.json()['orders']
        data: list[dict[str, int|str|dict[str,str]]] = []
        for raw_data in raw_datas:
            data.append({
            "name": "Название сделки satu",
            "price": int(re.sub(r'\D', '', raw_data['price'])),
            "custom_fields_values": [
                {
                    "field_id": 513379,
                    "values": [
                        {
                            "value": raw_data["delivery_address"]
                        }
                    ]
                },
                
                {
                    "field_id": 513381,
                    "values": [
                        {
                            "value": raw_data["delivery_option"].get('name', '') if raw_data["delivery_option"] else ''
                        }
                    ]
                },
                
                {
                    "field_id": 513383,
                    "values": [
                        {
                            "value": raw_data["payment_option"].get('name', '') if raw_data["payment_option"] else ''
                        }
                    ]
                },

                {
                    "field_id": 513385,
                    "values": [
                        {
                            "value": '\n'.join([row.get('name', '') for row in raw_data["products"]])
                        }
                    ]
                },
            ],
            "_embedded":{
                "contacts":[
                    {
                    "first_name":f"{raw_data['client_first_name']} {raw_data['client_last_name']}",
                    "custom_fields_values":[
                        {
                            "field_code":"EMAIL",
                            "values":[
                                {
                                "enum_code":"WORK",
                                "value":f"{raw_data['email']}"
                                }
                            ]
                        },
                        {
                            "field_code":"PHONE",
                            "values":[
                                {
                                "enum_code":"WORK",
                                "value":f"{raw_data['phone']}"
                                }
                            ]
                        }
                    ]
                    }
                ]
            },
            "pipeline_id":PIPLINE,
        },)

        if data:
            logging.info("Данные с сату корректно получены")
            response = post_request_amo(data)
            logging.info(f"Ответ с амо: {response}")
        else:
            logging.warning("С Сату ничего не найдено")


    with open('event_log.txt', 'a+', encoding='utf-8') as f:
        logging.info(f"{datetime.now().strftime('%Y.%m.%mT%H:%M')} -- Загружено {len(data)}")
        f.write(f"{datetime.now().strftime('%Y.%m.%mT%H:%M')} -- Загружено {len(data)}\n")
    return

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(task, 'interval', minutes=1)
    scheduler.start()
    print("Планировщик запущен")
    logging.info("Планировщик запущено")
    
    yield

    scheduler.shutdown()
    print("Планировщик остановлен")
    logging.info("Планировщик запущено")
    

app = FastAPI(lifespan=lifespan)



@app.get("/get-order/")
async def get_products():
    headers = {"Authorization": f"Bearer {API_TOKEN_SATU}"}
    with open('last_date.txt', 'a+') as f:
        f.seek(0)
        date = f.read()
        date = datetime.strptime(date, "%Y.%m.%dT%H:%M")
    
    params = {
        # 'limit': 10,
        'date_from': date,
        'status': 'pending',
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(API_URL_SATU, headers=headers, params=params)
            response.raise_for_status() 
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Ошибка запроса: {exc}")
        
        return response.json()

@app.get("/logs", response_class=PlainTextResponse)
def get_logs():
    try:
        with open("app.log", "r") as log_file:
            logs = log_file.read()
        return logs
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="194.4.56.35", port=8000)
