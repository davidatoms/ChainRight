#!/usr/bin/env python3
"""
Blockchain Visualizer with Interactive Claude Conversations
Shows all blocks, their ownership, and enables interactive Claude back-and-forth.
"""

import json
import time
from datetime import datetime, date
from typing import Dict, Any, List
from ownership_blockchain import OwnershipBlockchain, OwnedSentence
from input_output_tokens import ClaudeInteractionManager
import os


class BlockchainVisualizer:
    """Visualizes blockchain blocks and ownership information."""
    
    def __init__(self, blockchain: OwnershipBlockchain):
        self.blockchain = blockchain
    
    def visualize_block(self, block, block_index: int) -> str:
        """Create a detailed visualization of a single block."""
        visualization = f"\n{'='*80}\n"
        visualization += f"BLOCK {block_index}\n"
        visualization += f"{'='*80}\n"
        
        # Block metadata
        visualization += f"Index: {block.index}\n"
        visualization += f"Date: {block.date_str}\n"
        visualization += f"Hash: {block.hash}\n"
        visualization += f"Previous Hash: {block.previous_hash[:16]}...\n"
        visualization += f"Nonce: {block.nonce}\n"
        visualization += f"Timestamp: {datetime.fromtimestamp(block.timestamp)}\n"
        visualization += f"Total Sentences: {len(block.sentences)}\n"
        
        # Authors in this block
        authors = block.get_authors()
        visualization += f"Authors: {', '.join(authors)}\n"
        
        # Sentences by author
        visualization += f"\nSENTENCES BY AUTHOR:\n"
        visualization += f"{'-'*40}\n"
        
        for author in authors:
            author_sentences = block.get_sentences_by_author(author)
            visualization += f"\n{author.upper()} ({len(author_sentences)} sentences):\n"
            
            for i, sentence in enumerate(author_sentences, 1):
                # Format sentence based on type
                if "Claude API interaction" in sentence.text:
                    # Parse token information
                    parts = sentence.text.split(',')
                    input_tokens = "unknown"
                    output_tokens = "unknown"
                    curl_hash = "unknown"
                    
                    for part in parts:
                        if 'input tokens' in part:
                            input_tokens = part.split()[0]
                        elif 'output tokens' in part:
                            output_tokens = part.split()[0]
                        elif 'curl_hash' in part:
                            curl_hash = part.split(':')[1].strip()
                    
                    visualization += f"  {i}. API Interaction - Input: {input_tokens}, Output: {output_tokens}, Hash: {curl_hash}\n"
                elif "Claude response" in sentence.text:
                    visualization += f"  {i}. Claude Response: {sentence.text[18:80]}{'...' if len(sentence.text) > 80 else ''}\n"
                elif "Prompt:" in sentence.text:
                    visualization += f"  {i}. Prompt Details: {sentence.text[8:80]}{'...' if len(sentence.text) > 80 else ''}\n"
                else:
                    visualization += f"  {i}. {sentence.text[:80]}{'...' if len(sentence.text) > 80 else ''}\n"
        
        return visualization
    
    def visualize_chain_summary(self) -> str:
        """Create a summary visualization of the entire chain."""
        visualization = f"\n{'='*80}\n"
        visualization += f"BLOCKCHAIN SUMMARY\n"
        visualization += f"{'='*80}\n"
        
        visualization += f"Total Blocks: {len(self.blockchain.chain)}\n"
        visualization += f"Total Sentences: {sum(len(block.sentences) for block in self.blockchain.chain)}\n"
        visualization += f"Chain Valid: {self.blockchain.is_chain_valid()}\n"
        
        # Get all authors
        all_authors = self.blockchain.get_all_authors()
        visualization += f"Total Authors: {len(all_authors)}\n"
        visualization += f"Authors: {', '.join(all_authors)}\n"
        
        # Block summary table
        visualization += f"\nBLOCK SUMMARY TABLE:\n"
        visualization += f"{'-'*80}\n"
        visualization += f"{'Block':<6} {'Date':<12} {'Authors':<20} {'Sentences':<10} {'Hash (first 16)':<20}\n"
        visualization += f"{'-'*80}\n"
        
        for i, block in enumerate(self.blockchain.chain):
            authors_str = ', '.join(block.get_authors())
            if len(authors_str) > 18:
                authors_str = authors_str[:15] + "..."
            
            visualization += f"{block.index:<6} {block.date_str:<12} {authors_str:<20} {len(block.sentences):<10} {block.hash[:16]:<20}\n"
        
        return visualization
    
    def visualize_ownership_analysis(self) -> str:
        """Create detailed ownership analysis."""
        visualization = f"\n{'='*80}\n"
        visualization += f"OWNERSHIP ANALYSIS\n"
        visualization += f"{'='*80}\n"
        
        # Get ownership summary
        summary = self.blockchain.get_ownership_summary()
        
        visualization += f"Total Blocks: {summary['total_blocks']}\n"
        visualization += f"Total Sentences: {summary['total_sentences']}\n"
        visualization += f"All Authors: {', '.join(summary['authors'])}\n"
        
        # Author statistics
        visualization += f"\nAUTHOR STATISTICS:\n"
        visualization += f"{'-'*40}\n"
        
        for author, stats in summary['author_stats'].items():
            if author != "system":
                first_time = datetime.fromtimestamp(stats['first_contribution'])
                last_time = datetime.fromtimestamp(stats['last_contribution'])
                visualization += f"\n{author.upper()}:\n"
                visualization += f"  Sentences: {stats['sentence_count']}\n"
                visualization += f"  First Contribution: {first_time}\n"
                visualization += f"  Last Contribution: {last_time}\n"
        
        # Date statistics
        visualization += f"\nCONTRIBUTIONS BY DATE:\n"
        visualization += f"{'-'*40}\n"
        
        for date_str, sentences in summary['date_stats'].items():
            authors_on_date = set(s['author'] for s in sentences)
            visualization += f"\n{date_str}:\n"
            visualization += f"  Sentences: {len(sentences)}\n"
            visualization += f"  Authors: {', '.join(authors_on_date)}\n"
        
        return visualization
    
    def visualize_conversation_flow(self) -> str:
        """Visualize conversation flow between users and Claude."""
        visualization = f"\n{'='*80}\n"
        visualization += f"CONVERSATION FLOW\n"
        visualization += f"{'='*80}\n"
        
        all_sentences = []
        for block in self.blockchain.chain:
            all_sentences.extend(block.sentences)
        
        # Sort by timestamp
        all_sentences.sort(key=lambda x: x.timestamp)
        
        current_conversation = []
        conversations = []
        
        for sentence in all_sentences:
            if sentence.author in ["claude", "system"]:
                current_conversation.append(sentence)
            else:
                if current_conversation:
                    conversations.append(current_conversation)
                current_conversation = [sentence]
        
        if current_conversation:
            conversations.append(current_conversation)
        
        for i, conversation in enumerate(conversations, 1):
            visualization += f"\nConversation {i}:\n"
            visualization += f"{'-'*40}\n"
            
            for sentence in conversation:
                timestamp = datetime.fromtimestamp(sentence.timestamp)
                if sentence.author == "claude":
                    visualization += f"[{timestamp.strftime('%H:%M:%S')}] Claude: {sentence.text[18:60]}{'...' if len(sentence.text) > 60 else ''}\n"
                elif sentence.author == "system":
                    visualization += f"[{timestamp.strftime('%H:%M:%S')}] System: {sentence.text[:60]}{'...' if len(sentence.text) > 60 else ''}\n"
                else:
                    visualization += f"[{timestamp.strftime('%H:%M:%S')}] {sentence.author}: {sentence.text[:60]}{'...' if len(sentence.text) > 60 else ''}\n"
        
        return visualization
    
    def save_visualization(self, filename: str = None) -> str:
        """Save complete visualization to file."""
        if filename is None:
            today = date.today().isoformat()
            filename = f"blockchain_visualization_{today}.txt"
        
        visualization = ""
        visualization += self.visualize_chain_summary()
        visualization += self.visualize_ownership_analysis()
        visualization += self.visualize_conversation_flow()
        
        # Add detailed block visualizations
        for i, block in enumerate(self.blockchain.chain):
            visualization += self.visualize_block(block, i)
        
        with open(filename, 'w') as f:
            f.write(visualization)
        
        return filename


