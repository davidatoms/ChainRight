"""Rarity scoring for ChainRight concepts.

This module computes a rarity score for each concept based on:
1. Frequency (how common is this concept in the corpus?)
2. Freshness (is it newly minted or aged?)
3. Source quality (where did it come from: genesis, training, user?)

The rarity score is used to determine sliver weight awarded for each use.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class SourceKind(str, Enum):
    """Source origin type for rarity multiplier."""
    GENESIS_BLOCK = "genesis_block"
    TRAINING_DERIVED = "training_derived"
    USER_GENERATED = "user_generated"


@dataclass
class RarityMetrics:
    """Rarity score breakdown for a concept."""
    concept_id: str
    frequency_percentile: float  # 0.0 (rare) to 1.0 (common)
    age_days: int
    source_kind: SourceKind
    total_uses: int
    creation_date: datetime
    
    # Computed scores (see compute_rarity_score)
    rarity_from_frequency: float  # 0.0 (common) to 1.0 (rare)
    freshness_multiplier: float   # 0.5 to 1.0 (decays over 1 year)
    source_multiplier: float      # 0.9, 1.0, or 1.2
    base_weight: float            # product of above
    
    def to_dict(self) -> dict:
        return {
            "concept_id": self.concept_id,
            "frequency_percentile": self.frequency_percentile,
            "age_days": self.age_days,
            "source_kind": self.source_kind.value,
            "total_uses": self.total_uses,
            "rarity_from_frequency": self.rarity_from_frequency,
            "freshness_multiplier": self.freshness_multiplier,
            "source_multiplier": self.source_multiplier,
            "base_weight": self.base_weight,
        }


def compute_rarity_score(
    concept_id: str,
    frequency_percentile: float,
    creation_date: datetime,
    source_kind: SourceKind,
    total_uses: int,
    now: Optional[datetime] = None,
) -> RarityMetrics:
    """Compute rarity metrics for a concept."""
    if now is None:
        now = datetime.utcnow()
    
    # TODO: Refine frequency-to-rarity mapping. Current: linear inversion.
    # A log or power curve may compress very common words more aggressively.
    rarity_from_frequency = 1.0 - frequency_percentile

    # TODO: Tune freshness decay curve. Current: linear over 365 days.
    # An exponential or piecewise curve may better match how quickly value fades.
    age_days = (now - creation_date).days
    freshness_multiplier = max(0.5, 1.0 - (age_days / 365.0))

    # TODO: Decide source multiplier values. Current proposal favors curated genesis.
    source_multiplier = {
        SourceKind.GENESIS_BLOCK: 1.2,
        SourceKind.TRAINING_DERIVED: 1.0,
        SourceKind.USER_GENERATED: 0.9,
    }[source_kind]

    # TODO: Add saturation/capping for very popular concepts so rewards do not run away.
    base_weight = rarity_from_frequency * freshness_multiplier * source_multiplier
    
    return RarityMetrics(
        concept_id=concept_id,
        frequency_percentile=frequency_percentile,
        age_days=age_days,
        source_kind=source_kind,
        total_uses=total_uses,
        creation_date=creation_date,
        rarity_from_frequency=rarity_from_frequency,
        freshness_multiplier=freshness_multiplier,
        source_multiplier=source_multiplier,
        base_weight=base_weight,
    )


def sliver_weight_for_use(
    base_weight: float,
    use_kind: str,  # "retrieval", "generation", "validation", "training"
) -> float:
    """Compute sliver weight for a single use."""

    # TODO: Calibrate use_multiplier values with real effort data.
    # Retrieval should remain the cheapest, validation the most expensive.
    use_multiplier = {
        "retrieval": 0.5,
        "generation": 1.0,
        "validation": 2.0,
        "training": 1.5,
    }.get(use_kind, 1.0)
    
    return base_weight * use_multiplier
