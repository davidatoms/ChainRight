"""Equilibrium tests for prompt/model/output trust conditions.

Operationalizes the conditions in §1 of "AI in Financial Services as the
N-body Problem": a prompt-model-output triple is at equilibrium only when
each test below produces a result inside its acceptance band.

Each public function takes an `llm: Callable[[str], str]` so the same harness
runs against any provider (chainright.llm_cli, a mock, or a local Ollama
instance) without coupling to a specific SDK.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from chainright.tokenization import (
    tokenize_words_and_punctuation,
)


LLM = Callable[[str], str]


DEFAULT_HUMAN_CPS = 3.5
"""Empirical baseline characters-per-second from the cli.py --typing-test mode.

Used by the cost-weighted equilibrium aggregator to convert typed character
counts into human-time costs. Override with the cps measured for the actual
operator running the verifier.
"""


# ---------------------------------------------------------------------------
# Typing-cost accounting
# ---------------------------------------------------------------------------

def typing_seconds(chars: int, cps: float = DEFAULT_HUMAN_CPS) -> float:
    if cps <= 0 or chars <= 0:
        return 0.0
    return chars / cps


def result_typed_chars(result) -> int:
    """Sum the human-typed character count implicit in a test result.

    Excludes ground-truth strings since those are sourced externally
    (corpora, regulatory text, databases), not typed by the verifier.
    """
    cls = type(result).__name__

    if cls == "CompressionResult":
        return len(result.original_prompt) + len(result.compressed_prompt)
    if cls == "ProportionalityResult":
        return len(result.prompt)
    if cls == "TimeCostResult":
        return 0
    if cls == "StabilityResult":
        return sum(len(v) for v in result.variants)
    if cls == "DecompositionResult":
        return len(result.composite_prompt) + sum(len(s) for s in result.sub_prompts)
    if cls == "ExpertAgreementResult":
        return len(result.prompt) + len(result.rationale)
    if cls == "ProviderComparison":
        return len(result.prompt)
    if cls == "VerifiabilityResult":
        return sum(len(p) for p in result.prompts)
    return 0


# ---------------------------------------------------------------------------
# Scoring primitives
# ---------------------------------------------------------------------------

def _word_set(text: str) -> set:
    return {t.lower() for t in tokenize_words_and_punctuation(text).tokens if t.isalnum()}


def jaccard(a: str, b: str) -> float:
    """Jaccard similarity on lowercased alphanumeric word tokens.

    Cheap, deterministic, no model dependency. Sufficient for variance and
    overlap signals; not a substitute for human judgment on factual accuracy.
    """
    sa, sb = _word_set(a), _word_set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def ground_truth_score(response: str, ground_truth: str) -> float:
    return jaccard(response, ground_truth)


def word_count(text: str) -> int:
    return tokenize_words_and_punctuation(text).count


# ---------------------------------------------------------------------------
# 1. Prompt compression — fewer tokens, same or better accuracy?
# ---------------------------------------------------------------------------

@dataclass
class CompressionResult:
    original_prompt: str
    compressed_prompt: str
    original_response: str
    compressed_response: str
    ground_truth: str
    original_tokens: int
    compressed_tokens: int
    original_score: float
    compressed_score: float

    @property
    def token_reduction(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return 1.0 - (self.compressed_tokens / self.original_tokens)

    @property
    def accuracy_delta(self) -> float:
        return self.compressed_score - self.original_score

    @property
    def passes(self) -> bool:
        """Compression is a win iff tokens drop and accuracy does not."""
        return self.token_reduction > 0 and self.accuracy_delta >= 0


def compression_test(
    llm: LLM,
    original_prompt: str,
    compressed_prompt: str,
    ground_truth: str,
) -> CompressionResult:
    original_response = llm(original_prompt)
    compressed_response = llm(compressed_prompt)
    return CompressionResult(
        original_prompt=original_prompt,
        compressed_prompt=compressed_prompt,
        original_response=original_response,
        compressed_response=compressed_response,
        ground_truth=ground_truth,
        original_tokens=word_count(original_prompt),
        compressed_tokens=word_count(compressed_prompt),
        original_score=ground_truth_score(original_response, ground_truth),
        compressed_score=ground_truth_score(compressed_response, ground_truth),
    )


# ---------------------------------------------------------------------------
# 2. Input/output proportionality — does the model fill ambiguity with inference?
# ---------------------------------------------------------------------------

@dataclass
class ProportionalityResult:
    prompt: str
    response: str
    input_tokens: int
    output_tokens: int
    ratio: float            # output / input
    threshold: float
    flagged: bool           # True => output is disproportionate to input

    @property
    def passes(self) -> bool:
        return not self.flagged


def proportionality_test(
    llm: LLM,
    prompt: str,
    threshold: float = 5.0,
) -> ProportionalityResult:
    """Flags responses that are >threshold× the prompt length in word tokens.

    A short prompt that produces a verbose response is the signature of the
    model inferring intent that the user did not specify.
    """
    response = llm(prompt)
    in_tok = word_count(prompt)
    out_tok = word_count(response)
    ratio = out_tok / in_tok if in_tok > 0 else float("inf")
    return ProportionalityResult(
        prompt=prompt,
        response=response,
        input_tokens=in_tok,
        output_tokens=out_tok,
        ratio=ratio,
        threshold=threshold,
        flagged=ratio > threshold,
    )


# ---------------------------------------------------------------------------
# 3. Time-cost — does AI deployment beat a human expert?
# ---------------------------------------------------------------------------

@dataclass
class TimeCostResult:
    prompt_typing_seconds: float
    response_reading_seconds: float
    verification_seconds: float
    total_human_time_seconds: float
    expert_baseline_seconds: float

    @property
    def efficiency_collapses(self) -> bool:
        return self.total_human_time_seconds >= self.expert_baseline_seconds

    @property
    def passes(self) -> bool:
        return not self.efficiency_collapses


def time_cost_test(
    prompt: str,
    response: str,
    expert_baseline_seconds: float,
    verification_seconds: float = 0.0,
    typing_wpm: float = 40.0,
    reading_wpm: float = 250.0,
) -> TimeCostResult:
    """Compares (typing prompt + reading response + verifying) to expert time."""
    prompt_words = word_count(prompt)
    response_words = word_count(response)
    typing_s = (prompt_words / typing_wpm) * 60.0 if typing_wpm > 0 else 0.0
    reading_s = (response_words / reading_wpm) * 60.0 if reading_wpm > 0 else 0.0
    total = typing_s + reading_s + verification_seconds
    return TimeCostResult(
        prompt_typing_seconds=typing_s,
        response_reading_seconds=reading_s,
        verification_seconds=verification_seconds,
        total_human_time_seconds=total,
        expert_baseline_seconds=expert_baseline_seconds,
    )


# ---------------------------------------------------------------------------
# 4. Semantic stability — variance under paraphrase
# ---------------------------------------------------------------------------

@dataclass
class StabilityResult:
    variants: List[str]
    responses: List[str]
    pairwise_similarities: List[float]
    mean_similarity: float
    min_similarity: float
    threshold: float

    @property
    def passes(self) -> bool:
        return self.min_similarity >= self.threshold


def semantic_stability_test(
    llm: LLM,
    variants: Sequence[str],
    threshold: float = 0.6,
) -> StabilityResult:
    """Submits paraphrastic variants of the same query and measures variance.

    Low pairwise Jaccard => the prompt is exploiting surface features rather
    than a stable underlying representation.
    """
    if len(variants) < 2:
        raise ValueError("semantic_stability_test requires at least 2 variants")

    responses = [llm(v) for v in variants]
    sims: List[float] = []
    for i in range(len(responses)):
        for j in range(i + 1, len(responses)):
            sims.append(jaccard(responses[i], responses[j]))

    return StabilityResult(
        variants=list(variants),
        responses=responses,
        pairwise_similarities=sims,
        mean_similarity=sum(sims) / len(sims),
        min_similarity=min(sims),
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# 5. Prompt decomposition — is the composite answer an artifact of conflation?
# ---------------------------------------------------------------------------

@dataclass
class DecompositionResult:
    composite_prompt: str
    sub_prompts: List[str]
    composite_response: str
    sub_responses: List[str]
    overlap_with_composite: List[float]
    mean_overlap: float
    threshold: float

    @property
    def passes(self) -> bool:
        return self.mean_overlap >= self.threshold


def prompt_decomposition_test(
    llm: LLM,
    composite_prompt: str,
    sub_prompts: Sequence[str],
    threshold: float = 0.4,
) -> DecompositionResult:
    """Compares the composite-prompt response to per-sub-question responses."""
    if not sub_prompts:
        raise ValueError("prompt_decomposition_test requires at least 1 sub-prompt")

    composite_response = llm(composite_prompt)
    sub_responses = [llm(sp) for sp in sub_prompts]
    overlaps = [jaccard(composite_response, sr) for sr in sub_responses]

    return DecompositionResult(
        composite_prompt=composite_prompt,
        sub_prompts=list(sub_prompts),
        composite_response=composite_response,
        sub_responses=sub_responses,
        overlap_with_composite=overlaps,
        mean_overlap=sum(overlaps) / len(overlaps),
        threshold=threshold,
    )


# ---------------------------------------------------------------------------
# 6. Expert agreement — pre-model expert rating of the prompt
# ---------------------------------------------------------------------------

@dataclass
class ExpertAgreementResult:
    prompt: str
    expert_id: str
    rating: float           # caller-defined scale, e.g. 1-5
    minimum: float
    rationale: str

    @property
    def passes(self) -> bool:
        return self.rating >= self.minimum


def expert_agreement_test(
    prompt: str,
    expert_id: str,
    rating: float,
    minimum: float,
    rationale: str = "",
) -> ExpertAgreementResult:
    """Records an expert's pre-model rating of the prompt's well-formedness.

    The model is intentionally not invoked here. The caller supplies the
    rating from a human reviewer; this function is a structured way to
    capture and gate on it.
    """
    return ExpertAgreementResult(
        prompt=prompt,
        expert_id=expert_id,
        rating=rating,
        minimum=minimum,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# 7. Provider comparison — open-source vs closed, same prompt
# ---------------------------------------------------------------------------

@dataclass
class ProviderResult:
    provider: str
    response: str
    score: float
    latency_seconds: float


@dataclass
class ProviderComparison:
    prompt: str
    ground_truth: str
    score_floor: float = 0.0
    results: List[ProviderResult] = field(default_factory=list)

    def best(self) -> Optional[ProviderResult]:
        return max(self.results, key=lambda r: r.score) if self.results else None

    @property
    def passes(self) -> bool:
        """True iff at least one provider scored at or above `score_floor`.

        Without this property, `EquilibriumReport.at_equilibrium` would treat
        every provider comparison as failing (it falls back to False on
        missing attributes), which silently dropped the clause from the
        eight-clause CNF.
        """
        b = self.best()
        return b is not None and b.score >= self.score_floor


def provider_comparison_test(
    providers: Mapping[str, LLM],
    prompt: str,
    ground_truth: str,
    score_floor: float = 0.5,
) -> ProviderComparison:
    """Runs the same prompt against many providers and scores each.

    Use to ask whether an open-source model meets the bar a closed model sets,
    or whether an enterprise can substitute a smaller model for a larger one.
    The clause passes iff the best provider's Jaccard score against ground
    truth is at or above `score_floor`.
    """
    results: List[ProviderResult] = []
    for name, llm in providers.items():
        t0 = perf_counter()
        response = llm(prompt)
        elapsed = perf_counter() - t0
        results.append(ProviderResult(
            provider=name,
            response=response,
            score=ground_truth_score(response, ground_truth),
            latency_seconds=elapsed,
        ))
    return ProviderComparison(
        prompt=prompt,
        ground_truth=ground_truth,
        score_floor=score_floor,
        results=results,
    )


# ---------------------------------------------------------------------------
# 8. Verifiability iteration — how many rounds until the response is acceptable?
# ---------------------------------------------------------------------------

@dataclass
class VerifiabilityResult:
    rounds: int
    prompts: List[str]
    responses: List[str]
    accepted: bool
    total_seconds: float


def verifiability_iteration_test(
    llm: LLM,
    initial_prompt: str,
    verifier: Callable[[str], bool],
    refine: Callable[[str, str], str],
    max_rounds: int = 5,
) -> VerifiabilityResult:
    """Iterates prompt -> response -> verify -> refine until accepted or max_rounds.

    `verifier(response) -> bool` decides if a response is acceptable.
    `refine(prompt, response) -> str` returns the next prompt given the last one.
    Both are caller-supplied so the harness stays agnostic to the domain.
    """
    prompts: List[str] = []
    responses: List[str] = []
    accepted = False
    t0 = perf_counter()
    prompt = initial_prompt

    for _ in range(max_rounds):
        prompts.append(prompt)
        response = llm(prompt)
        responses.append(response)
        if verifier(response):
            accepted = True
            break
        prompt = refine(prompt, response)

    return VerifiabilityResult(
        rounds=len(responses),
        prompts=prompts,
        responses=responses,
        accepted=accepted,
        total_seconds=perf_counter() - t0,
    )


# ---------------------------------------------------------------------------
# Equilibrium aggregator
# ---------------------------------------------------------------------------

@dataclass
class EquilibriumReport:
    """Bundle of test outcomes; equilibrium holds iff every component passes."""
    components: Dict[str, object] = field(default_factory=dict)

    def add(self, name: str, result) -> None:
        self.components[name] = result

    @property
    def at_equilibrium(self) -> bool:
        if not self.components:
            return False
        return all(getattr(r, "passes", False) for r in self.components.values())

    def failing(self) -> List[str]:
        return [n for n, r in self.components.items() if not getattr(r, "passes", False)]

    def typing_cost_seconds(self, cps: float = DEFAULT_HUMAN_CPS) -> float:
        return sum(
            typing_seconds(result_typed_chars(r), cps=cps)
            for r in self.components.values()
        )

    def cost_breakdown(self, cps: float = DEFAULT_HUMAN_CPS) -> Dict[str, Dict[str, float]]:
        """Per-component typing cost breakdown.

        Returns name -> {chars, seconds, passes}. Sums across components are
        available via `typing_cost_seconds`.
        """
        out: Dict[str, Dict[str, float]] = {}
        for name, r in self.components.items():
            chars = result_typed_chars(r)
            out[name] = {
                "typed_chars": chars,
                "typing_seconds": typing_seconds(chars, cps=cps),
                "passes": bool(getattr(r, "passes", False)),
            }
        return out

    def cost_weighted_summary(self, cps: float = DEFAULT_HUMAN_CPS) -> Dict[str, object]:
        """A regulator-shaped summary: pass/fail plus cost-of-verification.

        A boolean `at_equilibrium` is what the verifier returns; the cost is
        what the operator paid to run that verifier on this triple.
        """
        return {
            "at_equilibrium": self.at_equilibrium,
            "failing_components": self.failing(),
            "total_typing_seconds": self.typing_cost_seconds(cps=cps),
            "cps_assumed": cps,
            "components": self.cost_breakdown(cps=cps),
        }
