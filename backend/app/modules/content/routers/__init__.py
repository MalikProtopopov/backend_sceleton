"""Content module sub-routers."""

from app.modules.content.routers.topic_router import router as topic_router
from app.modules.content.routers.article_router import router as article_router
from app.modules.content.routers.faq_router import router as faq_router
from app.modules.content.routers.case_router import router as case_router
from app.modules.content.routers.review_router import router as review_router
from app.modules.content.routers.bulk_router import router as bulk_router

__all__ = [
    "topic_router",
    "article_router",
    "faq_router",
    "case_router",
    "review_router",
    "bulk_router",
]
