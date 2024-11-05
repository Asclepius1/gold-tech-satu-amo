from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.responses import PlainTextResponse
from endpoint import router as endpoint_router
from fastapi import FastAPI, HTTPException
from service import task

import contextlib
import logging
import codecs



log_file = codecs.open('app.log', 'a+', 'utf-8')
logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    stream=log_file)

logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(task, 'interval', hours=1)
    scheduler.start()
    print("Планировщик запущен")
    logging.info("Планировщик запущено")
    
    yield

    scheduler.shutdown()
    print("Планировщик остановлен")
    logging.info("Планировщик запущено")
    



app = FastAPI(lifespan=lifespan)
app.include_router(endpoint_router)

@app.get("/logs", response_class=PlainTextResponse, tags=['logs'])
def get_logs():
    try:
        with open("app.log", "r", encoding='utf-8') as log_file:
            logs = log_file.read()
        return logs
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Log file not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="194.4.56.35", port=8000)
    # uvicorn.run("main:app", host="localhost", reload=True)
    
