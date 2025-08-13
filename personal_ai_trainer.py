#!/usr/bin/env python3
"""
Personal AI Trainer
Train personalized AI models from your own conversation data in the blockchain.
"""

import hashlib
import json
import time
import os
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from colorama import init, Fore, Back, Style

# Import the blockchain classes
from blockchain import Block, Blockchain

# Initialize colorama
init(autoreset=True)


class PersonalAITrainer:
    """Train personalized AI models from user's conversation data."""
    
    def __init__(self, user_id: str, blockchain_file: str = "global_conversations.json"):
        self.user_id = user_id
        self.blockchain_file = blockchain_file
        self.blockchain = self.load_blockchain()
        self.personal_data_dir = f"personal_ai_data/{user_id}"
        os.makedirs(self.personal_data_dir, exist_ok=True)
        
    def load_blockchain(self) -> Blockchain:
        """Load the global conversation blockchain."""
        if not os.path.exists(self.blockchain_file):
            raise FileNotFoundError(f"Blockchain file {self.blockchain_file} not found")
        
        return Blockchain.load_from_file(self.blockchain_file)
    
    def extract_personal_conversations(self) -> List[Dict]:
        """Extract all conversations for this specific user."""
        conversations = []
        current_session = None
        session_messages = []
        
        for block in self.blockchain.chain:
            try:
                data_list = json.loads(block.data)
                for data_item in data_list:
                    entry = json.loads(data_item)
                    
                    # Only include this user's conversations
                    if entry.get("user_id") != self.user_id:
                        continue
                    
                    session_id = entry.get("session_id")
                    message_type = entry.get("message_type")
                    message = entry.get("message")
                    
                    # Start new session
                    if session_id != current_session:
                        if session_messages:
                            conversations.extend(self._process_session_messages(session_messages))
                        current_session = session_id
                        session_messages = []
                    
                    session_messages.append({
                        "type": message_type,
                        "content": message,
                        "timestamp": entry.get("timestamp"),
                        "block_index": block.index,
                        "message_hash": entry.get("message_hash")
                    })
                    
            except (json.JSONDecodeError, KeyError):
                continue
        
        # Process final session
        if session_messages:
            conversations.extend(self._process_session_messages(session_messages))
        
        return conversations
    
    def _process_session_messages(self, messages: List[Dict]) -> List[Dict]:
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
                    "timestamp": user_msg["timestamp"],
                    "block_indices": [user_msg["block_index"], claude_messages[i]["block_index"]],
                    "message_hashes": [user_msg["message_hash"], claude_messages[i]["message_hash"]]
                }
                conversations.append(conversation)
        
        return conversations
    
    def generate_training_datasets(self) -> Dict[str, str]:
        """Generate various training datasets for personal AI."""
        conversations = self.extract_personal_conversations()
        
        if not conversations:
            print(f"{Fore.YELLOW}No conversations found for user: {self.user_id}")
            return {}
        
        datasets = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. OpenAI Fine-tuning Format
        openai_file = f"{self.personal_data_dir}/openai_training_{timestamp}.json"
        self._export_openai_format(conversations, openai_file)
        datasets["openai"] = openai_file
        
        # 2. JSONL Format
        jsonl_file = f"{self.personal_data_dir}/conversations_{timestamp}.jsonl"
        self._export_jsonl(conversations, jsonl_file)
        datasets["jsonl"] = jsonl_file
        
        # 3. Knowledge Base Format
        knowledge_file = f"{self.personal_data_dir}/knowledge_base_{timestamp}.json"
        self._export_knowledge_base(conversations, knowledge_file)
        datasets["knowledge"] = knowledge_file
        
        # 4. Personal Insights Format
        insights_file = f"{self.personal_data_dir}/personal_insights_{timestamp}.json"
        self._export_personal_insights(conversations, insights_file)
        datasets["insights"] = insights_file
        
        return datasets
    
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
    
    def _export_jsonl(self, conversations: List[Dict], filename: str):
        """Export as JSONL format."""
        with open(filename, 'w') as f:
            for conv in conversations:
                f.write(json.dumps(conv) + '\n')
    
    def _export_knowledge_base(self, conversations: List[Dict], filename: str):
        """Export as structured knowledge base."""
        knowledge_base = {
            "user_id": self.user_id,
            "generated_timestamp": datetime.now().isoformat(),
            "total_conversations": len(conversations),
            "knowledge_entries": []
        }
        
        for conv in conversations:
            # Extract key concepts and insights
            entry = {
                "question": conv["user_message"],
                "answer": conv["claude_response"],
                "timestamp": conv["timestamp"],
                "block_reference": conv["block_indices"],
                "hash_verification": conv["message_hashes"]
            }
            knowledge_base["knowledge_entries"].append(entry)
        
        with open(filename, 'w') as f:
            json.dump(knowledge_base, f, indent=2)
    
    def _export_personal_insights(self, conversations: List[Dict], filename: str):
        """Export personal insights and patterns."""
        insights = {
            "user_id": self.user_id,
            "generated_timestamp": datetime.now().isoformat(),
            "conversation_analysis": self._analyze_conversations(conversations),
            "personal_patterns": self._extract_personal_patterns(conversations),
            "knowledge_gaps": self._identify_knowledge_gaps(conversations),
            "learning_progress": self._track_learning_progress(conversations)
        }
        
        with open(filename, 'w') as f:
            json.dump(insights, f, indent=2)
    
    def _analyze_conversations(self, conversations: List[Dict]) -> Dict:
        """Analyze conversation patterns and statistics."""
        total_user_words = sum(len(conv["user_message"].split()) for conv in conversations)
        total_claude_words = sum(len(conv["claude_response"].split()) for conv in conversations)
        
        # Extract common topics
        topics = {}
        for conv in conversations:
            words = conv["user_message"].lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    topics[word] = topics.get(word, 0) + 1
        
        # Get top topics
        top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_conversations": len(conversations),
            "total_user_words": total_user_words,
            "total_claude_words": total_claude_words,
            "average_user_message_length": total_user_words / len(conversations),
            "average_claude_response_length": total_claude_words / len(conversations),
            "top_topics": top_topics,
            "conversation_frequency": self._calculate_conversation_frequency(conversations)
        }
    
    def _extract_personal_patterns(self, conversations: List[Dict]) -> Dict:
        """Extract personal communication patterns."""
        patterns = {
            "question_types": [],
            "communication_style": "",
            "interests": [],
            "learning_style": ""
        }
        
        # Analyze question patterns
        question_words = ["what", "how", "why", "when", "where", "who", "which"]
        question_counts = {word: 0 for word in question_words}
        
        for conv in conversations:
            message_lower = conv["user_message"].lower()
            for word in question_words:
                if word in message_lower:
                    question_counts[word] += 1
        
        patterns["question_types"] = question_counts
        
        # Analyze communication style
        avg_length = sum(len(conv["user_message"]) for conv in conversations) / len(conversations)
        if avg_length > 100:
            patterns["communication_style"] = "detailed"
        elif avg_length > 50:
            patterns["communication_style"] = "moderate"
        else:
            patterns["communication_style"] = "concise"
        
        return patterns
    
    def _identify_knowledge_gaps(self, conversations: List[Dict]) -> List[str]:
        """Identify potential knowledge gaps based on questions."""
        knowledge_gaps = []
        
        # Look for follow-up questions that might indicate gaps
        for i, conv in enumerate(conversations):
            if "don't understand" in conv["user_message"].lower() or \
               "can you explain" in conv["user_message"].lower() or \
               "what do you mean" in conv["user_message"].lower():
                knowledge_gaps.append({
                    "gap": conv["user_message"],
                    "context": conv["claude_response"],
                    "timestamp": conv["timestamp"]
                })
        
        return knowledge_gaps
    
    def _track_learning_progress(self, conversations: List[Dict]) -> Dict:
        """Track learning progress over time."""
        # Group conversations by date
        daily_conversations = {}
        for conv in conversations:
            date = conv["timestamp"][:10]  # YYYY-MM-DD
            if date not in daily_conversations:
                daily_conversations[date] = []
            daily_conversations[date].append(conv)
        
        # Calculate daily metrics
        daily_metrics = {}
        for date, convs in daily_conversations.items():
            daily_metrics[date] = {
                "conversations": len(convs),
                "total_words": sum(len(conv["user_message"].split()) + len(conv["claude_response"].split()) for conv in convs),
                "average_engagement": len(convs) / 1  # conversations per day
            }
        
        return daily_metrics
    
    def _calculate_conversation_frequency(self, conversations: List[Dict]) -> Dict:
        """Calculate conversation frequency patterns."""
        if not conversations:
            return {}
        
        # Group by hour of day
        hourly_counts = {i: 0 for i in range(24)}
        for conv in conversations:
            try:
                hour = int(conv["timestamp"][11:13])
                hourly_counts[hour] += 1
            except:
                continue
        
        return hourly_counts
    
    def get_personal_stats(self) -> Dict:
        """Get comprehensive personal statistics."""
        conversations = self.extract_personal_conversations()
        
        if not conversations:
            return {"error": "No conversations found"}
        
        total_conversations = len(conversations)
        total_user_words = sum(len(conv["user_message"].split()) for conv in conversations)
        total_claude_words = sum(len(conv["claude_response"].split()) for conv in conversations)
        
        # Calculate unique sessions
        unique_sessions = set()
        for conv in conversations:
            if "session_id" in conv:
                unique_sessions.add(conv["session_id"])
        
        return {
            "user_id": self.user_id,
            "total_conversations": total_conversations,
            "total_user_words": total_user_words,
            "total_claude_words": total_claude_words,
            "unique_sessions": len(unique_sessions),
            "average_user_message_length": total_user_words / total_conversations,
            "average_claude_response_length": total_claude_words / total_conversations,
            "data_size_mb": self._estimate_data_size(conversations),
            "conversation_span": self._get_conversation_timespan(conversations)
        }
    
    def _estimate_data_size(self, conversations: List[Dict]) -> float:
        """Estimate personal dataset size in MB."""
        total_chars = sum(
            len(conv["user_message"]) + len(conv["claude_response"]) 
            for conv in conversations
        )
        return round(total_chars / (1024 * 1024), 2)
    
    def _get_conversation_timespan(self, conversations: List[Dict]) -> Dict:
        """Get the timespan of conversations."""
        if not conversations:
            return {}
        
        timestamps = [conv["timestamp"] for conv in conversations]
        timestamps.sort()
        
        return {
            "first_conversation": timestamps[0],
            "last_conversation": timestamps[-1],
            "total_days": (datetime.fromisoformat(timestamps[-1].replace('Z', '+00:00')) - 
                          datetime.fromisoformat(timestamps[0].replace('Z', '+00:00'))).days
        }
    
    def display_personal_stats(self):
        """Display personal statistics with colors."""
        stats = self.get_personal_stats()
        
        if "error" in stats:
            print(f"{Fore.RED}{stats['error']}")
            return
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}PERSONAL AI TRAINING STATISTICS")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.GREEN}User ID: {stats['user_id']}")
        print(f"{Fore.WHITE}Total Conversations: {stats['total_conversations']}")
        print(f"{Fore.BLUE}Total User Words: {stats['total_user_words']:,}")
        print(f"{Fore.GREEN}Total Claude Words: {stats['total_claude_words']:,}")
        print(f"{Fore.MAGENTA}Unique Sessions: {stats['unique_sessions']}")
        print(f"{Fore.WHITE}Avg User Message: {stats['average_user_message_length']:.1f} words")
        print(f"{Fore.WHITE}Avg Claude Response: {stats['average_claude_response_length']:.1f} words")
        print(f"{Fore.CYAN}Dataset Size: {stats['data_size_mb']} MB")
        
        if stats['conversation_span']:
            span = stats['conversation_span']
            print(f"{Fore.YELLOW}First Conversation: {span['first_conversation'][:10]}")
            print(f"{Fore.YELLOW}Last Conversation: {span['last_conversation'][:10]}")
            print(f"{Fore.YELLOW}Total Days: {span['total_days']}")
        
        print(f"{Fore.CYAN}{'='*60}")


