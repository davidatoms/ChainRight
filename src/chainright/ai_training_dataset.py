#!/usr/bin/env python3
"""
AI Training Dataset from Global Conversation Blockchain
Transforms conversation blockchain into training datasets for AI models.
"""

import hashlib
import json
import time
import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from colorama import init, Fore, Back, Style

# Import the blockchain classes
from .blockchain import Block, Blockchain

# Initialize colorama
init(autoreset=True)


class AITrainingDataset:
    """Convert global conversation blockchain into AI training datasets."""
    
    def __init__(self, blockchain_file: str = "global_conversations.json"):
        self.blockchain_file = blockchain_file
        self.blockchain = self.load_blockchain()
        
    def load_blockchain(self) -> Blockchain:
        """Load the global conversation blockchain."""
        if not os.path.exists(self.blockchain_file):
            raise FileNotFoundError(f"Blockchain file {self.blockchain_file} not found")
        
        return Blockchain.load_from_file(self.blockchain_file)
    
    def extract_conversation_pairs(self, include_metadata: bool = True) -> List[Dict]:
        """Extract user-Claude conversation pairs for training."""
        conversations = []
        current_session = None
        session_messages = []
        
        for block in self.blockchain.chain:
            try:
                data_list = json.loads(block.data)
                for data_item in data_list:
                    entry = json.loads(data_item)
                    
                    session_id = entry.get("session_id")
                    message_type = entry.get("message_type")
                    message = entry.get("message")
                    user_id = entry.get("user_id")
                    
                    # Start new session
                    if session_id != current_session:
                        if session_messages:
                            conversations.extend(self._process_session_messages(session_messages, include_metadata))
                        current_session = session_id
                        session_messages = []
                    
                    session_messages.append({
                        "type": message_type,
                        "content": message,
                        "user_id": user_id,
                        "timestamp": entry.get("timestamp"),
                        "block_index": block.index,
                        "metadata": entry.get("metadata", {})
                    })
                    
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Process final session
        if session_messages:
            conversations.extend(self._process_session_messages(session_messages, include_metadata))
        
        return conversations
    
    def _process_session_messages(self, messages: List[Dict], include_metadata: bool) -> List[Dict]:
        """Process messages in a session to create conversation pairs."""
        conversations = []
        user_messages = []
        claude_messages = []
        
        # Separate user and Claude messages
        for msg in messages:
            if msg["type"] == "user_input":
                user_messages.append(msg)
            elif msg["type"] == "claude_response":
                claude_messages.append(msg)
        
        # Create conversation pairs
        for i, user_msg in enumerate(user_messages):
            if i < len(claude_messages):
                conversation = {
                    "user_message": user_msg["content"],
                    "claude_response": claude_messages[i]["content"],
                    "user_id": user_msg["user_id"],
                    "session_id": messages[0]["session_id"] if messages else None,
                    "timestamp": user_msg["timestamp"],
                    "block_indices": [user_msg["block_index"], claude_messages[i]["block_index"]]
                }
                
                if include_metadata:
                    conversation["metadata"] = {
                        "user_metadata": user_msg.get("metadata", {}),
                        "claude_metadata": claude_messages[i].get("metadata", {})
                    }
                
                conversations.append(conversation)
        
        return conversations
    
    def export_training_data(self, output_format: str = "json", 
                           output_file: str = None, 
                           include_metadata: bool = True,
                           filter_users: List[str] = None) -> str:
        """Export conversation data in various training formats."""
        
        conversations = self.extract_conversation_pairs(include_metadata)
        
        # Filter by users if specified
        if filter_users:
            conversations = [conv for conv in conversations if conv["user_id"] in filter_users]
        
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"ai_training_data_{timestamp}.{output_format}"
        
        if output_format.lower() == "json":
            self._export_json(conversations, output_file)
        elif output_format.lower() == "csv":
            self._export_csv(conversations, output_file)
        elif output_format.lower() == "jsonl":
            self._export_jsonl(conversations, output_file)
        elif output_format.lower() == "openai":
            self._export_openai_format(conversations, output_file)
        else:
            raise ValueError(f"Unsupported format: {output_format}")
        
        print(f"{Fore.GREEN}Training data exported to: {output_file}")
        print(f"{Fore.CYAN}Total conversation pairs: {len(conversations)}")
        
        return output_file
    
    def _export_json(self, conversations: List[Dict], filename: str):
        """Export as JSON format."""
        with open(filename, 'w') as f:
            json.dump({
                "dataset_info": {
                    "total_conversations": len(conversations),
                    "export_timestamp": datetime.now().isoformat(),
                    "source_blockchain": self.blockchain_file,
                    "format": "conversation_pairs"
                },
                "conversations": conversations
            }, f, indent=2)
    
    def _export_csv(self, conversations: List[Dict], filename: str):
        """Export as CSV format."""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "user_message", "claude_response", "user_id", 
                "session_id", "timestamp", "block_indices"
            ])
            
            for conv in conversations:
                writer.writerow([
                    conv["user_message"],
                    conv["claude_response"],
                    conv["user_id"],
                    conv["session_id"],
                    conv["timestamp"],
                    json.dumps(conv["block_indices"])
                ])
    
    def _export_jsonl(self, conversations: List[Dict], filename: str):
        """Export as JSONL (JSON Lines) format."""
        with open(filename, 'w') as f:
            for conv in conversations:
                f.write(json.dumps(conv) + '\n')
    
    def _export_openai_format(self, conversations: List[Dict], filename: str):
        """Export in OpenAI fine-tuning format."""
        training_data = []
        
        for conv in conversations:
            training_data.append({
                "messages": [
                    {"role": "user", "content": conv["user_message"]},
                    {"role": "assistant", "content": conv["claude_response"]}
                ]
            })
        
        with open(filename, 'w') as f:
            json.dump(training_data, f, indent=2)
    
    def get_dataset_statistics(self) -> Dict:
        """Get comprehensive dataset statistics."""
        conversations = self.extract_conversation_pairs()
        
        total_conversations = len(conversations)
        unique_users = set()
        unique_sessions = set()
        total_user_words = 0
        total_claude_words = 0
        
        for conv in conversations:
            unique_users.add(conv["user_id"])
            if conv["session_id"]:
                unique_sessions.add(conv["session_id"])
            
            total_user_words += len(conv["user_message"].split())
            total_claude_words += len(conv["claude_response"].split())
        
        return {
            "total_conversations": total_conversations,
            "unique_users": len(unique_users),
            "unique_sessions": len(unique_sessions),
            "total_user_words": total_user_words,
            "total_claude_words": total_claude_words,
            "average_user_message_length": total_user_words / total_conversations if total_conversations > 0 else 0,
            "average_claude_response_length": total_claude_words / total_conversations if total_conversations > 0 else 0,
            "data_size_mb": self._estimate_data_size(conversations)
        }
    
    def _estimate_data_size(self, conversations: List[Dict]) -> float:
        """Estimate dataset size in MB."""
        total_chars = sum(
            len(conv["user_message"]) + len(conv["claude_response"]) 
            for conv in conversations
        )
        return round(total_chars / (1024 * 1024), 2)
    
    def display_dataset_stats(self):
        """Display dataset statistics with colors."""
        stats = self.get_dataset_statistics()
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}AI TRAINING DATASET STATISTICS")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.GREEN}Total Conversations: {stats['total_conversations']}")
        print(f"{Fore.MAGENTA}Unique Users: {stats['unique_users']}")
        print(f"{Fore.YELLOW}Unique Sessions: {stats['unique_sessions']}")
        print(f"{Fore.BLUE}Total User Words: {stats['total_user_words']:,}")
        print(f"{Fore.GREEN}Total Claude Words: {stats['total_claude_words']:,}")
        print(f"{Fore.WHITE}Avg User Message: {stats['average_user_message_length']:.1f} words")
        print(f"{Fore.WHITE}Avg Claude Response: {stats['average_claude_response_length']:.1f} words")
        print(f"{Fore.CYAN}Estimated Size: {stats['data_size_mb']} MB")
        print(f"{Fore.CYAN}{'='*60}")


