from typing import Optional

from pydantic import BaseModel, Field, model_validator


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