class PersonalAITrainerCLI:
    """CLI for personal AI training."""
    
    def __init__(self):
        self.trainer = None
        
    def run(self):
        """Run the personal AI trainer CLI."""
        print(f"{Fore.CYAN}Personal AI Trainer")
        print(f"{Fore.CYAN}Train your own AI from your conversation data")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.YELLOW}Commands:")
        print(f"{Fore.GREEN}  /load <user_id> - Load your conversation data")
        print(f"{Fore.GREEN}  /stats - Show your personal statistics")
        print(f"{Fore.GREEN}  /generate - Generate training datasets")
        print(f"{Fore.GREEN}  /train - Prepare for model training")
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
                print(f"{Fore.RED}Usage: /load <user_id>")
                return
            
            user_id = parts[1]
            try:
                self.trainer = PersonalAITrainer(user_id)
                print(f"{Fore.GREEN}Loaded conversation data for user: {user_id}")
            except Exception as e:
                print(f"{Fore.RED}Error loading data: {e}")
        
        elif cmd == '/stats':
            if not self.trainer:
                print(f"{Fore.RED}Please load your data first with /load <user_id>")
                return
            
            self.trainer.display_personal_stats()
        
        elif cmd == '/generate':
            if not self.trainer:
                print(f"{Fore.RED}Please load your data first with /load <user_id>")
                return
            
            try:
                datasets = self.trainer.generate_training_datasets()
                print(f"{Fore.GREEN}Generated training datasets:")
                for format_type, filepath in datasets.items():
                    print(f"{Fore.CYAN}  {format_type}: {filepath}")
            except Exception as e:
                print(f"{Fore.RED}Error generating datasets: {e}")
        
        elif cmd == '/train':
            if not self.trainer:
                print(f"{Fore.RED}Please load your data first with /load <user_id>")
                return
            
            print(f"{Fore.CYAN}Personal AI Training Preparation:")
            print(f"{Fore.YELLOW}1. Your training datasets are ready in: {self.trainer.personal_data_dir}")
            print(f"{Fore.YELLOW}2. Use the OpenAI format for fine-tuning existing models")
            print(f"{Fore.YELLOW}3. Use the knowledge base for RAG (Retrieval-Augmented Generation)")
            print(f"{Fore.YELLOW}4. Use personal insights for model personalization")
            print(f"{Fore.CYAN}Next steps:")
            print(f"{Fore.GREEN}  - Upload to OpenAI for fine-tuning")
            print(f"{Fore.GREEN}  - Use with local models (Llama, Mistral)")
            print(f"{Fore.GREEN}  - Create personalized embeddings")
        
        elif cmd in ['/quit', '/exit']:
            print(f"{Fore.GREEN}Goodbye!")
            sys.exit(0)
        
        else:
            print(f"{Fore.RED}Unknown command: {cmd}")
            print(f"{Fore.YELLOW}Available commands: /load, /stats, /generate, /train, /quit, /exit")


def main():
    """Main function."""
    print(f"{Fore.CYAN}Personal AI Trainer")
    print(f"{Fore.CYAN}Train your own AI from your conversation data")
    
    # Load environment variables
    load_dotenv()
    
    cli = PersonalAITrainerCLI()
    cli.run()


if __name__ == "__main__":
    main()
