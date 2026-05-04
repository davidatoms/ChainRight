"""Simple Wallet adapter for ChainRight (prototype).

This provides a lightweight local wallet that creates an address and a
secret key stored under the user's home `.chainright/wallets/` folder.

It implements HMAC-SHA256 signing as a prototype for binding creations to
an owner wallet. For production, replace with Ed25519 or an external
wallet provider.
"""

from __future__ import annotations

import hmac
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import secrets


WALLETS_DIR = Path.home() / ".chainright" / "wallets"
WALLETS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Wallet:
    address: str
    secret_key_hex: str
    metadata: dict = None

    @classmethod
    def create(cls, display_name: Optional[str] = None) -> "Wallet":
        addr = f"wallet_{secrets.token_hex(12)}"
        secret = secrets.token_hex(32)
        w = cls(address=addr, secret_key_hex=secret, metadata={"name": display_name})
        w._persist()
        return w

    @classmethod
    def load(cls, address: str) -> Optional["Wallet"]:
        f = WALLETS_DIR / f"{address}.json"
        if not f.exists():
            return None
        data = json.loads(f.read_text(encoding="utf-8"))
        return cls(address=data["address"], secret_key_hex=data["secret_key_hex"], metadata=data.get("metadata"))

    def _persist(self) -> None:
        f = WALLETS_DIR / f"{self.address}.json"
        f.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    def sign(self, message: bytes) -> str:
        """Return hex HMAC-SHA256 signature of message using secret key."""
        key = bytes.fromhex(self.secret_key_hex)
        sig = hmac.new(key, message, hashlib.sha256).hexdigest()
        return sig

    def verify(self, message: bytes, signature_hex: str) -> bool:
        key = bytes.fromhex(self.secret_key_hex)
        expected = hmac.new(key, message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature_hex)
