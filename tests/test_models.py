"""
Tests for data models.
"""

import pytest
from paper_auditor.models import (
    CitationMetadata, CitationContext, RelevanceScore, 
    JustificationCheck, CitationAudit, PaperAuditReport, CitationStatus
)


def test_citation_metadata():
    """Test CitationMetadata creation and validation."""
    metadata = CitationMetadata(
        title="Test Paper",
        authors=["Smith, J.", "Doe, J."],
        year=2021,
        doi="10.1000/test"
    )
    
    assert metadata.title == "Test Paper"
    assert len(metadata.authors) == 2
    assert metadata.year == 2021
    assert metadata.doi == "10.1000/test"


def test_citation_context():
    """Test CitationContext creation."""
    context = CitationContext(
        page_number=5,
        surrounding_text="This is a test citation [1].",
        claim_statement="This is a claim."
    )
    
    assert context.page_number == 5
    assert "test citation" in context.surrounding_text
    assert context.claim_statement == "This is a claim."


def test_relevance_score():
    """Test RelevanceScore validation."""
    score = RelevanceScore(score=4, explanation="Highly relevant")
    
    assert score.score == 4
    assert score.explanation == "Highly relevant"


def test_justification_check():
    """Test JustificationCheck creation."""
    check = JustificationCheck(justified=True, rationale="Good support")
    
    assert check.justified is True
    assert check.rationale == "Good support"


def test_citation_audit():
    """Test CitationAudit creation."""
    metadata = CitationMetadata(title="Test", year=2021)
    audit = CitationAudit(
        citation_key="ref_1",
        original_text="Reference 1",
        metadata=metadata
    )
    
    assert audit.citation_key == "ref_1"
    assert audit.metadata.title == "Test"
    assert audit.exists_online is False  # Default
    assert audit.status == CitationStatus.MISSING  # Default


def test_paper_audit_report():
    """Test PaperAuditReport statistics calculation."""
    metadata = CitationMetadata(title="Test", year=2021)
    
    # Create mock audits
    audit1 = CitationAudit("ref_1", "Ref 1", metadata)
    audit1.status = CitationStatus.PASS
    
    audit2 = CitationAudit("ref_2", "Ref 2", metadata)
    audit2.status = CitationStatus.SUSPECT
    
    audit3 = CitationAudit("ref_3", "Ref 3", metadata)
    audit3.status = CitationStatus.MISSING
    
    report = PaperAuditReport(
        paper_title="Test Paper",
        paper_authors=["Author"],
        total_citations=3,
        audited_citations=[audit1, audit2, audit3]
    )
    
    assert report.passed_count == 1
    assert report.suspect_count == 1
    assert report.missing_count == 1
    assert report.total_citations == 3


def test_citation_status_enum():
    """Test CitationStatus enum values."""
    assert CitationStatus.PASS.value == "✅ Pass"
    assert CitationStatus.SUSPECT.value == "⚠️ Suspect"
    assert CitationStatus.MISSING.value == "❌ Missing" 