from datetime import datetime
from fastapi import HTTPException
from requests.exceptions import ConnectionError

from sqlalchemy.orm import Session
from db import APICredentials, SessionLocal

import re
import httpx
import requests
import logging
import codecs

log_file = codecs.open('app.log', 'a+', 'utf-8')
logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    stream=log_file)

def create_leads_custom_fields(api_url_amo: str, api_token_amo: str) -> dict[str, str]:
    
    data = [
        {"name": "Адрес доставки", "type": "text", "is_api_only": True},
        {"name": "Тип доставки", "type": "text", "is_api_only": True},
        {"name": "Тип оплаты", "type": "text", "is_api_only": True},
        {"name": "Продукт", "type": "textarea", "is_api_only": True}
    ]
    
    url = f"{api_url_amo}/api/v4/leads/custom_fields"
    headers = {"Authorization": f"Bearer {api_token_amo}"}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Проверка на успешный статус
        return response
    except requests.exceptions.HTTPError as exc:
        # Обработка HTTP ошибок
        raise HTTPException(status_code=exc.response.status_code, detail=f"Ошибка запроса: {exc.response.text}")
    except requests.exceptions.ConnectionError:
        # Обработка ошибки подключения
        raise HTTPException(status_code=503, detail="Не удалось подключиться к серверу, проверьте корректность введенных данных")
    except Exception as e:
        # Обработка всех остальных ошибок
        raise HTTPException(status_code=500, detail=f"Произошла непредвиденная ошибка: {e}")


def post_request_amo(api_token_amo: str, api_url_amo: str, data: list[dict]) -> dict:
    headers = {"Authorization": f"Bearer {api_token_amo}"}
    try:
        response = requests.post(f"{api_url_amo}/api/v4/leads/complex", headers=headers, json=data).json()
        logging.info(f"Запрос в AmoCRM отправлен успешно: {response}")
        return response
    except httpx.HTTPStatusError as exc:
        logging.warning("Ошибка при отправке запроса в AmoCRM")
        raise HTTPException(status_code=exc.response.status_code, detail=f"Ошибка запроса: {exc}")



def get_api_credentials(db: Session, credential_id: int):
    return db.query(APICredentials).filter(APICredentials.id == credential_id).first()

def get_all_api_credentials(db: Session):
    return db.query(APICredentials).all()


def task() -> None:
    db = SessionLocal()
    credentials_list = get_all_api_credentials(db)
    db.close()


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
        for credentials in credentials_list:
            headers = {"Authorization": f"Bearer {credentials.api_token_satu}"}

            

            params = {
                # 'limit': 10,
                'date_from': date,
                'status': 'pending',
            }
            
            with httpx.Client() as client:
                try:
                    response = client.get(credentials.api_url_satu, headers=headers, params=params)

                    response.raise_for_status() 
                except httpx.HTTPStatusError as exc:
                    raise HTTPException(status_code=exc.response.status_code, detail=f"Ошибка запроса: {exc}")
                
                raw_datas: list[dict[str, str|dict[str,str]]] = response.json()['orders']
                data: list[dict[str, int|str|dict[str,str]]] = []
                for raw_data in raw_datas:
                    data.append({
                    "name": "Заявка с satu",
                    "price": int(re.sub(r'\D', '', raw_data['price'])),
                    "custom_fields_values": [
                        {
                            "field_id": credentials.address_id,
                            "values": [
                                {
                                    "value": raw_data["delivery_address"]
                                }
                            ]
                        },
                        
                        {
                            "field_id": credentials.delivry_type_id,
                            "values": [
                                {
                                    "value": raw_data["delivery_option"].get('name', '') if raw_data["delivery_option"] else ''
                                }
                            ]
                        },
                        
                        {
                            "field_id": credentials.payment_id,
                            "values": [
                                {
                                    "value": raw_data["payment_option"].get('name', '') if raw_data["payment_option"] else ''
                                }
                            ]
                        },

                        {
                            "field_id": credentials.product_id,
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
                    "pipeline_id":credentials.pipeline_id,
                },)

                project_name = re.search(r'https:\/\/([^.]+)\.', credentials.api_url_amo)[1]
                if data:
                    logging.info(f"Данные с сату корректно получены для {project_name}")
                    response = post_request_amo(credentials.api_token_amo, credentials.api_url_amo, data)
                    logging.info(f"Ответ с амо: {response}")
                else:
                    logging.warning(f"С Сату ничего не найдено для {project_name}")


            with open('event_log.txt', 'a+', encoding='utf-8') as f:
                logging.info(f"{datetime.now().strftime('%Y.%m.%mT%H:%M')} -- Загружено {len(data)}")
                f.write(f"{datetime.now().strftime('%Y.%m.%mT%H:%M')} -- Загружено {len(data)}\n")
            return