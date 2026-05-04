# Rarity Scoring & Bounty Pool Math for ChainRight

**Date**: May 3, 2026  
**Status**: Prototype (TODOs marked for refinement)

---

## 1. Rarity Scoring

### 1.1 Overview

Each concept has a **base_weight** that determines how many slivers users earn when using it.

```
base_weight = rarity_from_frequency × freshness_multiplier × source_multiplier
```

This score is then multiplied by a use-type multiplier to get the final **sliver_weight** for a specific use.

---

### 1.2 Component Formulas

#### **1.2.1 Rarity from Frequency**

Concepts that are rare should earn more slivers (to incentivize discovery of new knowledge).

```
frequency_percentile ∈ [0.0, 1.0]
  where:
    0.0 = concept appears in 0% of corpus (ultra-rare)
    1.0 = concept appears in 100% of corpus (ultra-common, like "the")

rarity_from_frequency = 1.0 - frequency_percentile

Examples:
  - "the" (appears in 95% of corpus) → frequency_percentile = 0.95 → rarity = 0.05
  - "Ricci flow surgery" (appears in 0.1% of corpus) → frequency_percentile = 0.001 → rarity = 0.999
```

**TODO-1.1**: Refine frequency mapping for extreme cases.
- **Current**: Linear (1.0 - percentile).
- **Suggestion 1**: Log scale to compress very common words.
  ```
  rarity_from_frequency = 1.0 - log(1.0 + frequency_percentile) / log(2.0)
  ```
  **Effect**: "the" (0.95) → rarity ≈ 0.06 (slightly lower); "Ricci" (0.001) → rarity ≈ 0.998 (nearly same).
  
- **Suggestion 2**: Power law (2-power compression).
  ```
  rarity_from_frequency = (1.0 - frequency_percentile) ** 2.0
  ```
  **Effect**: More aggressive penalty for common words; encourages mining rare concepts.

---

#### **1.2.2 Freshness Multiplier**

Newer concepts should earn more initially to encourage recent innovation.

```
age_days = (now - creation_date).days

freshness_multiplier = max(0.5, 1.0 - (age_days / 365.0))

Examples:
  - Age 0 days (new) → multiplier = 1.0 (full reward)
  - Age 30 days → multiplier = 0.917 (8.3% decay)
  - Age 180 days (6 months) → multiplier = 0.507 ≈ 0.5 (floor reached)
  - Age 365 days (1 year) → multiplier = 0.5 (floor)
```

**TODO-1.2**: Tune freshness decay curve.
- **Current**: Linear decay over 365 days, floor at 0.5.
- **Suggestion 1**: Exponential decay (steeper early, then flattens).
  ```
  freshness_multiplier = 0.5 + 0.5 * exp(-age_days / 180.0)
  ```
  **Effect**: 50% of reward loss in first 6 months; then gradual stabilization.

- **Suggestion 2**: Piecewise (no decay for 30 days, then linear).
  ```
  if age_days < 30: freshness_multiplier = 1.0
  else: freshness_multiplier = max(0.5, 1.0 - ((age_days - 30) / 335.0))
  ```
  **Effect**: New concepts get a 1-month "grace period" at full value.

- **Suggestion 3**: Adaptive (depends on concept popularity).
  ```
  if total_uses < 1000:
    decay_period = 365  # normal decay
  elif total_uses < 100000:
    decay_period = 180  # faster decay for popular concepts
  else:
    decay_period = 90   # very fast decay for viral concepts
  ```
  **Rationale**: Popular concepts stabilize; no need to boost indefinitely.

---

#### **1.2.3 Source Multiplier**

Different sources should be weighted differently by quality/curation level.

