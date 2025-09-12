#!/usr/bin/env python3
"""
Enhanced word list blockchain with online word sources and comprehensive word lists.
"""

import hashlib
import json
import time
import requests
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import os
import urllib.request
import urllib.error


class EnhancedWordListBlock:
    """Represents a block containing a comprehensive word list with metadata."""
    
    def __init__(self, index: int, word_list: List[str], date_str: str, source: str, 
                 word_count: int, previous_hash: str, timestamp: float = None):
        self.index = index
        self.word_list = word_list
        self.date_str = date_str
        self.source = source
        self.word_count = word_count
        self.previous_hash = previous_hash
        self.timestamp = timestamp or time.time()
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block."""
        block_string = json.dumps({
            'index': self.index,
            'word_list': self.word_list,
            'date_str': self.date_str,
            'source': self.source,
            'word_count': self.word_count,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int) -> None:
        """Mine the block with proof of work."""
        target = '0' * difficulty
        
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary for serialization."""
        return {
            'index': self.index,
            'word_list': self.word_list,
            'date_str': self.date_str,
            'source': self.source,
            'word_count': self.word_count,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, block_dict: Dict[str, Any]) -> 'EnhancedWordListBlock':
        """Create a block from dictionary."""
        block = cls(
            index=block_dict['index'],
            word_list=block_dict['word_list'],
            date_str=block_dict['date_str'],
            source=block_dict.get('source', 'unknown'),
            word_count=block_dict.get('word_count', len(block_dict['word_list'])),
            previous_hash=block_dict['previous_hash'],
            timestamp=block_dict['timestamp']
        )
        block.nonce = block_dict['nonce']
        block.hash = block_dict['hash']
        return block


class EnhancedWordListBlockchain:
    """A blockchain that uses comprehensive word lists as genesis blocks."""
    
    def __init__(self, difficulty: int = 4):
        self.chain: List[EnhancedWordListBlock] = []
        self.difficulty = difficulty
        self.pending_data: List[str] = []
    
    def create_enhanced_genesis_block(self, word_list: List[str], date_str: str, source: str) -> None:
        """Create the genesis block with a comprehensive word list."""
        genesis_block = EnhancedWordListBlock(
            index=0, 
            word_list=word_list, 
            date_str=date_str, 
            source=source,
            word_count=len(word_list),
            previous_hash="0"
        )
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
    
    def get_latest_block(self) -> EnhancedWordListBlock:
        """Get the most recent block in the chain."""
        return self.chain[-1]
    
    def add_data(self, data: str) -> None:
        """Add data to the pending transactions."""
        self.pending_data.append(data)
    
    def mine_pending_data(self) -> EnhancedWordListBlock:
        """Mine all pending data into a new block."""
        if not self.pending_data:
            raise ValueError("No pending data to mine")
        
        # Create a new block with all pending data
        new_block = EnhancedWordListBlock(
            index=len(self.chain),
            word_list=self.pending_data,  # Store data in word_list field for consistency
            date_str="",
            source="user_data",
            word_count=len(self.pending_data),
            previous_hash=self.get_latest_block().hash
        )
        
        # Mine the block
        new_block.mine_block(self.difficulty)
        
        # Add to chain
        self.chain.append(new_block)
        
        # Clear pending data
        self.pending_data = []
        
        return new_block
    
    def is_chain_valid(self) -> bool:
        """Validate the entire blockchain."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Check if current block's hash is valid
            if current_block.hash != current_block.calculate_hash():
                return False
            
            # Check if previous hash matches
            if current_block.previous_hash != previous_block.hash:
                return False
        
        return True
    
    def get_chain(self) -> List[Dict[str, Any]]:
        """Get the entire chain as a list of dictionaries."""
        return [block.to_dict() for block in self.chain]
    
    def save_to_file(self, filename: str) -> None:
        """Save the blockchain to a JSON file."""
        with open(filename, 'w') as f:
            json.dump({
                'chain': self.get_chain(),
                'pending_data': self.pending_data,
                'difficulty': self.difficulty
            }, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filename: str) -> 'EnhancedWordListBlockchain':
        """Load a blockchain from a JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        blockchain = cls(difficulty=data['difficulty'])
        blockchain.chain = [EnhancedWordListBlock.from_dict(block_dict) for block_dict in data['chain']]
        blockchain.pending_data = data['pending_data']
        
        return blockchain


