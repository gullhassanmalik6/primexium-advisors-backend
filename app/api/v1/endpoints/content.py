from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_roles
from app.database.session import get_db
from app.models.content import ContentItem, ContentType
from app.models.user import User, UserRole
from app.schemas.content import ContentCreate, ContentResponse, ContentUpdate

public_router = APIRouter(prefix="/content", tags=["content"])
admin_router = APIRouter(prefix="/admin/content", tags=["admin-content"])

STAFF_ROLES = (
    UserRole.ADMIN,
    UserRole.COUNSELLOR,
    UserRole.DOCUMENTATION_OFFICER,
    UserRole.FINANCE,
    UserRole.MARKETING,
)

staff_required = require_roles(*STAFF_ROLES)


@public_router.get("", response_model=list[ContentResponse])
def list_published_content(
    content_type: ContentType | None = None,
    db: Session = Depends(get_db),
) -> list[ContentItem]:
    query = select(ContentItem).where(ContentItem.is_published.is_(True))
    if content_type is not None:
        query = query.where(ContentItem.content_type == content_type)
    return list(db.scalars(query.order_by(ContentItem.sort_order.asc(), ContentItem.created_at.desc())).all())


@public_router.get("/{content_type}/{slug}", response_model=ContentResponse)
def get_published_content(
    content_type: ContentType,
    slug: str,
    db: Session = Depends(get_db),
) -> ContentItem:
    item = db.scalar(
        select(ContentItem).where(
            ContentItem.content_type == content_type,
            ContentItem.slug == slug,
            ContentItem.is_published.is_(True),
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    return item


@admin_router.get("", response_model=list[ContentResponse])
def admin_list_content(
    content_type: ContentType | None = None,
    published_only: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> list[ContentItem]:
    query = select(ContentItem)
    if content_type is not None:
        query = query.where(ContentItem.content_type == content_type)
    if published_only is True:
        query = query.where(ContentItem.is_published.is_(True))
    if published_only is False:
        query = query.where(ContentItem.is_published.is_(False))
    return list(db.scalars(query.order_by(ContentItem.sort_order.asc(), ContentItem.updated_at.desc())).all())


@admin_router.post("", response_model=ContentResponse, status_code=status.HTTP_201_CREATED)
def admin_create_content(
    payload: ContentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> ContentItem:
    existing = db.scalar(
        select(ContentItem).where(
            ContentItem.content_type == payload.content_type,
            ContentItem.slug == payload.slug.strip(),
        )
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already exists for this type")

    item = ContentItem(
        content_type=payload.content_type,
        slug=payload.slug.strip(),
        title=payload.title.strip(),
        summary=payload.summary,
        body=payload.body,
        data=payload.data or {},
        is_published=payload.is_published,
        sort_order=payload.sort_order,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@admin_router.patch("/{content_id}", response_model=ContentResponse)
def admin_update_content(
    content_id: UUID,
    payload: ContentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> ContentItem:
    item = db.get(ContentItem, content_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")

    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        conflict = db.scalar(
            select(ContentItem).where(
                ContentItem.content_type == item.content_type,
                ContentItem.slug == data["slug"].strip(),
                ContentItem.id != item.id,
            )
        )
        if conflict:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slug already exists")
        data["slug"] = data["slug"].strip()
    if "title" in data and data["title"] is not None:
        data["title"] = data["title"].strip()

    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@admin_router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_content(
    content_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(staff_required),
) -> None:
    item = db.get(ContentItem, content_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    db.delete(item)
    db.commit()
