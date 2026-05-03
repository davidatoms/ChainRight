"""
ChainRight CLI Commands

Subcommands for interacting with ChainRight:
- write: Interactive writing capture
- train: Model training on captured sessions
"""

from chainright.cli.write import write
from chainright.cli.train import train

__all__ = ["write", "train"]
