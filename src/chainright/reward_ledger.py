"""Reward ledger for ChainRight wallet-based slivers.

Tracks reward events (uses of concepts) and computes wallet balances and bounty pools.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json


@dataclass
class RewardEvent:
    """Single reward event: user earned slivers for a use."""
    event_id: str
    wallet_address: str
    concept_id: str
    use_kind: str  # "retrieval", "generation", "validation", "training"
    sliver_weight: float
    timestamp: datetime
    source_genesis_id: Optional[str] = None  # If concept came from this genesis block
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class BountyPool:
    """Accumulated bounty for a genesis block.
    
    When concepts from a genesis block are used, a portion of slivers
    go back to the genesis creator and source contributors.
    """
    genesis_id: str
    creator_wallet: str
    total_slivers_from_uses: float = 0.0
    creator_slivers_earned: float = 0.0  # Computed from bounty pct
    contributor_slivers: Dict[str, float] = field(default_factory=dict)  # wallet -> slivers
    use_count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


class RewardLedger:
    """Append-only reward ledger."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize reward ledger.
        
        Args:
            data_dir: Directory to persist ledger (e.g., ~/.chainright/rewards/).
        """
        if data_dir is None:
            data_dir = Path.home() / ".chainright" / "rewards"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.events: List[RewardEvent] = []
        self.bounty_pools: Dict[str, BountyPool] = {}
        self._load_from_disk()
    
    def _load_from_disk(self) -> None:
        """Load ledger from disk if it exists."""
        ledger_file = self.data_dir / "ledger.jsonl"
        if ledger_file.exists():
            with open(ledger_file, "r") as f:
                for line in f:
                    if line.strip():
                        d = json.loads(line)
                        evt = RewardEvent(
                            event_id=d["event_id"],
                            wallet_address=d["wallet_address"],
                            concept_id=d["concept_id"],
                            use_kind=d["use_kind"],
                            sliver_weight=d["sliver_weight"],
                            timestamp=datetime.fromisoformat(d["timestamp"]),
                            source_genesis_id=d.get("source_genesis_id"),
                            metadata=d.get("metadata", {}),
                        )
                        self.events.append(evt)
    
    def _persist_to_disk(self) -> None:
        """Append latest event to ledger file."""
        ledger_file = self.data_dir / "ledger.jsonl"
        if self.events:
            latest = self.events[-1]
            with open(ledger_file, "a") as f:
                f.write(json.dumps(latest.to_dict()) + "\n")
    
    def add_reward(
        self,
        event_id: str,
        wallet_address: str,
        concept_id: str,
        use_kind: str,
        sliver_weight: float,
        source_genesis_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> RewardEvent:
        """
        Record a reward event.
        
        Args:
            event_id: Unique event identifier.
            wallet_address: Recipient wallet.
            concept_id: Concept being used.
            use_kind: Type of use.
            sliver_weight: Slivers earned.
            source_genesis_id: Origin genesis block (if applicable).
            metadata: Additional context.
        
        Returns:
            The created RewardEvent.
        """
        evt = RewardEvent(
            event_id=event_id,
            wallet_address=wallet_address,
            concept_id=concept_id,
            use_kind=use_kind,
            sliver_weight=sliver_weight,
            timestamp=datetime.utcnow(),
            source_genesis_id=source_genesis_id,
            metadata=metadata or {},
        )
        self.events.append(evt)
        self._persist_to_disk()
        
        # Update bounty pools if genesis_id provided
        if source_genesis_id:
            self._update_bounty_for_genesis(source_genesis_id, wallet_address, sliver_weight)
        
        return evt
    
    def _update_bounty_for_genesis(
        self,
        genesis_id: str,
        wallet_address: str,
        sliver_weight: float,
    ) -> None:
        """
        Update bounty pool for a genesis block when one of its concepts is used.
        
        Math:
        -----
        # TODO: Decide bounty percentage. Current proposal: tiered by popularity.
        # Tier 1 (uses 0-10K): creator gets 10%, bounty_pool = 0.10
        # Tier 2 (uses 10K-100K): creator gets 8%, bounty_pool = 0.08
        # Tier 3 (uses 100K+): creator gets 5%, bounty_pool = 0.05
        #
        # Rationale: popular concepts benefit from network effects; fair to scale
        # creator % down but absolute earnings keep growing.
        #
        # Alternative (simpler): fixed 10% always. Easier to reason about.
        # TODO: Decide and implement.
        #
        # TODO: Handle contributor slivers. Current stub just accumulates total.
        # If concepts in genesis came from OTHER genesis blocks, those contributors
        # should get a slice (e.g., 5% each).
        # Requires tracking provenance: which genesis blocks contributed concepts.
        #
        # Suggested flow:
        # 1. Look up concept in genesis metadata (source_concepts).
        # 2. For each source concept, check if it came from another genesis_id.
        # 3. Allocate sliver_weight % to original creators.
        # 4. Remaining % to current creator.
        """
        if genesis_id not in self.bounty_pools:
            # Stub: should fetch creator_wallet from genesis_builder or registry.
            self.bounty_pools[genesis_id] = BountyPool(
                genesis_id=genesis_id,
                creator_wallet="unknown",  # TODO: load from genesis metadata
                total_slivers_from_uses=0.0,
            )
        
        pool = self.bounty_pools[genesis_id]
        pool.total_slivers_from_uses += sliver_weight
        pool.use_count += 1
        
        # TODO: Implement tiered bounty calculation.
        # For now, stub at 10%.
        creator_pct = 0.10
        pool.creator_slivers_earned += sliver_weight * creator_pct
    
    def get_wallet_balance(self, wallet_address: str) -> float:
        """
        Compute total slivers earned by wallet.
        
        Args:
            wallet_address: Wallet to query.
        
        Returns:
            Total slivers.
        """
        return sum(
            evt.sliver_weight
            for evt in self.events
            if evt.wallet_address == wallet_address
        )
    
    def get_wallet_uses(self, wallet_address: str) -> List[RewardEvent]:
        """
        Get all reward events for a wallet.
        
        Args:
            wallet_address: Wallet to query.
        
        Returns:
            List of RewardEvents.
        """
        return [
            evt for evt in self.events
            if evt.wallet_address == wallet_address
        ]
    
    def get_concept_uses(self, concept_id: str) -> List[RewardEvent]:
        """
        Get all reward events for a concept.
        
        Args:
            concept_id: Concept to query.
        
        Returns:
            List of RewardEvents.
        """
        return [
            evt for evt in self.events
            if evt.concept_id == concept_id
        ]
    
    def get_bounty_summary(self, genesis_id: str) -> Optional[BountyPool]:
        """
        Get bounty pool for a genesis block.
        
        Args:
            genesis_id: Genesis ID.
        
        Returns:
            BountyPool or None if not found.
        """
        return self.bounty_pools.get(genesis_id)
    
    def export_ledger(self, output_path: Path) -> None:
        """
        Export ledger to JSON file.
        
        Args:
            output_path: Where to write.
        """
        with open(output_path, "w") as f:
            json.dump(
                {
                    "events": [evt.to_dict() for evt in self.events],
                    "bounty_pools": {
                        gid: pool.to_dict()
                        for gid, pool in self.bounty_pools.items()
                    },
                },
                f,
                indent=2,
            )
    
    def summary(self) -> Dict:
        """
        Get summary statistics.
        
        Returns:
            Dict with totals.
        """
        total_slivers = sum(evt.sliver_weight for evt in self.events)
        unique_wallets = len(set(evt.wallet_address for evt in self.events))
        unique_concepts = len(set(evt.concept_id for evt in self.events))
        
        return {
            "total_events": len(self.events),
            "total_slivers": total_slivers,
            "unique_wallets": unique_wallets,
            "unique_concepts": unique_concepts,
            "genesis_bounties": len(self.bounty_pools),
        }
