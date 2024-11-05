from fastapi import APIRouter, Query
from typing import List
from fastapi import HTTPException, Depends
from fastapi.responses import PlainTextResponse

from sqlalchemy.orm import Session
from db import APICredentials, get_db, APICredentialsResponse

from service import create_leads_custom_fields

router = APIRouter(tags=['Satu'])


@router.post("/add-credentials/",
            summary="Добавить учётные данные",
            description="Эндпоинт для добавления учетных данных в базу данных")
def add_credentials(
    api_token_satu: str = Query(..., description="Токен для доступа к Satu.kz API", example="your-satu-token",),
    api_url_amo: str = Query(..., description="Базовый URL AmoCRM", example="https://yourcompany.amocrm.com"),
    api_token_amo: str = Query(..., description="Токен для доступа к API AmoCRM", example="your-amo-token"),
    pipeline_id: int = Query(..., description="ID воронки в AmoCRM", example=123456),
    db: Session = Depends(get_db)
):
    """
    Этот эндпоинт принимает токены и идентификатор воронки для настройки интеграции с AmoCRM.
    """

    data = create_leads_custom_fields(api_url_amo, api_token_amo)
    address_id = data["_embedded"]["custom_fields"][0]['id']
    delivry_type_id = data["_embedded"]["custom_fields"][1]['id']
    payment_id = data["_embedded"]["custom_fields"][2]['id']
    product_id = data["_embedded"]["custom_fields"][3]['id']

    if api_url_amo[-1] == '/':
        api_url_amo = api_url_amo[:-1]
    new_credentials = APICredentials(
        api_url_satu="https://my.satu.kz/api/v1/orders/list",
        api_token_satu=api_token_satu,
        api_url_amo=api_url_amo,
        api_token_amo=api_token_amo,
        pipeline_id=pipeline_id,
        address_id=address_id,
        delivry_type_id=delivry_type_id,
        payment_id=payment_id,
        product_id=product_id,
    )
    db.add(new_credentials)
    db.commit()
    db.refresh(new_credentials)
    return {"message": "Учетные данные успешно добавлены", "id": new_credentials.id}

@router.delete("/delete-credentials/",
               summary="Удаление учетных данных",
               description="Этот эндпоинт принимает ID (можно узнать в /get-all-credentials/) либо URL AmoCRM для удаление с базы данных, после удаление обработка не будет действовать удаленному объекту")
def delete_credentials(url_amo: str = Query(..., description="Базовый URL AmoCRM"), 
                       id: int = Query(..., description="ID"), 
                       db: Session = Depends(get_db)):
    
    """
    Эндпоинт для удаление учетных данных с базы данных по ID либо по URL AmoCRM
    """

    if not url_amo and not id:
        raise HTTPException(status_code=400, detail="Необходимо указать либо URL Amo, либо ID.")

    query = None
    if url_amo:
        query = db.query(APICredentials).filter(APICredentials.api_url_amo == url_amo).first()
    elif id:
        query = db.query(APICredentials).filter(APICredentials.id == id).first()
    
    if not query:
        raise HTTPException(status_code=404, detail="Запись не найдена.")
    
    db.delete(query)
    db.commit()
    return {"detail": "Запись успешно удалена"}

@router.get("/get-all-credentials/", response_model=List[APICredentialsResponse], summary="Вывести список учеток", description="Выводит весь список учетных данных имеющихся в базе данных")
def get_all_credentials(db: Session = Depends(get_db)):
    credentials = db.query(APICredentials).all()
    return credentials



# @app.get("/get-order/")
# async def get_products():
#     headers = {"Authorization": f"Bearer {API_TOKEN_SATU}"}
#     with open('last_date.txt', 'a+') as f:
#         f.seek(0)
#         date = f.read()
#         date = datetime.strptime(date, "%Y.%m.%dT%H:%M")
    
#     params = {
#         # 'limit': 10,
#         'date_from': date,
#         'status': 'pending',
#     }
    
#     async with httpx.AsyncClient() as client:
#         try:
#             response = await client.get(API_URL_SATU, headers=headers, params=params)
#             response.raise_for_status() 
#         except httpx.HTTPStatusError as exc:
#             raise HTTPException(status_code=exc.response.status_code, detail=f"Ошибка запроса: {exc}")
        
#         return response.json()