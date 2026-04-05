"""
Tests for ClaudeCLIReal and LLMCli.
All external API calls are mocked — no network required.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from chainright.claude_cli_real import ClaudeCLIReal
from chainright.llm_cli import LLMCli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _anthropic_response(text: str) -> str:
    """Return a minimal Anthropic API JSON response string."""
    return json.dumps({
        "content": [{"type": "text", "text": text}],
        "model": "claude-3-5-sonnet-20241022",
        "role": "assistant"
    })


def _openai_response(text: str) -> str:
    return json.dumps({
        "choices": [{"message": {"content": text, "role": "assistant"}}]
    })


def _make_subprocess_result(stdout: str, returncode: int = 0) -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = ""
    return result


# ---------------------------------------------------------------------------
# ClaudeCLIReal
# ---------------------------------------------------------------------------

class TestClaudeCLIReal:
    def _cli(self, api_key: str = "test-key") -> ClaudeCLIReal:
        with patch.dict(os.environ, {"CLAUDE_API_KEY": api_key}):
            return ClaudeCLIReal(difficulty=1, api_key=api_key)

    def test_session_id_is_8_chars(self):
        cli = self._cli()
        assert len(cli.session_id) == 8

    def test_hash_string_is_sha256(self):
        cli = self._cli()
        h = cli.hash_string("hello")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_is_deterministic(self):
        cli = self._cli()
        assert cli.hash_string("abc") == cli.hash_string("abc")

    def test_call_claude_api_success(self):
        cli = self._cli()
        mock_result = _make_subprocess_result(_anthropic_response("Hello there!"))

        with patch("subprocess.run", return_value=mock_result):
            response = cli.call_claude_api("Hi")

        assert response == "Hello there!"

    def test_call_claude_api_updates_context(self):
        cli = self._cli()
        mock_result = _make_subprocess_result(_anthropic_response("Context reply"))

        with patch("subprocess.run", return_value=mock_result):
            cli.call_claude_api("Test message")

        assert len(cli.conversation_context) == 1
        assert cli.conversation_context[0]["user"] == "Test message"
        assert cli.conversation_context[0]["claude"] == "Context reply"

    def test_call_claude_api_timeout(self):
        import subprocess
        cli = self._cli()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("curl", 30)):
            response = cli.call_claude_api("anything")
        assert "timed out" in response.lower()

    def test_call_claude_api_no_key(self):
        cli = ClaudeCLIReal(difficulty=1, api_key=None)
        response = cli.call_claude_api("hello")
        assert "error" in response.lower()

    def test_add_to_blockchain_mines_block(self):
        cli = self._cli()
        block = cli.add_to_blockchain("some content", "user_input")
        assert block is not None
        assert len(cli.blockchain.chain) == 2  # genesis + mined


# ---------------------------------------------------------------------------
# LLMCli
# ---------------------------------------------------------------------------

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "config", "providers.json"
)


@pytest.fixture
def anthropic_cli():
    """LLMCli wired to Anthropic with a fake key."""
    with patch.dict(os.environ, {"CLAUDE_API_KEY": "test-key"}):
        yield LLMCli(provider="anthropic", difficulty=1, config_path=_CONFIG_PATH)


class TestLLMCli:
    def test_provider_label_set(self, anthropic_cli):
        assert anthropic_cli.provider_label == "Anthropic"

    def test_model_id_set(self, anthropic_cli):
        assert anthropic_cli.model_config["id"] != ""

    def test_session_id_length(self, anthropic_cli):
        assert len(anthropic_cli.session_id) == 8

    def test_hash_is_sha256(self, anthropic_cli):
        h = anthropic_cli._hash("test")
        assert len(h) == 64

    def test_unknown_provider_exits(self):
        with pytest.raises(SystemExit):
            LLMCli(provider="nonexistent_provider_xyz", difficulty=1, config_path=_CONFIG_PATH)

    def test_mine_adds_block(self, anthropic_cli):
        block = anthropic_cli._mine("hello world", "user")
        assert block is not None
        assert len(anthropic_cli.blockchain.chain) == 2

    def test_call_anthropic_success(self, anthropic_cli):
        mock_result = _make_subprocess_result(_anthropic_response("LLM reply"))
        with patch("subprocess.run", return_value=mock_result):
            resp = anthropic_cli._call_llm("Hello")
        assert resp == "LLM reply"

    def test_call_anthropic_timeout(self, anthropic_cli):
        import subprocess
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("curl", 30)):
            resp = anthropic_cli._call_llm("hello")
        assert "timed out" in resp.lower()

    def test_call_anthropic_bad_json(self, anthropic_cli):
        mock_result = _make_subprocess_result("not-json")
        with patch("subprocess.run", return_value=mock_result):
            resp = anthropic_cli._call_llm("hello")
        assert "error" in resp.lower()

    def test_context_accumulates(self, anthropic_cli):
        mock_result = _make_subprocess_result(_anthropic_response("reply"))
        with patch("subprocess.run", return_value=mock_result):
            anthropic_cli._call_llm("first")
            # Simulate the context update that run() does
            anthropic_cli.conversation_context.append({"user": "first", "llm": "reply"})
            anthropic_cli._call_llm("second")
        assert len(anthropic_cli.conversation_context) == 1  # manually added one

    def test_openai_compatible_call(self):
        """LLMCli routes non-Anthropic, non-Google providers through OpenAI-compatible path."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            cli = LLMCli(provider="openai", difficulty=1, config_path=_CONFIG_PATH)

        mock_result = _make_subprocess_result(_openai_response("OpenAI reply"))
        with patch("subprocess.run", return_value=mock_result):
            resp = cli._call_llm("Hello")
        assert resp == "OpenAI reply"

    def test_handle_command_clear(self, anthropic_cli):
        anthropic_cli.conversation_context = [{"user": "x", "llm": "y"}]
        anthropic_cli._handle_command("/clear")
        assert anthropic_cli.conversation_context == []

    def test_handle_command_quit(self, anthropic_cli):
        with pytest.raises(SystemExit):
            anthropic_cli._handle_command("/quit")

    def test_handle_command_save_load(self, anthropic_cli, tmp_path):
        fname = str(tmp_path / "chain.json")
        anthropic_cli._handle_command(f"/save {fname}")
        assert os.path.exists(fname)
        anthropic_cli._handle_command(f"/load {fname}")
        assert anthropic_cli.blockchain.is_chain_valid()
