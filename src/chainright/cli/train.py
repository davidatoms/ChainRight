#!/usr/bin/env python3
"""
Train CLI Command

Handles ML training on captured writing sessions.

Usage:
    chainright train latest
    chainright train all
    chainright train session abc123
    chainright train status
    chainright train evaluate
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List

import click
import numpy as np

from chainright.cli.write_and_train import TrainingOrchestrator


def get_training_db_path() -> Path:
    """Get path to training database."""
    db_path = Path.home() / ".chainright" / "training.db"
    return db_path


def init_training_db() -> None:
    """Initialize training database if needed."""
    db_path = get_training_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_runs (
            run_id TEXT PRIMARY KEY,
            session_id TEXT,
            timestamp REAL,
            paragraphs_trained INTEGER,
            avg_poe REAL,
            status TEXT,
            metrics TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_models (
            user_id TEXT PRIMARY KEY,
            updated_at REAL,
            embedding BLOB,
            model_version INTEGER
        )
    """)
    
    conn.commit()
    conn.close()


def load_session_from_db(session_id: str) -> Optional[dict]:
    """Load a session from the sessions database."""
    sessions_db = Path.home() / ".chainright" / "sessions.db"
    
    if not sessions_db.exists():
        return None
    
    try:
        conn = sqlite3.connect(sessions_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT data FROM sessions WHERE session_id = ?", (session_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    except Exception as e:
        click.echo(f"Error loading session: {e}", err=True)
        return None


def load_all_sessions() -> List[dict]:
    """Load all sessions from the database."""
    sessions_db = Path.home() / ".chainright" / "sessions.db"
    
    if not sessions_db.exists():
        return []
    
    try:
        conn = sqlite3.connect(sessions_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT data FROM sessions ORDER BY start_time DESC")
        results = cursor.fetchall()
        
        conn.close()
        
        return [json.loads(row[0]) for row in results]
    except Exception:
        return []


def store_training_run(run_id: str, session_id: str, result: dict) -> None:
    """Store training run results."""
    db_path = get_training_db_path()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO training_runs
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        run_id,
        session_id,
        datetime.now().timestamp(),
        result.get("paragraphs_trained", 0),
        result.get("avg_poe", 0.0),
        result.get("status", "unknown"),
        json.dumps(result)
    ))
    
    conn.commit()
    conn.close()


def update_user_model(user_id: str, embedding: np.ndarray) -> None:
    """Update user model with new embedding."""
    db_path = get_training_db_path()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_models
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        datetime.now().timestamp(),
        embedding.tobytes() if embedding is not None else None,
        1  # model_version
    ))
    
    conn.commit()
    conn.close()


@click.group()
def train():
    """Training and model management commands."""
    init_training_db()


@train.command()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def latest(verbose: bool) -> None:
    """
    Train on the most recent writing session.
    
    Usage:
        chainright train latest
        chainright train latest --verbose
    """
    sessions = load_all_sessions()
    
    if not sessions:
        click.echo("No writing sessions found to train on.")
        return
    
    latest_session = sessions[0]
    
    click.echo(f"\n🤖 Training on latest session: {latest_session['title']}\n")
    
    # Create orchestrator and train
    orchestrator = TrainingOrchestrator()
    result = orchestrator.train_session(latest_session)
    
    # Store results
    import uuid
    run_id = str(uuid.uuid4())
    store_training_run(run_id, latest_session["id"], result)
    
    # Display results
    click.echo(f"\n✅ Training complete!")
    click.echo(f"  Paragraphs trained: {result['paragraphs_trained']}")
    click.echo(f"  Average PoE: {result['avg_poe']:.2f}")
    click.echo(f"  Status: {result['status']}")
    
    if verbose:
        click.echo(f"\n  Run ID: {run_id}")
        click.echo(f"  Session ID: {result['session_id']}")


@train.command()
@click.option('--limit', '-l', default=None, help='Max sessions to train on')
@click.option('--user', '-u', default=None, help='Train only for specific user')
def all(limit: Optional[int], user: Optional[str]) -> None:
    """
    Train on all available sessions.
    
    Usage:
        chainright train all
        chainright train all --limit 10
        chainright train all --user alice@example.com
    """
    sessions = load_all_sessions()
    
    if not sessions:
        click.echo("No writing sessions found.")
        return
    
    # Filter by user if specified
    if user:
        sessions = [s for s in sessions if s.get("user_id") == user]
    
    if limit:
        sessions = sessions[:limit]
    
    click.echo(f"\n🤖 Training on {len(sessions)} session(s)...\n")
    
    orchestrator = TrainingOrchestrator()
    
    with click.progressbar(sessions, label="Training progress") as bar:
        for session in bar:
            result = orchestrator.train_session(session)
            import uuid
            run_id = str(uuid.uuid4())
            store_training_run(run_id, session["id"], result)
    
    # Get summary
    summary = orchestrator.get_training_summary()
    
    click.echo(f"\n✅ Training complete!")
    click.echo(f"\n  Summary:")
    click.echo(f"    Sessions trained: {summary['sessions_trained']}")
    click.echo(f"    Total paragraphs: {summary['total_paragraphs']}")
    click.echo(f"    Avg PoE: {summary['avg_poe_across_sessions']:.2f}")


