from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdvisoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    category: str | None = Field(default=None, max_length=64)
    is_active: bool = True

    @field_validator("title", "content", "category")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("text field cannot be blank")
        return normalized


class AdvisoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    category: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None

    @field_validator("title", "content", "category")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("text field cannot be blank")
        return normalized


class AdvisoryRead(BaseModel):
    id: int
    hara_area_id: int
    title: str
    content: str
    category: str | None
    is_active: bool
    created_by_user_id: int
    updated_by_user_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
