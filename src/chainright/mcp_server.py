#!/usr/bin/env python3
"""
ChainRight MCP Server
Exposes the Relativistic Blockchain as a Model Context Protocol (MCP) Resource and Tool.
"""

import json
import os
import asyncio
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# Import core ChainRight components
from .global_conversation_blockchain import GlobalConversationBlockchain
from .blockchain import Block
from .device_awareness import DeviceAwareness

# Initialize FastMCP server
mcp = FastMCP("ChainRight")

# Global state for the blockchain
# Defaulting to a local-only file for MCP security
LEDGER_FILE = os.getenv("CHAINRIGHT_LEDGER", "mcp_conversations.json")
gc_blockchain = GlobalConversationBlockchain(blockchain_file=LEDGER_FILE)

@mcp.resource("chainright://ledger")
def get_ledger() -> str:
    """
    Returns the complete immutable conversation history from the blockchain.
    Use this to retrieve context from previous "Knowledge Fragments".
    """
    stats = gc_blockchain.get_blockchain_stats()
    chain_data = gc_blockchain.blockchain.get_chain()
    
    # Return as a structured summary for the LLM
    return json.dumps({
        "summary": stats,
        "history": chain_data
    }, indent=2)

@mcp.resource("chainright://device")
def get_device_info() -> str:
    """
    Returns the current node's hardware classification and P2P status.
    """
    return json.dumps(DeviceAwareness.classify_device(), indent=2)

@mcp.tool()
def mine_conversation(user_id: str, message: str, message_type: str = "mcp_interaction", 
                     session_id: str = "mcp_session") -> str:
    """
    Hashes and mines a new conversation entry into the blockchain.
    
    Args:
        user_id: The ID of the user or agent committing the data.
        message: The text content to be made immutable.
        message_type: The category (e.g., 'research_note', 'code_snippet').
        session_id: Unique ID for the current context.
    """
    try:
        # Measure a mock 'internal latency' for the relativistic engine
        # In a real tool call, this would track the LLM's response time
        block = gc_blockchain.add_conversation_entry(
            user_id=user_id,
            message=message,
            message_type=message_type,
            session_id=session_id,
            metadata={"source": "mcp_tool_call"}
        )
        
        return f"Successfully mined Block {block.index}. Hash: {block.hash[:12]}... (Difficulty: {block.difficulty})"
    except Exception as e:
        return f"Error mining block: {str(e)}"

@mcp.tool()
def search_knowledge(query: str) -> str:
    """
    Searches the blockchain for specific keywords or concepts.
    Returns matching Knowledge Fragments.
    """
    results = gc_blockchain.search_message_content(query)
    if not results:
        return f"No fragments found for query: '{query}'"
    
    return json.dumps(results, indent=2)

@mcp.tool()
def get_manifold_stats() -> str:
    """
    Returns the current relativistic metrics of the blockchain, 
    including curvature, energy, and entropy.
    """
    stats = gc_blockchain.get_blockchain_stats()
    device = DeviceAwareness.classify_device()
    
    return json.dumps({
        "blockchain_stats": stats,
        "node_classification": device["type"],
        "p2p_ready": device["p2p_status"]
    }, indent=2)

if __name__ == "__main__":
    # Start the MCP server using stdio transport
    mcp.run()
