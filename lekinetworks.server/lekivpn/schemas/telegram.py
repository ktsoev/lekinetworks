from typing import Optional

from pydantic import BaseModel


class UserRegisterRequest(BaseModel):
    telegram_id: str = None
    telegram_name: str = None
    referred_by_id: Optional[str] = None


class UserOrder(BaseModel):
    telegram_id: str = None
    device_id: int = None
    vpn_key: str = None
    expiry_date: str = None


class VpnRequest(BaseModel):
    telegram_id: str = None
    device_id: int = None


class VpnOrderRequest(BaseModel):
    telegram_id: str = None
    duration_days: int = None


class VpnExtendRequest(VpnOrderRequest):
    device_id: int = None


class User(BaseModel):
    telegram_id: str = None


class ReferredData(BaseModel):
    referred_id: str = None
    expiry_date: str = None


class PromocodeData(User):
    promocode: str = None


class PromocodeResponse(User):
    duration_days: int = None
    vpn_url: str = None


class PaymentLogRequest(BaseModel):
    telegram_id: str = None
    amount_kopecks: int = None
    currency: str = None
    product_id: str = None
    device_id: int = None
    payment_type: str = None
