#!/usr/bin/env python3
"""
Simple Text-Based Visualizer for Word List Blockchain Analysis
Generates charts and visualizations using only text output.
"""

from wordlist_blockchain import create_word_list_blockchain, WordListBlockchain
from collections import Counter
import json
from typing import List, Dict, Any


def create_bar_chart(data: Dict[str, int], title: str, max_width: int = 50) -> str:
    """Create a simple text-based bar chart."""
    if not data:
        return "No data available"
    
    max_value = max(data.values())
    chart = f"\n{title}\n" + "=" * len(title) + "\n"
    
    for key, value in sorted(data.items()):
        bar_length = int((value / max_value) * max_width) if max_value > 0 else 0
        bar = "█" * bar_length
        chart += f"{key:>10}: {bar} {value:,}\n"
    
    return chart


def create_word_length_distribution(words: List[str]) -> str:
    """Create a visualization of word length distribution."""
    length_counts = Counter(len(word) for word in words)
    
    chart = "\nWord Length Distribution\n" + "=" * 30 + "\n"
    chart += "Length | Count | Bar Chart\n"
    chart += "-" * 40 + "\n"
    
    max_count = max(length_counts.values())
    
    for length in sorted(length_counts.keys()):
        count = length_counts[length]
        bar_length = int((count / max_count) * 30) if max_count > 0 else 0
        bar = "█" * bar_length
        chart += f"{length:>6} | {count:>5} | {bar}\n"
    
    return chart


def create_alphabetical_distribution(words: List[str]) -> str:
    """Create a visualization of words by starting letter."""
    letter_counts = Counter(word[0].lower() for word in words if word)
    
    chart = "\nWords by Starting Letter\n" + "=" * 25 + "\n"
    
    for letter in 'abcdefghijklmnopqrstuvwxyz':
        if letter in letter_counts:
            count = letter_counts[letter]
            bar_length = int((count / max(letter_counts.values())) * 40)
            bar = "█" * bar_length
            chart += f"{letter.upper()}: {bar} {count:,}\n"
    
    return chart


def create_comparison_table(blockchains: Dict[str, WordListBlockchain]) -> str:
    """Create a comparison table for multiple blockchains."""
    table = "\nBlockchain Comparison Table\n" + "=" * 35 + "\n"
    table += "Date       | Words  | Avg Len | Hash (first 16 chars)\n"
    table += "-" * 65 + "\n"
    
    for date in sorted(blockchains.keys()):
        blockchain = blockchains[date]
        genesis = blockchain.chain[0]
        words = genesis.word_list
        
        avg_length = sum(len(word) for word in words) / len(words)
        hash_preview = genesis.hash[:16]
        
        table += f"{date} | {len(words):>6,} | {avg_length:>7.1f} | {hash_preview}\n"
    
    return table


def create_semantic_breakdown(words: List[str]) -> str:
    """Create a breakdown of words by semantic categories."""
    categories = {
        'Technology': ['computer', 'internet', 'software', 'hardware', 'digital', 'online', 'web', 'app', 'code', 'data', 'network', 'system', 'program', 'device', 'screen', 'keyboard', 'mouse', 'server', 'database', 'algorithm'],
        'Nature': ['tree', 'flower', 'animal', 'bird', 'fish', 'mountain', 'river', 'ocean', 'forest', 'grass', 'leaf', 'root', 'branch', 'wing', 'fin', 'fur', 'feather', 'stone', 'water', 'earth'],
        'Emotions': ['happy', 'sad', 'angry', 'excited', 'worried', 'calm', 'nervous', 'joyful', 'fearful', 'peaceful', 'anxious', 'confident', 'surprised', 'disappointed', 'grateful', 'proud', 'ashamed', 'curious', 'bored', 'interested'],
        'Colors': ['red', 'blue', 'green', 'yellow', 'black', 'white', 'purple', 'orange', 'pink', 'brown', 'gray', 'gold', 'silver', 'navy', 'crimson', 'emerald', 'violet', 'indigo', 'turquoise', 'maroon'],
        'Numbers': ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'hundred', 'thousand', 'million', 'billion', 'zero', 'first', 'second', 'third', 'fourth', 'fifth'],
        'Family': ['mother', 'father', 'sister', 'brother', 'daughter', 'son', 'grandmother', 'grandfather', 'aunt', 'uncle', 'cousin', 'niece', 'nephew', 'parent', 'child', 'spouse', 'wife', 'husband', 'partner', 'relative']
    }
    
    breakdown = "\nSemantic Category Breakdown\n" + "=" * 30 + "\n"
    
    for category, keywords in categories.items():
        matches = [word for word in words if any(keyword in word.lower() for keyword in keywords)]
        if matches:
            breakdown += f"{category:>12}: {len(matches):>4} words\n"
    
    return breakdown


def create_vocabulary_summary(words: List[str]) -> str:
    """Create a comprehensive vocabulary summary."""
    summary = "\nVocabulary Summary\n" + "=" * 20 + "\n"
    
    # Basic statistics
    total_words = len(words)
    unique_words = len(set(words))
    avg_length = sum(len(word) for word in words) / total_words
    min_length = min(len(word) for word in words)
    max_length = max(len(word) for word in words)
    
    summary += f"Total words: {total_words:,}\n"
    summary += f"Unique words: {unique_words:,}\n"
    summary += f"Average length: {avg_length:.1f} characters\n"
    summary += f"Length range: {min_length}-{max_length} characters\n"
    
    # Most common word lengths
    length_counts = Counter(len(word) for word in words)
    most_common_length = length_counts.most_common(1)[0]
    summary += f"Most common length: {most_common_length[0]} letters ({most_common_length[1]:,} words)\n"
    
    # Words starting with each letter
    letter_counts = Counter(word[0].lower() for word in words if word)
    most_common_letter = letter_counts.most_common(1)[0]
    summary += f"Most common starting letter: '{most_common_letter[0]}' ({most_common_letter[1]:,} words)\n"
    
    return summary


