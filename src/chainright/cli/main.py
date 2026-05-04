#!/usr/bin/env python3
"""
ChainRight CLI - Main Entry Point

Provides command-line interface for ChainRight operations:
    chainright write      - Interactive writing capture with real-time PoE
    chainright train      - Model training on captured sessions
    chainright genesis    - Genesis block management (pretraining corpus)
    chainright tokenize   - Multi-strategy text tokenization
    chainright copyright  - Copyright registration and AI usage detection
"""

import click
from chainright.cli.write import write
from chainright.cli.train import train
from chainright.cli.genesis import genesis
from chainright.cli.tokenize import tokenize
from chainright.cli.copyright import copyright_group


@click.group()
@click.version_option(version="0.1.0", prog_name="ChainRight")
def cli():
    """
    ChainRight: The Relativistic Conversation Blockchain
    
    Transform your thoughts into immutable, valued knowledge assets.
    Protect your creativity from AI scraping with copyright blockchain.
    
    Examples:
        chainright genesis init --sources ./library
        chainright copyright register my_work.txt --title "My Song" --creator "Me" --wallet "0x..."
        chainright write start "My debugging session"
        chainright train latest
    """
    pass


# Add subcommand groups
cli.add_command(genesis)
cli.add_command(write)
cli.add_command(train)
cli.add_command(tokenize)
cli.add_command(copyright_group)


if __name__ == "__main__":
    cli()
