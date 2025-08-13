#!/usr/bin/env python3
"""
Interactive script for creating word list blockchains with custom dates.
"""

from wordlist_blockchain import create_word_list_blockchain, WordListBlockchain
from datetime import datetime, date
import os


def get_user_date() -> str:
    """Get a date from the user."""
    print("\nDate Options:")
    print("1. Today's date")
    print("2. Custom date")
    print("3. Historical date (e.g., 2020-01-01)")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        return date.today().isoformat()
    elif choice == "2":
        while True:
            try:
                custom_date = input("Enter date (YYYY-MM-DD): ").strip()
                # Validate date format
                datetime.strptime(custom_date, "%Y-%m-%d")
                return custom_date
            except ValueError:
                print("Invalid date format. Please use YYYY-MM-DD")
    elif choice == "3":
        historical_dates = [
            "2020-01-01", "2019-01-01", "2018-01-01", "2017-01-01", "2016-01-01",
            "2015-01-01", "2010-01-01", "2005-01-01", "2000-01-01", "1995-01-01"
        ]
        print("\nHistorical dates available:")
        for i, hist_date in enumerate(historical_dates, 1):
            print(f"{i}. {hist_date}")
        
        try:
            hist_choice = int(input("Enter choice (1-10): ")) - 1
            if 0 <= hist_choice < len(historical_dates):
                return historical_dates[hist_choice]
            else:
                print("Invalid choice, using today's date")
                return date.today().isoformat()
        except ValueError:
            print("Invalid choice, using today's date")
            return date.today().isoformat()
    else:
        print("Invalid choice, using today's date")
        return date.today().isoformat()


def get_difficulty() -> int:
    """Get mining difficulty from user."""
    print("\nMining Difficulty:")
    print("1. Easy (1 leading zero) - Fast mining")
    print("2. Medium (2 leading zeros) - Moderate mining")
    print("3. Hard (3 leading zeros) - Slow mining")
    print("4. Very Hard (4 leading zeros) - Very slow mining")
    
    try:
        choice = int(input("Enter choice (1-4): ").strip())
        if 1 <= choice <= 4:
            return choice
        else:
            print("Invalid choice, using medium difficulty")
            return 2
    except ValueError:
        print("Invalid choice, using medium difficulty")
        return 2


def display_blockchain_info(blockchain: WordListBlockchain) -> None:
    """Display detailed blockchain information."""
    print(f"\n{'='*60}")
    print("BLOCKCHAIN CREATED SUCCESSFULLY!")
    print(f"{'='*60}")
    
    genesis = blockchain.chain[0]
    print(f"Genesis Block Information:")
    print(f"  Date: {genesis.date_str}")
    print(f"  Word Count: {len(genesis.word_list):,}")
    print(f"  Hash: {genesis.hash}")
    print(f"  Nonce: {genesis.nonce}")
    print(f"  Mining Difficulty: {blockchain.difficulty}")
    print(f"  Chain Valid: {blockchain.is_chain_valid()}")
    
    print(f"\nSample Words (first 20):")
    sample_words = genesis.word_list[:20]
    print(f"  {', '.join(sample_words)}")
    
    print(f"\nSample Words (last 20):")
    sample_words = genesis.word_list[-20:]
    print(f"  {', '.join(sample_words)}")
    
    # Word statistics
    word_lengths = [len(word) for word in genesis.word_list]
    avg_length = sum(word_lengths) / len(word_lengths)
    max_length = max(word_lengths)
    min_length = min(word_lengths)
    
    print(f"\nWord Statistics:")
    print(f"  Average word length: {avg_length:.1f} characters")
    print(f"  Longest word: {max_length} characters")
    print(f"  Shortest word: {min_length} characters")


def interactive_wordlist_blockchain():
    """Interactive word list blockchain creation."""
    print("Word List Blockchain Creator")
    print("=" * 50)
    print("Create a blockchain with English words as the genesis block")
    print("This creates a timestamped snapshot of the English language")
    
    # Get user preferences
    user_date = get_user_date()
    difficulty = get_difficulty()
    
    print(f"\nCreating blockchain...")
    print(f"Date: {user_date}")
    print(f"Difficulty: {difficulty}")
    print("This may take a moment...")
    
    # Create blockchain
    blockchain = create_word_list_blockchain(user_date, difficulty)
    
    # Display information
    display_blockchain_info(blockchain)
    
    # Ask if user wants to add more data
    while True:
        add_more = input("\nAdd more data to the blockchain? (y/n): ").lower()
        if add_more in ['y', 'yes']:
            new_data = input("Enter new data: ")
            blockchain.add_data(new_data)
            blockchain.mine_pending_data()
            print(f"Added new block! Chain length: {len(blockchain.chain)}")
        elif add_more in ['n', 'no']:
            break
        else:
            print("Please enter 'y' or 'n'")
    
    # Save blockchain
    save_choice = input("\nSave blockchain to file? (y/n): ").lower()
    if save_choice in ['y', 'yes']:
        filename = input(f"Enter filename (default: wordlist_blockchain_{user_date}.json): ").strip()
        if not filename:
            filename = f"wordlist_blockchain_{user_date}.json"
        blockchain.save_to_file(filename)
        print(f"Blockchain saved to {filename}")
        
        # Show file size
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"File size: {size:,} bytes ({size/1024:.1f} KB)")
    
    return blockchain


def compare_wordlists():
    """Compare word lists from different dates."""
    print("\nWord List Comparison")
    print("=" * 30)
    
    # Create blockchains for different dates
    dates = ["2020-01-01", "2023-01-01", date.today().isoformat()]
    blockchains = []
    
    for date_str in dates:
        print(f"\nCreating blockchain for {date_str}...")
        blockchain = create_word_list_blockchain(date_str, difficulty=1)
        blockchains.append((date_str, blockchain))
    
    print(f"\n{'='*60}")
    print("COMPARISON RESULTS")
    print(f"{'='*60}")
    
    for date_str, blockchain in blockchains:
        genesis = blockchain.chain[0]
        print(f"\n{date_str}:")
        print(f"  Word Count: {len(genesis.word_list):,}")
        print(f"  Hash: {genesis.hash}")
        print(f"  Nonce: {genesis.nonce}")


if __name__ == "__main__":
    print("Word List Blockchain Interactive Tool")
    print("=" * 50)
    
    print("Choose an option:")
    print("1. Create word list blockchain")
    print("2. Compare word lists from different dates")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        interactive_wordlist_blockchain()
    elif choice == "2":
        compare_wordlists()
    else:
        print("Invalid choice, creating word list blockchain...")
        interactive_wordlist_blockchain()
