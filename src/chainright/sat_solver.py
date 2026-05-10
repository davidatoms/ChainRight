"""SAT-style search for an equilibrium-passing prompt under a typing-cost budget.

Equilibrium is structurally a CNF formula (see notes/equilibrium_as_sat.md):
each test in chainright.equilibrium is a clause and `at_equilibrium` is their
conjunction. Generation of a satisfying (prompt, response) tuple is the
NP-hard direction; verification of a candidate is fast.

The solver here enumerates candidate prompts via a caller-supplied generator,
evaluates each via a caller-supplied evaluator, and stops as soon as one
candidate satisfies the formula — or when a typing-cost budget (in seconds
of human-equivalent typing) is exhausted. The budget cap is the empirical
content of the §1 time-cost test applied to the verifier itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable, Iterable, List, Optional

from chainright.equilibrium import (
    DEFAULT_HUMAN_CPS,
    EquilibriumReport,
    typing_seconds,
)


@dataclass
class SearchStep:
    candidate: str
    report: EquilibriumReport
    step_typing_seconds: float
    cumulative_typing_seconds: float
    accepted: bool


@dataclass
class SearchResult:
    accepted: bool
    final_candidate: Optional[str]
    steps: List[SearchStep] = field(default_factory=list)
    total_typing_seconds: float = 0.0
    wall_clock_seconds: float = 0.0
    budget_seconds: float = 0.0
    aborted_over_budget: bool = False

    @property
    def candidates_examined(self) -> int:
        return len(self.steps)

    @property
    def cost_to_satisfy(self) -> Optional[float]:
        return self.total_typing_seconds if self.accepted else None


def solve_equilibrium(
    initial_prompt: str,
    candidate_generator: Callable[[str], Iterable[str]],
    evaluator: Callable[[str], EquilibriumReport],
    budget_seconds: float,
    cps: float = DEFAULT_HUMAN_CPS,
    include_initial: bool = True,
) -> SearchResult:
    """Search the candidate space until equilibrium holds or budget is spent.

    Each candidate is charged its own typing cost (chars/cps) regardless of
    whether the evaluator passes — typing the candidate is what the operator
    paid for.

    Args:
        initial_prompt: starting candidate.
        candidate_generator: function mapping the initial prompt to an
            iterable of variant candidates. Caller controls the search order.
        evaluator: function returning an EquilibriumReport for a candidate.
            Typically wraps the LLM call plus the equilibrium tests.
        budget_seconds: maximum cumulative typing-equivalent cost. Search
            aborts when the next candidate would push past this.
        cps: characters per second used to convert typed chars to seconds.
        include_initial: if True, evaluate `initial_prompt` first before
            consulting the generator. Default True.

    Returns:
        SearchResult with the trajectory and outcome.
    """
    candidates: List[str] = []
    if include_initial:
        candidates.append(initial_prompt)
    candidates.extend(candidate_generator(initial_prompt))

    steps: List[SearchStep] = []
    cumulative = 0.0
    accepted_step: Optional[SearchStep] = None
    aborted = False

    wall_start = perf_counter()
    for candidate in candidates:
        step_cost = typing_seconds(len(candidate), cps=cps)
        if cumulative + step_cost > budget_seconds:
            aborted = True
            break

        report = evaluator(candidate)
        cumulative += step_cost

        passes = report.at_equilibrium
        step = SearchStep(
            candidate=candidate,
            report=report,
            step_typing_seconds=step_cost,
            cumulative_typing_seconds=cumulative,
            accepted=passes,
        )
        steps.append(step)
        if passes:
            accepted_step = step
            break

    wall = perf_counter() - wall_start

    return SearchResult(
        accepted=accepted_step is not None,
        final_candidate=accepted_step.candidate if accepted_step else None,
        steps=steps,
        total_typing_seconds=cumulative,
        wall_clock_seconds=wall,
        budget_seconds=budget_seconds,
        aborted_over_budget=aborted,
    )


# ---------------------------------------------------------------------------
# Default candidate generators
# ---------------------------------------------------------------------------

def truncation_generator(strides: Iterable[int] = (8, 16, 24, 40, 60)) -> Callable[[str], List[str]]:
    """Generate prefix-truncations of the initial prompt at fixed word counts."""
    strides_list = list(strides)

    def gen(prompt: str) -> List[str]:
        words = prompt.split()
        out: List[str] = []
        seen = set()
        for k in strides_list:
            if k >= len(words):
                continue
            candidate = " ".join(words[:k])
            if candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
        return out

    return gen


def word_drop_generator(
    n_drops: int = 1,
    keep_first: int = 1,
    keep_last: int = 0,
) -> Callable[[str], List[str]]:
    """Generate variants that drop `n_drops` consecutive interior words.

    Conservative neighbor function: small edits to a base prompt. Useful when
    the search wants to test whether a particular hedging phrase or filler is
    what tips the prompt out of equilibrium.
    """
    def gen(prompt: str) -> List[str]:
        words = prompt.split()
        if len(words) <= keep_first + keep_last + n_drops:
            return []
        out: List[str] = []
        for i in range(keep_first, len(words) - n_drops - keep_last):
            variant = words[:i] + words[i + n_drops:]
            out.append(" ".join(variant))
        return out

    return gen
