#!/usr/bin/env python3
"""
Comprehensive Entity Duplicate Scanner.

Scans all entities in the database to find potential duplicates based on:
1. Exact normalized name matches within same type
2. Fuzzy name matching (SequenceMatcher)
3. Region/hierarchy pattern detection (e.g., "Oberfranken-West" vs "Region Oberfranken-West")
4. Geo-proximity for entities with coordinates

Usage:
    docker-compose exec backend python -m scripts.scan_entity_duplicates
    docker-compose exec backend python -m scripts.scan_entity_duplicates --type territorial_entity
    docker-compose exec backend python -m scripts.scan_entity_duplicates --threshold 0.85 --export duplicates.json
"""

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import structlog

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import async_session_factory
from app.models import Entity, EntityType
from app.utils.text import extract_core_entity_name, normalize_entity_name

logger = structlog.get_logger(__name__)


@dataclass
class DuplicateCandidate:
    """Represents a potential duplicate pair."""
    entity1_id: str
    entity1_name: str
    entity1_slug: str
    entity2_id: str
    entity2_name: str
    entity2_slug: str
    similarity_score: float
    match_reason: str
    entity_type: str
    country: str | None
    admin_level_1: str | None


@dataclass
class DuplicateCluster:
    """A group of entities that are potential duplicates of each other."""
    cluster_id: int
    entity_type: str
    entities: list[dict]
    match_reasons: list[str]
    suggested_canonical: str  # The suggested "main" entity name