class InteractiveClaudeConversation:
    """Interactive Claude conversation with blockchain visualization."""
    
    def __init__(self, api_key: str = None):
        self.manager = ClaudeInteractionManager(api_key)
        self.visualizer = BlockchainVisualizer(self.manager.blockchain)
        self.conversation_history = []
    
    def start_conversation(self):
        """Start an interactive conversation with Claude."""
        print("Interactive Claude Conversation with Blockchain Visualization")
        print("=" * 70)
        
        # Check for API key
        api_key = os.getenv('CLAUDE_API_KEY')
        if not api_key:
            print("No CLAUDE_API_KEY found. Set it with: export CLAUDE_API_KEY='your-key-here'")
            print("Running in mock mode...")
        
        print("\nCommands:")
        print("  'chat' - Start a conversation with Claude")
        print("  'visualize' - Show blockchain visualization")
        print("  'stats' - Show conversation statistics")
        print("  'save' - Save blockchain to file")
        print("  'quit' - Exit")
        
        while True:
            print(f"\n{'='*50}")
            command = input("Enter command: ").strip().lower()
            
            if command == 'quit':
                break
            elif command == 'chat':
                self.chat_with_claude()
            elif command == 'visualize':
                self.show_visualization()
            elif command == 'stats':
                self.show_statistics()
            elif command == 'save':
                self.save_blockchain()
            else:
                print("Unknown command. Use: chat, visualize, stats, save, or quit")
        
        # Final save
        self.save_blockchain()
        print("Conversation ended. Blockchain saved.")
    
    def chat_with_claude(self):
        """Interactive chat with Claude."""
        print("\nStarting chat with Claude...")
        print("Type 'back' to return to main menu")
        
        user_name = input("Enter your name: ").strip()
        if not user_name or user_name.lower() == 'back':
            return
        
        conversation_count = 0
        
        while True:
            print(f"\n{'='*40}")
            prompt = input(f"{user_name}: ").strip()
            
            if not prompt:
                continue
            elif prompt.lower() == 'back':
                break
            
            conversation_count += 1
            print(f"\nConversation #{conversation_count}")
            
            # Interact with Claude
            result = self.manager.interact_with_claude(prompt, user_name)
            
            if result['success']:
                print(f"\nClaude: {result['claude_response']}")
                
                # Add to conversation history
                self.conversation_history.append({
                    'user': user_name,
                    'prompt': prompt,
                    'claude_response': result['claude_response'],
                    'timestamp': time.time()
                })
            else:
                print(f"Error: {result['error']}")
    
    def show_visualization(self):
        """Show blockchain visualization."""
        print("\n" + "="*80)
        print("BLOCKCHAIN VISUALIZATION")
        print("="*80)
        
        # Show summary
        print(self.visualizer.visualize_chain_summary())
        
        # Show ownership analysis
        print(self.visualizer.visualize_ownership_analysis())
        
        # Show conversation flow
        print(self.visualizer.visualize_conversation_flow())
        
        # Ask if user wants to see detailed blocks
        show_details = input("\nShow detailed block information? (y/n): ").strip().lower()
        if show_details in ['y', 'yes']:
            for i, block in enumerate(self.blockchain.chain):
                print(self.visualizer.visualize_block(block, i))
    
    def show_statistics(self):
        """Show conversation statistics."""
        stats = self.manager.get_token_statistics()
        
        print(f"\n{'='*50}")
        print("CONVERSATION STATISTICS")
        print(f"{'='*50}")
        print(f"Total input tokens: {stats['total_input_tokens']:,}")
        print(f"Total output tokens: {stats['total_output_tokens']:,}")
        print(f"Total interactions: {stats['total_interactions']}")
        print(f"Unique curl scripts: {stats['unique_curl_scripts']}")
        print(f"Unique users: {stats['unique_users']}")
        print(f"Users: {', '.join(stats['users'])}")
        
        # Conversation history
        print(f"\nConversation History:")
        print(f"Total conversations: {len(self.conversation_history)}")
        for i, conv in enumerate(self.conversation_history, 1):
            timestamp = datetime.fromtimestamp(conv['timestamp'])
            print(f"  {i}. [{timestamp.strftime('%H:%M:%S')}] {conv['user']}: {conv['prompt'][:50]}{'...' if len(conv['prompt']) > 50 else ''}")
    
    def save_blockchain(self):
        """Save blockchain and visualization."""
        # Save blockchain
        blockchain_file = self.manager.save_blockchain()
        print(f"Blockchain saved to: {blockchain_file}")
        
        # Save visualization
        viz_file = self.visualizer.save_visualization()
        print(f"Visualization saved to: {viz_file}")
        
        return blockchain_file, viz_file


