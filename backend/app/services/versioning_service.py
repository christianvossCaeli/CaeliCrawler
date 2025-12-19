"""Service for entity versioning with diff-based storage."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity_version import EntityVersion
from app.models.user import User
from app.services.audit_service import compute_diff

# Create a full snapshot every N versions for efficient reconstruction
SNAPSHOT_INTERVAL = 10


async def create_version(
    session: AsyncSession,
    entity: Any,
    old_data: Dict[str, Any],
    new_data: Dict[str, Any],
    user: Optional[User] = None,
    change_reason: Optional[str] = None,
) -> Optional[EntityVersion]:
    """
    Create a new version record for an entity.

    Args:
        session: Database session
        entity: The entity being versioned
        old_data: Entity state before changes
        new_data: Entity state after changes
        user: User making the change
        change_reason: Optional description of why change was made

    Returns:
        Created EntityVersion or None if no changes
    """
    entity_type = entity.__class__.__name__
    entity_id = entity.id

    # Get versionable fields only (exclude internal fields)
    if hasattr(entity, "get_versionable_fields"):
        fields = entity.get_versionable_fields()
        old_data = {k: v for k, v in old_data.items() if k in fields}
        new_data = {k: v for k, v in new_data.items() if k in fields}

    # Compute diff
    diff = compute_diff(old_data, new_data)

    if not diff:
        return None  # No changes to version

    # Get next version number
    result = await session.execute(
        select(EntityVersion.version_number)
        .where(
            and_(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
            )
        )
        .order_by(desc(EntityVersion.version_number))
        .limit(1)
    )
    last_version = result.scalar_one_or_none() or 0
    new_version_number = last_version + 1

    # Create snapshot every N versions for efficient reconstruction
    snapshot = None
    if new_version_number % SNAPSHOT_INTERVAL == 0:
        snapshot = new_data

    version = EntityVersion(
        entity_type=entity_type,
        entity_id=entity_id,
        version_number=new_version_number,
        diff=diff,
        snapshot=snapshot,
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        change_reason=change_reason,
    )
    session.add(version)

    # Update entity version counter if it has one
    if hasattr(entity, "version"):
        entity.version = new_version_number

    return version


async def create_initial_version(
    session: AsyncSession,
    entity: Any,
    user: Optional[User] = None,
) -> EntityVersion:
    """
    Create the initial version (v1) for a new entity.

    Args:
        session: Database session
        entity: The newly created entity
        user: User who created the entity

    Returns:
        Created EntityVersion
    """
    entity_type = entity.__class__.__name__

    # Get entity data for snapshot
    if hasattr(entity, "to_dict"):
        snapshot = entity.to_dict()
    else:
        snapshot = {"id": str(entity.id)}

    version = EntityVersion(
        entity_type=entity_type,
        entity_id=entity.id,
        version_number=1,
        diff={"created": True},
        snapshot=snapshot,  # Always snapshot on creation
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        change_reason="Initial creation",
    )
    session.add(version)

    # Set entity version if supported
    if hasattr(entity, "version"):
        entity.version = 1

    return version


async def get_version_history(
    session: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> List[EntityVersion]:
    """
    Get version history for an entity.

    Args:
        session: Database session
        entity_type: Model name
        entity_id: Entity ID
        limit: Maximum number of versions to return
        offset: Number of versions to skip

    Returns:
        List of EntityVersion records, newest first
    """
    result = await session.execute(
        select(EntityVersion)
        .where(
            and_(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
            )
        )
        .order_by(desc(EntityVersion.version_number))
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_version(
    session: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    version_number: int,
) -> Optional[EntityVersion]:
    """
    Get a specific version of an entity.

    Args:
        session: Database session
        entity_type: Model name
        entity_id: Entity ID
        version_number: Version number to retrieve

    Returns:
        EntityVersion or None if not found
    """
    result = await session.execute(
        select(EntityVersion).where(
            and_(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
                EntityVersion.version_number == version_number,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_latest_version_number(
    session: AsyncSession,
    entity_type: str,
    entity_id: UUID,
) -> int:
    """
    Get the latest version number for an entity.

    Args:
        session: Database session
        entity_type: Model name
        entity_id: Entity ID

    Returns:
        Latest version number or 0 if no versions exist
    """
    result = await session.execute(
        select(EntityVersion.version_number)
        .where(
            and_(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
            )
        )
        .order_by(desc(EntityVersion.version_number))
        .limit(1)
    )
    return result.scalar_one_or_none() or 0


async def reconstruct_at_version(
    session: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    target_version: int,
) -> Optional[Dict[str, Any]]:
    """
    Reconstruct entity state at a specific version.

    Uses snapshots for efficiency when available.

    Args:
        session: Database session
        entity_type: Model name
        entity_id: Entity ID
        target_version: Version number to reconstruct

    Returns:
        Entity state dict at that version, or None if version doesn't exist
    """
    # Find nearest snapshot at or before target version
    snapshot_result = await session.execute(
        select(EntityVersion)
        .where(
            and_(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
                EntityVersion.version_number <= target_version,
                EntityVersion.snapshot.isnot(None),
            )
        )
        .order_by(desc(EntityVersion.version_number))
        .limit(1)
    )
    snapshot_version = snapshot_result.scalar_one_or_none()

    # If we have a snapshot exactly at target version, return it
    if snapshot_version and snapshot_version.version_number == target_version:
        return dict(snapshot_version.snapshot)

    # Start from snapshot or empty state
    if snapshot_version:
        state = dict(snapshot_version.snapshot)
        start_version = snapshot_version.version_number + 1
    else:
        state = {}
        start_version = 1

    # Apply diffs from start to target
    versions_result = await session.execute(
        select(EntityVersion)
        .where(
            and_(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
                EntityVersion.version_number >= start_version,
                EntityVersion.version_number <= target_version,
            )
        )
        .order_by(EntityVersion.version_number)
    )

    for version in versions_result.scalars():
        for field, change in version.diff.items():
            if field == "created":
                continue
            if isinstance(change, dict) and "new" in change:
                state[field] = change["new"]

    return state if state else None


async def get_version_count(
    session: AsyncSession,
    entity_type: str,
    entity_id: UUID,
) -> int:
    """
    Get the total number of versions for an entity.

    Args:
        session: Database session
        entity_type: Model name
        entity_id: Entity ID

    Returns:
        Total version count
    """
    from sqlalchemy import func

    result = await session.execute(
        select(func.count(EntityVersion.id)).where(
            and_(
                EntityVersion.entity_type == entity_type,
                EntityVersion.entity_id == entity_id,
            )
        )
    )
    return result.scalar() or 0
