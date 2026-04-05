# Relativistic Metrics and Device Awareness

ChainRight uses two systems to dynamically calibrate proof-of-work difficulty: **LLMGeometrics** (which measures the information complexity of each exchange) and **DeviceAwareness** (which classifies the hardware running the node). Together they ensure that mining difficulty is proportional to the actual computational and informational work being done.

---

## LLMGeometrics — measuring information complexity

The `LLMGeometrics` class treats each prompt/response pair as a point on an information manifold and computes several metrics borrowed from physics and information theory.

```python
from chainright.geometrics import LLMGeometrics

geo = LLMGeometrics()

prompt   = "What is Shannon entropy?"
response = "Shannon entropy measures the average uncertainty in a probability distribution..."

metrics = geo.get_full_metrics(prompt, response)
print(metrics)
# {
#   'energy':     0.72,   # information density (compression ratio)
#   'entropy':    0.81,   # Shannon entropy of the text
#   'curvature':  0.34,   # semantic shift between prompt and response
#   'difficulty': 3,      # recommended mining difficulty
# }
```

### What each metric means

| Metric | Source | What it captures |
|--------|--------|-----------------|
| **Entropy** | Shannon entropy of character distribution | How unpredictable / information-rich the text is |
| **Energy** | zlib compression ratio | Information density — how much is packed in |
| **Curvature** | Hellinger-like distance between prompt and response distributions | How much the response diverges semantically from the prompt |
| **Gaussian Well** | Compressibility stability | How stable the information manifold is at this point |
| **Temperature** | Normalized entropy | "Heat" of the exchange — high temperature = high novelty |
| **Power** | Work / time elapsed | Computational throughput of the exchange |

### Difficulty scoring

The difficulty score combines all metrics with a temporal friction factor. A simple, repetitive exchange gets a low difficulty (fast mining). A dense, semantically rich exchange gets a higher difficulty:

```python
difficulty = geo.get_difficulty_score(prompt, response, elapsed_seconds=1.2)
# Returns an integer (e.g., 2–6) used as the proof-of-work target
```

---

## DeviceAwareness — classifying your node

`DeviceAwareness` reads the system's hardware at runtime and classifies the node into one of two tiers. This classification adjusts the difficulty multiplier so that a Raspberry Pi and a server don't compete on equal terms.

```python
from chainright.device_awareness import DeviceAwareness

info = DeviceAwareness.get_system_info()
print(info)
# {
#   'os':        'Linux',
#   'cpu_count': 8,
#   'ram_gb':    16.0,
#   'hostname':  'my-server'
# }

node_type = DeviceAwareness.classify_node()
print(node_type)  # 'COMPUTE_NODE' or 'EDGE_SIGNAL'
```

### Classification rules

| Node type | CPU cores | RAM | Difficulty multiplier |
|-----------|-----------|-----|----------------------|
| `EDGE_SIGNAL` | ≤ 2 | < 2.5 GB | 0.5× (easier mining) |
| `COMPUTE_NODE` | > 2 | ≥ 2.5 GB | 1.0× (standard mining) |

### P2P readiness check

```python
p2p_ready = DeviceAwareness.check_p2p_capability()
print(p2p_ready)  # True / False
```

This tests whether the node can bind a socket for peer-to-peer communication. Useful before attempting to connect to other ChainRight nodes.

### Dynamic configuration

```python
config = DeviceAwareness.get_dynamic_config()
# Returns:
# {
#   'node_type':            'COMPUTE_NODE',
#   'difficulty_multiplier': 1.0,
#   'max_difficulty_clamp':  8,
#   'p2p_capable':          True
# }
```

The blockchain automatically calls this at startup and applies the multiplier to all subsequent mining operations.

---

## Run the device self-test

```bash
python -m chainright.device_awareness
```

Output example:
```
=== ChainRight Device Awareness ===
OS:          Linux
CPU cores:   8
RAM:         15.7 GB
Hostname:    research-node-01

Node type:   COMPUTE_NODE
P2P capable: True
Difficulty multiplier: 1.0x
Max difficulty clamp:  8
```

---

## MCP Server

ChainRight exposes its blockchain as a Model Context Protocol (MCP) server, letting any MCP-compatible AI client interact with the ledger through structured tools.

### Start the server

```bash
python -m chainright.mcp_server
```

Or set the ledger path explicitly:

```bash
CHAINRIGHT_LEDGER=/path/to/ledger.json python -m chainright.mcp_server
```

### Available resources

| Resource URI | Returns |
|-------------|---------|
| `chainright://ledger` | Full conversation history and chain stats |
| `chainright://device` | Device classification and P2P status |

### Available tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `mine_conversation` | `user_id`, `prompt`, `response` | Hash and mine an exchange into the chain |
| `search_knowledge` | `keyword` | Full-text search across all blocks |
| `get_manifold_stats` | — | Blockchain stats + device info + geometric metrics |

### Connect from Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "chainright": {
      "command": "python",
      "args": ["-m", "chainright.mcp_server"],
      "env": {
        "CHAINRIGHT_LEDGER": "/path/to/ledger.json"
      }
    }
  }
}
```

Claude can then mine conversations, search the ledger, and inspect node metrics directly through the chat interface.
