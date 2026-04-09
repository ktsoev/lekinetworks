from fastapi import APIRouter, Request

from app.forward import forward_site_webhook

router = APIRouter()


@router.post("/yookassa")
async def webhook_yookassa(request: Request):
    return await forward_site_webhook(request, "yookassa")


@router.post("/cryptobot")
async def webhook_cryptobot(request: Request):
    return await forward_site_webhook(request, "cryptobot")


@router.post("/oxprocessing")
async def webhook_oxprocessing(request: Request):
    return await forward_site_webhook(request, "oxprocessing")