def fetch_words_from_url(url: str) -> List[str]:
    """Fetch words from a URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        words = [word.strip().lower() for word in response.text.split('\n') 
                if word.strip().isalpha() and len(word.strip()) > 1]
        return words
    except Exception as e:
        print(f"Failed to fetch from {url}: {e}")
        return []


def get_comprehensive_english_words() -> tuple[List[str], str]:
    """Get a comprehensive list of English words from multiple sources."""
    words = []
    source = "multiple_sources"
    
    # Online word sources
    word_urls = [
        "https://raw.githubusercontent.com/dwyl/english-words/master/words.txt",
        "https://www.mit.edu/~ecprice/wordlist.10000",
        "https://raw.githubusercontent.com/words/an-array-of-english-words/master/words.json"
    ]
    
    print("Fetching words from online sources...")
    
    for url in word_urls:
        try:
            url_words = fetch_words_from_url(url)
            if url_words:
                words.extend(url_words)
                print(f"Fetched {len(url_words)} words from {url}")
        except Exception as e:
            print(f"Failed to fetch from {url}: {e}")
    
    # Local word sources
    local_sources = [
        "/usr/share/dict/words",  # Unix/Linux
        "/usr/dict/words",        # Some Unix systems
        "words.txt"               # Local file
    ]
    
    for source in local_sources:
        if os.path.exists(source):
            try:
                with open(source, 'r') as f:
                    local_words = [word.strip().lower() for word in f.readlines() 
                                  if word.strip().isalpha() and len(word.strip()) > 1]
                words.extend(local_words)
                print(f"Added {len(local_words)} words from {source}")
            except Exception as e:
                print(f"Failed to read from {source}: {e}")
    
    # Remove duplicates and sort
    unique_words = list(set(words))
    unique_words.sort()
    
    # Limit to reasonable size for performance
    if len(unique_words) > 50000:
        unique_words = unique_words[:50000]
        source = "multiple_sources_truncated"
    
    print(f"Total unique words collected: {len(unique_words)}")
    
    return unique_words, source


def get_basic_english_words() -> tuple[List[str], str]:
    """Get a basic list of English words as fallback."""
    basic_words = [
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with", "he", "as", "you", "do", "at",
        "this", "but", "his", "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would", "there", "their", "what",
        "so", "up", "out", "if", "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know", "take",
        "people", "into", "year", "your", "good", "some", "could", "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over",
        "think", "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these",
        "give", "day", "most", "us", "water", "been", "call", "oil", "sit", "now", "find", "down", "day", "did", "get", "come", "made", "may", "part",
        "over", "new", "sound", "take", "only", "little", "work", "know", "place", "year", "live", "me", "back", "give", "most", "very", "after", "thing",
        "our", "just", "name", "good", "sentence", "man", "think", "say", "great", "where", "help", "through", "much", "before", "line", "right", "too",
        "mean", "old", "any", "same", "tell", "boy", "follow", "came", "want", "show", "also", "around", "form", "three", "small", "set", "put", "end",
        "does", "another", "well", "large", "must", "big", "even", "such", "because", "turn", "here", "why", "ask", "went", "men", "read", "need", "land",
        "different", "home", "us", "move", "try", "kind", "hand", "picture", "again", "change", "off", "play", "spell", "air", "away", "animal", "house",
        "point", "page", "letter", "mother", "answer", "found", "study", "still", "learn", "should", "America", "world", "high", "every", "near", "add",
        "food", "between", "own", "below", "country", "plant", "last", "school", "father", "keep", "tree", "never", "start", "city", "earth", "eye",
        "light", "thought", "head", "under", "story", "saw", "left", "don't", "few", "while", "along", "might", "close", "something", "seem", "next",
        "hard", "open", "example", "begin", "life", "always", "those", "both", "paper", "together", "got", "group", "often", "run", "important", "until",
        "children", "side", "feet", "car", "mile", "night", "walk", "white", "sea", "began", "grow", "took", "river", "four", "carry", "state", "once",
        "book", "hear", "stop", "without", "second", "later", "miss", "idea", "enough", "eat", "face", "watch", "far", "Indian", "real", "almost", "let",
        "above", "girl", "sometimes", "mountain", "cut", "young", "talk", "soon", "list", "song", "being", "leave", "family", "it's", "body", "music",
        "color", "stand", "sun", "questions", "fish", "area", "mark", "dog", "horse", "birds", "problem", "complete", "room", "knew", "since", "ever",
        "piece", "told", "usually", "didn't", "friends", "easy", "heard", "order", "red", "door", "sure", "become", "top", "ship", "across", "today",
        "during", "short", "better", "best", "however", "low", "hours", "black", "products", "happened", "whole", "measure", "remember", "early",
        "waves", "reached", "listen", "wind", "rock", "space", "covered", "fast", "several", "hold", "himself", "toward", "five", "step", "morning",
        "passed", "vowel", "true", "hundred", "against", "pattern", "numeral", "table", "north", "slowly", "money", "map", "farm", "pulled", "draw",
        "voice", "seen", "cold", "cried", "plan", "notice", "south", "sing", "war", "ground", "fall", "king", "town", "I'll", "unit", "figure", "certain",
        "field", "travel", "wood", "fire", "upon"
    ]
    
    return basic_words, "basic_english_list"


def create_enhanced_word_list_blockchain(date_str: str = None, difficulty: int = 4, 
                                        use_comprehensive: bool = True) -> EnhancedWordListBlockchain:
    """Create a blockchain with comprehensive English words as the genesis block."""
    if date_str is None:
        date_str = date.today().isoformat()
    
    # Get English words
    if use_comprehensive:
        try:
            words, source = get_comprehensive_english_words()
            if len(words) < 100:  # Fallback if comprehensive fetch fails
                words, source = get_basic_english_words()
        except Exception as e:
            print(f"Comprehensive word fetch failed: {e}")
            words, source = get_basic_english_words()
    else:
        words, source = get_basic_english_words()
    
    # Create blockchain
    blockchain = EnhancedWordListBlockchain(difficulty=difficulty)
    blockchain.create_enhanced_genesis_block(words, date_str, source)
    
    return blockchain


def demo_enhanced_word_list_blockchain():
    """Demonstrate the enhanced word list blockchain functionality."""
    print("Creating an enhanced blockchain with comprehensive English words...")
    
    # Create blockchain with today's date
    today = date.today().isoformat()
    blockchain = create_enhanced_word_list_blockchain(today, difficulty=2, use_comprehensive=True)
    
    print(f"Blockchain created with date: {today}")
    print(f"Genesis block contains {len(blockchain.chain[0].word_list)} English words")
    print(f"Word source: {blockchain.chain[0].source}")
    print(f"Chain length: {len(blockchain.chain)}")
    print(f"Chain valid: {blockchain.is_chain_valid()}")
    
    # Display genesis block info
    genesis = blockchain.chain[0]
    print(f"\nGenesis Block Details:")
    print(f"  Index: {genesis.index}")
    print(f"  Date: {genesis.date_str}")
    print(f"  Source: {genesis.source}")
    print(f"  Word Count: {genesis.word_count}")
    print(f"  First 20 words: {genesis.word_list[:20]}")
    print(f"  Hash: {genesis.hash}")
    print(f"  Nonce: {genesis.nonce}")
    print(f"  Timestamp: {datetime.fromtimestamp(genesis.timestamp)}")
    
    # Add some additional data
    blockchain.add_data("Additional blockchain data after word list")
    blockchain.add_data("More user data")
    blockchain.mine_pending_data()
    
    print(f"\nAfter adding data, chain length: {len(blockchain.chain)}")
    
    # Save to file
    filename = f"enhanced_wordlist_blockchain_{today}.json"
    blockchain.save_to_file(filename)
    print(f"Blockchain saved to {filename}")
    
    return blockchain


if __name__ == "__main__":
    demo_enhanced_word_list_blockchain()
