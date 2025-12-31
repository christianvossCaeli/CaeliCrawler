#!/usr/bin/env python3
"""
Audit Script for Contact Facets

Analyzes existing contact facet values and categorizes them:
- Real persons (name contains first/last name pattern)
- Organizations/departments (no person name pattern)
- Roles without names (only function like "Bürgermeister")
- Duplicates (same person across different entities)

This script helps identify contacts that should be converted to
Person or Organization entities for the new entity reference feature.

Usage:
    python scripts/audit_contact_facets.py --output audit_report.json
    python scripts/audit_contact_facets.py --format csv --output audit_report.csv
"""

import argparse
import asyncio
import csv
import json
import logging
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_session_context
from app.models import FacetType, FacetValue

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ContactAnalysis:
    """Analysis result for a single contact facet value."""
    facet_value_id: str
    entity_id: str
    entity_name: str
    contact_name: str
    contact_role: str | None
    contact_email: str | None
    contact_phone: str | None
    category: str  # 'person', 'organization', 'role_only', 'unknown'
    confidence: float  # 0.0 - 1.0
    reasoning: str
    potential_duplicates: list[str]  # List of other facet_value_ids with similar names


@dataclass
class AuditSummary:
    """Summary of the audit results."""
    total_contacts: int
    persons: int
    organizations: int
    roles_only: int
    unknown: int
    potential_duplicates: int
    timestamp: str


