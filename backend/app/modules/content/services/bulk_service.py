"""Content module - bulk operations service."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.content.models import ArticleStatus
from app.modules.content.schemas import (
    BulkAction,
    BulkOperationItemResult,
    BulkOperationRequest,
    BulkOperationSummary,
    BulkResourceType,
)
from app.modules.content.services.article_service import ArticleService
from app.modules.content.services.case_service import CaseService
from app.modules.content.services.faq_service import FAQService
from app.modules.content.services.review_service import ReviewService


class BulkOperationService:
    """Service for bulk operations on content."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.article_service = ArticleService(db)
        self.case_service = CaseService(db)
        self.faq_service = FAQService(db)
        self.review_service = ReviewService(db)

    async def execute(
        self, tenant_id: UUID, request: BulkOperationRequest
    ) -> BulkOperationSummary:
        """Execute bulk operation synchronously."""
        results: list[BulkOperationItemResult] = []

        for item_id in request.ids:
            try:
                await self._execute_single(
                    tenant_id=tenant_id,
                    resource_type=request.resource_type,
                    action=request.action,
                    item_id=item_id,
                )
                results.append(BulkOperationItemResult(
                    id=item_id,
                    status="success",
                    message=f"{request.action.value} completed",
                ))
            except Exception as e:
                results.append(BulkOperationItemResult(
                    id=item_id,
                    status="error",
                    message=str(e),
                ))

        succeeded = sum(1 for r in results if r.status == "success")
        failed = sum(1 for r in results if r.status == "error")

        return BulkOperationSummary(
            total=len(request.ids),
            succeeded=succeeded,
            failed=failed,
            details=results,
        )

    async def _execute_single(
        self,
        tenant_id: UUID,
        resource_type: BulkResourceType,
        action: BulkAction,
        item_id: UUID,
    ) -> None:
        """Execute action on a single resource."""
        if resource_type == BulkResourceType.ARTICLES:
            await self._execute_article_action(tenant_id, action, item_id)
        elif resource_type == BulkResourceType.CASES:
            await self._execute_case_action(tenant_id, action, item_id)
        elif resource_type == BulkResourceType.FAQ:
            await self._execute_faq_action(tenant_id, action, item_id)
        elif resource_type == BulkResourceType.REVIEWS:
            await self._execute_review_action(tenant_id, action, item_id)

    async def _execute_article_action(
        self, tenant_id: UUID, action: BulkAction, item_id: UUID
    ) -> None:
        """Execute action on an article."""
        if action == BulkAction.PUBLISH:
            await self.article_service.publish(item_id, tenant_id)
        elif action == BulkAction.UNPUBLISH:
            await self.article_service.unpublish(item_id, tenant_id)
        elif action == BulkAction.ARCHIVE:
            article = await self.article_service.get_by_id(item_id, tenant_id)
            article.archive()
            await self.db.flush()
        elif action == BulkAction.DELETE:
            await self.article_service.soft_delete(item_id, tenant_id)

    async def _execute_case_action(
        self, tenant_id: UUID, action: BulkAction, item_id: UUID
    ) -> None:
        """Execute action on a case."""
        if action == BulkAction.PUBLISH:
            await self.case_service.publish(item_id, tenant_id)
        elif action == BulkAction.UNPUBLISH:
            await self.case_service.unpublish(item_id, tenant_id)
        elif action == BulkAction.ARCHIVE:
            case = await self.case_service.get_by_id(item_id, tenant_id)
            case.status = ArticleStatus.ARCHIVED.value
            await self.db.flush()
        elif action == BulkAction.DELETE:
            await self.case_service.soft_delete(item_id, tenant_id)

    async def _execute_faq_action(
        self, tenant_id: UUID, action: BulkAction, item_id: UUID
    ) -> None:
        """Execute action on a FAQ."""
        faq = await self.faq_service.get_by_id(item_id, tenant_id)
        if action == BulkAction.PUBLISH:
            faq.is_published = True
            await self.db.flush()
        elif action == BulkAction.UNPUBLISH:
            faq.is_published = False
            await self.db.flush()
        elif action == BulkAction.DELETE:
            await self.faq_service.soft_delete(item_id, tenant_id)
        # Archive not applicable for FAQ

    async def _execute_review_action(
        self, tenant_id: UUID, action: BulkAction, item_id: UUID
    ) -> None:
        """Execute action on a review."""
        if action == BulkAction.PUBLISH:
            # For reviews, publish means approve
            await self.review_service.approve(item_id, tenant_id)
        elif action == BulkAction.UNPUBLISH:
            # For reviews, unpublish means reject
            await self.review_service.reject(item_id, tenant_id)
        elif action == BulkAction.DELETE:
            await self.review_service.soft_delete(item_id, tenant_id)
        # Archive not applicable for reviews
