#!/usr/bin/env python3
"""
Comprehensive test script for enhanced paper auditor capabilities.
Tests advanced citation extraction, lookup strategies, and full-text vs abstract analysis.
"""

import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any

# Set up logging before importing our modules
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from paper_auditor.extractors import TextExtractor
from paper_auditor.lookup import CitationLookup
from paper_auditor.evaluator import RelevanceEvaluator
from paper_auditor.models import CitationMetadata

def test_enhanced_citation_extraction():
    """Test the enhanced citation extraction patterns."""
    print("\n" + "=" * 80)
    print("TESTING ENHANCED CITATION EXTRACTION")
    print("=" * 80)
    
    extractor = TextExtractor()
    
    # Test with various citation formats
    test_texts = [
        # Numbered citations
        "Recent studies [1,2,3] have shown significant improvements in machine learning algorithms [4-7].",
        
        # Author-year citations
        "According to Smith et al. (2021), the methodology demonstrates significant improvements (Jones, 2020; Brown & Davis, 2019).",
        
        # Mixed formats
        "The approach^1,2 builds on previous work¹ and shows promise (Wilson, 2021, p. 45) for future applications [8].",
        
        # DOI and identifier patterns
        "See doi:10.1038/nature12373 and arXiv:2103.00020v1 for detailed analysis. PMID: 12345678 provides additional context.",
        
        # Complex citation contexts
        """Research in deep learning has advanced rapidly in recent years. Smith and colleagues (2021) demonstrated 
        that transformer architectures can achieve state-of-the-art results [15-17]. Similarly, the work by 
        Jones et al. (2020) showed improvements in computer vision tasks^18,19. These findings are consistent 
        with earlier studies (Brown, 2019; Davis & Wilson, 2018) that established the foundational principles."""
    ]
    
    total_patterns_tested = len(extractor.citation_patterns)
    patterns_detected = set()
    
    print(f"Testing {total_patterns_tested} citation patterns:")
    for i, pattern in enumerate(extractor.citation_patterns, 1):
        print(f"   {i:2d}. {pattern[:60]}{'...' if len(pattern) > 60 else ''}")
    
    print(f"\nTesting citation extraction on {len(test_texts)} sample texts:")
    
    for i, text in enumerate(test_texts, 1):
        print(f"\n--- Test Text {i} ---")
        print(f"Text: {text[:100]}...")
        
        citations, contexts = extractor.extract_citations_and_contexts(text, use_full_text=True)
        
        print(f"Found {len(citations)} citations and {len(contexts)} contexts")
        
        # Check which patterns were triggered
        for j, pattern in enumerate(extractor.compiled_patterns):
            matches = pattern.finditer(text)
            match_count = len(list(matches))
            if match_count > 0:
                patterns_detected.add(j)
                print(f"   Pattern {j+1}: {match_count} matches")
    
    coverage_rate = len(patterns_detected) / total_patterns_tested
    print(f"\nPattern Coverage: {len(patterns_detected)}/{total_patterns_tested} ({coverage_rate*100:.1f}%)")
    
    # Assertions for test validation
    assert total_patterns_tested >= 10, f"Should have at least 10 patterns, got {total_patterns_tested}"
    assert len(patterns_detected) >= 7, f"Should detect at least 7 patterns, got {len(patterns_detected)}"
    assert coverage_rate >= 0.6, f"Should achieve at least 60% coverage, got {coverage_rate*100:.1f}%"
    
    print(f"✅ Enhanced citation extraction test PASSED!")
    print(f"   - Patterns tested: {total_patterns_tested}")
    print(f"   - Patterns detected: {len(patterns_detected)}")
    print(f"   - Coverage rate: {coverage_rate*100:.1f}%")

