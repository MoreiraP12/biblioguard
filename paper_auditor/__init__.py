"""
Paper Reference Auditor

A tool for auditing the references of research papers to verify their existence,
relevance, and justification for claims made in the paper.
"""

__version__ = "1.0.0"
__author__ = "Paper Auditor"

from .auditor import PaperAuditor
from .models import (
    CitationMetadata, CitationContext, RelevanceScore, 
    JustificationCheck, CitationAudit, PaperAuditReport, CitationStatus
)
from .reporters import generate_report

__all__ = [
    'PaperAuditor',
    'CitationMetadata', 
    'CitationContext', 
    'RelevanceScore',
    'JustificationCheck', 
    'CitationAudit', 
    'PaperAuditReport', 
    'CitationStatus',
    'generate_report'
] 