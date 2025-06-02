"""
Main auditor class that orchestrates the citation auditing process.
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from tqdm import tqdm

from .models import CitationMetadata, CitationContext, CitationAudit, PaperAuditReport, CitationStatus
from .extractors import PaperExtractor, ReferenceExtractor
from .lookup import CitationLookup
from .llm_evaluator import create_evaluator, LLMEvaluator

logger = logging.getLogger(__name__)


class PaperAuditor:
    """Main class for auditing research paper references."""
    
    def __init__(self, model_type: str = "gpt-3.5-turbo", **model_kwargs):
        """Initialize the auditor with specified LLM model."""
        self.paper_extractor = PaperExtractor()
        self.reference_extractor = ReferenceExtractor()
        self.lookup = CitationLookup()
        self.evaluator = create_evaluator(model_type, **model_kwargs)
        
        logger.info(f"Initialized PaperAuditor with model: {model_type}")
    
    def audit_paper(
        self, 
        paper_path: str, 
        references_path: Optional[str] = None,
        output_format: str = "markdown"
    ) -> PaperAuditReport:
        """
        Audit a research paper's references.
        
        Args:
            paper_path: Path to PDF or text file of the paper
            references_path: Path to BibTeX or CSL JSON references (optional)
            output_format: Output format ("markdown" or "json")
        
        Returns:
            PaperAuditReport with complete audit results
        """
        logger.info(f"Starting audit of paper: {paper_path}")
        
        # Step 1: Extract paper content and citations
        paper_text, citation_contexts = self._extract_paper_content(paper_path)
        paper_title, paper_authors = self.paper_extractor.extract_paper_metadata(paper_text)
        
        # Extract abstract (first few paragraphs)
        paper_abstract = self._extract_abstract(paper_text)
        
        logger.info(f"Extracted paper: {paper_title}")
        logger.info(f"Found {len(citation_contexts)} citation contexts")
        
        # Step 2: Extract reference metadata
        reference_metadata = self._extract_references(references_path, paper_text)
        logger.info(f"Found {len(reference_metadata)} references")
        
        # Step 3: Match citations to references and audit each one
        audited_citations = self._audit_citations(
            reference_metadata, 
            citation_contexts,
            paper_title,
            paper_abstract
        )
        
        # Step 4: Create final report
        report = PaperAuditReport(
            paper_title=paper_title,
            paper_authors=paper_authors,
            total_citations=len(reference_metadata),
            audited_citations=audited_citations
        )
        
        logger.info(f"Audit complete. Results: {report.passed_count} pass, "
                   f"{report.suspect_count} suspect, {report.missing_count} missing")
        
        return report
    
    def _extract_paper_content(self, paper_path: str) -> tuple[str, List[CitationContext]]:
        """Extract content from paper file."""
        path = Path(paper_path)
        
        if path.suffix.lower() == '.pdf':
            return self.paper_extractor.extract_from_pdf(paper_path)
        else:
            return self.paper_extractor.extract_from_text(paper_path)
    
    def _extract_abstract(self, paper_text: str) -> str:
        """Extract abstract from paper text."""
        # Simple heuristic: look for "Abstract" section
        lines = paper_text.split('\n')
        abstract_lines = []
        in_abstract = False
        
        for line in lines:
            line = line.strip()
            if line.lower().startswith('abstract'):
                in_abstract = True
                continue
            elif in_abstract:
                if line.lower().startswith(('introduction', 'keywords', '1.', 'i.')):
                    break
                if line:
                    abstract_lines.append(line)
        
        abstract = ' '.join(abstract_lines)
        # Return first 1000 characters if abstract is very long
        return abstract[:1000] if len(abstract) > 1000 else abstract
    
    def _extract_references(self, references_path: Optional[str], paper_text: str) -> List[CitationMetadata]:
        """Extract reference metadata from file or paper text."""
        if references_path:
            path = Path(references_path)
            if path.suffix.lower() == '.bib':
                return self.reference_extractor.extract_from_bibtex(references_path)
            elif path.suffix.lower() == '.json':
                return self.reference_extractor.extract_from_csl_json(references_path)
        
        # Fallback: try to extract references from paper text
        return self._extract_references_from_text(paper_text)
    
    def _extract_references_from_text(self, paper_text: str) -> List[CitationMetadata]:
        """Extract references from paper text (simple heuristic)."""
        references = []
        lines = paper_text.split('\n')
        
        # Look for "References" section
        in_references = False
        current_ref = ""
        
        for line in lines:
            line = line.strip()
            
            if line.lower().startswith(('references', 'bibliography')):
                in_references = True
                continue
            
            if in_references:
                # Simple heuristic: each reference starts with a number
                if line and (line[0].isdigit() or line.startswith('[')):
                    if current_ref:
                        # Process previous reference
                        metadata = self._parse_reference_text(current_ref)
                        if metadata:
                            references.append(metadata)
                    current_ref = line
                elif line:
                    current_ref += " " + line
        
        # Process last reference
        if current_ref:
            metadata = self._parse_reference_text(current_ref)
            if metadata:
                references.append(metadata)
        
        return references
    
    def _parse_reference_text(self, ref_text: str) -> Optional[CitationMetadata]:
        """Parse a reference text string into metadata."""
        # Very basic parsing - could be improved significantly
        import re
        
        # Try to extract title (usually in quotes or after authors)
        title_match = re.search(r'"([^"]+)"', ref_text)
        title = title_match.group(1) if title_match else ""
        
        # Try to extract year
        year_match = re.search(r'\b(19|20)\d{2}\b', ref_text)
        year = int(year_match.group()) if year_match else None
        
        # Try to extract DOI
        doi_match = re.search(r'doi[:\s]*(10\.\d+/[^\s]+)', ref_text, re.IGNORECASE)
        doi = doi_match.group(1) if doi_match else None
        
        if title or doi:
            return CitationMetadata(
                title=title,
                year=year,
                doi=doi
            )
        
        return None
    
    def _audit_citations(
        self, 
        references: List[CitationMetadata],
        contexts: List[CitationContext],
        paper_title: str,
        paper_abstract: str
    ) -> List[CitationAudit]:
        """Audit all citations."""
        audited_citations = []
        
        # Create a simple mapping - in a real implementation, 
        # you'd want more sophisticated citation matching
        for i, ref in enumerate(tqdm(references, desc="Auditing citations")):
            audit = CitationAudit(
                citation_key=f"ref_{i+1}",
                original_text=f"Reference {i+1}",
                metadata=ref,
                contexts=contexts[:1] if contexts else []  # Simplified matching
            )
            
            # Step 1: Look up citation online
            lookup_result = self.lookup.lookup_citation(ref)
            audit.exists_online = lookup_result['found']
            audit.existence_details = lookup_result.get('details', {})
            audit.source_database = lookup_result.get('source')
            
            if lookup_result['found']:
                # Update metadata with found information
                found_metadata = lookup_result['metadata']
                if found_metadata:
                    audit.metadata = found_metadata
            
            # Step 2: Evaluate relevance
            if audit.exists_online and audit.metadata:
                try:
                    audit.relevance = self.evaluator.evaluate_relevance(
                        paper_title, paper_abstract, audit.metadata
                    )
                except Exception as e:
                    logger.warning(f"Relevance evaluation failed for {ref.title}: {e}")
            
            # Step 3: Evaluate justification
            if audit.contexts and audit.metadata:
                try:
                    audit.justification = self.evaluator.evaluate_justification(
                        audit.contexts[0], audit.metadata
                    )
                except Exception as e:
                    logger.warning(f"Justification evaluation failed for {ref.title}: {e}")
            
            # Step 4: Determine overall status
            audit.status = self._determine_status(audit)
            
            audited_citations.append(audit)
        
        return audited_citations
    
    def _determine_status(self, audit: CitationAudit) -> CitationStatus:
        """Determine the overall status of a citation."""
        # Missing if not found online
        if not audit.exists_online:
            return CitationStatus.MISSING
        
        # Suspect if relevance score is too low
        if audit.relevance and audit.relevance.score <= 2:
            return CitationStatus.SUSPECT
        
        # Suspect if justification is poor
        if audit.justification and not audit.justification.justified:
            return CitationStatus.SUSPECT
        
        # Otherwise, it passes
        return CitationStatus.PASS 