```
source_multiplier_map = {
    GENESIS_BLOCK: 1.2,     # Peer-reviewed, curated genesis block
    TRAINING_DERIVED: 1.0,  # Output from training pipeline (baseline)
    USER_GENERATED: 0.9,    # Direct user input (potentially noisy)
}

base_weight = rarity_from_frequency × freshness_multiplier × source_multiplier

Examples:
  - Rare word from genesis → 0.999 × 1.0 × 1.2 = 1.199
  - Common word from user → 0.05 × 0.917 × 0.9 ≈ 0.041
```

**TODO-1.3**: Decide source weighting strategy.
- **Current**: Genesis 1.2x, Training 1.0x, User 0.9x.
- **Suggestion 1**: Penalize user-generated more (0.8x) to reduce spam.
- **Suggestion 2**: Reward user-generated higher (1.1x) to bootstrap community contributions.
- **Suggestion 3**: Add multi-tier based on verification.
  ```
  VERIFIED_USER: 1.1x
  UNVERIFIED_USER: 0.7x
  ```

---

#### **1.2.4 Saturation / Capping**

Very popular concepts should not generate runaway payouts.

```
# TODO-1.4: Add saturation logic.

Option 1: Linear cap
  if total_uses > 100_000:
    base_weight *= (100_000 / total_uses)
  Effect: Cap rewards at 100k uses; concept still earns but doesn't compound.

Option 2: Logarithmic diminishing returns
  saturation = log(1.0 + total_uses) / log(1.0 + 100_000)
  base_weight *= saturation
  Effect: Smooth curve; older, popular concepts earn less per new use.

Option 3: Tiered saturation (discrete)
  uses_tier = total_uses // 10_000
  saturation_factor = 1.0 / (1.0 + 0.1 * uses_tier)
  base_weight *= saturation_factor
  Effect: Every 10k uses, payout reduces by 10%.
```

---

### 1.3 Use-Type Multiplier

When a concept is actually used (retrieval, generation, training, validation), apply a use-type multiplier.

```
use_multiplier_map = {
    "retrieval": 0.5,      # Light work; concept already exists
    "generation": 1.0,     # Standard; user generates with this concept
    "validation": 2.0,     # Heavy work; manually reviewed
    "training": 1.5,       # Model learns; contributes to model fitness
}

sliver_weight = base_weight × use_multiplier

Examples:
  - Rare genesis concept retrieved → 1.2 × 0.5 = 0.6 slivers
  - Common user word used for generation → 0.041 × 1.0 = 0.041 slivers
  - Validated domain term in training → 1.5 × 1.5 = 2.25 slivers
```

**TODO-1.5**: Calibrate use multipliers with actual effort data.
- **Current guesses**: based on intuition (retrieval < generation < training < validation).
- **Refinement**: Run pilot with small user group, measure:
  - Average retrieval latency (should be O(1)).
  - Average generation latency (O(n) + model time).
  - Average training session (O(m * n) + compute).
  - Average validation effort (manual review time).
  - Then set multipliers proportional to effort ratio.

---

### 1.4 Summary Formula

```
sliver_weight(concept_id, use_kind) = 
    (1.0 - frequency_percentile)
    × max(0.5, 1.0 - (age_days / 365.0))
    × source_multiplier[source_kind]
    × [apply saturation if needed]
    × use_multiplier[use_kind]
```

---

## 2. Bounty Pool Math

### 2.1 Overview

When concepts from a genesis block are used, a **bounty pool** is created. Portions of slivers earned go back to:
- **Genesis creator**: Royalty for publishing.
- **Original contributors**: If concepts came from other genesis blocks.
- **Validators/trainers**: If they validated or trained on that data.

---

### 2.2 Bounty Distribution

#### **2.2.1 Creator Share (Tiered by Popularity)**

