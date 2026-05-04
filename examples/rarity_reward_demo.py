#!/usr/bin/env python3
"""
Example: Rarity scoring and reward ledger in action.

This demonstrates:
1. Computing rarity scores for concepts.
2. Adding rewards to a ledger.
3. Querying wallet balances and bounty pools.
"""

from datetime import datetime, timedelta
from pathlib import Path
import json

from chainright import (
    Wallet, UserProfile, UseEvent,
    SourceKind, RarityMetrics, compute_rarity_score, sliver_weight_for_use,
    RewardEvent, RewardLedger
)


def main():
    print("=" * 60)
    print("ChainRight Rarity & Reward System Demo")
    print("=" * 60)
    
    # 1. Create wallets for creators and users
    print("\n1. Creating wallets...")
    creator_wallet = Wallet.create("Genesis Creator")
    user_wallet_1 = Wallet.create("User Alice")
    user_wallet_2 = Wallet.create("User Bob")
    print(f"   Creator: {creator_wallet.address}")
    print(f"   User 1:  {user_wallet_1.address}")
    print(f"   User 2:  {user_wallet_2.address}")
    
    # 2. Create reward ledger
    print("\n2. Initializing reward ledger...")
    ledger = RewardLedger()
    print(f"   Ledger path: {ledger.data_dir}")
    
    # 3. Compute rarity scores for different concepts
    print("\n3. Computing rarity scores for sample concepts...")
    
    now = datetime.utcnow()
    
    # Concept A: Common word (e.g., "the")
    concept_a = compute_rarity_score(
        concept_id="word_the",
        frequency_percentile=0.95,
        creation_date=now - timedelta(days=100),
        source_kind=SourceKind.GENESIS_BLOCK,
        total_uses=10_000,
        now=now,
    )
    print(f"   A. 'the' (common, from genesis):")
    print(f"      Rarity: {concept_a.base_weight:.4f}")
    
    # Concept B: Rare domain term
    concept_b = compute_rarity_score(
        concept_id="ricci_flow_surgery",
        frequency_percentile=0.001,
        creation_date=now - timedelta(days=1),
        source_kind=SourceKind.GENESIS_BLOCK,
        total_uses=5,
        now=now,
    )
    print(f"   B. 'Ricci flow surgery' (rare, new genesis):")
    print(f"      Rarity: {concept_b.base_weight:.4f}")
    
    # Concept C: User-generated, moderately common
    concept_c = compute_rarity_score(
        concept_id="user_insight_42",
        frequency_percentile=0.5,
        creation_date=now - timedelta(days=7),
        source_kind=SourceKind.USER_GENERATED,
        total_uses=100,
        now=now,
    )
    print(f"   C. User-generated insight (moderate, 1 week old):")
    print(f"      Rarity: {concept_c.base_weight:.4f}")
    
    # 4. Simulate uses and add rewards
    print("\n4. Simulating concept uses and logging rewards...")
    
    # User 1 retrieves the common word "the"
    sliver_a_retrieval = sliver_weight_for_use(concept_a.base_weight, "retrieval")
    ledger.add_reward(
        event_id="evt_001",
        wallet_address=user_wallet_1.address,
        concept_id="word_the",
        use_kind="retrieval",
        sliver_weight=sliver_a_retrieval,
        source_genesis_id="gen_001",
        metadata={"description": "Retrieved 'the' from genesis"},
    )
    print(f"   evt_001: User 1 retrieved 'the' → {sliver_a_retrieval:.4f} slivers")
    
    # User 2 validates the rare domain term (high effort)
    sliver_b_validation = sliver_weight_for_use(concept_b.base_weight, "validation")
    ledger.add_reward(
        event_id="evt_002",
        wallet_address=user_wallet_2.address,
        concept_id="ricci_flow_surgery",
        use_kind="validation",
        sliver_weight=sliver_b_validation,
        source_genesis_id="gen_002",
        metadata={"description": "Validated rare domain term"},
    )
    print(f"   evt_002: User 2 validated 'Ricci flow' → {sliver_b_validation:.4f} slivers")
    
    # User 1 uses the rare term for training
    sliver_b_training = sliver_weight_for_use(concept_b.base_weight, "training")
    ledger.add_reward(
        event_id="evt_003",
        wallet_address=user_wallet_1.address,
        concept_id="ricci_flow_surgery",
        use_kind="training",
        sliver_weight=sliver_b_training,
        source_genesis_id="gen_002",
        metadata={"description": "Used rare term in training run"},
    )
    print(f"   evt_003: User 1 trained with 'Ricci flow' → {sliver_b_training:.4f} slivers")
    
    # User 1 generates with user-generated concept
    sliver_c_generation = sliver_weight_for_use(concept_c.base_weight, "generation")
    ledger.add_reward(
        event_id="evt_004",
        wallet_address=user_wallet_1.address,
        concept_id="user_insight_42",
        use_kind="generation",
        sliver_weight=sliver_c_generation,
        source_genesis_id=None,
        metadata={"description": "Generated with user insight"},
    )
    print(f"   evt_004: User 1 generated with insight → {sliver_c_generation:.4f} slivers")
    
    # 5. Query wallet balances
    print("\n5. Wallet balances:")
    for wallet, label in [(user_wallet_1, "User 1"), (user_wallet_2, "User 2")]:
        balance = ledger.get_wallet_balance(wallet.address)
        print(f"   {label} ({wallet.address[:16]}...): {balance:.4f} slivers")
    
    # 6. Concept usage stats
    print("\n6. Concept usage summary:")
    for concept_id in ["word_the", "ricci_flow_surgery", "user_insight_42"]:
        uses = ledger.get_concept_uses(concept_id)
        total_slivers = sum(e.sliver_weight for e in uses)
        print(f"   {concept_id}: {len(uses)} uses, {total_slivers:.4f} total slivers")
    
    # 7. Bounty pool summary
    print("\n7. Bounty pool status:")
    print(f"   Ledger has {len(ledger.bounty_pools)} bounty pools")
    for genesis_id, pool in ledger.bounty_pools.items():
        print(f"   {genesis_id}: {pool.use_count} uses, {pool.total_slivers_from_uses:.4f} total slivers")
        print(f"            → Creator earns: {pool.creator_slivers_earned:.4f} slivers")
    
    # 8. Overall ledger summary
    print("\n8. Ledger summary:")
    summary = ledger.summary()
    for key, val in summary.items():
        print(f"   {key}: {val}")
    
    # 9. Export ledger
    export_path = Path.home() / ".chainright" / "rewards" / "demo_export.json"
    ledger.export_ledger(export_path)
    print(f"\n9. Exported ledger to: {export_path}")
    
    print("\n" + "=" * 60)
    print("Demo complete! Check math and adjust TODO items as needed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
