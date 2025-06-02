"""
Report generators for audit results.
"""

import json
from typing import Dict, Any
from datetime import datetime

from .models import PaperAuditReport, CitationAudit, CitationStatus


class MarkdownReporter:
    """Generate Markdown reports."""
    
    def generate_report(self, report: PaperAuditReport) -> str:
        """Generate a comprehensive Markdown report."""
        md_lines = []
        
        # Header
        md_lines.append("# Paper Reference Audit Report")
        md_lines.append("")
        md_lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append("")
        
        # Paper info
        md_lines.append("## Paper Information")
        md_lines.append("")
        md_lines.append(f"**Title**: {report.paper_title}")
        if report.paper_authors:
            md_lines.append(f"**Authors**: {', '.join(report.paper_authors)}")
        md_lines.append(f"**Total Citations**: {report.total_citations}")
        md_lines.append("")
        
        # Summary
        md_lines.append("## Summary")
        md_lines.append("")
        md_lines.append(f"- ✅ **Passed**: {report.passed_count} citations")
        md_lines.append(f"- ⚠️ **Suspect**: {report.suspect_count} citations")
        md_lines.append(f"- ❌ **Missing**: {report.missing_count} citations")
        md_lines.append("")
        
        # Pass rate
        total_audited = len(report.audited_citations)
        if total_audited > 0:
            pass_rate = (report.passed_count / total_audited) * 100
            md_lines.append(f"**Pass Rate**: {pass_rate:.1f}%")
        md_lines.append("")
        
        # Detailed results
        md_lines.append("## Detailed Results")
        md_lines.append("")
        
        # Group by status
        for status in [CitationStatus.MISSING, CitationStatus.SUSPECT, CitationStatus.PASS]:
            status_citations = [c for c in report.audited_citations if c.status == status]
            
            if status_citations:
                md_lines.append(f"### {status.value}")
                md_lines.append("")
                
                for citation in status_citations:
                    md_lines.extend(self._format_citation(citation))
                    md_lines.append("")
        
        return "\n".join(md_lines)
    
    def _format_citation(self, citation: CitationAudit) -> list[str]:
        """Format a single citation for Markdown."""
        lines = []
        
        # Citation header
        title = citation.metadata.title or "Unknown Title"
        lines.append(f"#### {citation.status.value} {title}")
        lines.append("")
        
        # Basic info
        if citation.metadata.authors:
            lines.append(f"**Authors**: {', '.join(citation.metadata.authors[:3])}")
        if citation.metadata.year:
            lines.append(f"**Year**: {citation.metadata.year}")
        if citation.metadata.journal:
            lines.append(f"**Journal**: {citation.metadata.journal}")
        if citation.metadata.doi:
            lines.append(f"**DOI**: {citation.metadata.doi}")
        
        # Existence check
        lines.append(f"**Found Online**: {'Yes' if citation.exists_online else 'No'}")
        if citation.source_database:
            lines.append(f"**Source**: {citation.source_database}")
        
        # Relevance score
        if citation.relevance:
            lines.append(f"**Relevance Score**: {citation.relevance.score}/5")
            lines.append(f"**Relevance Explanation**: {citation.relevance.explanation}")
        
        # Justification
        if citation.justification:
            justified_text = "Yes" if citation.justification.justified else "No"
            lines.append(f"**Supports Claim**: {justified_text}")
            lines.append(f"**Justification**: {citation.justification.rationale}")
        
        # Context
        if citation.contexts:
            context = citation.contexts[0]
            if context.claim_statement:
                lines.append(f"**Claim**: \"{context.claim_statement}\"")
        
        return lines


class JSONReporter:
    """Generate JSON reports."""
    
    def generate_report(self, report: PaperAuditReport) -> str:
        """Generate a comprehensive JSON report."""
        report_dict = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "tool_version": "1.0.0"
            },
            "paper": {
                "title": report.paper_title,
                "authors": report.paper_authors,
                "total_citations": report.total_citations
            },
            "summary": {
                "passed_count": report.passed_count,
                "suspect_count": report.suspect_count,
                "missing_count": report.missing_count,
                "total_audited": len(report.audited_citations),
                "pass_rate": (report.passed_count / len(report.audited_citations) * 100) if report.audited_citations else 0
            },
            "citations": [self._citation_to_dict(citation) for citation in report.audited_citations]
        }
        
        return json.dumps(report_dict, indent=2, ensure_ascii=False)
    
    def _citation_to_dict(self, citation: CitationAudit) -> Dict[str, Any]:
        """Convert citation audit to dictionary."""
        citation_dict = {
            "citation_key": citation.citation_key,
            "original_text": citation.original_text,
            "status": citation.status.value,
            "exists_online": citation.exists_online,
            "source_database": citation.source_database,
            "metadata": {
                "title": citation.metadata.title,
                "authors": citation.metadata.authors,
                "year": citation.metadata.year,
                "journal": citation.metadata.journal,
                "volume": citation.metadata.volume,
                "pages": citation.metadata.pages,
                "doi": citation.metadata.doi,
                "pmid": citation.metadata.pmid,
                "arxiv_id": citation.metadata.arxiv_id,
                "url": citation.metadata.url,
                "abstract": citation.metadata.abstract
            }
        }
        
        # Add relevance info
        if citation.relevance:
            citation_dict["relevance"] = {
                "score": citation.relevance.score,
                "explanation": citation.relevance.explanation
            }
        
        # Add justification info
        if citation.justification:
            citation_dict["justification"] = {
                "justified": citation.justification.justified,
                "rationale": citation.justification.rationale
            }
        
        # Add contexts
        if citation.contexts:
            citation_dict["contexts"] = [
                {
                    "page_number": ctx.page_number,
                    "section": ctx.section,
                    "surrounding_text": ctx.surrounding_text,
                    "claim_statement": ctx.claim_statement
                }
                for ctx in citation.contexts
            ]
        
        return citation_dict


def generate_report(report: PaperAuditReport, format_type: str = "markdown") -> str:
    """Generate a report in the specified format."""
    if format_type.lower() == "json":
        reporter = JSONReporter()
    else:
        reporter = MarkdownReporter()
    
    return reporter.generate_report(report) 