```
total_slivers_from_uses = sum of all sliver_weight for uses of genesis concepts

# Option A: Fixed percentage (simpler)
creator_pct = 0.10  # 10% always
creator_earnings = total_slivers_from_uses × creator_pct

# Option B: Tiered percentage (more nuanced)
if use_count < 10_000:
    creator_pct = 0.10  # 10%
elif use_count < 100_000:
    creator_pct = 0.08  # 8%
else:
    creator_pct = 0.05  # 5%

creator_earnings = total_slivers_from_uses × creator_pct

Examples (tiered):
  - Genesis used 1,000 times; total slivers = 500
    creator_earnings = 500 × 0.10 = 50 slivers
  
  - Genesis used 50,000 times; total slivers = 25,000
    creator_earnings = 25,000 × 0.08 = 2,000 slivers
  
  - Genesis used 500,000 times; total slivers = 250,000
    creator_earnings = 250,000 × 0.05 = 12,500 slivers
  
  Ratio: 50 → 2,000 → 12,500 (creator still earns more as concept scales, but % decreases)
```

**TODO-2.1**: Decide between fixed vs. tiered creator percentage.
- **Fixed (10%)**: Simpler to explain; consistent; but encourages many small genesis blocks.
- **Tiered**: Rewards scale; but complex; may penalize viral concepts.
- **Hybrid**: Fixed 10% for first 50k uses, then 8% beyond. (Compromise.)

---

#### **2.2.2 Contributor Share (If Provenance Available)**

If the genesis block reused concepts from other genesis blocks, original creators should earn a slice.

```
# TODO-2.2: Implement contributor tracking.
# Current: Stub (not implemented).
# 
# Required data: For each concept in genesis, track if it came from another genesis_id.
# This requires metadata in genesis_builder (provenance chain).
#
# Proposed formula:
#   For each source concept:
#     if source_genesis_id exists:
#       contributor_earnings += total_slivers × 0.05  # 5% per source
#     (Multiple sources can contribute, but cap total at 30%)

# Pseudocode:
source_concepts = genesis_metadata["source_concepts"]
contributor_pool = 0.0
contributor_shares = {}

for source_concept in source_concepts:
    source_genesis_id = source_concept.get("from_genesis_id")
    if source_genesis_id:
        source_creator_wallet = fetch_wallet(source_genesis_id)
        contributor_shares[source_creator_wallet] += total_slivers × 0.05

# Cap contributor pool
contributor_pool = min(0.30, sum(contributor_shares.values()))
for wallet in contributor_shares:
    contributor_shares[wallet] *= (contributor_pool / sum(contributor_shares.values()))
```

---

#### **2.2.3 Validation/Training Share (If Applicable)**

If a genesis block was validated by a user or used to train a model, that user earns slivers.

```
# TODO-2.3: Tie validation rewards to genesis.
# Current: Stub (not implemented).
#
# Proposed:
#   - When a user validates genesis concepts, record validation_event.
#   - Each validation_event earns high slivers (e.g., 2.0x multiplier).
#   - No bounty pool redirect needed (validation is recorded directly as UseEvent).
#
# For training:
#   - When genesis concepts are used as training data, log as training UseEvent.
#   - Training UseEvent earns slivers (via base_weight × 1.5 multiplier).
#   - No bounty redirect (creator already gets % via bounty pool).
```

---

### 2.3 Summary Distribution

```
total_slivers_from_genesis_uses = S

creator_pct = [fixed 10% OR tiered based on use_count]
contributor_pct = 0.05 per source (capped 30%)  # TODO
validation_pct = 0 (separate UseEvent)          # TODO
remaining_pct = 1.0 - creator_pct - contributor_pct

Example (tiered, 1 source contributor):
  S = 1000 slivers earned from genesis uses
  creator_pct = 0.10 → creator = 100 slivers
  contributor_pct = 0.05 (1 source) → contributor = 50 slivers
  remaining = 850 slivers (stay in validation/trainer wallets as separate UseEvents)
```

---

### 2.4 Bounty Pool CLI & Inspection

```
# TODO-2.4: Implement CLI commands for bounty inspection.

chainright reward bounty --genesis-id <id> --format json
  Output: { genesis_id, creator_wallet, total_slivers, creator_earnings, contributors, use_count }

chainright reward leaderboard
  Output: Top 100 genesis creators by total_earnings (slivers)
```

