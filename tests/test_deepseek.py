#!/usr/bin/env python3
"""
Test script for DeepSeek API integration with BiblioGuard
"""

import os
import sys
from pathlib import Path

# Add the paper_auditor module to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_deepseek_evaluator():
    """Test the DeepSeek evaluator directly."""
    print("Testing DeepSeek Evaluator...")
    
    try:
        from paper_auditor.llm_evaluator import DeepSeekEvaluator
        from paper_auditor.models import CitationMetadata, CitationContext
        
        # Check if API key is available
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            print("❌ DEEPSEEK_API_KEY not found in environment")
            print("   Set it with: export DEEPSEEK_API_KEY='your-key-here'")
            return False
        
        print("✅ DeepSeek API key found")
        
        # Initialize evaluator
        evaluator = DeepSeekEvaluator(model="deepseek-chat", api_key=api_key)
        print("✅ DeepSeek evaluator initialized")
        
        # Test citation metadata
        citation = CitationMetadata(
            title="Machine Learning in Healthcare: A Survey",
            authors=["Smith, J.", "Doe, A."],
            year=2023,
            journal="Journal of Medical AI"
        )
        
        # Test relevance evaluation
        print("\n🧪 Testing relevance evaluation...")
        relevance = evaluator.evaluate_relevance(
            paper_title="AI Applications in Medical Diagnosis",
            paper_abstract="This paper reviews recent advances in artificial intelligence for medical diagnosis, focusing on machine learning algorithms and their clinical applications.",
            citation_metadata=citation
        )
        
        print(f"   Relevance Score: {relevance.score}/5")
        print(f"   Explanation: {relevance.explanation}")
        
        # Test justification evaluation
        print("\n🧪 Testing justification evaluation...")
        context = CitationContext(
            page_number=3,
            section="Related Work",
            surrounding_text="Recent studies have shown promising results in AI-powered diagnosis. Smith et al. (2023) demonstrated significant improvements in diagnostic accuracy using machine learning approaches.",
            claim_statement="demonstrated significant improvements in diagnostic accuracy using machine learning approaches"
        )
        
        justification = evaluator.evaluate_justification(
            citation_context=context,
            citation_metadata=citation
        )
        
        print(f"   Justified: {justification.justified}")
        print(f"   Rationale: {justification.rationale}")
        
        print("\n✅ DeepSeek evaluator tests completed successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing DeepSeek evaluator: {e}")
        return False

def test_paper_auditor_with_deepseek():
    """Test the full PaperAuditor with DeepSeek."""
    print("\n" + "="*50)
    print("Testing PaperAuditor with DeepSeek...")
    
    try:
        from paper_auditor import PaperAuditor
        
        # Initialize with DeepSeek
        auditor = PaperAuditor(model_type="deepseek", model="deepseek-chat")
        print("✅ PaperAuditor with DeepSeek initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing PaperAuditor with DeepSeek: {e}")
        return False

def test_backend_api():
    """Test the backend API models endpoint."""
    print("\n" + "="*50)
    print("Testing Backend API...")
    
    try:
        import requests
        
        # Test models endpoint
        response = requests.get("http://localhost:8000/models")
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            deepseek_models = [m for m in models if "deepseek" in m.lower()]
            
            if deepseek_models:
                print(f"✅ Found DeepSeek models in API: {deepseek_models}")
                return True
            else:
                print("❌ No DeepSeek models found in API response")
                return False
        else:
            print(f"❌ API not responding (status: {response.status_code})")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Backend API not running on localhost:8000")
        print("   Start it with: python backend_api.py")
        return False
    except Exception as e:
        print(f"❌ Error testing backend API: {e}")
        return False

if __name__ == "__main__":
    print("BiblioGuard DeepSeek Integration Test")
    print("=" * 50)
    
    results = []
    
    # Test 1: DeepSeek Evaluator
    results.append(test_deepseek_evaluator())
    
    # Test 2: PaperAuditor with DeepSeek
    results.append(test_paper_auditor_with_deepseek())
    
    # Test 3: Backend API
    results.append(test_backend_api())
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! DeepSeek integration is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        
    print("\nNext steps:")
    if not os.getenv('DEEPSEEK_API_KEY'):
        print("1. Set up your DeepSeek API key:")
        print("   export DEEPSEEK_API_KEY='your-key-here'")
    print("2. Start the backend API: python backend_api.py")
    print("3. Start the frontend: cd biblioguard-ui && npm start")
    print("4. Test the complete workflow in the web interface") 