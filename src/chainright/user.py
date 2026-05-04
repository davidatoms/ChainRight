"""User identity and profile objects for ChainRight usage records."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict
import uuid


@dataclass
class UserProfile:
    """Represents a person or agent using ChainRight."""

    user_id: str
    display_name: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.user_id:
            self.user_id = f"user_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

