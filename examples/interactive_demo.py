#!/usr/bin/env python3
"""
Interactive Demo for Blockchain Visualization with Claude Conversations
Shows how to visualize blocks, ownership, and have interactive conversations.
"""

from blockchain_visualizer import InteractiveClaudeConversation, demo_visualization
import os


def show_demo_menu():
    """Show the demo menu and handle user choices."""
    print("Blockchain Visualization Interactive Demo")
    print("=" * 50)
    
    print("\nAvailable demos:")
    print("1. Sample blockchain visualization (no API key needed)")
    print("2. Interactive Claude conversation (requires API key)")
    print("3. Load existing blockchain and visualize")
    print("4. Exit")
    
    while True:
        print(f"\n{'='*30}")
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == "1":
            run_sample_visualization()
        elif choice == "2":
            run_interactive_conversation()
        elif choice == "3":
            load_existing_blockchain()
        elif choice == "4":
            print("Demo ended.")
            break
        else:
            print("Invalid choice. Please enter 1-4.")


def run_sample_visualization():
    """Run the sample blockchain visualization."""
    print("\nRunning sample blockchain visualization...")
    print("This creates a sample blockchain with conversations and shows detailed visualization.")
    
    blockchain, visualizer = demo_visualization()
    
    print("\nSample visualization complete!")
    print("Check the generated files:")
    print("- blockchain_visualization_YYYY-MM-DD.txt (detailed visualization)")
    print("- ownership_blockchain_YYYY-MM-DD.json (blockchain data)")


def run_interactive_conversation():
    """Run interactive Claude conversation."""
    print("\nStarting interactive Claude conversation...")
    
    # Check for API key
    api_key = os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("No CLAUDE_API_KEY found in environment variables.")
        print("To use real Claude API:")
        print("1. Get an API key from https://console.anthropic.com/")
        print("2. Set it: export CLAUDE_API_KEY='your-key-here'")
        print("3. Run this demo again")
        print("\nRunning in mock mode instead...")
    
    # Start interactive conversation
    conversation = InteractiveClaudeConversation(api_key)
    conversation.start_conversation()


def load_existing_blockchain():
    """Load and visualize an existing blockchain."""
    print("\nLoading existing blockchain...")
    
    # Look for existing blockchain files
    import glob
    blockchain_files = glob.glob("*.json")
    blockchain_files = [f for f in blockchain_files if "blockchain" in f.lower()]
    
    if not blockchain_files:
        print("No existing blockchain files found.")
        print("Run demo option 1 first to create a sample blockchain.")
        return
    
    print("Found blockchain files:")
    for i, file in enumerate(blockchain_files, 1):
        print(f"  {i}. {file}")
    
    try:
        choice = int(input(f"\nSelect file (1-{len(blockchain_files)}): ")) - 1
        if 0 <= choice < len(blockchain_files):
            selected_file = blockchain_files[choice]
            visualize_existing_blockchain(selected_file)
        else:
            print("Invalid choice.")
    except ValueError:
        print("Invalid input. Please enter a number.")


def visualize_existing_blockchain(filename: str):
    """Visualize an existing blockchain file."""
    print(f"\nLoading blockchain from: {filename}")
    
    try:
        from ownership_blockchain import OwnershipBlockchain
        from blockchain_visualizer import BlockchainVisualizer
        
        # Load blockchain
        blockchain = OwnershipBlockchain.load_from_file(filename)
        
        # Create visualizer
        visualizer = BlockchainVisualizer(blockchain)
        
        # Show visualization
        print(visualizer.visualize_chain_summary())
        print(visualizer.visualize_ownership_analysis())
        print(visualizer.visualize_conversation_flow())
        
        # Ask if user wants detailed blocks
        show_details = input("\nShow detailed block information? (y/n): ").strip().lower()
        if show_details in ['y', 'yes']:
            for i, block in enumerate(blockchain.chain):
                print(visualizer.visualize_block(block, i))
        
        # Save visualization
        viz_file = visualizer.save_visualization()
        print(f"\nVisualization saved to: {viz_file}")
        
    except Exception as e:
        print(f"Error loading blockchain: {e}")


def quick_demo():
    """Quick demo showing key features."""
    print("Quick Blockchain Visualization Demo")
    print("=" * 40)
    
    print("\nThis demo shows:")
    print("1. How blocks are structured and owned")
    print("2. How conversations flow through the blockchain")
    print("3. How to track who said what and when")
    print("4. How to visualize the entire conversation history")
    
    print("\nKey features:")
    print("- Each block contains sentences from different authors")
    print("- Authors can be users (Alice, Bob, Carol) or Claude")
    print("- Each sentence is timestamped and cryptographically secured")
    print("- The blockchain shows the complete conversation flow")
    print("- You can see who owns each piece of information")
    
    print("\nRunning sample visualization...")
    blockchain, visualizer = demo_visualization()
    
    print("\nDemo complete! The visualization shows:")
    print("- Block summary table with authors and sentence counts")
    print("- Ownership analysis showing who contributed what")
    print("- Conversation flow showing the back-and-forth dialogue")
    print("- Detailed block information with all metadata")


if __name__ == "__main__":
    print("Blockchain Visualization Interactive Demo")
    print("=" * 50)
    
    print("This demo shows how to:")
    print("- Visualize blockchain blocks and their ownership")
    print("- Track conversations between users and Claude")
    print("- See who owns each piece of information")
    print("- Analyze the flow of information through time")
    
    print("\nChoose demo type:")
    print("1. Quick demo (recommended)")
    print("2. Full interactive menu")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        quick_demo()
    elif choice == "2":
        show_demo_menu()
    else:
        print("Invalid choice, running quick demo...")
        quick_demo()
