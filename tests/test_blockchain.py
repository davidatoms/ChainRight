"""
Tests for core blockchain functionality.
"""

import json
import os
import tempfile

import pytest

from chainright.blockchain import Block, Blockchain, create_string_blockchain


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------

class TestBlock:
    def test_hash_is_deterministic(self):
        b = Block(index=0, data="hello", previous_hash="0", timestamp=1000.0, difficulty=1)
        assert b.calculate_hash() == b.hash

    def test_hash_changes_with_nonce(self):
        b = Block(index=0, data="hello", previous_hash="0", timestamp=1000.0, difficulty=1)
        original = b.hash
        b.nonce += 1
        b.hash = b.calculate_hash()
        assert b.hash != original

    def test_mine_block_satisfies_difficulty(self):
        b = Block(index=1, data="data", previous_hash="abc", timestamp=1000.0, difficulty=2)
        b.mine_block(difficulty=2)
        assert b.hash.startswith("00")

    def test_to_dict_roundtrip(self):
        b = Block(index=1, data="roundtrip", previous_hash="abc", timestamp=1000.0, difficulty=1)
        d = b.to_dict()
        restored = Block.from_dict(d)
        assert restored.index == b.index
        assert restored.data == b.data
        assert restored.hash == b.hash
        assert restored.nonce == b.nonce


# ---------------------------------------------------------------------------
# Blockchain
# ---------------------------------------------------------------------------

class TestBlockchain:
    def test_genesis_block_created_on_init(self):
        bc = Blockchain(difficulty=1)
        assert len(bc.chain) == 1
        assert bc.chain[0].index == 0

    def test_is_chain_valid_after_init(self):
        bc = Blockchain(difficulty=1)
        assert bc.is_chain_valid()

    def test_mine_adds_block(self):
        bc = Blockchain(difficulty=1)
        bc.add_data("test data")
        result = bc.mine_pending_data()
        assert len(bc.chain) == 2
        assert isinstance(result, dict)
        assert "block" in result

    def test_pending_data_cleared_after_mine(self):
        bc = Blockchain(difficulty=1)
        bc.add_data("a")
        bc.add_data("b")
        bc.mine_pending_data()
        assert bc.pending_data == []

    def test_mine_with_no_pending_raises(self):
        bc = Blockchain(difficulty=1)
        with pytest.raises(ValueError):
            bc.mine_pending_data()

    def test_chain_valid_after_multiple_blocks(self):
        bc = Blockchain(difficulty=1)
        bc.add_data("block 1")
        bc.mine_pending_data()
        bc.add_data("block 2")
        bc.mine_pending_data()
        assert bc.is_chain_valid()
        assert len(bc.chain) == 3  # genesis + 2 mined

    def test_tampered_data_invalidates_chain(self):
        bc = Blockchain(difficulty=1)
        bc.add_data("legit data")
        bc.mine_pending_data()
        # Tamper with block 1
        bc.chain[1].data = "tampered"
        assert not bc.is_chain_valid()

    def test_tampered_hash_invalidates_chain(self):
        bc = Blockchain(difficulty=1)
        bc.add_data("legit data")
        bc.mine_pending_data()
        bc.chain[1].hash = "0" * 64
        assert not bc.is_chain_valid()

    def test_get_block_by_index(self):
        bc = Blockchain(difficulty=1)
        block = bc.get_block_by_index(0)
        assert block.index == 0

    def test_get_block_by_index_out_of_range(self):
        bc = Blockchain(difficulty=1)
        with pytest.raises(IndexError):
            bc.get_block_by_index(99)

    def test_get_block_by_hash(self):
        bc = Blockchain(difficulty=1)
        genesis_hash = bc.chain[0].hash
        block = bc.get_block_by_hash(genesis_hash)
        assert block.index == 0

    def test_get_block_by_hash_not_found(self):
        bc = Blockchain(difficulty=1)
        with pytest.raises(ValueError):
            bc.get_block_by_hash("nonexistent")

    def test_get_chain_returns_list_of_dicts(self):
        bc = Blockchain(difficulty=1)
        chain = bc.get_chain()
        assert isinstance(chain, list)
        assert isinstance(chain[0], dict)
        assert "hash" in chain[0]

    def test_get_latest_block(self):
        bc = Blockchain(difficulty=1)
        bc.add_data("latest")
        bc.mine_pending_data()
        latest = bc.get_latest_block()
        assert latest.index == 1


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_and_load(self):
        bc = Blockchain(difficulty=1)
        bc.add_data("persist me")
        bc.mine_pending_data()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            fname = f.name

        try:
            bc.save_to_file(fname)
            loaded = Blockchain.load_from_file(fname)
            assert loaded.is_chain_valid()
            assert len(loaded.chain) == len(bc.chain)
            assert loaded.chain[-1].hash == bc.chain[-1].hash
        finally:
            os.unlink(fname)

    def test_save_file_is_valid_json(self):
        bc = Blockchain(difficulty=1)
        bc.add_data("json test")
        bc.mine_pending_data()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            fname = f.name

        try:
            bc.save_to_file(fname)
            with open(fname) as f:
                data = json.load(f)
            assert "chain" in data
            assert "difficulty" in data
            assert "pending_data" in data
        finally:
            os.unlink(fname)


# ---------------------------------------------------------------------------
# create_string_blockchain helper
# ---------------------------------------------------------------------------

class TestCreateStringBlockchain:
    def test_returns_valid_blockchain(self):
        bc = create_string_blockchain("hello world", difficulty=1)
        assert bc.is_chain_valid()

    def test_chain_contains_input_string(self):
        text = "unique test string 12345"
        bc = create_string_blockchain(text, difficulty=1)
        # The string is stored inside the mined block's data JSON
        chain_json = json.dumps(bc.get_chain())
        assert text in chain_json

    def test_chain_has_two_blocks(self):
        bc = create_string_blockchain("data", difficulty=1)
        # genesis + 1 mined block
        assert len(bc.chain) == 2
