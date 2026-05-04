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
from .knowledge_hierarchy import (
    Concept, Sentence, Paragraph, Section, Chapter, Book,
    KnowledgeHierarchy, Metalocation
)
from .genesis_builder import GenesisBuilder
from .user import UserProfile
from .use import UseEvent
from .uses import UsesCollection
from .pretraining import PretrainingBuilder, PretrainingRecord
from .training import TrainingPipeline, TrainingRun
from .posttraining import PosttrainingAnalyzer, PosttrainingReport
from .wallet import Wallet
from .rarity import (
    SourceKind, RarityMetrics, compute_rarity_score, sliver_weight_for_use
)
from .reward_ledger import RewardEvent, BountyPool, RewardLedger
from .tokenization import (
    TokenizationView, TokenizationReport,
    tokenize_characters, tokenize_whitespace,
    tokenize_words_and_punctuation, tokenize_bytes,
    tokenize_sentences, tokenize_tiktoken,
    build_tokenization_report,
)

__all__ = [
    "Block",
    "Blockchain", 
    "create_string_blockchain",
    "GlobalConversationBlockchain",
    "PersonalAITrainer",
    "AITrainingDataset",
    "OwnershipBlockchain",
    "OwnedSentence", 
    "OwnershipBlock",
    "Concept",
    "Sentence",
    "Paragraph",
    "Section",
    "Chapter",
    "Book",
    "KnowledgeHierarchy",
    "Metalocation",
    "GenesisBuilder",
    "UserProfile",
    "UseEvent",
    "UsesCollection",
    "PretrainingBuilder",
    "PretrainingRecord",
    "TrainingPipeline",
    "TrainingRun",
    "PosttrainingAnalyzer",
    "PosttrainingReport",
    "Wallet",
    "SourceKind",
    "RarityMetrics",
    "compute_rarity_score",
    "sliver_weight_for_use",
    "RewardEvent",
    "BountyPool",
    "RewardLedger",
    "TokenizationView",
    "TokenizationReport",
    "tokenize_characters",
    "tokenize_whitespace",
    "tokenize_words_and_punctuation",
    "tokenize_bytes",
    "tokenize_sentences",
    "tokenize_tiktoken",
    "build_tokenization_report",
]