---

## 3. Validation & Tuning

### 3.1 Synthetic Test Cases

To validate formulas, run these examples:

**Test 1: Common word (e.g., "the")**
```
concept_id = "word_the"
frequency_percentile = 0.95  # appears in 95% of corpus
creation_date = today - 100 days
source_kind = GENESIS_BLOCK
total_uses = 10_000

rarity = 1.0 - 0.95 = 0.05
freshness = 1.0 - (100 / 365) = 0.726
source = 1.2
base_weight = 0.05 × 0.726 × 1.2 = 0.044

retrieval use: 0.044 × 0.5 = 0.022 slivers
generation use: 0.044 × 1.0 = 0.044 slivers
```

**Test 2: Rare domain term**
```
concept_id = "ricci_flow_surgery"
frequency_percentile = 0.001  # appears in 0.1% of corpus
creation_date = today - 1 day
source_kind = GENESIS_BLOCK
total_uses = 5

rarity = 1.0 - 0.001 = 0.999
freshness = 1.0 - (1 / 365) = 0.997
source = 1.2
base_weight = 0.999 × 0.997 × 1.2 = 1.194

retrieval use: 1.194 × 0.5 = 0.597 slivers
validation use: 1.194 × 2.0 = 2.388 slivers
```

**Test 3: Bounty pool (tiered)**
```
genesis_id = "gen_001"
creator_wallet = "wallet_abc123"
use_count = 50_000
total_slivers_from_uses = 25_000

creator_pct (tiered) = 0.08  (10k-100k tier)
creator_earnings = 25_000 × 0.08 = 2_000 slivers
```

### 3.2 Tuning Checklist

- [ ] **Rarity formula**: Do rare concepts earn noticeably more? (2-10x baseline.)
- [ ] **Freshness decay**: Do old concepts still have value? (0.5x minimum reasonable.)
- [ ] **Use multipliers**: Does validation feel more valuable than retrieval? (2.0x vs. 0.5x reasonable.)
- [ ] **Bounty creator share**: Is 5-10% fair to creator? (Too high = discourages reuse; too low = discourages genesis.)
- [ ] **Saturation**: Do viral concepts eventually stabilize? (No runaway inflation.)
- [ ] **Real data**: Collect 100 uses from pilot users; compute stats; compare to projections.

---

## 4. TODOs (Implementation Order)

1. **TODO-1.1**: Choose frequency mapping (linear vs. log vs. power). **Recommend**: Start linear; refine if testing shows issues.
2. **TODO-1.2**: Choose freshness decay (linear vs. exponential vs. piecewise). **Recommend**: Start linear; tune decay period with user feedback.
3. **TODO-1.3**: Finalize source multipliers (1.2 / 1.0 / 0.9). **Recommend**: Start with current; adjust after seeing distribution.
4. **TODO-1.4**: Add saturation capping. **Recommend**: Implement after first 10k uses of any concept.
5. **TODO-1.5**: Calibrate use multipliers with effort data. **Recommend**: Use synthetic data first; refine with real pilot.
6. **TODO-2.1**: Decide creator share (fixed vs. tiered). **Recommend**: Fixed 10% for now; migrate to tiered after 3 months.
7. **TODO-2.2**: Track provenance & implement contributor shares. **Recommend**: Defer to Phase 2; requires genesis provenance chain.
8. **TODO-2.3**: Wire validation rewards. **Recommend**: Implement validation CLI first, then tie to genesis.
9. **TODO-2.4**: Add bounty inspection CLI. **Recommend**: Build after ledger is working.

---

## References

- [Rarity Score Calculation](src/chainright/rarity.py)
- [Reward Ledger](src/chainright/reward_ledger.py)
- [Use Events](src/chainright/use.py)
- [Wallet Integration](src/chainright/wallet.py)
