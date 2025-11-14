"""
Graphiti Checkpoint Service for MySQL-based checkpoint storage.
Provides methods to track which knowledge base entities have been loaded to Neo4j.
Survives Railway deploys and container restarts.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, Set, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import func

from bot.database.database import DATABASE_ENABLED, SessionLocal
from bot.database.models import GraphitiCheckpoint

logger = logging.getLogger(__name__)


class GraphitiCheckpointService:
    """
    Service for managing Graphiti knowledge base loading checkpoints.
    Stores checkpoint data in MySQL to survive container restarts.
    """

    def __init__(self):
        self.db_enabled = DATABASE_ENABLED
        if not self.db_enabled:
            logger.warning("Database is disabled. Checkpoint service will be skipped.")

    def is_loaded(self, entity_id: str, db: Optional[Session] = None) -> bool:
        """
        Check if an entity has already been loaded to Neo4j.

        Args:
            entity_id: Unique entity ID from knowledge base
            db: Database session (optional)

        Returns:
            True if entity is in checkpoint, False otherwise
        """
        if not self.db_enabled:
            return False

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            exists = db.query(GraphitiCheckpoint).filter(
                GraphitiCheckpoint.entity_id == entity_id
            ).first() is not None

            return exists

        except Exception as e:
            logger.error(f"Error checking if entity {entity_id} is loaded: {e}")
            return False

        finally:
            if close_session:
                db.close()

    def mark_loaded(
        self,
        entity_id: str,
        entity_type: str,
        episode_id: Optional[str] = None,
        tier: Optional[int] = None,
        batch_number: Optional[int] = None,
        db: Optional[Session] = None
    ) -> bool:
        """
        Mark an entity as successfully loaded to Neo4j.

        Args:
            entity_id: Unique entity ID
            entity_type: Entity type (FAQ, Lesson, Correction, etc.)
            episode_id: Episode ID from Neo4j/Graphiti
            tier: Tier number (1=FAQ, 2=Lessons, 3=Questions)
            batch_number: Batch number
            db: Database session (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self.db_enabled:
            return False

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # Check if already exists
            existing = db.query(GraphitiCheckpoint).filter(
                GraphitiCheckpoint.entity_id == entity_id
            ).first()

            if existing:
                # Update existing checkpoint
                existing.episode_id = episode_id
                existing.loaded_at = datetime.utcnow()
                logger.debug(f"Updated checkpoint for {entity_id}")
            else:
                # Create new checkpoint
                checkpoint = GraphitiCheckpoint(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    episode_id=episode_id,
                    tier=tier,
                    batch_number=batch_number,
                    loaded_at=datetime.utcnow()
                )
                db.add(checkpoint)

            db.commit()
            return True

        except IntegrityError as e:
            db.rollback()
            logger.warning(f"Integrity error marking {entity_id} as loaded (already exists?): {e}")
            return True  # Already exists, consider it success

        except Exception as e:
            db.rollback()
            logger.error(f"Error marking {entity_id} as loaded: {e}")
            return False

        finally:
            if close_session:
                db.close()

    def get_loaded_count(
        self,
        entity_type: Optional[str] = None,
        db: Optional[Session] = None
    ) -> int:
        """
        Get count of loaded entities.

        Args:
            entity_type: Filter by entity type (optional)
            db: Database session (optional)

        Returns:
            Number of loaded entities
        """
        if not self.db_enabled:
            return 0

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            query = db.query(func.count(GraphitiCheckpoint.entity_id))

            if entity_type:
                query = query.filter(GraphitiCheckpoint.entity_type == entity_type)

            count = query.scalar()
            return count or 0

        except Exception as e:
            logger.error(f"Error getting loaded count: {e}")
            return 0

        finally:
            if close_session:
                db.close()

    def get_loaded_ids(
        self,
        entity_type: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Set[str]:
        """
        Get set of loaded entity IDs.

        Args:
            entity_type: Filter by entity type (optional)
            db: Database session (optional)

        Returns:
            Set of entity IDs that have been loaded
        """
        if not self.db_enabled:
            return set()

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            query = db.query(GraphitiCheckpoint.entity_id)

            if entity_type:
                query = query.filter(GraphitiCheckpoint.entity_type == entity_type)

            ids = {row[0] for row in query.all()}
            return ids

        except Exception as e:
            logger.error(f"Error getting loaded IDs: {e}")
            return set()

        finally:
            if close_session:
                db.close()

    def get_stats(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Get checkpoint statistics.

        Returns:
            Dictionary with statistics:
            - total: Total number of loaded entities
            - by_type: Count by entity type
            - by_tier: Count by tier
        """
        if not self.db_enabled:
            return {"total": 0, "by_type": {}, "by_tier": {}}

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # Total count
            total = db.query(func.count(GraphitiCheckpoint.entity_id)).scalar() or 0

            # Count by type
            by_type_rows = db.query(
                GraphitiCheckpoint.entity_type,
                func.count(GraphitiCheckpoint.entity_id)
            ).group_by(GraphitiCheckpoint.entity_type).all()

            by_type = {row[0]: row[1] for row in by_type_rows}

            # Count by tier
            by_tier_rows = db.query(
                GraphitiCheckpoint.tier,
                func.count(GraphitiCheckpoint.entity_id)
            ).filter(GraphitiCheckpoint.tier.isnot(None)).group_by(GraphitiCheckpoint.tier).all()

            by_tier = {row[0]: row[1] for row in by_tier_rows}

            return {
                "total": total,
                "by_type": by_type,
                "by_tier": by_tier
            }

        except Exception as e:
            logger.error(f"Error getting checkpoint stats: {e}")
            return {"total": 0, "by_type": {}, "by_tier": {}}

        finally:
            if close_session:
                db.close()

    def clear_all(self, db: Optional[Session] = None) -> bool:
        """
        Clear all checkpoints (for reset).

        Args:
            db: Database session (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self.db_enabled:
            return False

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            deleted_count = db.query(GraphitiCheckpoint).delete()
            db.commit()

            logger.info(f"Cleared {deleted_count} checkpoint entries")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error clearing checkpoints: {e}")
            return False

        finally:
            if close_session:
                db.close()

    def clear_by_type(
        self,
        entity_type: str,
        db: Optional[Session] = None
    ) -> bool:
        """
        Clear checkpoints for a specific entity type.

        Args:
            entity_type: Entity type to clear
            db: Database session (optional)

        Returns:
            True if successful, False otherwise
        """
        if not self.db_enabled:
            return False

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            deleted_count = db.query(GraphitiCheckpoint).filter(
                GraphitiCheckpoint.entity_type == entity_type
            ).delete()
            db.commit()

            logger.info(f"Cleared {deleted_count} {entity_type} checkpoint entries")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Error clearing {entity_type} checkpoints: {e}")
            return False

        finally:
            if close_session:
                db.close()


# Singleton instance
_checkpoint_service = None


def get_checkpoint_service() -> GraphitiCheckpointService:
    """Get singleton instance of GraphitiCheckpointService"""
    global _checkpoint_service
    if _checkpoint_service is None:
        _checkpoint_service = GraphitiCheckpointService()
    return _checkpoint_service