def demo_visualization():
    """Demonstrate blockchain visualization with sample data."""
    print("Blockchain Visualization Demo")
    print("=" * 40)
    
    # Create a sample blockchain with conversations
    blockchain = OwnershipBlockchain(difficulty=1)
    today = date.today().isoformat()
    blockchain.create_genesis_block(today)
    
    # Add sample conversations
    conversations = [
        ("Alice", "What is blockchain technology?"),
        ("claude", "Blockchain is a distributed ledger technology..."),
        ("Bob", "How does mining work?"),
        ("claude", "Mining involves solving complex mathematical puzzles..."),
        ("Alice", "Can you explain smart contracts?"),
        ("claude", "Smart contracts are self-executing contracts..."),
        ("Carol", "What are the benefits of blockchain?"),
        ("claude", "Blockchain offers transparency, security, and decentralization...")
    ]
    
    # Add conversations to blockchain
    for author, text in conversations:
        blockchain.add_sentence(text, author)
        if author != "claude":  # Mine after each user input
            blockchain.mine_pending_sentences(today)
    
    # Create visualizer
    visualizer = BlockchainVisualizer(blockchain)
    
    # Show visualization
    print(visualizer.visualize_chain_summary())
    print(visualizer.visualize_ownership_analysis())
    print(visualizer.visualize_conversation_flow())
    
    # Save visualization
    filename = visualizer.save_visualization()
    print(f"\nVisualization saved to: {filename}")
    
    return blockchain, visualizer


if __name__ == "__main__":
    print("Blockchain Visualizer with Interactive Claude Conversations")
    print("=" * 70)
    
    print("Choose mode:")
    print("1. Demo visualization with sample data")
    print("2. Interactive Claude conversation")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        demo_visualization()
    elif choice == "2":
        conversation = InteractiveClaudeConversation()
        conversation.start_conversation()
    else:
        print("Invalid choice, running demo...")
        demo_visualization()
