"""
ChainRight - Global Conversation Blockchain

A decentralized platform for creating immutable, attributed conversations with AI 
that can be used for personal AI training and global knowledge sharing.
"""

__version__ = "0.1.0"
__author__ = "David Adams"
__email__ = "david@chainright.ai"

from .blockchain import Block, Blockchain, create_string_blockchain
from .global_conversation_blockchain import GlobalConversationBlockchain
from .personal_ai_trainer import PersonalAITrainer
from .ai_training_dataset import AITrainingDataset
from .ownership_blockchain import OwnershipBlockchain, OwnedSentence, OwnershipBlock

__all__ = [
    "Block",
    "Blockchain", 
    "create_string_blockchain",
    "GlobalConversationBlockchain",
    "PersonalAITrainer",
    "AITrainingDataset",
    "OwnershipBlockchain",
    "OwnedSentence", 
    "OwnershipBlock"
]