def test_enhanced_lookup_strategies():
    """Test enhanced lookup strategies with fallbacks."""
    print("\n" + "=" * 80)
    print("TESTING ENHANCED LOOKUP STRATEGIES")
    print("=" * 80)
    
    lookup = CitationLookup()
    
    # Test citations with varying levels of information
    test_citations = [
        # Complete citation with DOI
        CitationMetadata(
            title="Attention is All You Need",
            authors=["Vaswani, A.", "Shazeer, N."],
            year=2017,
            doi="10.1038/nature12373"
        ),
        
        # Citation with partial information
        CitationMetadata(
            title="Deep Learning for Computer Vision",
            authors=["Smith, J."],
            year=2020
        ),
        
        # Citation with only title (fuzzy search test)
        CitationMetadata(
            title="Machine Learning Applications Healthcare"
        ),
        
        # Citation with arXiv ID
        CitationMetadata(
            title="Transformer Networks",
            arxiv_id="1706.03762"
        ),
        
        # Citation with PMID
        CitationMetadata(
            title="Medical Research Study",
            pmid="12345678"
        )
    ]
    
    print(f"Testing lookup for {len(test_citations)} citations:")
    
    results = {
        'primary_success': 0,
        'secondary_success': 0,
        'fallback_success': 0,
        'total_success': 0,
        'source_distribution': {},
        'confidence_scores': [],
        'lookup_details': []
    }
    
    for i, citation in enumerate(test_citations, 1):
        print(f"\n--- Citation {i} ---")
        print(f"Title: {citation.title}")
        print(f"Authors: {citation.authors}")
        print(f"Year: {citation.year}")
        print(f"DOI: {citation.doi}")
        print(f"arXiv: {citation.arxiv_id}")
        print(f"PMID: {citation.pmid}")
        
        start_time = time.time()
        
        # Test with fallbacks enabled
        result_with_fallbacks = lookup.lookup_citation(citation, enable_fallbacks=True)
        
        # Test without fallbacks
        result_without_fallbacks = lookup.lookup_citation(citation, enable_fallbacks=False)
        
        lookup_time = time.time() - start_time
        
        print(f"Lookup time: {lookup_time:.2f}s")
        print(f"Found (with fallbacks): {result_with_fallbacks['found']}")
        print(f"Found (without fallbacks): {result_without_fallbacks['found']}")
        
        if result_with_fallbacks['found']:
            results['total_success'] += 1
            source = result_with_fallbacks['source']
            confidence = result_with_fallbacks['confidence']
            
            print(f"Source: {source}")
            print(f"Confidence: {confidence:.3f}")
            
            # Categorize by lookup method
            if source in ['doi', 'pmid', 'arxiv']:
                results['primary_success'] += 1
            elif 'fallback' in source or 'fuzzy' in source:
                results['fallback_success'] += 1
            else:
                results['secondary_success'] += 1
            
            # Track source distribution
            results['source_distribution'][source] = results['source_distribution'].get(source, 0) + 1
            results['confidence_scores'].append(confidence)
            
            # Full text availability check
            full_text_available = result_with_fallbacks.get('full_text_available', False)
            print(f"Full text available: {full_text_available}")
        
        results['lookup_details'].append({
            'citation_title': citation.title,
            'found_with_fallbacks': result_with_fallbacks['found'],
            'found_without_fallbacks': result_without_fallbacks['found'],
            'source': result_with_fallbacks.get('source'),
            'confidence': result_with_fallbacks.get('confidence', 0.0),
            'lookup_time': lookup_time
        })
    
    # Calculate statistics
    total_citations = len(test_citations)
    success_rate = results['total_success'] / total_citations
    avg_confidence = sum(results['confidence_scores']) / len(results['confidence_scores']) if results['confidence_scores'] else 0
    
    print(f"\n--- LOOKUP RESULTS ---")
    print(f"Total success rate: {results['total_success']}/{total_citations} ({success_rate*100:.1f}%)")
    print(f"Primary methods: {results['primary_success']}")
    print(f"Secondary methods: {results['secondary_success']}")
    print(f"Fallback methods: {results['fallback_success']}")
    print(f"Average confidence: {avg_confidence:.3f}")
    print(f"Source distribution: {results['source_distribution']}")
    
    # Assertions for test validation
    assert success_rate >= 0.8, f"Should achieve at least 80% success rate, got {success_rate*100:.1f}%"
    assert avg_confidence >= 0.7, f"Should achieve at least 70% average confidence, got {avg_confidence:.1f}%"
    
    print(f"✅ Enhanced lookup strategies test PASSED!")
    print(f"   - Success rate: {success_rate*100:.1f}%")
    print(f"   - Average confidence: {avg_confidence:.3f}")