class ContactAuditor:
    """Audits contact facet values for entity reference conversion."""

    # Organization indicators (German and English)
    ORG_PATTERNS = [
        r'\bgmbh\b', r'\bag\b', r'\be\.v\.?\b', r'\bverein\b', r'\bverband\b',
        r'\bgesellschaft\b', r'\bbehörde\b', r'\bamt\b', r'\bministerium\b',
        r'\bdirektion\b', r'\babteilung\b', r'\bregierung\b', r'\bverwaltung\b',
        r'\bbundesland\b', r'\bkreis\b', r'\blandkreis\b', r'\bstadt\b',
        r'\bgemeinde\b', r'\bkommune\b', r'\bregion\b', r'\bbezirk\b',
        r'\buniversität\b', r'\bhochschule\b', r'\binstitut\b', r'\bstiftung\b',
        r'\bzuständig', r'\bplanungsbehörde\b', r'\bregionalverband\b',
        r'\bfachbereich\b', r'\breferat\b', r'\bdezernat\b', r'\bsekretariat\b',
        # Additional patterns found in audit
        r'\bplanungsverband\b', r'\bplanungsverbände\b', r'\blandesamt\b',
        r'\blandtag\b', r'\blandesregierung\b', r'\blandesplanungsbehörde\b',
        r'\bverbandsversammlung\b', r'\bgenehmigungsdirektion\b',
        r'\bregionaldirektion\b', r'\bplanungsausschuss\b',
        r'\bbezirksregierung\b', r'\bregierungsbezirk\b',
    ]

    # Role-only patterns (titles/functions without names)
    ROLE_PATTERNS = [
        r'^bürgermeister(in)?$', r'^oberbürgermeister(in)?$',
        r'^landrat\b', r'^landrät', r'^amtsleiter', r'^dezernent',
        r'^fachbereichsleiter', r'^abteilungsleiter', r'^sachbearbeiter',
        r'^pressesprecher', r'^ansprechpartner', r'^kontakt$',
        r'^zuständige\s+\w+behörde', r'^zuständiger?\s+\w+',
        r'^regionsbeauftragter?\b', r'^träger\s+der\s+\w+',
    ]

    # Person name patterns (German first names are often capitalized, 2-4 words)
    PERSON_PATTERNS = [
        # Title + Name patterns (Dr., Prof., Dipl.-Geogr., Dr.-Ing.)
        r'^(dr\.?\-?ing\.?|dr\.|prof\.|dipl\.?\-?\w*\.?)\s*[\w\-]+\s+[\w\-]+',
        # First Last patterns (with capitalized words, including hyphenated)
        r'^[A-ZÄÖÜ][a-zäöüß]+\s+[A-ZÄÖÜ][a-zäöüß\-]+$',
        # First Middle Last (including hyphenated names)
        r'^[A-ZÄÖÜ][a-zäöüß]+\s+[A-ZÄÖÜ][a-zäöüß\-]+\s+[A-ZÄÖÜ][a-zäöüß\-]+$',
        # Names with nobility particles (von, van, de, etc.)
        r'^[A-ZÄÖÜ][a-zäöüß]+\s+(von|van|de|zu|vom)\s+[A-ZÄÖÜ][a-zäöüß\-]+$',
        # Hyphenated first names (Klaus-Dieter, Hans-Peter)
        r'^[A-ZÄÖÜ][a-zäöüß]+\-[A-ZÄÖÜ][a-zäöüß]+\s+[A-ZÄÖÜ][a-zäöüß\-]+$',
        # Hyphenated surnames only (First Geiß-Netthöfel)
        r'^[A-ZÄÖÜ][a-zäöüß]+\s+[A-ZÄÖÜ][a-zäöüß]+\-[A-ZÄÖÜ][a-zäöüß]+$',
    ]

    def __init__(self, session):
        self.session = session
        self.name_index: dict[str, list[str]] = defaultdict(list)  # normalized_name -> [facet_value_ids]

    async def run_audit(self) -> tuple[list[ContactAnalysis], AuditSummary]:
        """Run the full audit and return results."""
        logger.info("Starting contact facet audit...")

        # Get all contact facet values
        contact_type = await self._get_contact_facet_type()
        if not contact_type:
            logger.error("No 'contact' facet type found in database")
            return [], AuditSummary(0, 0, 0, 0, 0, 0, datetime.now().isoformat())

        facet_values = await self._get_contact_facet_values(contact_type.id)
        logger.info(f"Found {len(facet_values)} contact facet values to analyze")

        # Build name index for duplicate detection
        self._build_name_index(facet_values)

        # Analyze each contact
        results = []
        for fv in facet_values:
            analysis = self._analyze_contact(fv)
            results.append(analysis)

        # Generate summary
        summary = self._generate_summary(results)

        logger.info(f"Audit complete. Summary: {summary}")
        return results, summary

    async def _get_contact_facet_type(self) -> FacetType | None:
        """Get the contact facet type."""
        result = await self.session.execute(
            select(FacetType).where(FacetType.slug == 'contact')
        )
        return result.scalar_one_or_none()

    async def _get_contact_facet_values(self, facet_type_id: UUID) -> list[FacetValue]:
        """Get all contact facet values with their entities."""
        result = await self.session.execute(
            select(FacetValue)
            .options(selectinload(FacetValue.entity))
            .where(
                FacetValue.facet_type_id == facet_type_id,
                FacetValue.is_active.is_(True),
            )
            .order_by(FacetValue.created_at.desc())
        )
        return result.scalars().all()

    def _build_name_index(self, facet_values: list[FacetValue]):
        """Build index of normalized names for duplicate detection."""
        for fv in facet_values:
            name = self._extract_name(fv.value)
            if name:
                normalized = self._normalize_name(name)
                self.name_index[normalized].append(str(fv.id))

    def _extract_name(self, value: dict) -> str | None:
        """Extract contact name from facet value."""
        if not value:
            return None
        return value.get('name', '') or ''

    def _extract_role(self, value: dict) -> str | None:
        """Extract contact role from facet value."""
        if not value:
            return None
        return value.get('role', '') or value.get('position', '')

    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison."""
        # Lowercase, remove extra whitespace, remove special chars
        normalized = name.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized

    def _analyze_contact(self, fv: FacetValue) -> ContactAnalysis:
        """Analyze a single contact facet value."""
        value = fv.value or {}
        name = self._extract_name(value)
        role = self._extract_role(value)

        # Determine category
        category, confidence, reasoning = self._categorize_contact(name, role)

        # Find potential duplicates
        normalized_name = self._normalize_name(name) if name else ''
        duplicates = []
        if normalized_name and normalized_name in self.name_index:
            duplicates = [id for id in self.name_index[normalized_name] if id != str(fv.id)]

        return ContactAnalysis(
            facet_value_id=str(fv.id),
            entity_id=str(fv.entity_id),
            entity_name=fv.entity.name if fv.entity else 'Unknown',
            contact_name=name or '',
            contact_role=role,
            contact_email=value.get('email'),
            contact_phone=value.get('phone') or value.get('telefon'),
            category=category,
            confidence=confidence,
            reasoning=reasoning,
            potential_duplicates=duplicates,
        )

    def _categorize_contact(self, name: str, role: str | None) -> tuple[str, float, str]:
        """
        Categorize a contact as person, organization, role_only, or unknown.

        Returns: (category, confidence, reasoning)
        """
        if not name:
            if role:
                return ('role_only', 0.9, f"No name, only role: {role}")
            return ('unknown', 0.5, "No name or role provided")

        name_lower = name.lower()

        # Check for organization patterns
        for pattern in self.ORG_PATTERNS:
            if re.search(pattern, name_lower):
                return ('organization', 0.9, f"Contains organization indicator: {pattern}")

        # Check for role-only patterns
        for pattern in self.ROLE_PATTERNS:
            if re.match(pattern, name_lower):
                return ('role_only', 0.85, f"Matches role pattern: {pattern}")

        # Check for person name patterns
        for pattern in self.PERSON_PATTERNS:
            if re.match(pattern, name):
                return ('person', 0.85, "Matches person name pattern")

        # Heuristic: 2-3 capitalized words likely a person
        words = name.split()
        if 2 <= len(words) <= 3:
            capitalized = sum(1 for w in words if w[0].isupper() and w[1:].islower())
            if capitalized == len(words):
                return ('person', 0.7, f"Name has {len(words)} capitalized words (likely person)")

        # If role contains person-like name pattern, might still be person
        if role and re.search(r'\b(herr|frau|dr\.|prof\.)\b', role.lower()):
            return ('person', 0.6, "Role contains person title")

        # Long names with multiple parts often organizations
        if len(words) > 4:
            return ('organization', 0.6, f"Long name with {len(words)} words (likely organization)")

        return ('unknown', 0.4, "Could not determine category")

    def _generate_summary(self, results: list[ContactAnalysis]) -> AuditSummary:
        """Generate summary statistics from results."""
        categories = defaultdict(int)
        duplicate_count = 0

        for r in results:
            categories[r.category] += 1
            if r.potential_duplicates:
                duplicate_count += 1

        return AuditSummary(
            total_contacts=len(results),
            persons=categories['person'],
            organizations=categories['organization'],
            roles_only=categories['role_only'],
            unknown=categories['unknown'],
            potential_duplicates=duplicate_count,
            timestamp=datetime.now().isoformat(),
        )


def export_to_json(results: list[ContactAnalysis], summary: AuditSummary, output_path: str):
    """Export results to JSON file."""
    data = {
        'summary': asdict(summary),
        'results': [asdict(r) for r in results],
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"JSON report saved to: {output_path}")


def export_to_csv(results: list[ContactAnalysis], output_path: str):
    """Export results to CSV file."""
    fieldnames = [
        'facet_value_id', 'entity_id', 'entity_name', 'contact_name',
        'contact_role', 'contact_email', 'contact_phone', 'category',
        'confidence', 'reasoning', 'duplicate_count'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for r in results:
            row = asdict(r)
            row['duplicate_count'] = len(row.pop('potential_duplicates', []))
            writer.writerow(row)

    logger.info(f"CSV report saved to: {output_path}")


async def main():
    parser = argparse.ArgumentParser(description='Audit contact facet values for entity conversion')
    parser.add_argument('--output', '-o', default='contact_audit_report.json',
                       help='Output file path (default: contact_audit_report.json)')
    parser.add_argument('--format', '-f', choices=['json', 'csv'], default='json',
                       help='Output format (default: json)')
    args = parser.parse_args()

    async with get_session_context() as session:
        auditor = ContactAuditor(session)
        results, summary = await auditor.run_audit()

        # Print summary to console

        # Export results
        if args.format == 'json':
            export_to_json(results, summary, args.output)
        else:
            export_to_csv(results, args.output)

        # Show sample results
        for r in results[:10]:
            if r.potential_duplicates:
                pass


if __name__ == '__main__':
    asyncio.run(main())