class TrainingDatasetCLI:
    """CLI for managing AI training datasets."""
    
    def __init__(self):
        self.dataset = None
        
    def run(self):
        """Run the training dataset CLI."""
        print(f"{Fore.CYAN}AI Training Dataset Manager")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.YELLOW}Commands:")
        print(f"{Fore.GREEN}  /load <blockchain_file> - Load blockchain file")
        print(f"{Fore.GREEN}  /stats - Show dataset statistics")
        print(f"{Fore.GREEN}  /export <format> <filename> - Export training data")
        print(f"{Fore.GREEN}  /formats - Show available export formats")
        print(f"{Fore.GREEN}  /quit or /exit - Exit")
        print(f"{Fore.CYAN}{'='*60}")
        
        while True:
            try:
                command = input(f"\n{Fore.BLUE}Command: ").strip()
                
                if not command:
                    continue
                
                if command.startswith('/'):
                    self.handle_command(command)
                else:
                    print(f"{Fore.RED}Please use a command starting with /")
                    
            except KeyboardInterrupt:
                print(f"\n\n{Fore.YELLOW}Exiting...")
                break
            except Exception as e:
                print(f"\n{Fore.RED}Error: {e}")
    
    def handle_command(self, command: str):
        """Handle CLI commands."""
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == '/load':
            if len(parts) < 2:
                print(f"{Fore.RED}Usage: /load <blockchain_file>")
                return
            
            blockchain_file = parts[1]
            try:
                self.dataset = AITrainingDataset(blockchain_file)
                print(f"{Fore.GREEN}Loaded blockchain: {blockchain_file}")
            except Exception as e:
                print(f"{Fore.RED}Error loading blockchain: {e}")
        
        elif cmd == '/stats':
            if not self.dataset:
                print(f"{Fore.RED}Please load a blockchain first with /load")
                return
            
            self.dataset.display_dataset_stats()
        
        elif cmd == '/export':
            if not self.dataset:
                print(f"{Fore.RED}Please load a blockchain first with /load")
                return
            
            if len(parts) < 2:
                print(f"{Fore.RED}Usage: /export <format> [filename]")
                print(f"{Fore.YELLOW}Available formats: json, csv, jsonl, openai")
                return
            
            format_type = parts[1]
            filename = parts[2] if len(parts) > 2 else None
            
            try:
                output_file = self.dataset.export_training_data(
                    output_format=format_type,
                    output_file=filename
                )
                print(f"{Fore.GREEN}Exported to: {output_file}")
            except Exception as e:
                print(f"{Fore.RED}Error exporting: {e}")
        
        elif cmd == '/formats':
            print(f"{Fore.CYAN}Available Export Formats:")
            print(f"{Fore.GREEN}  json - Standard JSON with metadata")
            print(f"{Fore.GREEN}  csv - Comma-separated values")
            print(f"{Fore.GREEN}  jsonl - JSON Lines (one JSON per line)")
            print(f"{Fore.GREEN}  openai - OpenAI fine-tuning format")
        
        elif cmd in ['/quit', '/exit']:
            print(f"{Fore.GREEN}Goodbye!")
            sys.exit(0)
        
        else:
            print(f"{Fore.RED}Unknown command: {cmd}")
            print(f"{Fore.YELLOW}Available commands: /load, /stats, /export, /formats, /quit, /exit")


def main():
    """Main function."""
    print(f"{Fore.CYAN}AI Training Dataset Manager")
    print(f"{Fore.CYAN}Transform conversation blockchain into training datasets")
    
    # Load environment variables
    load_dotenv()
    
    cli = TrainingDatasetCLI()
    cli.run()


if __name__ == "__main__":
    main()
