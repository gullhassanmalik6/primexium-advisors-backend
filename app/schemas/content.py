from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.content import ContentType


class ContentCreate(BaseModel):
    content_type: ContentType
    slug: str = Field(min_length=2, max_length=255)
    title: str = Field(min_length=2, max_length=255)
    summary: str | None = None
    body: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    is_published: bool = True
    sort_order: int = 0


class ContentUpdate(BaseModel):
    slug: str | None = Field(default=None, min_length=2, max_length=255)
    title: str | None = Field(default=None, min_length=2, max_length=255)
    summary: str | None = None
    body: str | None = None
    data: dict[str, Any] | None = None
    is_published: bool | None = None
    sort_order: int | None = None


class ContentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content_type: ContentType
    slug: str
    title: str
    summary: str | None
    body: str | None
    data: dict[str, Any]
    is_published: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
