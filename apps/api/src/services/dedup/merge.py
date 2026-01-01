"""Event merging logic for deduplication."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from src.models.event import Event, GeoPrecision
from src.services.dedup.quality import GEO_PRECISION_SCORE
from src.services.dedup.types import MergeResult


@dataclass
class MergePatch:
    """Patch containing fields to update on existing event."""
    
    fields: dict[str, Any]
    updated_field_names: list[str]


class EventMerger:
    """Merge incoming event data into existing event."""
    
    def build_merge_patch(
        self,
        *,
        existing: Event,
        incoming: dict[str, Any],
        incoming_quality: float,
        existing_quality: float,
    ) -> MergePatch | None:
        """Build a patch for merging incoming data into existing event.
        
        Merge strategy:
        1. If incoming quality > existing: update all non-null incoming fields
        2. If qualities are equal: only fill null fields in existing
        3. If incoming quality < existing: only update if incoming has better specific data
        
        Always:
        - geo_precision: keep higher precision
        - GLIDE number: keep if either has it
        
        Args:
            existing: The existing event
            incoming: Dict of incoming event fields
            incoming_quality: Quality score of incoming data
            existing_quality: Quality score of existing event
            
        Returns:
            MergePatch if updates needed, None otherwise
        """
        updates: dict[str, Any] = {}
        updated_fields: list[str] = []
        
        # 1. GLIDE number - always prefer non-null
        if not existing.glide_number and incoming.get("glide_number"):
            updates["glide_number"] = incoming["glide_number"]
            updated_fields.append("glide_number")
        
        # 2. geo_precision - always keep higher
        incoming_precision = incoming.get("geo_precision")
        if incoming_precision:
            existing_precision = existing.geo_precision or GeoPrecision.unknown
            
            if isinstance(incoming_precision, str):
                incoming_precision = GeoPrecision(incoming_precision)
            
            existing_rank = GEO_PRECISION_SCORE.get(existing_precision, 0)
            incoming_rank = GEO_PRECISION_SCORE.get(incoming_precision, 0)
            
            if incoming_rank > existing_rank:
                updates["geo_precision"] = incoming_precision
                updated_fields.append("geo_precision")
                
                # Also update coordinates if precision is better
                if incoming.get("lat") is not None and incoming.get("lng") is not None:
                    updates["lat"] = incoming["lat"]
                    updates["lng"] = incoming["lng"]
                    updated_fields.extend(["lat", "lng"])
                    
                if incoming.get("geo_method"):
                    updates["geo_method"] = incoming["geo_method"]
                    updated_fields.append("geo_method")
        
        # 3. Quality-based field updates
        if incoming_quality > existing_quality:
            # Incoming is better - take all non-null fields
            self._apply_better_source_fields(existing, incoming, updates, updated_fields)
        elif abs(incoming_quality - existing_quality) < 0.01:
            # Tie - only fill nulls
            self._fill_null_fields(existing, incoming, updates, updated_fields)
        else:
            # Existing is better - only update specific better data
            self._apply_specific_improvements(existing, incoming, updates, updated_fields)
        
        if not updates:
            return None
        
        # Always update timestamp
        updates["updated_at"] = datetime.utcnow()
        
        return MergePatch(
            fields=updates,
            updated_field_names=updated_fields,
        )
    
    def _apply_better_source_fields(
        self,
        existing: Event,
        incoming: dict[str, Any],
        updates: dict[str, Any],
        updated_fields: list[str],
    ) -> None:
        """Apply fields from better quality source."""
        # Text fields
        for field in ["title", "description", "region"]:
            if incoming.get(field) and incoming[field] != getattr(existing, field):
                updates[field] = incoming[field]
                updated_fields.append(field)
        
        # Numeric fields
        if incoming.get("affected_population") and not existing.affected_population:
            updates["affected_population"] = incoming["affected_population"]
            updated_fields.append("affected_population")
        
        # Severity (take from better source)
        if incoming.get("severity") and incoming["severity"] != existing.severity:
            updates["severity"] = incoming["severity"]
            updated_fields.append("severity")
        
        # Source URL (prefer non-null)
        if incoming.get("source_url") and not existing.source_url:
            updates["source_url"] = incoming["source_url"]
            updated_fields.append("source_url")
    
    def _fill_null_fields(
        self,
        existing: Event,
        incoming: dict[str, Any],
        updates: dict[str, Any],
        updated_fields: list[str],
    ) -> None:
        """Only fill fields that are null in existing."""
        fillable = [
            ("description", "description"),
            ("region", "region"),
            ("affected_population", "affected_population"),
            ("source_url", "source_url"),
        ]
        
        for incoming_key, existing_attr in fillable:
            if incoming.get(incoming_key) and getattr(existing, existing_attr) is None:
                updates[incoming_key] = incoming[incoming_key]
                updated_fields.append(incoming_key)
    
    def _apply_specific_improvements(
        self,
        existing: Event,
        incoming: dict[str, Any],
        updates: dict[str, Any],
        updated_fields: list[str],
    ) -> None:
        """Apply only specific improvements from lower-quality source."""
        # Only fill completely missing data
        if incoming.get("description") and not existing.description:
            updates["description"] = incoming["description"]
            updated_fields.append("description")
        
        if incoming.get("affected_population") and not existing.affected_population:
            updates["affected_population"] = incoming["affected_population"]
            updated_fields.append("affected_population")
    
    def create_merge_result(
        self,
        event_id: UUID,
        patch: MergePatch | None,
        incoming_quality: float,
        existing_quality: float,
    ) -> MergeResult:
        """Create a MergeResult from merge operation.
        
        Args:
            event_id: ID of the merged event
            patch: Applied patch or None if no changes
            incoming_quality: Quality score of incoming
            existing_quality: Quality score of existing
            
        Returns:
            MergeResult with details
        """
        if patch is None:
            return MergeResult(
                event_id=event_id,
                updated_fields=[],
                chosen_primary_reason="existing_quality_higher",
                incoming_quality=incoming_quality,
                existing_quality=existing_quality,
            )
        
        if incoming_quality > existing_quality:
            reason = "incoming_quality_higher"
        elif abs(incoming_quality - existing_quality) < 0.01:
            reason = "quality_tie_filled_nulls"
        else:
            reason = "specific_improvements_applied"
        
        return MergeResult(
            event_id=event_id,
            updated_fields=patch.updated_field_names,
            chosen_primary_reason=reason,
            incoming_quality=incoming_quality,
            existing_quality=existing_quality,
        )
