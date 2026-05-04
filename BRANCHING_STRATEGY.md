# ChainRight Branching Strategy

## Overview

This document describes the branching model for ChainRight development. The project uses a **multi-path architecture** where different feature areas can be developed in parallel, with strategic merge gates before convergence.

## Branch Structure

### Main Branches (Permanent)

- **main** - Production releases (stable, tagged versions)
- **develop** - Integration branch, receives merged feature branches
- **experimental** - High-risk exploration (optional)

### Feature Categories

All feature branches follow the pattern: `category/feature-name`

## 1. Cryptography Foundations (Phase 1)

**Merge to:** `develop`  
**Priority:** CRITICAL - all other paths depend on this

```
cryptography/ed25519-signatures
  └─ Implement Ed25519 signing for blocks & transactions
  └─ Verify signatures on chain validation
  
cryptography/merkle-trees
  └─ Implement Merkle tree for transaction batching
  └─ Add Merkle root to block headers
  
cryptography/account-model
  └─ Define account structure with nonces, public keys
  └─ Implement account-based state model
  
cryptography/state-trie
  └─ Implement Merkle-Patricia trie for state
  └─ Add state root to block headers
```

**Merge Order:** ed25519 → merkle-trees → account-model → state-trie

## 2. Networking Layer (Phase 2)

