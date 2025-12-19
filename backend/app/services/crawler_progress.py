"""Redis-based crawler progress tracking for live updates."""

import json
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

import redis.asyncio as redis

from app.config import settings


class CrawlerProgress:
    """Track crawler progress in Redis for real-time updates."""

    # Redis key patterns
    LOG_KEY = "crawler:log:{job_id}"
    CURRENT_URL_KEY = "crawler:current:{job_id}"
    STATS_KEY = "crawler:stats:{job_id}"
    MAX_LOG_ENTRIES = 50
    LOG_TTL = 3600  # 1 hour

    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def log_url(self, job_id: UUID, url: str, status: str = "fetched", doc_found: bool = False):
        """Log a URL being crawled."""
        r = await self.get_redis()

        entry = {
            "url": url,
            "status": status,
            "doc_found": doc_found,
            "timestamp": datetime.utcnow().isoformat(),
        }

        key = self.LOG_KEY.format(job_id=str(job_id))

        # Add to list (left push = newest first)
        await r.lpush(key, json.dumps(entry))

        # Trim to max entries
        await r.ltrim(key, 0, self.MAX_LOG_ENTRIES - 1)

        # Set TTL
        await r.expire(key, self.LOG_TTL)

        # Update current URL
        current_key = self.CURRENT_URL_KEY.format(job_id=str(job_id))
        await r.set(current_key, url, ex=self.LOG_TTL)

    async def get_log(self, job_id: UUID, limit: int = 20) -> List[Dict]:
        """Get recent log entries for a job."""
        r = await self.get_redis()
        key = self.LOG_KEY.format(job_id=str(job_id))

        entries = await r.lrange(key, 0, limit - 1)
        return [json.loads(e) for e in entries]

    async def get_current_url(self, job_id: UUID) -> Optional[str]:
        """Get the current URL being crawled."""
        r = await self.get_redis()
        key = self.CURRENT_URL_KEY.format(job_id=str(job_id))
        return await r.get(key)

    async def increment_pages(self, job_id: UUID, count: int = 1):
        """Increment pages crawled counter."""
        r = await self.get_redis()
        key = self.STATS_KEY.format(job_id=str(job_id))
        await r.hincrby(key, "pages_crawled", count)
        await r.expire(key, self.LOG_TTL)

    async def increment_documents(self, job_id: UUID, count: int = 1):
        """Increment documents found counter."""
        r = await self.get_redis()
        key = self.STATS_KEY.format(job_id=str(job_id))
        await r.hincrby(key, "documents_found", count)
        await r.expire(key, self.LOG_TTL)

    async def get_stats(self, job_id: UUID) -> Dict:
        """Get current stats for a job."""
        r = await self.get_redis()
        key = self.STATS_KEY.format(job_id=str(job_id))
        stats = await r.hgetall(key)
        return {
            "pages_crawled": int(stats.get("pages_crawled", 0)),
            "documents_found": int(stats.get("documents_found", 0)),
        }

    async def clear_job(self, job_id: UUID):
        """Clear progress data for a job."""
        r = await self.get_redis()
        await r.delete(
            self.LOG_KEY.format(job_id=str(job_id)),
            self.CURRENT_URL_KEY.format(job_id=str(job_id)),
            self.STATS_KEY.format(job_id=str(job_id))
        )

    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# Global instance
crawler_progress = CrawlerProgress()
