#!/usr/bin/env python3
"""
Write and Train: Real-time writing capture + ML training pipeline

This module orchestrates the flow:
1. User writes text interactively
2. System captures text in real-time
3. Monolith embeds text and learns from it
4. Physics engine calculates Proof of Effort
5. Local blockchain records session
6. Recommendations update based on writing patterns
"""

import time
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np

from chainright.blockchain import Block, Blockchain
from chainright.geometrics import LLMGeometrics


class WriteCaptureCLI:
    """
    Manages real-time writing capture with simultaneous ML training.
    
    Workflow:
        start_session() → capture_paragraph() [loop] → end_session()
    """
    
    def __init__(self, title: str, user_id: str = "local_user", 
                 blockchain: Optional[Blockchain] = None):
        """
        Initialize a new writing capture session.
        
        Args:
            title: Title of the writing session
            user_id: User identifier
            blockchain: Optional blockchain instance for recording
        """
        self.session_id = str(uuid.uuid4())
        self.title = title
        self.user_id = user_id
        self.blockchain = blockchain or Blockchain(difficulty=1)
        
        self.session = {
            "id": self.session_id,
            "title": title,
            "user_id": user_id,
            "start_time": None,
            "end_time": None,
            "paragraphs": [],
            "paragraph_metadata": [],
            "embeddings": [],
            "poe_scores": [],
            "total_poe": 0.0,
            "total_chars": 0,
            "features": {}
        }
        
        self.is_active = False
        self.paragraph_count = 0
    
    def start_session(self) -> None:
        """Begin a new writing capture session."""
        self.session["start_time"] = time.time()
        self.is_active = True
        
        print(f"\n{'='*60}")
        print(f"📝 Writing Session: {self.title}")
        print(f"Session ID: {self.session_id}")
        print(f"{'='*60}")
        print("Type your thoughts. Press Ctrl+D to finish.\n")
    
    def capture_paragraph(self, text: str) -> Dict[str, Any]:
        """
        Capture a single paragraph and immediately process it.
        
        Processing pipeline:
        1. Extract writing features (complexity, technical density, etc.)
        2. Calculate Proof of Effort
        3. Prepare for training
        
        Args:
            text: The paragraph text to capture
            
        Returns:
            Dictionary with captured metadata
        """
        if not text.strip():
            return None
        
        self.paragraph_count += 1
        timestamp = time.time()
        
        # 1. Extract features
        features = self._extract_features(text)
        
        # 2. Calculate PoE (using existing geometrics)
        poe_score = LLMGeometrics.score_difficulty(
            text,
            base_difficulty=2,
            latency_ms=0
        )
        
        # 3. Create mock embedding (will be real with Monolith)
        embedding = self._create_mock_embedding(text)
        
        # 4. Store in session
        self.session["paragraphs"].append(text)
        self.session["paragraph_metadata"].append({
            "index": self.paragraph_count,
            "timestamp": timestamp,
            "char_count": len(text),
            "word_count": len(text.split()),
            "poe_score": poe_score,
            "features": features
        })
        self.session["embeddings"].append(embedding)
        self.session["poe_scores"].append(poe_score)
        self.session["total_poe"] += poe_score
        self.session["total_chars"] += len(text)
        
        # 5. Display feedback
        self._display_capture_feedback(text, poe_score, features)
        
        return {
            "text": text,
            "embedding": embedding,
            "poe": poe_score,
            "features": features,
            "timestamp": timestamp
        }
    
    def _extract_features(self, text: str) -> Dict[str, Any]:
        """Extract writing features for training."""
        words = text.split()
        chars = len(text)
        
        # Basic feature extraction
        features = {
            "char_count": chars,
            "word_count": len(words),
            "avg_word_length": chars / len(words) if words else 0,
            "sentence_count": text.count('.') + text.count('!') + text.count('?'),
            "technical_density": self._calculate_technical_density(text),
            "complexity": self._calculate_complexity(text),
            "sentiment": self._estimate_sentiment(text)
        }
        
        return features
    
    def _calculate_technical_density(self, text: str) -> float:
        """Estimate technical density (0.0 to 1.0)."""
        technical_keywords = [
            'async', 'await', 'thread', 'race', 'mutex', 'lock',
            'algorithm', 'optimization', 'pattern', 'architecture',
            'deploy', 'scale', 'performance', 'memory', 'cpu',
            'network', 'database', 'cache', 'queue', 'index'
        ]
        
        text_lower = text.lower()
        count = sum(1 for keyword in technical_keywords if keyword in text_lower)
        density = min(count / len(text.split()), 1.0)
        
        return density
    
    def _calculate_complexity(self, text: str) -> float:
        """Estimate text complexity (0.0 to 1.0)."""
        # Longer text, more technical, more detailed = more complex
        features = self._extract_features(text)
        complexity = (
            features["technical_density"] * 0.5 +
            min(features["avg_word_length"] / 10, 1.0) * 0.3 +
            min(features["sentence_count"] / 5, 1.0) * 0.2
        )
        return min(complexity, 1.0)
    
    def _estimate_sentiment(self, text: str) -> str:
        """Rough sentiment estimation."""
        positive_words = ['great', 'excellent', 'solved', 'working', 'efficient']
        negative_words = ['problem', 'error', 'bug', 'issue', 'failed']
        
        text_lower = text.lower()
        pos_count = sum(1 for w in positive_words if w in text_lower)
        neg_count = sum(1 for w in negative_words if w in text_lower)
        
        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        else:
            return "neutral"
    
    def _create_mock_embedding(self, text: str) -> List[float]:
        """
        Create a mock embedding (placeholder until Monolith integration).
        
        In production, this would call Monolith's embed_text().
        """
        # For now: Hash-based pseudo-embedding
        import hashlib
        hash_val = hashlib.sha256(text.encode()).hexdigest()
        
        # Convert to 32-dim vector (mock)
        embedding = [
            float(hash_val[i:i+2], 16) / 255.0 
            for i in range(0, 64, 2)
        ]
        
        return embedding
    
    def _display_capture_feedback(self, text: str, poe: float, 
                                  features: Dict[str, Any]) -> None:
        """Display real-time feedback to user."""
        print(f"  ✓ Captured ({features['word_count']} words, "
              f"PoE: {poe:.2f}, complexity: {features['complexity']:.2f})")
    
    def end_session(self) -> Block:
        """
        Finalize the writing session and record to blockchain.
        
        Returns:
            Block: The mined block containing this session
        """
        self.session["end_time"] = time.time()
        self.is_active = False
        
        duration = self.session["end_time"] - self.session["start_time"]
        
        # Create data structure for blockchain
        session_data = {
            "type": "writing_session",
            "session_id": self.session_id,
            "title": self.title,
            "user_id": self.user_id,
            "duration_seconds": duration,
            "paragraph_count": self.paragraph_count,
            "total_chars": self.session["total_chars"],
            "total_poe": self.session["total_poe"],
            "avg_poe_per_paragraph": self.session["total_poe"] / max(self.paragraph_count, 1),
            "metadata": self.session["paragraph_metadata"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to blockchain
        self.blockchain.add_data(json.dumps(session_data))
        result = self.blockchain.mine_pending_data(latency_ms=duration * 1000)
        
        block = result["block"]
        
        # Display summary
        self._display_session_summary(duration, block)
        
        return block
    
    def _display_session_summary(self, duration: float, block: Block) -> None:
        """Display session completion summary."""
        print(f"\n{'='*60}")
        print("✓ Session Complete!")
        print(f"{'='*60}")
        print(f"Block Hash: {block.hash[:16]}...")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Paragraphs: {self.paragraph_count}")
        print(f"Total Characters: {self.session['total_chars']}")
        print(f"Total Proof of Effort: {self.session['total_poe']:.2f}")
        print(f"Average PoE per paragraph: {self.session['total_poe'] / max(self.paragraph_count, 1):.2f}")
        print(f"Difficulty: {block.difficulty}")
        print(f"Nonce: {block.nonce}")
        print(f"{'='*60}\n")
    
    def get_session_data(self) -> Dict[str, Any]:
        """Get the complete session data."""
        return self.session
    
    def get_user_embedding(self) -> Optional[np.ndarray]:
        """
        Get averaged user embedding from this session.
        
        Returns:
            User embedding vector or None if no embeddings
        """
        if not self.session["embeddings"]:
            return None
        
        embeddings_array = np.array(self.session["embeddings"])
        user_embedding = np.mean(embeddings_array, axis=0)
        
        return user_embedding
    
    def get_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get knowledge recommendations based on writing patterns.
        
        In full implementation, these would come from Monolith.
        For now, returns mock recommendations based on PoE scores.
        """
        # Analyze writing patterns
        avg_complexity = np.mean([
            m["features"]["complexity"] 
            for m in self.session["paragraph_metadata"]
        ])
        
        avg_technical = np.mean([
            m["features"]["technical_density"] 
            for m in self.session["paragraph_metadata"]
        ])
        
        # Mock recommendations (would be Monolith-based)
        recommendations = [
            {
                "rank": 1,
                "title": "Advanced Async Patterns",
                "relevance": 0.92 if avg_technical > 0.5 else 0.45,
                "poe": 6.8
            },
            {
                "rank": 2,
                "title": "Concurrency Fundamentals",
                "relevance": 0.85 if avg_complexity > 0.6 else 0.55,
                "poe": 5.2
            },
            {
                "rank": 3,
                "title": "Performance Optimization",
                "relevance": 0.78 if avg_technical > 0.3 else 0.40,
                "poe": 6.1
            }
        ]
        
        return sorted(recommendations, key=lambda x: x["relevance"], reverse=True)


class TrainingOrchestrator:
    """
    Manages the training phase: converting captured sessions to embeddings/features.
    
    Coordinates:
    1. Session data → Feature extraction
    2. Features → Monolith embeddings
    3. Embeddings → User model updates
    4. Training → Validation
    """
    
    def __init__(self):
        """Initialize training orchestrator."""
        self.trained_sessions = []
        self.user_model = None
    
    def train_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train on a captured session.
        
        Args:
            session_data: Session data from WriteCaptureCLI
            
        Returns:
            Training results and metrics
        """
        print(f"\n🤖 Training on session: {session_data['title']}")
        
        # Extract features
        features_list = [m["features"] for m in session_data["metadata"]]
        
        # Create training data
        training_data = {
            "session_id": session_data["session_id"],
            "user_id": session_data["user_id"],
            "paragraphs": session_data.get("paragraphs", []),
            "features": features_list,
            "poe_scores": session_data.get("poe_scores", []),
        }
        
        # Placeholder for Monolith training
        results = {
            "session_id": session_data["session_id"],
            "paragraphs_trained": len(features_list),
            "avg_poe": np.mean(session_data.get("poe_scores", [1.0])),
            "status": "success"
        }
        
        self.trained_sessions.append(results)
        
        print(f"  ✓ Trained on {len(features_list)} paragraphs")
        print(f"  ✓ Average PoE: {results['avg_poe']:.2f}")
        
        return results
    
    def get_training_summary(self) -> Dict[str, Any]:
        """Get summary of all training completed."""
        if not self.trained_sessions:
            return {"sessions_trained": 0}
        
        return {
            "sessions_trained": len(self.trained_sessions),
            "total_paragraphs": sum(s["paragraphs_trained"] for s in self.trained_sessions),
            "avg_poe_across_sessions": np.mean([s["avg_poe"] for s in self.trained_sessions])
        }
