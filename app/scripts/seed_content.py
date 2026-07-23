"""Seed CMS content from the default Primexium catalogue.

Usage:
  cd Backend
  python -m app.scripts.seed_content
"""

from datetime import UTC, datetime

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.content import ContentItem, ContentType

SEED = [
    {
        "content_type": ContentType.COUNTRY,
        "slug": "france",
        "title": "France",
        "summary": "Affordable tuition, strong research programs, and pathways into Europe’s job market.",
        "data": {
            "flag": "🇫🇷",
            "universities": "60+",
            "highlights": ["Low tuition public universities", "Post-study work options", "Rich cultural experience"],
        },
        "sort_order": 1,
    },
    {
        "content_type": ContentType.COUNTRY,
        "slug": "germany",
        "title": "Germany",
        "summary": "Tuition-free public universities and strong STEM programs with excellent industry links.",
        "data": {
            "flag": "🇩🇪",
            "universities": "70+",
            "highlights": ["Often tuition-free", "STEM & engineering focus", "18-month job seeker visa"],
        },
        "sort_order": 2,
    },
    {
        "content_type": ContentType.UNIVERSITY,
        "slug": "tu-munich",
        "title": "Technical University of Munich",
        "summary": "STEM",
        "data": {"country": "Germany", "ranking": 37, "focus": "STEM"},
        "sort_order": 1,
    },
    {
        "content_type": ContentType.PACKAGE,
        "slug": "premium",
        "title": "Premium",
        "summary": "99,999 PKR",
        "data": {
            "price": "99,999",
            "currency": "PKR",
            "popular": True,
            "features": [
                "Everything in Basic",
                "SOP Review",
                "Visa Application Support",
                "Interview Preparation",
                "Priority Support",
            ],
        },
        "sort_order": 2,
    },
    {
        "content_type": ContentType.BLOG,
        "slug": "winning-sop-guide",
        "title": "How to Write a Winning Statement of Purpose",
        "summary": "Expert tips to craft an SOP that gets you admitted to your dream university.",
        "body": "A strong SOP clearly connects your academic background, goals, and chosen program.",
        "data": {"category": "Applications", "date": "May 10, 2026"},
        "sort_order": 1,
    },
    {
        "content_type": ContentType.TESTIMONIAL,
        "slug": "sara-ahmed",
        "title": "Sara Ahmed",
        "summary": "Outstanding service! They helped me secure a scholarship and guided me through the entire visa process seamlessly.",
        "data": {
            "university": "University of Toronto",
            "country": "Canada",
            "rating": 5,
        },
        "sort_order": 1,
    },
]


def main() -> None:
    db = SessionLocal()
    created = 0
    try:
        for item in SEED:
            exists = db.scalar(
                select(ContentItem).where(
                    ContentItem.content_type == item["content_type"],
                    ContentItem.slug == item["slug"],
                )
            )
            if exists:
                continue
            db.add(
                ContentItem(
                    content_type=item["content_type"],
                    slug=item["slug"],
                    title=item["title"],
                    summary=item.get("summary"),
                    body=item.get("body"),
                    data=item.get("data", {}),
                    is_published=True,
                    sort_order=item.get("sort_order", 0),
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
            created += 1
        db.commit()
        print(f"Seeded {created} content item(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
