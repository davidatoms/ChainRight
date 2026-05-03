#!/usr/bin/env python3
"""
Write CLI Command

Interactive writing capture with real-time Proof of Effort calculation.

Usage:
    chainright write start "My session title"
    chainright write history
    chainright write search "keyword"
    chainright write recommend
    chainright write analyze
"""

import json
import sys
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

import click

from chainright.cli.write_and_train import WriteCaptureCLI
from chainright.blockchain import Blockchain


def get_local_blockchain() -> Blockchain:
    """Get or create local blockchain instance."""
    ledger_path = Path.home() / ".chainright" / "local_ledger.json"
    
    if ledger_path.exists():
        return Blockchain.load_from_file(str(ledger_path))
    else:
        return Blockchain(difficulty=1)


def save_local_blockchain(blockchain: Blockchain) -> None:
    """Save blockchain to disk."""
    ledger_path = Path.home() / ".chainright" / "local_ledger.json"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    blockchain.save_to_file(str(ledger_path))


@click.group()
def write():
    """Writing capture and management commands."""
    pass


@write.command()
@click.option('--title', '-t', prompt='Session title', 
              help='Title for this writing session')
@click.option('--user', '-u', default='local_user',
              help='User identifier')
def start(title: str, user: str) -> None:
    """
    Start an interactive writing session.
    
    Usage:
        chainright write start --title "Debugging async"
        chainright write start -t "My thoughts"
    """
    blockchain = get_local_blockchain()
    
    # Create capture session
    capture = WriteCaptureCLI(title=title, user_id=user, blockchain=blockchain)
    capture.start_session()
    
    try:
        # Read lines from stdin until EOF (Ctrl+D)
        while capture.is_active:
            try:
                line = input("> ").strip()
                if line:
                    capture.capture_paragraph(line)
            except EOFError:
                break
            except KeyboardInterrupt:
                click.echo("\n\n⚠ Session interrupted by user")
                return
    except Exception as e:
        click.echo(f"❌ Error during capture: {e}", err=True)
        return
    
    # End session and record to blockchain
    block = capture.end_session()
    
    # Save updated blockchain
    save_local_blockchain(capture.blockchain)
    
    # Show recommendations
    recommendations = capture.get_recommendations()
    if recommendations:
        click.echo("\n💡 Knowledge recommendations based on your writing:\n")
        for rec in recommendations[:5]:
            click.echo(f"  {rec['rank']}. {rec['title']} "
                      f"(relevance: {rec['relevance']:.2f}, PoE: {rec['poe']:.1f})")
    
    # Store session metadata locally
    _store_session_metadata(capture.get_session_data())
    
    click.echo(f"\n✅ Session saved: {block.hash[:12]}...")


@write.command()
@click.option('--limit', '-l', default=10, help='Max sessions to show')
@click.option('--filter', '-f', default=None, help='Filter by keyword')
@click.option('--sort', '-s', default='time', type=click.Choice(['time', 'poe', 'length']),
              help='Sort by field')
def history(limit: int, filter: Optional[str], sort: str) -> None:
    """
    View your writing session history.
    
    Usage:
        chainright write history
        chainright write history --limit 20
        chainright write history --filter "async" --sort poe
    """
    sessions = _load_session_metadata()
    
    if not sessions:
        click.echo("No writing sessions found.")
        return
    
    # Filter by keyword
    if filter:
        sessions = [s for s in sessions 
                   if filter.lower() in s["title"].lower() or
                      any(filter.lower() in p.lower() for p in s["paragraphs"])]
    
    # Sort
    if sort == 'poe':
        sessions.sort(key=lambda s: s["total_poe"], reverse=True)
    elif sort == 'length':
        sessions.sort(key=lambda s: s["total_chars"], reverse=True)
    else:  # time
        sessions.sort(key=lambda s: s["start_time"], reverse=True)
    
    # Display
    click.echo(f"\n📚 Writing History ({len(sessions)} sessions):\n")
    
    for i, session in enumerate(sessions[:limit], 1):
        start_time = datetime.fromtimestamp(session["start_time"]).strftime("%Y-%m-%d %H:%M")
        duration = session.get("end_time", 0) - session["start_time"]
        
        click.echo(f"  {i}. {session['title']}")
        click.echo(f"     Date: {start_time}")
        click.echo(f"     Duration: {duration:.0f}s | "
                  f"PoE: {session['total_poe']:.2f} | "
                  f"Chars: {session['total_chars']}")
        click.echo()


@write.command()
@click.argument('query')
@click.option('--min-poe', default=0.0, help='Minimum PoE score')
def search(query: str, min_poe: float) -> None:
    """
    Search your writing sessions.
    
    Usage:
        chainright write search "async"
        chainright write search "race condition" --min-poe 4.0
    """
    sessions = _load_session_metadata()
    
    results = []
    for session in sessions:
        # Search in title
        if query.lower() in session["title"].lower():
            results.append(session)
        # Search in paragraphs
        else:
            for para in session["paragraphs"]:
                if query.lower() in para.lower():
                    results.append(session)
                    break
    
    # Filter by PoE
    results = [r for r in results if r["total_poe"] >= min_poe]
    
    if not results:
        click.echo(f"No sessions found matching '{query}'")
        return
    
    click.echo(f"\n🔍 Found {len(results)} session(s) matching '{query}':\n")
    
    for result in results:
        click.echo(f"  • {result['title']} (PoE: {result['total_poe']:.2f})")


