#!/usr/bin/env python3
"""
Test script to demonstrate API logging functionality.

This script runs a few test lookups to generate API logs for demonstration.
"""

import sys
import os

# Add the package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paper_auditor.lookup import CitationLookup
from paper_auditor.models import CitationMetadata


def test_api_logging():
    """Test the API logging functionality with sample lookups."""
    print("Testing API logging functionality...")
    print("This will generate logs in logs/api_calls.log")
    
    # Initialize the lookup service
    lookup = CitationLookup()
    
    # Test cases for different APIs
    test_cases = [
        # Test DOI lookup (CrossRef)
        CitationMetadata(
            doi="10.1038/nature12373",
            title="A universal scaling law between gray matter and white matter of cerebral cortex"
        ),
        
        # Test PMID lookup (PubMed)
        CitationMetadata(
            pmid="12345678",
            title="Example paper title for PubMed"
        ),
        
        # Test arXiv lookup
        CitationMetadata(
            arxiv_id="1706.03762",
            title="Attention Is All You Need"
        ),
        
        # Test CrossRef search by title
        CitationMetadata(
            title="Deep learning",
            authors=["LeCun, Y.", "Bengio, Y.", "Hinton, G."]
        ),
        
        # Test PubMed search
        CitationMetadata(
            title="Machine learning in medicine",
            authors=["Smith, John"]
        ),
        
        # Test with non-existent DOI (will generate error log)
        CitationMetadata(
            doi="10.1234/nonexistent.doi",
            title="This DOI does not exist"
        )
    ]
    
    print(f"\nRunning {len(test_cases)} test lookups...")
    
    for i, metadata in enumerate(test_cases, 1):
        print(f"\nTest {i}: ", end="")
        
        if metadata.doi:
            print(f"DOI lookup for {metadata.doi}")
        elif metadata.pmid:
            print(f"PMID lookup for {metadata.pmid}")
        elif metadata.arxiv_id:
            print(f"arXiv lookup for {metadata.arxiv_id}")
        else:
            print(f"Title search for '{metadata.title[:50]}...'")
        
        try:
            result = lookup.lookup_citation(metadata)
            if result.get('found'):
                print(f"  ✓ Found via {result['source']} (confidence: {result.get('confidence', 0):.2f})")
            else:
                print(f"  ✗ Not found")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\n{'='*60}")
    print("API logging test completed!")
    print(f"{'='*60}")
    print("\nCheck the logs:")
    print("  • View raw logs: cat logs/api_calls.log")
    print("  • Analyze logs: python api_log_analyzer.py --stats")
    print("  • Show errors: python api_log_analyzer.py --errors-only")
    print("  • Service stats: python api_log_analyzer.py --service crossref --stats")


if __name__ == "__main__":
    test_api_logging() 