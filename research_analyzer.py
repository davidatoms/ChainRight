#!/usr/bin/env python3
"""
Research Analysis Tool for Word List Blockchains
Provides analytical capabilities for linguistic research applications.
"""

from wordlist_blockchain import create_word_list_blockchain, WordListBlockchain
from collections import Counter, defaultdict
import json
from typing import List, Dict, Any, Tuple
import os


class WordListAnalyzer:
    """Advanced analysis tools for word list blockchains."""
    
    def __init__(self, blockchain: WordListBlockchain):
        self.blockchain = blockchain
        self.words = blockchain.chain[0].word_list
        self.date = blockchain.chain[0].date_str
    
    def vocabulary_statistics(self) -> Dict[str, Any]:
        """Calculate comprehensive vocabulary statistics."""
        word_lengths = [len(word) for word in self.words]
        
        return {
            'total_words': len(self.words),
            'average_length': sum(word_lengths) / len(word_lengths),
            'median_length': sorted(word_lengths)[len(word_lengths)//2],
            'min_length': min(word_lengths),
            'max_length': max(word_lengths),
            'length_distribution': self._length_distribution(),
            'alphabetical_distribution': self._alphabetical_distribution(),
            'common_prefixes': self._common_prefixes(),
            'common_suffixes': self._common_suffixes(),
            'word_frequency_by_length': Counter(word_lengths)
        }
    
    def _length_distribution(self) -> Dict[int, int]:
        """Calculate distribution of word lengths."""
        return Counter(len(word) for word in self.words)
    
    def _alphabetical_distribution(self) -> Dict[str, int]:
        """Calculate distribution of words by starting letter."""
        return Counter(word[0].lower() for word in self.words if word)
    
    def _common_prefixes(self, min_length: int = 3) -> List[Tuple[str, int]]:
        """Find common prefixes in the word list."""
        prefixes = defaultdict(int)
        for word in self.words:
            for i in range(min_length, min(len(word), 8)):
                prefixes[word[:i]] += 1
        
        return sorted(prefixes.items(), key=lambda x: x[1], reverse=True)[:20]
    
    def _common_suffixes(self, min_length: int = 3) -> List[Tuple[str, int]]:
        """Find common suffixes in the word list."""
        suffixes = defaultdict(int)
        for word in self.words:
            for i in range(min_length, min(len(word), 8)):
                suffixes[word[-i:]] += 1
        
        return sorted(suffixes.items(), key=lambda x: x[1], reverse=True)[:20]
    
    def compare_with_other_list(self, other_words: List[str]) -> Dict[str, Any]:
        """Compare this word list with another."""
        this_set = set(self.words)
        other_set = set(other_words)
        
        common_words = this_set & other_set
        unique_to_this = this_set - other_set
        unique_to_other = other_set - this_set
        
        return {
            'common_words': len(common_words),
            'unique_to_this': len(unique_to_this),
            'unique_to_other': len(unique_to_other),
            'similarity_score': len(common_words) / len(this_set | other_set),
            'overlap_percentage': len(common_words) / len(this_set) * 100,
            'sample_common_words': list(common_words)[:20],
            'sample_unique_to_this': list(unique_to_this)[:20],
            'sample_unique_to_other': list(unique_to_other)[:20]
        }
    
    def semantic_categories(self) -> Dict[str, List[str]]:
        """Categorize words by semantic fields (basic implementation)."""
        categories = {
            'technology': ['computer', 'internet', 'software', 'hardware', 'digital', 'online', 'web', 'app', 'code', 'data'],
            'nature': ['tree', 'flower', 'animal', 'bird', 'fish', 'mountain', 'river', 'ocean', 'forest', 'grass'],
            'emotions': ['happy', 'sad', 'angry', 'excited', 'worried', 'calm', 'nervous', 'joyful', 'fearful', 'peaceful'],
            'colors': ['red', 'blue', 'green', 'yellow', 'black', 'white', 'purple', 'orange', 'pink', 'brown'],
            'numbers': ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'],
            'family': ['mother', 'father', 'sister', 'brother', 'daughter', 'son', 'grandmother', 'grandfather', 'aunt', 'uncle']
        }
        
        categorized_words = defaultdict(list)
        for word in self.words:
            word_lower = word.lower()
            for category, keywords in categories.items():
                if any(keyword in word_lower for keyword in keywords):
                    categorized_words[category].append(word)
        
        return dict(categorized_words)
    
    def export_analysis(self, filename: str) -> None:
        """Export analysis results to JSON file."""
        analysis_data = {
            'date': self.date,
            'statistics': self.vocabulary_statistics(),
            'semantic_categories': self.semantic_categories(),
            'blockchain_info': {
                'hash': self.blockchain.chain[0].hash,
                'nonce': self.blockchain.chain[0].nonce,
                'timestamp': self.blockchain.chain[0].timestamp,
                'chain_valid': self.blockchain.is_chain_valid()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        print(f"Analysis exported to {filename}")


class ComparativeAnalyzer:
    """Tools for comparing multiple word list blockchains."""
    
    def __init__(self, blockchains: Dict[str, WordListBlockchain]):
        self.blockchains = blockchains
        self.analyzers = {date: WordListAnalyzer(bc) for date, bc in blockchains.items()}
    
    def temporal_analysis(self) -> Dict[str, Any]:
        """Analyze vocabulary changes over time."""
        dates = sorted(self.blockchains.keys())
        results = {
            'dates': dates,
            'word_counts': [],
            'average_lengths': [],
            'vocabulary_growth': [],
            'common_words': set(),
            'unique_words_by_date': {}
        }
        
        # Collect data for each date
        for date in dates:
            analyzer = self.analyzers[date]
            stats = analyzer.vocabulary_statistics()
            
            results['word_counts'].append(stats['total_words'])
            results['average_lengths'].append(stats['average_length'])
            results['common_words'].update(analyzer.words)
            
            # Find words unique to this date
            other_words = set()
            for other_date in dates:
                if other_date != date:
                    other_words.update(self.analyzers[other_date].words)
            
            unique_words = set(analyzer.words) - other_words
            results['unique_words_by_date'][date] = list(unique_words)[:50]  # Top 50 unique words
        
        # Calculate growth rates
        for i in range(1, len(dates)):
            growth_rate = ((results['word_counts'][i] - results['word_counts'][i-1]) / 
                          results['word_counts'][i-1]) * 100
            results['vocabulary_growth'].append(growth_rate)
        
        return results
    
    def create_comparison_report(self, filename: str) -> None:
        """Create a comprehensive comparison report."""
        temporal_data = self.temporal_analysis()
        
        report = {
            'comparison_metadata': {
                'dates_analyzed': temporal_data['dates'],
                'total_unique_words_across_all_dates': len(temporal_data['common_words']),
                'analysis_timestamp': temporal_data['dates'][-1]
            },
            'temporal_analysis': {
                'dates': temporal_data['dates'],
                'word_counts': temporal_data['word_counts'],
                'average_lengths': temporal_data['average_lengths'],
                'vocabulary_growth': temporal_data['vocabulary_growth'],
                'total_unique_words': len(temporal_data['common_words']),
                'unique_words_by_date': temporal_data['unique_words_by_date']
            },
            'detailed_comparisons': {}
        }
        
        # Pairwise comparisons
        dates = temporal_data['dates']
        for i in range(len(dates)):
            for j in range(i+1, len(dates)):
                date1, date2 = dates[i], dates[j]
                comparison = self.analyzers[date1].compare_with_other_list(
                    self.analyzers[date2].words
                )
                report['detailed_comparisons'][f"{date1}_vs_{date2}"] = comparison
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Comparison report exported to {filename}")


def demo_research_analysis():
    """Demonstrate research analysis capabilities."""
    print("Research Analysis Demonstration")
    print("=" * 50)
    
    # Create blockchains for different dates
    dates = ["2020-01-01", "2023-01-01", "2025-08-13"]
    blockchains = {}
    
    print("Creating blockchains for analysis...")
    for date in dates:
        print(f"Creating blockchain for {date}...")
        blockchain = create_word_list_blockchain(date, difficulty=1)
        blockchains[date] = blockchain
    
    # Analyze individual blockchain
    print(f"\nAnalyzing blockchain for {dates[-1]}...")
    analyzer = WordListAnalyzer(blockchains[dates[-1]])
    stats = analyzer.vocabulary_statistics()
    
    print(f"Vocabulary Statistics for {dates[-1]}:")
    print(f"  Total words: {stats['total_words']:,}")
    print(f"  Average word length: {stats['average_length']:.1f} characters")
    print(f"  Longest word: {stats['max_length']} characters")
    print(f"  Shortest word: {stats['min_length']} characters")
    
    print(f"\nTop 10 word lengths by frequency:")
    for length, count in sorted(stats['word_frequency_by_length'].items())[:10]:
        print(f"  {length} letters: {count:,} words")
    
    print(f"\nTop 10 prefixes:")
    for prefix, count in stats['common_prefixes'][:10]:
        print(f"  '{prefix}': {count} words")
    
    # Semantic analysis
    print(f"\nSemantic Categories:")
    categories = analyzer.semantic_categories()
    for category, words in categories.items():
        if words:
            print(f"  {category}: {len(words)} words")
    
    # Comparative analysis
    print(f"\nComparative Analysis...")
    comparative = ComparativeAnalyzer(blockchains)
    temporal_data = comparative.temporal_analysis()
    
    print(f"Temporal Analysis Results:")
    for i, date in enumerate(temporal_data['dates']):
        print(f"  {date}: {temporal_data['word_counts'][i]:,} words")
        if i > 0:
            growth = temporal_data['vocabulary_growth'][i-1]
            print(f"    Growth from previous period: {growth:+.1f}%")
    
    # Export analysis
    analyzer.export_analysis(f"analysis_{dates[-1]}.json")
    comparative.create_comparison_report("comparative_analysis.json")
    
    print(f"\nAnalysis complete! Check the generated JSON files for detailed results.")


def interactive_research_analysis():
    """Interactive research analysis tool."""
    print("Interactive Research Analysis Tool")
    print("=" * 40)
    
    print("Choose analysis type:")
    print("1. Single blockchain analysis")
    print("2. Comparative analysis (multiple dates)")
    print("3. Custom date range analysis")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        # Single blockchain analysis
        date = input("Enter date (YYYY-MM-DD): ").strip()
        try:
            blockchain = create_word_list_blockchain(date, difficulty=1)
            analyzer = WordListAnalyzer(blockchain)
            
            print(f"\nAnalyzing blockchain for {date}...")
            stats = analyzer.vocabulary_statistics()
            
            print(f"Results:")
            print(f"  Total words: {stats['total_words']:,}")
            print(f"  Average length: {stats['average_length']:.1f} characters")
            print(f"  Length range: {stats['min_length']}-{stats['max_length']} characters")
            
            export = input("Export analysis to file? (y/n): ").lower()
            if export in ['y', 'yes']:
                filename = f"analysis_{date}.json"
                analyzer.export_analysis(filename)
        
        except Exception as e:
            print(f"Error: {e}")
    
    elif choice == "2":
        # Comparative analysis
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
            blockchains = {}
            for date in dates:
                print(f"Creating blockchain for {date}...")
                blockchain = create_word_list_blockchain(date, difficulty=1)
                blockchains[date] = blockchain
            
            comparative = ComparativeAnalyzer(blockchains)
            comparative.create_comparison_report("comparative_analysis.json")
            print("Comparative analysis complete!")
        
        except Exception as e:
            print(f"Error: {e}")
    
    elif choice == "3":
        # Custom range analysis
        start_date = input("Start date (YYYY-MM-DD): ").strip()
        end_date = input("End date (YYYY-MM-DD): ").strip()
        interval = input("Interval in years: ").strip()
        
        try:
            interval_years = int(interval)
            # This would require date arithmetic - simplified for demo
            print("Custom range analysis would be implemented here")
        except ValueError:
            print("Invalid interval")


if __name__ == "__main__":
    print("Word List Blockchain Research Analyzer")
    print("=" * 50)
    
    print("Choose mode:")
    print("1. Demo analysis")
    print("2. Interactive analysis")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        demo_research_analysis()
    elif choice == "2":
        interactive_research_analysis()
    else:
        print("Invalid choice, running demo...")
        demo_research_analysis()
