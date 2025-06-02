#!/usr/bin/env python3
"""
Demonstration script for the Paper Reference Auditor.

This script shows how to use the auditor programmatically to audit
a research paper's references.
"""

import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_auditor import PaperAuditor
from paper_auditor.reporters import generate_report


def main():
    """Demonstrate the paper auditor functionality."""
    
    # Paths to example files
    paper_path = Path(__file__).parent / "sample_paper.txt"
    references_path = Path(__file__).parent / "sample_references.bib"
    
    print("🔍 Paper Reference Auditor Demo")
    print("=" * 40)
    
    # Check if example files exist
    if not paper_path.exists():
        print(f"❌ Sample paper not found: {paper_path}")
        return
    
    if not references_path.exists():
        print(f"❌ Sample references not found: {references_path}")
        return
    
    # Check for API keys
    if not (os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')):
        print("⚠️ No API keys found. Running in demo mode without LLM evaluation.")
        print("Set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variables for full functionality.")
        demo_mode = True
    else:
        demo_mode = False
    
    try:
        # Initialize the auditor
        if demo_mode:
            # Mock evaluator for demo
            print("🤖 Using mock evaluator (no API calls)")
            auditor = MockPaperAuditor()
        else:
            print("🤖 Initializing with GPT-3.5-turbo")
            auditor = PaperAuditor(model_type="gpt-3.5-turbo")
        
        # Run the audit
        print(f"📄 Auditing paper: {paper_path.name}")
        print(f"📚 Using references: {references_path.name}")
        print()
        
        report = auditor.audit_paper(
            str(paper_path), 
            str(references_path)
        )
        
        # Generate and display report
        print("📊 Audit Results:")
        print("=" * 40)
        
        markdown_report = generate_report(report, "markdown")
        print(markdown_report)
        
        # Save JSON report
        json_report = generate_report(report, "json")
        output_path = Path(__file__).parent / "audit_report.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_report)
        
        print(f"\n💾 JSON report saved to: {output_path}")
        
        # Summary
        print(f"\n📈 Summary:")
        print(f"   ✅ Passed: {report.passed_count}")
        print(f"   ⚠️ Suspect: {report.suspect_count}")
        print(f"   ❌ Missing: {report.missing_count}")
        
    except Exception as e:
        print(f"❌ Error during audit: {e}")
        sys.exit(1)


class MockPaperAuditor:
    """Mock auditor for demonstration without API calls."""
    
    def audit_paper(self, paper_path, references_path=None):
        """Mock audit that doesn't make real API calls."""
        from paper_auditor.extractors import PaperExtractor, ReferenceExtractor
        from paper_auditor.models import (
            PaperAuditReport, CitationAudit, CitationStatus,
            RelevanceScore, JustificationCheck, CitationContext
        )
        
        # Extract paper content
        extractor = PaperExtractor()
        text, contexts = extractor.extract_from_text(paper_path)
        title, authors = extractor.extract_paper_metadata(text)
        
        # Extract references
        ref_extractor = ReferenceExtractor()
        references = ref_extractor.extract_from_bibtex(references_path)
        
        # Create mock audits
        audited_citations = []
        
        for i, ref in enumerate(references[:5]):  # Limit to first 5 for demo
            audit = CitationAudit(
                citation_key=f"ref_{i+1}",
                original_text=f"Reference {i+1}",
                metadata=ref,
                contexts=[contexts[0]] if contexts else []
            )
            
            # Mock results
            audit.exists_online = True
            audit.source_database = "crossref_doi"
            audit.relevance = RelevanceScore(
                score=4 if i < 3 else 2,  # First 3 are relevant
                explanation="Mock relevance evaluation"
            )
            audit.justification = JustificationCheck(
                justified=i < 4,  # First 4 are justified
                rationale="Mock justification evaluation"
            )
            
            # Determine status
            if i == 4:  # Last one is suspect due to low relevance
                audit.status = CitationStatus.SUSPECT
            else:
                audit.status = CitationStatus.PASS
            
            audited_citations.append(audit)
        
        return PaperAuditReport(
            paper_title=title,
            paper_authors=authors,
            total_citations=len(references),
            audited_citations=audited_citations
        )


if __name__ == "__main__":
    main() 