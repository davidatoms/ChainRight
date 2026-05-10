"""LLM adapters that satisfy the `LLM = Callable[[str], str]` contract.

Three adapters cover the live cases for the equilibrium harness:

- `static_corpus_llm`: returns a fixed text, ignoring the prompt. Free,
  deterministic, useful for tests and for the lookup-style examples that
  read pre-recorded model outputs from gpt-2-output-dataset.
- `chainright_llm_cli_adapter`: wraps `chainright.llm_cli.LLMCli` and
  clears its conversation context before each call so every prompt is
  evaluated statelessly. Routes to whichever provider/model is configured
  in `config/providers.json` (Anthropic / OpenAI / Google).
- `ollama_adapter`: direct HTTP adapter for a local Ollama server. No
  config file required. Useful for offline runs and for the §1.6
  "verify-against-a-local-model" path in the paper.

Each adapter returns a fresh `LLM` callable so the harness is unaware of
which provider is in play.
"""

from __future__ import annotations

from typing import Optional

from chainright.equilibrium import LLM


def static_corpus_llm(text: str) -> LLM:
    """Always return the same string regardless of prompt."""
    def llm(_prompt: str) -> str:
        return text
    return llm


def chainright_llm_cli_adapter(
    provider: str = "anthropic",
    model: Optional[str] = None,
    config_path: Optional[str] = None,
) -> LLM:
    """Wrap `chainright.llm_cli.LLMCli` as a stateless `(prompt) -> response`.

    Conversation context is cleared before each call so the harness sees
    each prompt in isolation. Requires the provider's API key in the env
    variable named by providers.json.
    """
    from chainright.llm_cli import LLMCli

    kwargs = {"provider": provider, "model": model}
    if config_path is not None:
        kwargs["config_path"] = config_path
    cli = LLMCli(**kwargs)

    def llm(prompt: str) -> str:
        cli.conversation_context = []
        return cli._call_llm(prompt)

    return llm


def ollama_adapter(
    model: str = "llama3",
    base_url: str = "http://localhost:11434",
    timeout: float = 120.0,
) -> LLM:
    """Direct adapter for a local Ollama server's /api/generate endpoint.

    Stateless by construction — Ollama's generate endpoint does not carry
    conversation state across calls.
    """
    import requests  # local import so the module stays importable without it

    def llm(prompt: str) -> str:
        resp = requests.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    return llm


# ---------------------------------------------------------------------------
# HuggingFace via circuit-tracer
# ---------------------------------------------------------------------------

def huggingface_via_circuit_tracer_adapter(
    model_name: str = "meta-llama/Llama-3.2-1B",
    transcoder_set: str = "mntss/transcoder-Llama-3.2-1B",
    *,
    backend: str = "transformerlens",
    device: Optional[str] = None,
    dtype: str = "float16",
    max_new_tokens: int = 256,
    temperature: float = 0.0,
    seed: Optional[int] = 42,
) -> LLM:
    """Load a HuggingFace transformer plus its transcoders via circuit-tracer
    and return a stateless `(prompt) -> response` callable.

    The returned model is a circuit-tracer ReplacementModel (a HookedTransformer
    subclass), so the same instance can be reused for `attribute()` calls if
    you also want the attribution graph — see
    `huggingface_via_circuit_tracer_with_attribution` for that variant.

    Defaults target the 3070 Ti / 8 GB VRAM regime: Llama-3.2 1B in float16
    with greedy decoding for reproducibility. Set `temperature` > 0 and a
    `seed` of None for stochastic sampling.

    Requires:
        pip install -e <path-to>/circuit-tracer
    """
    import torch  # local import; circuit-tracer is heavy
    from circuit_tracer import ReplacementModel  # type: ignore[import-not-found]

    if seed is not None:
        torch.manual_seed(seed)

    torch_dtype = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }.get(dtype, torch.float16)

    torch_device = torch.device(device) if device is not None else None

    model = ReplacementModel.from_pretrained(
        model_name=model_name,
        transcoder_set=transcoder_set,
        backend=backend,
        device=torch_device,
        dtype=torch_dtype,
    )

    def llm(prompt: str) -> str:
        with torch.no_grad():
            output = model.generate(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                verbose=False,
            )
        text = output if isinstance(output, str) else str(output)
        return text[len(prompt):] if text.startswith(prompt) else text

    return llm


def huggingface_via_circuit_tracer_with_attribution(
    model_name: str = "meta-llama/Llama-3.2-1B",
    transcoder_set: str = "mntss/transcoder-Llama-3.2-1B",
    *,
    backend: str = "transformerlens",
    device: Optional[str] = None,
    dtype: str = "float16",
    max_new_tokens: int = 64,
    temperature: float = 0.0,
    seed: Optional[int] = 42,
    attribution_offload: Optional[str] = "cpu",
    max_feature_nodes: Optional[int] = 4096,
):
    """Same as the adapter above, but returns a callable that also produces
    a circuit-tracer `Graph` per prompt.

    Returns:
        Callable[[str], Tuple[str, Graph]] — given a prompt, returns
        `(generated_text, attribution_graph)`. The graph captures the direct
        linear effects of every non-zero transcoder feature on the model's
        output logits at the final position.

    The attribution pass is expensive (much more than generation); use a
    smaller `max_feature_nodes` to keep memory in check on 8 GB VRAM.
    """
    import torch  # type: ignore
    from circuit_tracer import ReplacementModel, attribute  # type: ignore[import-not-found]

    if seed is not None:
        torch.manual_seed(seed)

    torch_dtype = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }.get(dtype, torch.float16)
    torch_device = torch.device(device) if device is not None else None

    model = ReplacementModel.from_pretrained(
        model_name=model_name,
        transcoder_set=transcoder_set,
        backend=backend,
        device=torch_device,
        dtype=torch_dtype,
    )

    def call(prompt: str):
        with torch.no_grad():
            output = model.generate(
                prompt,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                verbose=False,
            )
        text = output if isinstance(output, str) else str(output)
        response = text[len(prompt):] if text.startswith(prompt) else text

        graph = attribute(
            prompt,
            model,
            offload=attribution_offload,
            max_feature_nodes=max_feature_nodes,
            verbose=False,
        )
        return response, graph

    return call
