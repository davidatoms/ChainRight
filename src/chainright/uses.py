"""Collections and summaries for ChainRight use events."""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

from .use import UseEvent


@dataclass
class UsesCollection:
    """A collection of use events with aggregate metrics."""

    events: List[UseEvent] = field(default_factory=list)

    def add(self, event: UseEvent) -> None:
        self.events.append(event)

    def extend(self, events: Iterable[UseEvent]) -> None:
        for event in events:
            self.add(event)

    def by_user(self, user_id: str) -> List[UseEvent]:
        return [event for event in self.events if event.user_id == user_id]

    def summary(self) -> Dict[str, Any]:
        if not self.events:
            return {
                "count": 0,
                "avg_retrieval_time_ms": 0.0,
                "avg_generation_time_ms": 0.0,
                "avg_total_time_ms": 0.0,
                "avg_relevance_score": 0.0,
            }

        count = len(self.events)
        return {
            "count": count,
            "avg_retrieval_time_ms": sum(e.retrieval_time_ms for e in self.events) / count,
            "avg_generation_time_ms": sum(e.generation_time_ms for e in self.events) / count,
            "avg_total_time_ms": sum(e.total_time_ms for e in self.events) / count,
            "avg_relevance_score": sum(e.relevance_score for e in self.events) / count,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary(),
            "events": [event.to_dict() for event in self.events],
        }