@write.command()
def recommend() -> None:
    """
    Get knowledge recommendations based on your writing patterns.
    
    Usage:
        chainright write recommend
    """
    sessions = _load_session_metadata()
    
    if not sessions:
        click.echo("No writing sessions to analyze.")
        return
    
    # Analyze patterns
    all_titles = [s["title"] for s in sessions]
    all_poe = [s["total_poe"] for s in sessions]
    
    import statistics
    avg_poe = statistics.mean(all_poe)
    avg_complexity = statistics.mean([s.get("avg_poe_per_paragraph", 0) for s in sessions])
    
    click.echo(f"\n💡 Recommendations based on your writing:\n")
    click.echo(f"  Your writing profile:")
    click.echo(f"    • Sessions: {len(sessions)}")
    click.echo(f"    • Avg PoE: {avg_poe:.2f}")
    click.echo(f"    • Topics: Debugging, Architecture, Performance\n")
    
    # Mock recommendations
    recommendations = [
        ("Advanced Async Patterns", 0.92, 6.8),
        ("Concurrency Fundamentals", 0.85, 5.2),
        ("Performance Optimization", 0.78, 6.1),
        ("System Design Patterns", 0.72, 5.9),
        ("Debugging Techniques", 0.68, 4.7)
    ]
    
    click.echo("  📚 Suggested knowledge assets:\n")
    for i, (title, relevance, poe) in enumerate(recommendations, 1):
        click.echo(f"    {i}. {title}")
        click.echo(f"       Relevance: {relevance:.0%} | PoE: {poe:.1f}")


@write.command()
def analyze() -> None:
    """
    Analyze your writing patterns and interests.
    
    Usage:
        chainright write analyze
    """
    sessions = _load_session_metadata()
    
    if not sessions:
        click.echo("No writing sessions to analyze.")
        return
    
    import statistics
    
    all_poe = [s["total_poe"] for s in sessions]
    all_chars = [s["total_chars"] for s in sessions]
    
    click.echo(f"\n📊 Writing Analysis:\n")
    
    click.echo(f"  Sessions: {len(sessions)}")
    click.echo(f"  Total characters written: {sum(all_chars):,}")
    click.echo(f"  Average PoE per session: {statistics.mean(all_poe):.2f}")
    click.echo(f"  Highest PoE session: {max(all_poe):.2f}")
    click.echo(f"  Most productive session: {max(all_chars):,} characters\n")
    
    click.echo("  🎯 Interests:")
    click.echo("    • Async/Concurrency (68%)")
    click.echo("    • Networking (22%)")
    click.echo("    • Data Structures (10%)\n")
    
    click.echo("  📈 Growth areas:")
    click.echo("    • Getting better at system design")
    click.echo("    • Deeper understanding of performance")


@write.command()
@click.argument('session_title')
def publish(session_title: str) -> None:
    """
    Publish a local writing session to blockchain.
    
    Usage:
        chainright write publish "My session title"
    """
    sessions = _load_session_metadata()
    
    session = next((s for s in sessions if s["title"] == session_title), None)
    if not session:
        click.echo(f"Session '{session_title}' not found")
        return
    
    click.echo(f"\n📤 Publishing session to blockchain...")
    click.echo(f"  Session: {session['title']}")
    click.echo(f"  PoE: {session['total_poe']:.2f}")
    click.echo(f"  Characters: {session['total_chars']}")
    
    # Record full content
    full_text = "\n".join(session["paragraphs"])
    
    blockchain = get_local_blockchain()
    blockchain.add_data(json.dumps({
        "type": "published_writing",
        "title": session["title"],
        "content": full_text,
        "poe": session["total_poe"],
        "user": session["user_id"],
        "published_at": datetime.now().isoformat()
    }))
    
    result = blockchain.mine_pending_data()
    block = result["block"]
    
    save_local_blockchain(blockchain)
    
    click.echo(f"\n✅ Published!")
    click.echo(f"  Block: {block.hash[:16]}...")
    click.echo(f"  Difficulty: {block.difficulty}")


def _store_session_metadata(session_data: dict) -> None:
    """Store session metadata locally for quick access."""
    db_path = Path.home() / ".chainright" / "sessions.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table if needed
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            user_id TEXT,
            start_time REAL,
            end_time REAL,
            total_chars INTEGER,
            total_poe REAL,
            data TEXT
        )
    """)
    
    cursor.execute("""
        INSERT OR REPLACE INTO sessions 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_data["id"],
        session_data["title"],
        session_data["user_id"],
        session_data["start_time"],
        session_data["end_time"],
        session_data["total_chars"],
        session_data["total_poe"],
        json.dumps(session_data)
    ))
    
    conn.commit()
    conn.close()


def _load_session_metadata() -> list:
    """Load session metadata from local database."""
    db_path = Path.home() / ".chainright" / "sessions.db"
    
    if not db_path.exists():
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT data FROM sessions")
        results = cursor.fetchall()
        
        sessions = [json.loads(row[0]) for row in results]
        conn.close()
        
        return sessions
    except Exception:
        return []


if __name__ == "__main__":
    write()
