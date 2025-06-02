"""
Extractors for parsing research papers and reference lists.
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import pdfplumber
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

from .models import CitationMetadata, CitationContext

logger = logging.getLogger(__name__)


class PaperExtractor:
    """Extract text and citations from research papers."""
    
    def __init__(self):
        self.citation_patterns = [
            r'\[(\d+(?:[-,]\d+)*)\]',  # [1], [1-3], [1,2,3]
            r'\(([^)]*\d{4}[^)]*)\)',  # (Author 2021)
            r'\b([A-Z][a-z]+\s+et\s+al\.?,?\s+\d{4})',  # Author et al. 2021
        ]
    
    def extract_from_pdf(self, pdf_path: str) -> Tuple[str, List[CitationContext]]:
        """Extract text and citation contexts from PDF."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                citations = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""
                    full_text += page_text + "\n\n"
                    
                    # Extract citations from this page
                    page_citations = self._extract_citations_from_text(
                        page_text, page_num
                    )
                    citations.extend(page_citations)
                
                return full_text, citations
        except Exception as e:
            logger.error(f"Error extracting from PDF {pdf_path}: {e}")
            raise
    
    def extract_from_text(self, text_path: str) -> Tuple[str, List[CitationContext]]:
        """Extract text and citation contexts from plain text file."""
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            citations = self._extract_citations_from_text(text)
            return text, citations
        except Exception as e:
            logger.error(f"Error extracting from text {text_path}: {e}")
            raise
    
    def _extract_citations_from_text(
        self, text: str, page_num: Optional[int] = None
    ) -> List[CitationContext]:
        """Extract citation contexts from text."""
        citations = []
        
        for pattern in self.citation_patterns:
            for match in re.finditer(pattern, text):
                start, end = match.span()
                citation_text = match.group(1)
                
                # Extract surrounding context (±200 characters)
                context_start = max(0, start - 200)
                context_end = min(len(text), end + 200)
                surrounding_text = text[context_start:context_end]
                
                # Try to identify the claim statement (sentence containing citation)
                claim_start = text.rfind('.', context_start, start) + 1
                claim_end = text.find('.', end, context_end)
                if claim_end == -1:
                    claim_end = context_end
                
                claim_statement = text[claim_start:claim_end].strip()
                
                citations.append(CitationContext(
                    page_number=page_num,
                    surrounding_text=surrounding_text,
                    claim_statement=claim_statement
                ))
        
        return citations
    
    def extract_paper_metadata(self, text: str) -> Tuple[str, List[str]]:
        """Extract paper title and authors from text."""
        lines = text.split('\n')
        
        # Simple heuristic: title is often the first non-empty line
        title = ""
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:  # Avoid short headers
                title = line
                break
        
        # Look for author patterns
        authors = []
        author_patterns = [
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+[A-Z]\.)*)\s*$',
            r'([A-Z][a-z]+,\s+[A-Z]\.(?:\s+[A-Z]\.)*)',
        ]
        
        for line in lines[:20]:  # Check first 20 lines
            for pattern in author_patterns:
                matches = re.findall(pattern, line)
                authors.extend(matches)
        
        return title, authors


class ReferenceExtractor:
    """Extract references from BibTeX or CSL JSON."""
    
    def extract_from_bibtex(self, bibtex_path: str) -> List[CitationMetadata]:
        """Extract citations from BibTeX file."""
        try:
            with open(bibtex_path, 'r', encoding='utf-8') as f:
                parser = BibTexParser(common_strings=True)
                parser.customization = convert_to_unicode
                bib_database = bibtexparser.load(f, parser=parser)
            
            citations = []
            for entry in bib_database.entries:
                metadata = self._bibtex_to_metadata(entry)
                citations.append(metadata)
            
            return citations
        except Exception as e:
            logger.error(f"Error extracting from BibTeX {bibtex_path}: {e}")
            raise
    
    def extract_from_csl_json(self, json_path: str) -> List[CitationMetadata]:
        """Extract citations from CSL JSON file."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            citations = []
            for entry in data:
                metadata = self._csl_to_metadata(entry)
                citations.append(metadata)
            
            return citations
        except Exception as e:
            logger.error(f"Error extracting from CSL JSON {json_path}: {e}")
            raise
    
    def _bibtex_to_metadata(self, entry: Dict) -> CitationMetadata:
        """Convert BibTeX entry to CitationMetadata."""
        authors = []
        if 'author' in entry:
            # Parse "Last, First and Last2, First2" format
            author_str = entry['author']
            author_parts = author_str.split(' and ')
            for part in author_parts:
                authors.append(part.strip())
        
        year = None
        if 'year' in entry:
            try:
                year = int(entry['year'])
            except ValueError:
                pass
        
        return CitationMetadata(
            title=entry.get('title', '').strip('{}'),
            authors=authors,
            year=year,
            journal=entry.get('journal') or entry.get('booktitle'),
            volume=entry.get('volume'),
            pages=entry.get('pages'),
            doi=entry.get('doi'),
            pmid=entry.get('pmid'),
            arxiv_id=entry.get('eprint'),
            url=entry.get('url')
        )
    
    def _csl_to_metadata(self, entry: Dict) -> CitationMetadata:
        """Convert CSL JSON entry to CitationMetadata."""
        authors = []
        if 'author' in entry:
            for author in entry['author']:
                if 'family' in author and 'given' in author:
                    authors.append(f"{author['family']}, {author['given']}")
                elif 'literal' in author:
                    authors.append(author['literal'])
        
        year = None
        if 'issued' in entry and 'date-parts' in entry['issued']:
            try:
                year = entry['issued']['date-parts'][0][0]
            except (IndexError, TypeError):
                pass
        
        return CitationMetadata(
            title=entry.get('title'),
            authors=authors,
            year=year,
            journal=entry.get('container-title'),
            volume=entry.get('volume'),
            pages=entry.get('page'),
            doi=entry.get('DOI'),
            pmid=entry.get('PMID'),
            url=entry.get('URL')
        ) 