def visualize_blockchain(blockchain: WordListBlockchain, date: str) -> str:
    """Create a comprehensive visualization for a single blockchain."""
    words = blockchain.chain[0].word_list
    
    visualization = f"\n{'='*60}\n"
    visualization += f"BLOCKCHAIN VISUALIZATION FOR {date}\n"
    visualization += f"{'='*60}\n"
    
    # Summary
    visualization += create_vocabulary_summary(words)
    
    # Word length distribution
    visualization += create_word_length_distribution(words)
    
    # Alphabetical distribution
    visualization += create_alphabetical_distribution(words)
    
    # Semantic breakdown
    visualization += create_semantic_breakdown(words)
    
    # Sample words
    visualization += "\nSample Words (first 20):\n"
    visualization += "-" * 25 + "\n"
    visualization += ", ".join(words[:20]) + "\n"
    
    visualization += "\nSample Words (last 20):\n"
    visualization += "-" * 25 + "\n"
    visualization += ", ".join(words[-20:]) + "\n"
    
    return visualization


def compare_multiple_blockchains(dates: List[str]) -> str:
    """Create a comparison visualization for multiple blockchains."""
    print("Creating blockchains for comparison...")
    
    blockchains = {}
    for date in dates:
        print(f"Creating blockchain for {date}...")
        blockchain = create_word_list_blockchain(date, difficulty=1)
        blockchains[date] = blockchain
    
    comparison = f"\n{'='*60}\n"
    comparison += f"COMPARISON OF {len(dates)} BLOCKCHAINS\n"
    comparison += f"{'='*60}\n"
    
    # Comparison table
    comparison += create_comparison_table(blockchains)
    
    # Word count comparison
    word_counts = {date: len(bc.chain[0].word_list) for date, bc in blockchains.items()}
    comparison += create_bar_chart(word_counts, "Word Count Comparison")
    
    # Average length comparison
    avg_lengths = {}
    for date, bc in blockchains.items():
        words = bc.chain[0].word_list
        avg_lengths[date] = sum(len(word) for word in words) / len(words)
    
    comparison += create_bar_chart(avg_lengths, "Average Word Length Comparison")
    
    return comparison


def demo_visualization():
    """Demonstrate the visualization capabilities."""
    print("Word List Blockchain Visualizer")
    print("=" * 40)
    
    # Create a blockchain for today
    from datetime import date
    today = date.today().isoformat()
    
    print(f"Creating blockchain for {today}...")
    blockchain = create_word_list_blockchain(today, difficulty=1)
    
    # Generate visualization
    visualization = visualize_blockchain(blockchain, today)
    print(visualization)
    
    # Save visualization to file
    filename = f"visualization_{today}.txt"
    with open(filename, 'w') as f:
        f.write(visualization)
    
    print(f"\nVisualization saved to {filename}")


def interactive_visualization():
    """Interactive visualization tool."""
    print("Interactive Word List Blockchain Visualizer")
    print("=" * 50)
    
    print("Choose visualization type:")
    print("1. Single blockchain visualization")
    print("2. Multiple blockchain comparison")
    print("3. Custom analysis")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        date = input("Enter date (YYYY-MM-DD): ").strip()
        try:
            blockchain = create_word_list_blockchain(date, difficulty=1)
            visualization = visualize_blockchain(blockchain, date)
            print(visualization)
            
            save = input("Save visualization to file? (y/n): ").lower()
            if save in ['y', 'yes']:
                filename = f"visualization_{date}.txt"
                with open(filename, 'w') as f:
                    f.write(visualization)
                print(f"Visualization saved to {filename}")
        
        except Exception as e:
            print(f"Error: {e}")
    
    elif choice == "2":
        dates = []
        print("Enter dates (one per line, press Enter when done):")
        while True:
            date = input("Date (YYYY-MM-DD): ").strip()
            if not date:
                break
            dates.append(date)
        
        if len(dates) < 2:
            print("Need at least 2 dates for comparison")
            return
        
        try:
            comparison = compare_multiple_blockchains(dates)
            print(comparison)
            
            save = input("Save comparison to file? (y/n): ").lower()
            if save in ['y', 'yes']:
                filename = "blockchain_comparison.txt"
                with open(filename, 'w') as f:
                    f.write(comparison)
                print(f"Comparison saved to {filename}")
        
        except Exception as e:
            print(f"Error: {e}")
    
    elif choice == "3":
        print("Custom analysis options:")
        print("1. Word length analysis")
        print("2. Alphabetical distribution")
        print("3. Semantic category analysis")
        
        sub_choice = input("Enter choice (1-3): ").strip()
        
        date = input("Enter date for analysis (YYYY-MM-DD): ").strip()
        try:
            blockchain = create_word_list_blockchain(date, difficulty=1)
            words = blockchain.chain[0].word_list
            
            if sub_choice == "1":
                print(create_word_length_distribution(words))
            elif sub_choice == "2":
                print(create_alphabetical_distribution(words))
            elif sub_choice == "3":
                print(create_semantic_breakdown(words))
            else:
                print("Invalid choice")
        
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    print("Word List Blockchain Simple Visualizer")
    print("=" * 50)
    
    print("Choose mode:")
    print("1. Demo visualization")
    print("2. Interactive visualization")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        demo_visualization()
    elif choice == "2":
        interactive_visualization()
    else:
        print("Invalid choice, running demo...")
        demo_visualization()