def test_full_text_vs_abstract_analysis():
    """Test full-text vs abstract analysis performance."""
    print("\n" + "=" * 80)
    print("TESTING FULL-TEXT VS ABSTRACT ANALYSIS")
    print("=" * 80)
    
    evaluator = RelevanceEvaluator()
    
    # Sample paper content (simulated)
    sample_full_text = """
    Abstract
    
    This paper presents a novel approach to machine learning in healthcare applications.
    We demonstrate significant improvements in diagnostic accuracy using deep learning
    techniques applied to medical imaging data. Our methodology achieves 95% accuracy
    on benchmark datasets.
    
    Introduction
    
    Machine learning has shown tremendous promise in healthcare applications. Previous
    studies by Smith et al. (2020) established the foundation for computer-aided diagnosis.
    Recent work by Jones and Davis (2021) extended these approaches to include multi-modal
    data analysis. However, existing methods face limitations in scalability and accuracy.
    
    Methods
    
    We developed a novel convolutional neural network architecture specifically designed
    for medical image analysis. The network incorporates attention mechanisms inspired
    by transformer architectures (Vaswani et al., 2017). Our approach builds on the
    work of Brown et al. (2019) in transfer learning for medical applications.
    
    Results
    
    Our method achieved 95% accuracy on the test dataset, significantly outperforming
    existing approaches. The results are consistent with findings from Wilson (2021)
    who reported similar improvements using related techniques. Statistical analysis
    confirms the significance of our results (p < 0.001).
    
    Discussion
    
    The improved performance can be attributed to the novel attention mechanisms and
    improved training procedures. Future work should explore applications to other
    medical domains as suggested by recent reviews (Taylor & Anderson, 2022).
    """
    
    # Sample citations
    test_citations = [
        CitationMetadata(
            title="Foundation of Computer-Aided Diagnosis in Medical Imaging",
            authors=["Smith, J.", "Johnson, M."],
            year=2020,
            abstract="This study establishes fundamental principles for computer-aided diagnosis using machine learning techniques in medical imaging applications."
        ),
        CitationMetadata(
            title="Transformer Architectures for Attention Mechanisms",
            authors=["Vaswani, A.", "Shazeer, N."],
            year=2017,
            abstract="We propose the Transformer, a model architecture based solely on attention mechanisms, dispensing with recurrence and convolutions entirely."
        ),
        CitationMetadata(
            title="Transfer Learning Applications in Medical Image Analysis",
            authors=["Brown, K.", "Lee, S."],
            year=2019,
            abstract="We investigate transfer learning techniques for medical image analysis and demonstrate their effectiveness across multiple domains."
        ),
        CitationMetadata(
            title="Statistical Methods for Machine Learning Evaluation",
            authors=["Wilson, R."],
            year=2021,
            abstract="This paper reviews statistical methods for evaluating machine learning models and discusses best practices for significance testing."
        )
    ]
    
    paper_title = "Novel Deep Learning Approach for Medical Image Analysis"
    
    print(f"Analyzing {len(test_citations)} citations with both full-text and abstract-only approaches")
    
    comparison_results = evaluator.compare_full_text_vs_abstract_performance(
        paper_title, sample_full_text, test_citations
    )
    
    print("\n--- COMPARISON RESULTS ---")
    
    if 'comparison_stats' in comparison_results:
        stats = comparison_results['comparison_stats']
        
        print(f"Full-text average relevance: {stats['full_text_avg_score']:.3f}")
        print(f"Abstract-only average relevance: {stats['abstract_avg_score']:.3f}")
        print(f"Average difference: {stats['avg_difference']:.3f}")
        print(f"Full-text advantages: {stats['full_text_advantage_count']}")
        print(f"Abstract advantages: {stats['abstract_advantage_count']}")
        print(f"Equal scores: {stats['equal_count']}")
        
        # Detailed analysis
        print(f"\n--- DETAILED COMPARISON ---")
        for i, (ft_result, ab_result) in enumerate(zip(
            comparison_results['full_text_results'],
            comparison_results['abstract_results']
        )):
            print(f"\nCitation {i+1}: {ft_result['citation_title'][:50]}...")
            print(f"  Full-text score: {ft_result['relevance_score']:.3f}")
            print(f"  Abstract score:  {ab_result['relevance_score']:.3f}")
            print(f"  Difference:      {ft_result['relevance_score'] - ab_result['relevance_score']:+.3f}")
    
    # Add basic assertions if comparison_stats is available
    if 'comparison_stats' in comparison_results:
        stats = comparison_results['comparison_stats']
        if 'full_text_avg_score' in stats and 'abstract_avg_score' in stats:
            # Expect full-text to generally perform better or at least as well
            assert stats['full_text_avg_score'] >= stats['abstract_avg_score'] - 0.1, \
                f"Full-text should not perform significantly worse than abstract-only"
    
    print(f"✅ Full-text vs abstract analysis test COMPLETED!")

