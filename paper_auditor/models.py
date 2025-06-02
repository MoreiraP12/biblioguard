"""
Data models for the paper auditor tool.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum


class CitationStatus(Enum):
    """Status of a citation after audit."""
    PASS = "✅ Pass"
    SUSPECT = "⚠️ Suspect"
    MISSING = "❌ Missing"


@dataclass
class CitationMetadata:
    """Metadata for a citation."""
    title: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    pmid: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    abstract: Optional[str] = None


@dataclass
class CitationContext:
    """Context where a citation is used in the paper."""
    page_number: Optional[int] = None
    section: Optional[str] = None
    surrounding_text: str = ""
    claim_statement: str = ""


@dataclass
class RelevanceScore:
    """Relevance score and explanation."""
    score: int  # 0-5 scale
    explanation: str


@dataclass
class JustificationCheck:
    """Justification check result."""
    justified: bool
    rationale: str


@dataclass
class CitationAudit:
    """Complete audit result for a citation."""
    citation_key: str
    original_text: str
    metadata: CitationMetadata
    contexts: List[CitationContext] = field(default_factory=list)
    
    # Audit results
    exists_online: bool = False
    existence_details: str = ""
    relevance: Optional[RelevanceScore] = None
    justification: Optional[JustificationCheck] = None
    status: CitationStatus = CitationStatus.MISSING
    
    # Additional info
    source_database: Optional[str] = None
    api_response: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PaperAuditReport:
    """Complete audit report for a paper."""
    paper_title: str
    paper_authors: List[str]
    total_citations: int
    audited_citations: List[CitationAudit]
    
    # Summary statistics
    passed_count: int = 0
    suspect_count: int = 0
    missing_count: int = 0
    
    def __post_init__(self):
        """Calculate summary statistics."""
        self.passed_count = sum(1 for c in self.audited_citations if c.status == CitationStatus.PASS)
        self.suspect_count = sum(1 for c in self.audited_citations if c.status == CitationStatus.SUSPECT)
        self.missing_count = sum(1 for c in self.audited_citations if c.status == CitationStatus.MISSING) 