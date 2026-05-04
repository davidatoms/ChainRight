"""Pretraining data preparation for ChainRight distillation."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from .use import UseEvent
from .user import UserProfile
from .uses import UsesCollection


@dataclass
class PretrainingRecord:
    """A distilled record prepared for training or comparison."""

    user: UserProfile
    input_text: str
    target_text: str
    source_kind: str = "raw"
    source_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_use_event(self, retrieval_time_ms: float = 0.0, generation_time_ms: float = 0.0) -> UseEvent:
        return UseEvent(
            user_id=self.user.user_id,
            input_text=self.input_text,
            generated_text=self.target_text,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            relevance_score=float(self.metadata.get("relevance_score", 0.0)),
            output_kind=self.source_kind,
            source_id=self.source_id,
            retrieved_items=self.metadata.get("retrieved_items", []),
            wallet_address=self.metadata.get("wallet_address"),
        )


class PretrainingBuilder:
    """Build distilled records from raw JSONL/text corpora."""

    def __init__(self, user: UserProfile):
        self.user = user
        self.records: List[PretrainingRecord] = []

    def add_text(self, text: str, target_text: Optional[str] = None, **metadata: Any) -> PretrainingRecord:
        target = target_text if target_text is not None else text
        record = PretrainingRecord(
            user=self.user,
            input_text=text,
            target_text=target,
            metadata=metadata,
        )
        self.records.append(record)
        return record

    def ingest_jsonl(self, path: str | Path, text_key: str = "text", target_key: Optional[str] = None) -> int:
        count = 0
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                text = payload.get(text_key, "")
                target = payload.get(target_key, text) if target_key else text
                self.add_text(text, target, **{k: v for k, v in payload.items() if k not in {text_key, target_key}})
                count += 1
        return count

    def as_uses(self) -> UsesCollection:
        collection = UsesCollection()
        for record in self.records:
            collection.add(record.to_use_event())
        return collection

    def export_json(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "user": self.user.to_dict(),
                    "records": [
                        {
                            "input_text": record.input_text,
                            "target_text": record.target_text,
                            "source_kind": record.source_kind,
                            "source_id": record.source_id,
                            "metadata": record.metadata,
                        }
                        for record in self.records
                    ],
                },
                handle,
                indent=2,
            )
        return path

