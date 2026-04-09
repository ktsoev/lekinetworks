from typing import Optional

from pydantic import BaseModel, Field, model_validator


class SiteRequestCodeBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)


class SiteVerifyCodeBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    code: str = Field(..., min_length=4, max_length=12)


class SiteTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SiteMeResponse(BaseModel):
    id: int
    email: str


class SiteVpnOrderBody(BaseModel):
    site_user_id: int = Field(..., ge=1)
    duration_days: int = Field(..., ge=1, le=3650)


class SiteVpnExtendBody(BaseModel):
    device_id: int = Field(..., ge=1)
    duration_days: int = Field(..., ge=1, le=3650)


class SiteVpnDeviceBody(BaseModel):
    device_id: int = Field(..., ge=1)


class SitePromocodeBody(BaseModel):
    promocode: str = Field(..., min_length=1, max_length=128)


class SitePaymentLogBody(BaseModel):
    site_user_id: int = Field(..., ge=1)
    amount: int = Field(..., description="Для RUB — целые рубли")
    currency: str = Field(..., min_length=1, max_length=8)
    product_id: str = Field(..., min_length=1, max_length=64)
    device_id: int = Field(..., ge=0)
    payment_type: str = Field(..., min_length=1, max_length=32)
    external_id: Optional[str] = Field(
        None,
        max_length=128,
        description="Id платежа у провайдера; для идемпотентности webhook (уникален в БД)",
    )


class SiteCheckoutBody(BaseModel):
    plan_key: str = Field(..., min_length=1, max_length=32)
    return_url: str = Field(..., min_length=8, max_length=2048)
    email: Optional[str] = Field(None, max_length=255)
    extend: bool = Field(
        False,
        description="false — новая подписка (новый ключ); true — продлить device_id",
    )
    device_id: Optional[int] = Field(None, ge=1, description="Обязателен при extend=true")

    @model_validator(mode="after")
    def _device_required_for_extend(self):
        if self.extend and self.device_id is None:
            raise ValueError("device_id is required when extend is true")
        return self


class SiteCheckoutResponse(BaseModel):
    payment_id: str
    payment_url: str
    amount: float
    currency: str
    plan_key: str
    duration_days: int


class SitePaymentSiteRow(BaseModel):
    id: int
    amount: int
    currency: str
    product_id: str
    device_id: int
    payment_type: str
    external_id: Optional[str] = None
    created_at: str


class SiteVpnSubscriptionItem(BaseModel):
    device_id: int
    username: str
    subscription_url: str
    expire_at: Optional[str] = None
    status: str


class SiteSubscriptionOverviewResponse(BaseModel):
    site_user_id: int
    panel_telegram_id: str
    panel_reachable: bool
    has_active_vpn: bool
    subscriptions: list[SiteVpnSubscriptionItem]
    payments: list[SitePaymentSiteRow]
