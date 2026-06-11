from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

class GlossaryBase(BaseModel):
    term: str = Field(min_length=1, max_length=255)
    definition: str = Field(min_length=1)

    @field_validator("term", "definition")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text field cannot be blank")
        return normalized

class GlossaryCreate(GlossaryBase):
    pass

class GlossaryUpdate(BaseModel):
    term: str | None = Field(default=None, min_length=1, max_length=255)
    definition: str | None = Field(default=None, min_length=1)

    @field_validator("term", "definition")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("text field cannot be blank")
        return normalized

class GlossaryRead(GlossaryBase):
    id: int
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
