from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import asyncio
import uvicorn
from contextlib import asynccontextmanager
import json

from src.database.simple_db import db
from src.services.yookassa_service import get_yookassa_service, init_yookassa_service
from config import SUBSCRIPTION_PLANS, validate_config

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Validate critical environment configuration at startup
    validate_config()
    # Initialize external services that depend on env
    init_yookassa_service()
    # Simple database doesn't need pool initialization
    yield
    # Simple database doesn't need pool closing

app = FastAPI(title="Gemini Image Editor Bot API", lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Gemini Image Editor Bot API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/success")
async def payment_success():
    # Маршрут для redirect после оплаты (для удобного возврата пользователя)
    return {"status": "ok", "message": "Оплата завершена. Вернитесь в Telegram-бота."}

@app.post("/yookassa-webhook")
async def yookassa_webhook(request: Request):
    try:
        body = await request.body()
        webhook_data = json.loads(body)
        
        payment_data = await get_yookassa_service().handle_webhook(webhook_data)
        
        if payment_data and payment_data.get('status') == 'succeeded':
            user_id = payment_data['user_id']
            plan_type = payment_data['plan_type']
            payment_id = payment_data['payment_id']
            amount = payment_data['amount']
            
            plan = SUBSCRIPTION_PLANS.get(plan_type)
            if plan:
                await db.update_subscription(
                    user_id, 
                    plan_type=plan_type,
                    active=True, 
                    duration_days=plan['duration_days']
                )
                
                await db.log_payment(
                    user_id=user_id,
                    payment_id=payment_id,
                    plan_type=plan_type,
                    amount=amount,
                    currency="RUB",
                    status="succeeded",
                    payment_method="yookassa"
                )
        
        return JSONResponse(status_code=200, content={"status": "ok"})
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