def test_advanced_similarity_algorithms():
    """Test advanced similarity algorithms."""
    print("\n" + "=" * 80)
    print("TESTING ADVANCED SIMILARITY ALGORITHMS")
    print("=" * 80)
    
    lookup = CitationLookup()
    
    # Test title similarity with various scenarios
    title_pairs = [
        # Exact match
        ("Machine Learning in Healthcare", "Machine Learning in Healthcare"),
        
        # Very similar
        ("Deep Learning for Computer Vision", "Deep learning approaches for computer vision"),
        
        # Partially similar
        ("Neural Networks for Image Recognition", "Convolutional Neural Networks for Object Detection"),
        
        # Different but related
        ("Artificial Intelligence in Medicine", "Medical Applications of AI"),
        
        # Completely different
        ("Quantum Computing Algorithms", "Marine Biology Research Methods")
    ]
    
    print(f"Testing similarity algorithms on {len(title_pairs)} title pairs:")
    
    for i, (title1, title2) in enumerate(title_pairs, 1):
        similarity = lookup._enhanced_title_similarity(title1, title2)
        print(f"\n{i}. '{title1}'")
        print(f"   '{title2}'")
        print(f"   Similarity: {similarity:.3f}")
    
    # Test author similarity
    print(f"\n--- AUTHOR SIMILARITY TESTING ---")
    
    author_pairs = [
        # Exact match
        (["Smith, J.", "Jones, M."], ["Smith, J.", "Jones, M."]),
        
        # Partial match
        (["Smith, J.", "Brown, K."], ["Smith, J.", "Davis, L."]),
        
        # Fuzzy match (similar names)
        (["Smith, John"], ["Smith, J."]),
        
        # No match
        (["Wilson, R."], ["Taylor, S."])
    ]
    
    for i, (authors1, authors2) in enumerate(author_pairs, 1):
        similarity = lookup._calculate_author_similarity(authors1, authors2)
        print(f"\n{i}. {authors1} vs {authors2}")
        print(f"   Author similarity: {similarity:.3f}")

def run_comprehensive_test():
    """Run all comprehensive tests."""
    print("STARTING COMPREHENSIVE ENHANCED PAPER AUDITOR TESTS")
    print("=" * 80)
    
    test_results = {}
    
    try:
        # Test 1: Enhanced citation extraction
        print("\n[1/4] Enhanced Citation Extraction...")
        test_results['extraction'] = test_enhanced_citation_extraction()
        
        # Test 2: Enhanced lookup strategies  
        print("\n[2/4] Enhanced Lookup Strategies...")
        test_results['lookup'] = test_enhanced_lookup_strategies()
        
        # Test 3: Full-text vs abstract analysis
        print("\n[3/4] Full-text vs Abstract Analysis...")
        test_results['comparison'] = test_full_text_vs_abstract_analysis()
        
        # Test 4: Advanced similarity algorithms
        print("\n[4/4] Advanced Similarity Algorithms...")
        test_advanced_similarity_algorithms()
        
        # Calculate overall success metrics
        print("\n" + "=" * 80)
        print("OVERALL PERFORMANCE METRICS")
        print("=" * 80)
        
        extraction_coverage = test_results['extraction']['coverage_rate']
        lookup_success = test_results['lookup']['total_success'] / 5  # 5 test citations
        avg_confidence = sum(test_results['lookup']['confidence_scores']) / len(test_results['lookup']['confidence_scores']) if test_results['lookup']['confidence_scores'] else 0
        
        # Estimate overall success rate based on components
        estimated_success_rate = (
            extraction_coverage * 0.3 +  # 30% weight for extraction
            lookup_success * 0.5 +       # 50% weight for lookup success
            avg_confidence * 0.2          # 20% weight for confidence
        )
        
        print(f"Citation Pattern Coverage: {extraction_coverage*100:.1f}%")
        print(f"Lookup Success Rate: {lookup_success*100:.1f}%")
        print(f"Average Lookup Confidence: {avg_confidence:.3f}")
        print(f"Estimated Overall Success Rate: {estimated_success_rate*100:.1f}%")
        
        # Full-text vs abstract comparison
        if 'comparison_stats' in test_results['comparison']:
            comp_stats = test_results['comparison']['comparison_stats']
            ft_advantage = comp_stats['full_text_advantage_count']
            total_comparisons = len(test_results['comparison']['full_text_results'])
            ft_advantage_rate = ft_advantage / total_comparisons if total_comparisons > 0 else 0
            
            print(f"Full-text Analysis Advantage: {ft_advantage}/{total_comparisons} cases ({ft_advantage_rate*100:.1f}%)")
            print(f"Average Relevance Improvement: {comp_stats['avg_difference']:+.3f}")
        
        # Determine if we've achieved 90%+ target
        success_threshold = 0.90
        if estimated_success_rate >= success_threshold:
            print(f"\n🎉 SUCCESS: Achieved {estimated_success_rate*100:.1f}% success rate (target: {success_threshold*100:.0f}%+)")
        else:
            print(f"\n⚠️  IMPROVEMENT NEEDED: {estimated_success_rate*100:.1f}% success rate (target: {success_threshold*100:.0f}%+)")
            print("   Consider additional improvements to lookup strategies or citation patterns.")
        
        # Save detailed results
        results_file = "enhanced_test_results.json"
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        print(f"\nDetailed results saved to: {results_file}")
        
        return test_results
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    run_comprehensive_test() 