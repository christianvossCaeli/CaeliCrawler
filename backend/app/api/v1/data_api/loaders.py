"""Bulk-loading utilities to avoid N+1 queries."""

from typing import Dict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Document, Category, DataSource


async def bulk_load_documents_with_sources(
    session: AsyncSession, doc_ids: set
) -> Dict[UUID, Document]:
    """Bulk-load documents with their sources to avoid N+1 queries."""
    if not doc_ids:
        return {}
    result = await session.execute(
        select(Document)
        .options(selectinload(Document.source))
        .where(Document.id.in_(doc_ids))
    )
    return {doc.id: doc for doc in result.scalars().all()}


async def bulk_load_categories(
    session: AsyncSession, cat_ids: set
) -> Dict[UUID, Category]:
    """Bulk-load categories to avoid N+1 queries."""
    if not cat_ids:
        return {}
    result = await session.execute(
        select(Category).where(Category.id.in_(cat_ids))
    )
    return {cat.id: cat for cat in result.scalars().all()}


async def bulk_load_sources(
    session: AsyncSession, source_ids: set
) -> Dict[UUID, DataSource]:
    """Bulk-load data sources to avoid N+1 queries."""
    if not source_ids:
        return {}
    result = await session.execute(
        select(DataSource).where(DataSource.id.in_(source_ids))
    )
    return {src.id: src for src in result.scalars().all()}
