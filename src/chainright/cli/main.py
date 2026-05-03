#!/usr/bin/env python3
"""
ChainRight CLI - Main Entry Point

Provides command-line interface for ChainRight operations:
    chainright write      - Interactive writing capture with real-time PoE
    chainright train      - Model training on captured sessions
"""

import click
from chainright.cli.write import write
from chainright.cli.train import train


@click.group()
@click.version_option(version="0.1.0", prog_name="ChainRight")
def cli():
    """
    ChainRight: The Relativistic Conversation Blockchain
    
    Transform your thoughts into immutable, valued knowledge assets.
    
    Examples:
        chainright write start "My debugging session"
        chainright train latest
        chainright write history --sort poe
    """
    pass


# Add subcommand groups
cli.add_command(write)
cli.add_command(train)


if __name__ == "__main__":
    cli()