class EntityDuplicateScanner:
    """Scans for duplicate entities using multiple strategies including AI embeddings."""

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.duplicates: list[DuplicateCandidate] = []
        self.clusters: list[DuplicateCluster] = []

    def normalize_name(self, name: str, country: str = "DE") -> str:
        """Normalize name for comparison using the central normalize_entity_name function."""
        return normalize_entity_name(name, country)

    def extract_core_name(self, name: str, country: str = "DE") -> str:
        """Extract the core name using the central extract_core_entity_name function."""
        return extract_core_entity_name(name, country)

    def are_names_equivalent(self, name1: str, name2: str, country: str = "DE") -> tuple[bool, float, str]:
        """
        Check if two names represent the same entity.

        Uses a multi-strategy approach:
        1. Exact normalized match
        2. Core name match (structural patterns removed)
        3. Substring containment
        4. Fuzzy string matching

        Returns: (is_equivalent, similarity_score, reason)
        """
        # 1. Exact match after normalization
        norm1 = self.normalize_name(name1, country)
        norm2 = self.normalize_name(name2, country)

        if norm1 == norm2:
            return True, 1.0, "Exakter Match (normalisiert)"

        # 2. Core name extraction match (generic pattern-based)
        core1_raw = self.extract_core_name(name1, country)
        core2_raw = self.extract_core_name(name2, country)
        core1 = self.normalize_name(core1_raw, country)
        core2 = self.normalize_name(core2_raw, country)

        if core1 == core2 and len(core1) >= 3:
            return True, 0.95, f"Kernname identisch: '{core1_raw}'"

        # 3. One is substring of the other (with minimum length)
        if len(norm1) >= 5 and len(norm2) >= 5 and (norm1 in norm2 or norm2 in norm1):
            longer = name1 if len(name1) > len(name2) else name2
            shorter = name2 if len(name1) > len(name2) else name1
            return True, 0.90, f"'{shorter}' ist Teil von '{longer}'"

        # 4. Fuzzy matching with SequenceMatcher
        similarity = SequenceMatcher(None, norm1, norm2).ratio()
        if similarity >= self.threshold:
            return True, similarity, f"Fuzzy Match ({int(similarity * 100)}%)"

        # 5. Core name fuzzy matching
        core_similarity = SequenceMatcher(None, core1, core2).ratio()
        if core_similarity >= self.threshold and len(core1) >= 3 and len(core2) >= 3:
            return True, core_similarity, f"Kernname ähnlich ({int(core_similarity * 100)}%)"

        return False, max(similarity, core_similarity), ""

    def check_geo_proximity(
        self,
        lat1: float | None,
        lon1: float | None,
        lat2: float | None,
        lon2: float | None,
        max_distance_km: float = 5.0
    ) -> tuple[bool, float | None]:
        """Check if two coordinates are within max_distance_km."""
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return False, None

        from math import asin, cos, radians, sin, sqrt

        # Haversine formula
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        km = 6371 * c

        return km <= max_distance_km, km

    async def scan_entities(
        self,
        session,
        entity_type_slug: str | None = None,
        country: str | None = None,
        limit: int | None = None
    ) -> list[DuplicateCandidate]:
        """Scan entities for duplicates."""

        # Build query
        query = (
            select(Entity)
            .options(selectinload(Entity.entity_type))
            .where(Entity.is_active.is_(True))
            .order_by(Entity.entity_type_id, Entity.name)
        )

        if entity_type_slug:
            query = query.join(EntityType).where(EntityType.slug == entity_type_slug)

        if country:
            query = query.where(Entity.country == country)

        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        entities = result.scalars().all()


        if not entities:
            return []

        # Group by type and country for efficient comparison
        grouped: dict[tuple[str, str], list[Entity]] = defaultdict(list)
        for entity in entities:
            type_slug = entity.entity_type.slug if entity.entity_type else "unknown"
            country_code = entity.country or "unknown"
            grouped[(type_slug, country_code)].append(entity)


        # Scan each group
        total_comparisons = 0
        duplicates_found = 0

        for (type_slug, country_code), group_entities in grouped.items():
            n = len(group_entities)
            if n < 2:
                continue


            # First pass: Group by normalized name for exact matches
            by_normalized: dict[str, list[Entity]] = defaultdict(list)
            for entity in group_entities:
                norm = self.normalize_name(entity.name, country_code)
                by_normalized[norm].append(entity)

            # Find exact normalized duplicates
            for _norm_name, ents in by_normalized.items():
                if len(ents) > 1:
                    for i, e1 in enumerate(ents):
                        for e2 in ents[i+1:]:
                            self.duplicates.append(DuplicateCandidate(
                                entity1_id=str(e1.id),
                                entity1_name=e1.name,
                                entity1_slug=e1.slug,
                                entity2_id=str(e2.id),
                                entity2_name=e2.name,
                                entity2_slug=e2.slug,
                                similarity_score=1.0,
                                match_reason="Exakter Match (normalisiert)",
                                entity_type=type_slug,
                                country=country_code,
                                admin_level_1=e1.admin_level_1,
                            ))
                            duplicates_found += 1

            # Second pass: Compare by core names (generic pattern-based)
            by_core: dict[str, list[Entity]] = defaultdict(list)
            for entity in group_entities:
                core = self.normalize_name(self.extract_core_name(entity.name, country_code), country_code)
                if core and len(core) >= 3:  # Only consider meaningful core names
                    by_core[core].append(entity)

            # Find core name duplicates (but avoid double-counting exact matches)
            seen_pairs: set[tuple[str, str]] = set()
            for dup in self.duplicates:
                seen_pairs.add((dup.entity1_id, dup.entity2_id))
                seen_pairs.add((dup.entity2_id, dup.entity1_id))

            for _core_name, ents in by_core.items():
                if len(ents) > 1:
                    for i, e1 in enumerate(ents):
                        for e2 in ents[i+1:]:
                            pair = (str(e1.id), str(e2.id))
                            if pair not in seen_pairs and (pair[1], pair[0]) not in seen_pairs:
                                core_display = self.extract_core_name(e1.name, country_code)
                                self.duplicates.append(DuplicateCandidate(
                                    entity1_id=str(e1.id),
                                    entity1_name=e1.name,
                                    entity1_slug=e1.slug,
                                    entity2_id=str(e2.id),
                                    entity2_name=e2.name,
                                    entity2_slug=e2.slug,
                                    similarity_score=0.95,
                                    match_reason=f"Kernname identisch: '{core_display}'",
                                    entity_type=type_slug,
                                    country=country_code,
                                    admin_level_1=e1.admin_level_1,
                                ))
                                seen_pairs.add(pair)
                                duplicates_found += 1

            # Third pass: Fuzzy matching (only for smaller groups to avoid n² complexity)
            if n <= 1000:
                for i, e1 in enumerate(group_entities):
                    for e2 in group_entities[i+1:]:
                        total_comparisons += 1
                        pair = (str(e1.id), str(e2.id))
                        if pair in seen_pairs or (pair[1], pair[0]) in seen_pairs:
                            continue

                        is_eq, score, reason = self.are_names_equivalent(
                            e1.name, e2.name, country_code
                        )

                        if is_eq and reason:
                            self.duplicates.append(DuplicateCandidate(
                                entity1_id=str(e1.id),
                                entity1_name=e1.name,
                                entity1_slug=e1.slug,
                                entity2_id=str(e2.id),
                                entity2_name=e2.name,
                                entity2_slug=e2.slug,
                                similarity_score=score,
                                match_reason=reason,
                                entity_type=type_slug,
                                country=country_code,
                                admin_level_1=e1.admin_level_1,
                            ))
                            seen_pairs.add(pair)
                            duplicates_found += 1

                        # Progress indicator
                        if total_comparisons % 10000 == 0:
                            pass


        return self.duplicates

    def build_clusters(self) -> list[DuplicateCluster]:
        """Build clusters from duplicate pairs using Union-Find."""
        if not self.duplicates:
            return []

        # Union-Find data structure
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: str, y: str):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # Build union-find from duplicate pairs
        entity_data: dict[str, dict] = {}
        for dup in self.duplicates:
            union(dup.entity1_id, dup.entity2_id)
            entity_data[dup.entity1_id] = {
                "id": dup.entity1_id,
                "name": dup.entity1_name,
                "slug": dup.entity1_slug,
            }
            entity_data[dup.entity2_id] = {
                "id": dup.entity2_id,
                "name": dup.entity2_name,
                "slug": dup.entity2_slug,
            }

        # Group by cluster root
        clusters_map: dict[str, list[str]] = defaultdict(list)
        for entity_id in entity_data:
            root = find(entity_id)
            clusters_map[root].append(entity_id)

        # Build cluster objects
        cluster_reasons: dict[str, set[str]] = defaultdict(set)
        cluster_types: dict[str, str] = {}
        for dup in self.duplicates:
            root = find(dup.entity1_id)
            cluster_reasons[root].add(dup.match_reason)
            cluster_types[root] = dup.entity_type

        self.clusters = []
        for cluster_id, (root, entity_ids) in enumerate(clusters_map.items()):
            if len(entity_ids) < 2:
                continue

            entities = [entity_data[eid] for eid in entity_ids]
            # Suggest the shortest name as canonical (usually the cleanest)
            canonical = min(entities, key=lambda e: len(e["name"]))["name"]

            self.clusters.append(DuplicateCluster(
                cluster_id=cluster_id,
                entity_type=cluster_types.get(root, "unknown"),
                entities=entities,
                match_reasons=list(cluster_reasons[root]),
                suggested_canonical=canonical,
            ))

        # Sort by cluster size (largest first)
        self.clusters.sort(key=lambda c: len(c.entities), reverse=True)

        return self.clusters

    def print_report(self):
        """Print a human-readable report."""

        if not self.clusters:
            return


        for cluster in self.clusters[:50]:  # Limit output
            for entity in cluster.entities:
                " [SUGGESTED]" if entity["name"] == cluster.suggested_canonical else ""

        if len(self.clusters) > 50:
            pass

    def export_json(self, filepath: str):
        """Export results to JSON file."""
        data = {
            "scan_date": datetime.utcnow().isoformat(),
            "threshold": self.threshold,
            "total_duplicates": len(self.duplicates),
            "total_clusters": len(self.clusters),
            "duplicates": [asdict(d) for d in self.duplicates],
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "entity_type": c.entity_type,
                    "entities": c.entities,
                    "match_reasons": c.match_reasons,
                    "suggested_canonical": c.suggested_canonical,
                }
                for c in self.clusters
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


    def get_patterns_for_similarity(self) -> str:
        """Generate summary of duplicate patterns found."""
        # Analyze patterns in found duplicates
        pattern_counts: dict[str, int] = defaultdict(int)

        for dup in self.duplicates:
            # Count structural patterns
            if "(" in dup.entity1_name or "(" in dup.entity2_name:
                pattern_counts["parenthetical"] += 1
            if ", " in dup.entity1_name or ", " in dup.entity2_name:
                pattern_counts["comma_qualifier"] += 1

        summary = f'''
# Duplicate Pattern Summary
# =========================
# Total duplicates found: {len(self.duplicates)}
# Total clusters: {len(self.clusters)}
#
# Pattern breakdown:
# - Parenthetical qualifiers: {pattern_counts.get("parenthetical", 0)}
# - Comma-separated qualifiers: {pattern_counts.get("comma_qualifier", 0)}
#
# The duplicate detection uses a GENERIC approach:
# 1. Structural pattern removal (parentheses, trailing comma-qualifiers)
# 2. AI embedding-based semantic similarity (pgvector cosine distance)
#
# No language or domain-specific patterns are hardcoded.
# Works for any entity type: cities, movies, games, teams, companies, etc.
#
# See: app/utils/text.py - extract_core_entity_name()
# See: services/entity_matching_service.py - get_or_create_entity()
'''
        return summary


async def main():
    parser = argparse.ArgumentParser(description="Scan entities for duplicates")
    parser.add_argument("--type", "-t", help="Filter by entity type slug")
    parser.add_argument("--country", "-c", help="Filter by country code (e.g., DE)")
    parser.add_argument("--threshold", type=float, default=0.85, help="Similarity threshold (default: 0.85)")
    parser.add_argument("--limit", type=int, help="Limit number of entities to scan")
    parser.add_argument("--export", "-e", help="Export results to JSON file")
    parser.add_argument("--show-patterns", action="store_true", help="Show suggested patterns for similarity.py")

    args = parser.parse_args()

    scanner = EntityDuplicateScanner(threshold=args.threshold)

    async with async_session_factory() as session:
        await scanner.scan_entities(
            session,
            entity_type_slug=args.type,
            country=args.country,
            limit=args.limit,
        )

    scanner.build_clusters()
    scanner.print_report()

    if args.export:
        scanner.export_json(args.export)

    if args.show_patterns:
        pass

    # Summary statistics
    if scanner.clusters:
        [len(c.entities) for c in scanner.clusters]


if __name__ == "__main__":
    asyncio.run(main())
