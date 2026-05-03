"""
ChainRight CLI Commands

Subcommands for interacting with ChainRight:
- genesis: Build and manage Genesis Block (pretraining corpus)
- write: Interactive writing capture
- train: Model training on captured sessions
"""

from chainright.cli.write import write
from chainright.cli.train import train
from chainright.cli.genesis import genesis

__all__ = ["genesis", "write", "train"]
