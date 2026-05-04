"""Posttraining evaluation for retrieval-vs-generation comparisons."""

from dataclasses import dataclass, field
from typing import Any, Dict, List
import json
from pathlib import Path

from .uses import UsesCollection


@dataclass
class PosttrainingReport:
    """Evaluation results after training and distillation."""

    use_count: int
    retrieval_runtime_ms: float
    generation_runtime_ms: float
    total_runtime_ms: float
    retrieval_vs_generation_ratio: float
    avg_relevance_score: float
    notes: List[str] = field(default_factory=list)


class PosttrainingAnalyzer:
    """Compute runtime and relevance comparisons from use records."""

    def analyze(self, uses: UsesCollection) -> PosttrainingReport:
        summary = uses.summary()
        total_runtime = summary["avg_total_time_ms"]
        retrieval = summary["avg_retrieval_time_ms"]
        generation = summary["avg_generation_time_ms"]
        ratio = retrieval / generation if generation else 0.0

        notes = []
        if retrieval > generation:
            notes.append("Retrieval is slower than generation on average.")
        else:
            notes.append("Generation is slower than retrieval on average.")

        if summary["avg_relevance_score"] >= 0.7:
            notes.append("Retrieved context appears relevant enough to justify comparison.")
        else:
            notes.append("Retrieved context may be too weak to influence generation meaningfully.")

        return PosttrainingReport(
            use_count=summary["count"],
            retrieval_runtime_ms=retrieval,
            generation_runtime_ms=generation,
            total_runtime_ms=total_runtime,
            retrieval_vs_generation_ratio=ratio,
            avg_relevance_score=summary["avg_relevance_score"],
            notes=notes,
        )

    def export_report(self, report: PosttrainingReport, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(report.__dict__, handle, indent=2)
        return path