**Merge to:** `develop`  
**Dependencies:** cryptography/* (partial)

```
networking/p2p-discovery
  └─ Bootstrap node discovery (DHT or manual)
  └─ Peer manager with connection pooling
  
networking/peer-sync-protocol
  └─ Block propagation protocol
  └─ Transaction pool sync
  
networking/message-propagation
  └─ Message encoding/decoding
  └─ Peer communication middleware
  
networking/libp2p-integration
  └─ Optional: Use libp2p for robust P2P stack
```

**Merge Order:** p2p-discovery → message-propagation → peer-sync → libp2p (optional)

## 3. Physics Engine (Phase 2-3)

**Merge to:** `develop`  
**Dependencies:** Can start in parallel with networking  
**Status:** CORE DIFFERENTIATOR - this is ChainRight's unique advantage

```
physics/relativistic-metrics
  └─ Enhance entropy calculation beyond current geometrics.py
  └─ Add Kullback-Leibler divergence for info measure
  
physics/semantic-curvature-refinement
  └─ Move from character distribution to embedding-based curvature
  └─ Use semantic similarity to detect reasoning "turns"
  
physics/information-energy-calculation
  └─ Refine compression ratio heuristic
  └─ Correlate token count with semantic density
  
physics/gaussian-wells-stability
  └─ Implement confidence basin detection
  └─ Add uncertainty quantification from LLM logits
  └─ Hallucination detection via geometry
  
physics/ricci-flow-surgery
  └─ Implement manifold transition when complexity threshold exceeded
  └─ Archive old manifold + create new genesis with parent link
  └─ Preserve lineage through symbolic cryptographic link
  
physics/big-o-computational-complexity
  └─ Map conversation patterns to Big O notation
  └─ Predict complexity without execution
  
physics/proof-of-effort-synthesis
  └─ Combine all metrics into unified PoE score
  └─ Validate PoE = computational effort expended
```

**Merge Order:** All can develop in parallel, then merge in dependency order:
1. relativistic-metrics
2. semantic-curvature-refinement, information-energy-calculation, gaussian-wells-stability (parallel)
3. ricci-flow-surgery
4. big-o-computational-complexity
5. proof-of-effort-synthesis

## 4. Consensus Mechanisms (Phase 3)

**Merge to:** `develop`  
**Dependencies:** cryptography/*, physics/*, networking/*  
**⚠️ DECISION GATE:** Choose ONE consensus path

```
consensus/pow-difficulty-from-physics
  └─ Extends current PoW with physics-driven difficulty
  └─ difficulty = f(relativistic_metrics)
  └─ Simple, maintains current mining approach
  
consensus/pos-validator-physics-weighted
  └─ Switch to Proof of Stake
  └─ Validator weight = PoE contributions
  └─ Slashing for Byzantine behavior
  
consensus/hybrid-proof-of-effort
  └─ Mixed PoW + PoE scoring
  └─ Best of both worlds approach
  
consensus/manifold-fork-resolution
  └─ Fork choice rule using physical metrics
  └─ Select chain with highest cumulative PoE
```

**Decision:** Which path are you leaning toward?
- **PoW-physics:** Simpler, closer to current impl
- **PoS-weighted:** Better for scaling, requires validator set
- **Hybrid:** Balanced approach

## 5. Storage Backend (Phase 2-3, Parallel)

**Merge to:** `develop`  
**Dependencies:** cryptography/state-trie (for Merkle operations)

```
storage/rocksdb-migration
  └─ Replace JSON file storage with RocksDB
  └─ Key-value store for blocks & state
  
storage/merkle-snapshot
  └─ Implement state snapshots for fast sync
  └─ Checkpoint system for long-running nodes
  
storage/state-sync-protocol
  └─ Fast sync for new nodes (don't replay all blocks)
  └─ Merkle proof download
```

**Merge Order:** rocksdb-migration → merkle-snapshot → state-sync-protocol

## 6. Integration / Deployment Model (Phase 4)

**Merge to:** `develop`  
**Dependencies:** consensus/*, networking/*, storage/*  
**⚠️ DECISION GATE:** Choose ONE deployment model

```
integration/l1-standalone
  └─ Full decentralized P2P network
  └─ You control entire infrastructure
  └─ Highest complexity, full autonomy
  └─ For: Public blockchain networks
  
integration/l2-rollup-optimistic
  └─ Deploy as Optimistic Rollup on Ethereum
  └─ Batches of your blocks → L1 for finality
  └─ Lower gas costs, Ethereum security
  └─ For: Scalability without full decentralization
  
integration/sidechain-model
  └─ Parallel sidechain with periodic L1 anchoring
  └─ Hybrid of L1 and L2 approaches
  └─ Periodic merkle root commits to Ethereum
```

**Decision:** What's your deployment target?
- **L1-Standalone:** Full independence, more work
- **L2-Rollup:** Leverage Ethereum, easier to deploy
- **Sidechain:** Hybrid approach, balanced complexity

## 7. API/RPC Layer (Phase 5)

**Merge to:** `develop`  
**Dependencies:** All previous phases (or at least core infrastructure)

```
api/json-rpc-2.0-core
  └─ Standard JSON-RPC 2.0 endpoints
  └─ eth_*, chain_* methods
  
api/rest-endpoints
  └─ REST API for common operations
  └─ OpenAPI/Swagger documentation
  
api/websocket-subscriptions
  └─ Real-time subscriptions for new blocks
  └─ Event streaming
```

**Merge Order:** json-rpc → rest-endpoints → websocket

## 8. Tooling (Phase 5)

**Merge to:** `develop`  
**Dependencies:** Most infrastructure should be ready

```
tooling/cli-node-runner
  └─ Command-line tool to run a node
  └─ Configuration management
  
tooling/block-explorer
  └─ Web UI for visualizing blocks
  └─ Transaction search, state inspection
  
tooling/monitoring-prometheus
  └─ Prometheus metrics export
  └─ Grafana dashboards
```

## Workflow Examples

### Starting a feature branch

```bash
# Update develop to latest
git checkout develop
git pull origin develop

# Create feature branch off develop
git checkout -b physics/semantic-curvature-refinement

# Make changes, commit, push
git add src/chainright/geometrics.py
git commit -m "feat: add embedding-based semantic curvature"
git push origin physics/semantic-curvature-refinement

# Create PR to develop for review
```

### Merging to develop

```bash
# After PR is approved and CI passes
git checkout develop
git pull origin develop
git merge --no-ff physics/semantic-curvature-refinement
git push origin develop
```

### Release to main

```bash
# When develop is stable and ready
git checkout main
git pull origin main
git merge --no-ff develop
git tag -a v0.2.0 -m "Release v0.2.0: Physics engine foundation"
git push origin main --tags
```

## Dependency Graph

```
                    main
                     ↑
                  develop ←─────────────────────────┐
                    ↑                               │
         ┌──────────┼──────────┬──────────────────┐ │
         │          │          │                  │ │
    Phase 1      Phase 2     Phase 3            Phase 4-5
    (Foundation) (Parallel)  (Decision)         (Polish)
         │          │          │                  │ │
    cryptography/ networking/ physics/  ─┐   storage/    │
    ├─ ed25519    ├─ p2p      ├─ metrics  ├─→ rocksdb   │
    ├─ merkle     ├─ sync     ├─ curvature├─→ snapshot  │
    ├─ account    ├─ message  ├─ energy   │   state-sync│
    └─ state-trie └─ libp2p   ├─ wells    │            │
                              ├─ surgery  │         ┌──┴─────────────┬──────────┐
                              ├─ big-o    │         │                │          │
                              └─ poe      ├──→ consensus/  integration/  api/  tooling/
                                                ├─ pow-physics  ├─ l1         ├─ json-rpc
                                                ├─ pos-weighted ├─ l2-rollup  ├─ rest
                                                ├─ hybrid       └─ sidechain  └─ websocket
                                                └─ fork-resolve
```

## Decision Gates

**Gate 1: After Phase 2** - Decide consensus mechanism
- [ ] Will we use PoW physics, PoS weighted, or Hybrid?

**Gate 2: After Phase 3** - Decide deployment model
- [ ] Will we build L1 standalone, L2 rollup, or sidechain?

## Status Tracking

Create issues for each branch with labels:
- `phase-1`: Foundation work
- `phase-2`: Parallel infrastructure
- `phase-3`: Consensus decision
- `phase-4`: Integration
- `phase-5`: Polish & tooling

## Commands Reference

```bash
# List all local branches
git branch -a

# List only feature branches
git branch -a | grep -E 'cryptography|physics|networking|consensus|storage|integration|api|tooling'

# Switch to a branch
git checkout physics/semantic-curvature-refinement

# Delete a local branch
git branch -d physics/old-approach

# Delete a remote branch
git push origin --delete physics/old-approach

# Create and push all branches to remote
git push origin --all
```

---

**Next Steps:**
1. Push all branches to remote: `git push origin --all`
2. Assign team members to branch groups
3. Start with Phase 1: cryptography foundations
4. Track progress in GitHub Issues
