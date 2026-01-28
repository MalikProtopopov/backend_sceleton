"""API routes for content module.

This module includes sub-routers for each content entity:
- topic_router: Topics (public + admin + locales)
- article_router: Articles (public + admin + locales)
- faq_router: FAQ (public + admin + locales)
- case_router: Cases (public + admin + locales)
- review_router: Reviews (public + admin)
- bulk_router: Bulk operations
"""

from fastapi import APIRouter

from app.modules.content.routers import (
    article_router,
    bulk_router,
    case_router,
    faq_router,
    review_router,
    topic_router,
)

router = APIRouter()

# Include all sub-routers
router.include_router(topic_router)
router.include_router(article_router)
router.include_router(faq_router)
router.include_router(case_router)
router.include_router(review_router)
router.include_router(bulk_router)
