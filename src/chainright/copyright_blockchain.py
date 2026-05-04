#!/usr/bin/env python3
"""Copyright Registry Blockchain for transparent work ownership and licensing."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from chainright.content_fingerprint import ContentFingerprint
from chainright.blockchain import Blockchain


@dataclass
class CopyrightRecord:
    """A record of copyrighted content registered on the blockchain."""
    
    fingerprint: dict  # ContentFingerprint as dict
    creator_wallet: str  # Public key / wallet address
    creator_name: str  # Human-readable creator name
    work_title: str  # Title of the work
    work_description: str  # Description of the work
    license_type: str  # License type (CC-BY, Commercial, All Rights Reserved, etc.)
    licensing_contact: str  # Email or website for licensing inquiries
    registration_timestamp: float
    block_hash: str  # Hash of the block containing this record
    guessed_attributes: dict[str, str] = field(default_factory=dict)
    verification_result: Optional[dict] = None
    verification_block_hash: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "record_type": "copyright_registration",
            "fingerprint": self.fingerprint,
            "creator_wallet": self.creator_wallet,
            "creator_name": self.creator_name,
            "work_title": self.work_title,
            "work_description": self.work_description,
            "license_type": self.license_type,
            "licensing_contact": self.licensing_contact,
            "registration_timestamp": self.registration_timestamp,
            "block_hash": self.block_hash,
            "guessed_attributes": self.guessed_attributes,
            "verification_result": self.verification_result,
            "verification_block_hash": self.verification_block_hash,
        }


@dataclass
class VerificationResult:
    """Lean-style attribute verification trace for a registered work."""

    content_hash: str
    guessed_attributes: dict[str, str]
    actual_attributes: dict[str, str]
    matched_attributes: list[str]
    mismatched_attributes: list[str]
    score: float
    proof_trace: list[str]
    verification_timestamp: float
    method: str = "lean-style-calculation"

    def to_dict(self) -> dict:
        return {
            "record_type": "copyright_verification",
            "content_hash": self.content_hash,
            "guessed_attributes": self.guessed_attributes,
            "actual_attributes": self.actual_attributes,
            "matched_attributes": self.matched_attributes,
            "mismatched_attributes": self.mismatched_attributes,
            "score": self.score,
            "proof_trace": self.proof_trace,
            "verification_timestamp": self.verification_timestamp,
            "method": self.method,
        }


class CopyrightBlockchain:
    """
    Blockchain for registering copyrighted works with licensing information.
    
    Purpose:
    - Enable creators to register their works with ownership proof
    - Allow AI companies and others to discover who owns a work
    - Support transparent licensing workflows
    - Provide immutable proof of prior art and ownership
    - Make it easy to properly attribute and license content
    """
    
    def __init__(self, difficulty: int = 2):
        """Initialize the copyright registry blockchain."""
        genesis_data = self._build_copyright_genesis()
        self.blockchain = Blockchain(difficulty=difficulty, genesis_data=genesis_data)
        self.records: dict[str, CopyrightRecord] = {}  # Hash -> Record mapping
    
    def _build_copyright_genesis(self) -> str:
        """Build the genesis block data for copyright tracking."""
        genesis_info = {
            "type": "COPYRIGHT_REGISTRY",
            "purpose": "Transparent work ownership registry enabling proper licensing",
            "created": datetime.now().isoformat(),
            "description": "Each work is registered with creator, license type, and licensing contact info",
            "use_cases": [
                "AI companies can look up who owns a work before training",
                "Creators can prove prior art and ownership",
                "Transparent licensing: creators specify what's allowed (CC-BY, commercial, etc.)",
                "Licensing contact info enables proper legal agreements",
                "Immutable timestamp proof of when the work was created/registered"
            ],
            "license_types_supported": [
                "CC-BY (Creative Commons Attribution)",
                "CC-BY-SA (Creative Commons Share-Alike)",
                "CC-BY-NC (Creative Commons Non-Commercial)",
                "MIT (Open Source)",
                "Commercial (Contact Creator)",
                "All Rights Reserved (Request Permission)",
                "Public Domain",
                "Custom"
            ]
        }
        return json.dumps(genesis_info)
    
    @staticmethod
    def load_from_file(file_path: str | Path) -> CopyrightBlockchain:
        """Load copyright blockchain from disk."""
        copyright_chain = CopyrightBlockchain.__new__(CopyrightBlockchain)
        copyright_chain.blockchain = Blockchain.load_from_file(str(file_path))
        copyright_chain.records = {}

        for block in copyright_chain.blockchain.chain[1:]:
            try:
                raw_payload = json.loads(block.data)
            except json.JSONDecodeError:
                continue

            payloads = raw_payload if isinstance(raw_payload, list) else [raw_payload]
            for payload_item in payloads:
                if isinstance(payload_item, str):
                    try:
                        payload = json.loads(payload_item)
                    except json.JSONDecodeError:
                        continue
                elif isinstance(payload_item, dict):
                    payload = payload_item
                else:
                    continue

                record_type = payload.get("record_type")
                if record_type == "copyright_registration":
                    fingerprint = payload.get("fingerprint", {})
                    content_hash = fingerprint.get("content_hash")
                    if not content_hash:
                        continue

                    copyright_chain.records[content_hash] = CopyrightRecord(
                        fingerprint=fingerprint,
                        creator_wallet=payload.get("creator_wallet", ""),
                        creator_name=payload.get("creator_name", ""),
                        work_title=payload.get("work_title", ""),
                        work_description=payload.get("work_description", ""),
                        license_type=payload.get("license_type", ""),
                        licensing_contact=payload.get("licensing_contact", ""),
                        registration_timestamp=payload.get("registration_timestamp", 0.0),
                        block_hash=payload.get("block_hash", block.hash),
                        guessed_attributes=payload.get("guessed_attributes", {}) or {},
                        verification_result=payload.get("verification_result"),
                        verification_block_hash=payload.get("verification_block_hash"),
                    )
                elif record_type == "copyright_verification":
                    content_hash = payload.get("content_hash")
                    if not content_hash or content_hash not in copyright_chain.records:
                        continue

                    copyright_chain.records[content_hash].verification_result = payload
                    copyright_chain.records[content_hash].verification_block_hash = block.hash
        return copyright_chain
    
    def register_work(
        self,
        fingerprint: ContentFingerprint,
        creator_wallet: str,
        creator_name: str,
        work_title: str,
        work_description: str,
        license_type: str,
        licensing_contact: str,
        guessed_attributes: Optional[dict[str, str]] = None,
    ) -> CopyrightRecord:
        """
        Register a work on the copyright registry blockchain.
        
        Args:
            fingerprint: ContentFingerprint of the work
            creator_wallet: Public key/wallet address of the creator
            creator_name: Human name of the creator
            work_title: Title of the work
            work_description: Description of the work
            license_type: License type (CC-BY, Commercial, etc.)
            licensing_contact: Email or website for licensing inquiries
        
        Returns:
            CopyrightRecord with the registration details
        """
        # Create registration record
        record = CopyrightRecord(
            fingerprint=fingerprint.to_dict(),
            creator_wallet=creator_wallet,
            creator_name=creator_name,
            work_title=work_title,
            work_description=work_description,
            license_type=license_type,
            licensing_contact=licensing_contact,
            registration_timestamp=time.time(),
            block_hash="",  # Will be set after mining
            guessed_attributes=guessed_attributes or {},
        )
        
        # Add to blockchain pending data
        record_json = json.dumps(record.to_dict())
        self.blockchain.add_data(record_json)
        
        # Mine the block
        result = self.blockchain.mine_pending_data()
        block = result["block"]
        
        # Update record with block hash
        record.block_hash = block.hash
        self.records[fingerprint.content_hash] = record
        
        return record

    def _normalize_attribute_value(self, value: object) -> str:
        """Normalize attribute values for stable comparison."""
        return str(value).strip().casefold()

    def _build_lean_style_trace(
        self,
        guessed_attributes: dict[str, str],
        actual_attributes: dict[str, str],
        matched_attributes: list[str],
        mismatched_attributes: list[str],
        score: float,
    ) -> list[str]:
        """Build a Lean-style calculation trace for the attribute comparison."""
        total = max(len(set(guessed_attributes) | set(actual_attributes)), 1)
        matched = len(matched_attributes)
        return [
            "theorem attribute_verification : score = matched / total := by",
            f"  -- guessed keys: {', '.join(sorted(guessed_attributes)) or 'none'}",
            f"  -- actual keys: {', '.join(sorted(actual_attributes)) or 'none'}",
            f"  -- matched keys: {', '.join(sorted(matched_attributes)) or 'none'}",
            f"  -- mismatched keys: {', '.join(sorted(mismatched_attributes)) or 'none'}",
            "  calc",
            f"    score = {matched} / {total} := by rfl",
            f"    _ = {score:.6f} := by norm_num",
        ]

    def verify_work_attributes(
        self,
        content_hash: str,
        actual_attributes: dict[str, str],
    ) -> Optional[VerificationResult]:
        """Verify a registered work's guessed attributes against actual attributes."""
        record = self.lookup_by_hash(content_hash)
        if not record:
            return None

        guessed_attributes = record.guessed_attributes or {}
        comparison_keys = sorted(set(guessed_attributes) | set(actual_attributes))
        matched_attributes: list[str] = []
        mismatched_attributes: list[str] = []

        for key in comparison_keys:
            guessed_value = guessed_attributes.get(key)
            actual_value = actual_attributes.get(key)
            if guessed_value is None or actual_value is None:
                mismatched_attributes.append(key)
                continue

            if self._normalize_attribute_value(guessed_value) == self._normalize_attribute_value(actual_value):
                matched_attributes.append(key)
            else:
                mismatched_attributes.append(key)

        total_fields = max(len(comparison_keys), 1)
        score = len(matched_attributes) / total_fields
        proof_trace = self._build_lean_style_trace(
            guessed_attributes,
            actual_attributes,
            matched_attributes,
            mismatched_attributes,
            score,
        )

        result = VerificationResult(
            content_hash=content_hash,
            guessed_attributes=guessed_attributes,
            actual_attributes=actual_attributes,
            matched_attributes=matched_attributes,
            mismatched_attributes=mismatched_attributes,
            score=score,
            proof_trace=proof_trace,
            verification_timestamp=time.time(),
        )

        self.blockchain.add_data(json.dumps(result.to_dict()))
        mined_block = self.blockchain.mine_pending_data()["block"]

        record.verification_result = result.to_dict()
        record.verification_block_hash = mined_block.hash
        self.records[content_hash] = record
        return result
    
    def lookup_by_hash(self, content_hash: str) -> Optional[CopyrightRecord]:
        """Look up a registered work by its content hash."""
        return self.records.get(content_hash)
    
    def lookup_by_creator(self, creator_wallet: str) -> list[CopyrightRecord]:
        """Get all works registered by a specific creator wallet."""
        return [r for r in self.records.values() if r.creator_wallet == creator_wallet]
    
    def get_all_records(self) -> list[CopyrightRecord]:
        """Get all registered works."""
        return list(self.records.values())
    
    def save_to_file(self, file_path: str | Path) -> None:
        """Save the blockchain to disk."""
        self.blockchain.save_to_file(str(file_path))
    
    def get_licensing_info(self, content_hash: str) -> Optional[dict]:
        """
        Get licensing information for a work.
        
        This enables anyone to find out:
        - Who owns the work
        - What license applies
        - How to contact for licensing
        """
        record = self.lookup_by_hash(content_hash)
        if not record:
            return None
        
        return {
            "content_hash": content_hash,
            "creator": record.creator_name,
            "creator_wallet": record.creator_wallet,
            "work_title": record.work_title,
            "work_description": record.work_description,
            "license_type": record.license_type,
            "licensing_contact": record.licensing_contact,
            "guessed_attributes": record.guessed_attributes,
            "verification_result": record.verification_result,
            "verification_block_hash": record.verification_block_hash,
            "registered_at": record.registration_timestamp,
            "registered_at_iso": datetime.fromtimestamp(record.registration_timestamp).isoformat(),
            "block_hash": record.block_hash,
            "proof": f"Immutably recorded on ChainRight copyright registry at block {record.block_hash[:16]}...",
        }
    
    def get_chain_integrity_proof(self) -> dict:
        """
        Get a proof of the entire chain's integrity.
        
        Shows the chain of custody from genesis to the most recent block.
        """
        if not self.blockchain.chain:
            return {}
        
        latest_block = self.blockchain.chain[-1]
        
        return {
            "total_blocks": len(self.blockchain.chain),
            "total_registered_works": len(self.records),
            "chain_head_hash": latest_block.hash,
            "chain_head_index": latest_block.index,
            "chain_timestamp": latest_block.timestamp,
            "difficulty": self.blockchain.base_difficulty,
        }
