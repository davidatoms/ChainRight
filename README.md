# ChainRight: The Relativistic Conversation Blockchain

[![CI](https://github.com/davidatoms/ChainRight/actions/workflows/ci.yml/badge.svg)](https://github.com/davidatoms/ChainRight/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/chainright.svg)](https://pypi.org/project/chainright/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://davidatoms.github.io/ChainRight)

**ChainRight** is a decentralized engine designed to transform transient AI interactions into immutable, attributed, and verifiable "Knowledge Assets."

By treating every conversation as a trajectory through a semantic manifold, ChainRight uses relativistic metrics to determine the "computational effort" required to preserve a thought. It is the first blockchain system where the mining difficulty is a direct function of the **cognitive complexity** of the data being recorded.

---

## The Vision: From Flat Logs to Curved Manifolds

Standard chat logs are "flat" — they record text but lose the context of effort, stability, and intellectual "sharpness." ChainRight introduces a **Relativistic Engine** that gauges each interaction using three core geometric primitives:

1. **Semantic Curvature:** Measures the "turn" in information space. A predictable chat has low curvature; a radical cognitive shift or a creative breakthrough has high curvature.
2. **Information Energy:** Derived from information density. Dense, technical, or code-heavy responses represent higher "Energy" states.
3. **Gaussian Wells:** Identifies "Basins of Stability" (where a model is confident and structured) versus "Chaotic Ridges" (where a model is transitioning or potentially hallucinating).

---

## Big O as Computational Gravity

In traditional computer science, **Big O notation** measures the efficiency of an algorithm. In **ChainRight**, we use Big O to define the **Proof of Effort**:

- **O(1) - Geodesic Paths:** Simple, stable conversations are computationally "cheap" to mine.
- **O(n log n) - State Transitions:** Complex logic requiring significant internal work from the AI increases curvature, raising the mining difficulty.
- **O(Singularity) - Ricci Flow Surgery:** When a conversation reaches an extreme level of complexity, the engine performs a **Ricci Flow Surgery**. The current manifold is archived and a new one is birthed, preserving the lineage through a symbolic cryptographic link.

---

## Features

- **Multi-Provider Support:** Integrated with Claude, GPT-4, Gemini, Mistral, and DeepSeek.
- **Device Awareness:** Automatically detects if running on a Compute Node (server/PC) or Edge Signal device and adjusts constraints accordingly.
- **Knowledge Provenance:** Every block records the `node_type`, `latency_ms`, and `geometric_score`, proving exactly how much "work" went into generating that piece of knowledge.

---

## Quick Start

```bash
pip install chainright
```

Start a blockchain-hashed conversation with any LLM:

```bash
chainright-llm --provider anthropic
chainright-llm --provider openai --model gpt-4o
```

Or use Python directly:

```python
from chainright import Blockchain

bc = Blockchain()
bc.add_data("My first immutable thought.")
bc.mine_pending_data()
print(bc.is_chain_valid())  # True
```

---

## License

- **Codebase**: Licensed under the [Apache License, Version 2.0](LICENSE).
- **Conversation Datasets**: Licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

---

**ChainRight**: Mapping the geometry of thought.