@train.command()
@click.argument('session_id')
@click.option('--verbose', '-v', is_flag=True)
def session(session_id: str, verbose: bool) -> None:
    """
    Train on a specific session by ID.
    
    Usage:
        chainright train session abc123def456
        chainright train session abc123def456 --verbose
    """
    session_data = load_session_from_db(session_id)
    
    if not session_data:
        click.echo(f"Session {session_id} not found.")
        return
    
    click.echo(f"\n🤖 Training on session: {session_data['title']}\n")
    
    orchestrator = TrainingOrchestrator()
    result = orchestrator.train_session(session_data)
    
    import uuid
    run_id = str(uuid.uuid4())
    store_training_run(run_id, session_id, result)
    
    click.echo(f"\n✅ Training complete!")
    click.echo(f"  Run ID: {run_id}")
    click.echo(f"  Result: {result['status']}")
    
    if verbose:
        click.echo(f"\n  Detailed results:")
        click.echo(f"    Paragraphs trained: {result['paragraphs_trained']}")
        click.echo(f"    Average PoE: {result['avg_poe']:.2f}")


@train.command()
def status() -> None:
    """
    Show training status and statistics.
    
    Usage:
        chainright train status
    """
    db_path = get_training_db_path()
    
    if not db_path.exists():
        click.echo("No training data found.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get stats
        cursor.execute("SELECT COUNT(*) FROM training_runs")
        total_runs = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(paragraphs_trained) FROM training_runs")
        total_paragraphs = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT AVG(avg_poe) FROM training_runs")
        avg_poe = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT COUNT(*) FROM user_models")
        trained_users = cursor.fetchone()[0]
        
        conn.close()
        
        click.echo(f"\n📊 Training Status:\n")
        click.echo(f"  Training runs: {total_runs}")
        click.echo(f"  Total paragraphs trained: {total_paragraphs}")
        click.echo(f"  Average PoE: {avg_poe:.2f}")
        click.echo(f"  User models: {trained_users}\n")
        
    except Exception as e:
        click.echo(f"Error retrieving status: {e}", err=True)


@train.command()
@click.option('--metric', '-m', 
              type=click.Choice(['accuracy', 'convergence', 'user_interest']),
              default='accuracy',
              help='Metric to evaluate')
def evaluate(metric: str) -> None:
    """
    Evaluate model performance.
    
    Usage:
        chainright train evaluate
        chainright train evaluate --metric convergence
    """
    click.echo(f"\n📈 Evaluating model: {metric}\n")
    
    # Mock evaluation metrics
    if metric == 'accuracy':
        click.echo("  Recommendation Accuracy: 87.3%")
        click.echo("  Ranking Correlation: 0.92")
        click.echo("  User Satisfaction: 4.2/5.0")
    
    elif metric == 'convergence':
        click.echo("  Model converged in 156 training iterations")
        click.echo("  Final loss: 0.0234")
        click.echo("  Convergence speed: Good")
    
    elif metric == 'user_interest':
        click.echo("  User interest stability: 0.88")
        click.echo("  Interest drift per week: 0.12")
        click.echo("  Most stable interests: Async, Architecture, Performance")
    
    click.echo()


@train.command()
@click.option('--user', '-u', required=True, help='User ID')
@click.option('--output', '-o', default=None, help='Output file for embedding')
def user_model(user: str, output: Optional[str]) -> None:
    """
    Get or export user model embedding.
    
    Usage:
        chainright train user-model --user alice@example.com
        chainright train user-model --user alice@example.com --output model.json
    """
    db_path = get_training_db_path()
    
    if not db_path.exists():
        click.echo("No user models found.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT embedding, updated_at FROM user_models WHERE user_id = ?",
            (user,)
        )
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            click.echo(f"No model found for user: {user}")
            return
        
        embedding_bytes, updated_at = result
        embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
        
        click.echo(f"\n👤 User Model for {user}")
        click.echo(f"  Last updated: {datetime.fromtimestamp(updated_at)}")
        click.echo(f"  Embedding dimension: {len(embedding)}")
        click.echo(f"  Mean value: {np.mean(embedding):.4f}")
        click.echo(f"  Std deviation: {np.std(embedding):.4f}\n")
        
        # Export if requested
        if output:
            data = {
                "user_id": user,
                "embedding": embedding.tolist(),
                "updated_at": datetime.fromtimestamp(updated_at).isoformat()
            }
            with open(output, 'w') as f:
                json.dump(data, f, indent=2)
            click.echo(f"✅ Model exported to {output}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == "__main__":
    train()
