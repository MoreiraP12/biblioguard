"""
Extractors for parsing research papers and reference lists.
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

import pdfplumber
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode
import fitz  # PyMuPDF
from fuzzywuzzy import fuzz

from .models import CitationMetadata, CitationContext

logger = logging.getLogger(__name__)


class PaperExtractor:
    """Extract text and citations from research papers."""
    
    def __init__(self):
        # Comprehensive citation patterns for different styles
        self.citation_patterns = [
            # Numbered citations: [1], [1-3], [1,2,3], [1, 2, 3], [1-3, 5, 7-9]
            r'\[(\d+(?:[-–,]\s*\d+)*(?:\s*,\s*\d+(?:[-–]\d+)*)*)\]',
            
            # Parenthetical numbered: (1), (1-3), (1,2,3)
            r'\((\d+(?:[-–,]\s*\d+)*(?:\s*,\s*\d+(?:[-–]\d+)*)*)\)',
            
            # Author-year citations: (Smith, 2021), (Smith et al., 2021), (Smith & Jones, 2021)
            r'\(([A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|&|and)\s+[A-Z][a-zA-Z]+)*,?\s*\d{4}[a-z]?(?:\s*;\s*[A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.?|&|and)\s+[A-Z][a-zA-Z]+)*,?\s*\d{4}[a-z]?)*)\)',
            
            # Inline author-year: Smith (2021), Smith et al. (2021)
            r'\b([A-Z][a-zA-Z]+(?:\s+et\s+al\.?)?)\s+\((\d{4}[a-z]?)\)',
            
            # Multiple inline: Smith, Jones, and Taylor (2021)
            r'\b([A-Z][a-zA-Z]+(?:,\s+[A-Z][a-zA-Z]+)*,?\s+(?:and|&)\s+[A-Z][a-zA-Z]+)\s+\((\d{4}[a-z]?)\)',
            
            # Superscript style: text^1, text^1,2,3
            r'\^(\d+(?:,\s*\d+)*)',
            
            # Nature style: text1, text1,2,3 (numbers immediately after words)
            r'\b([a-zA-Z]+)(\d+(?:,\s*\d+)*)\b',
            
            # Harvard style: (Smith 2021), (Smith and Jones 2021)
            r'\(([A-Z][a-zA-Z]+(?:\s+(?:and|&)\s+[A-Z][a-zA-Z]+)*\s+\d{4}[a-z]?)\)',
        ]
        
        # Reference section headers
        self.reference_headers = [
            r'^\s*REFERENCES?\s*$',
            r'^\s*BIBLIOGRAPHY\s*$',
            r'^\s*WORKS?\s+CITED\s*$',
            r'^\s*LITERATURE\s+CITED\s*$',
            r'^\s*CITED\s+LITERATURE\s*$',
            r'^\s*SOURCES?\s*$',
        ]
        
        # Reference numbering patterns
        self.reference_patterns = [
            r'^\s*(\d+)\.\s+(.+)',  # 1. Author, Title...
            r'^\s*\[(\d+)\]\s+(.+)',  # [1] Author, Title...
            r'^\s*(\d+)\s+(.+)',  # 1 Author, Title...
            r'^\s*\((\d+)\)\s+(.+)',  # (1) Author, Title...
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
                
                # Additional extraction from full text for better context
                full_citations = self._extract_citations_from_text(full_text)
                
                # Merge and deduplicate citations
                citations = self._merge_citations(citations, full_citations)
                
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
            for match in re.finditer(pattern, text, re.IGNORECASE):
                start, end = match.span()
                citation_text = match.group(1) if match.groups() else match.group(0)
                
                # Extract surrounding context (±300 characters for better context)
                context_start = max(0, start - 300)
                context_end = min(len(text), end + 300)
                surrounding_text = text[context_start:context_end]
                
                # Better claim statement extraction
                claim_statement = self._extract_claim_statement(text, start, end)
                
                # Try to identify section
                section = self._identify_section(text, start)
                
                citations.append(CitationContext(
                    page_number=page_num,
                    section=section,
                    surrounding_text=surrounding_text,
                    claim_statement=claim_statement
                ))
        
        return citations
    
    def _extract_claim_statement(self, text: str, start: int, end: int) -> str:
        """Extract the claim statement containing the citation."""
        # Find sentence boundaries
        sentence_start = start
        sentence_end = end
        
        # Look backwards for sentence start
        for i in range(start - 1, max(0, start - 500), -1):
            if text[i] in '.!?':
                # Check if it's not an abbreviation
                if i + 1 < len(text) and text[i + 1].isspace():
                    sentence_start = i + 1
                    break
            elif text[i] in '\n\r' and i > 0 and text[i-1] in '\n\r':
                # Paragraph break
                sentence_start = i + 1
                break
        
        # Look forwards for sentence end
        for i in range(end, min(len(text), end + 500)):
            if text[i] in '.!?':
                # Check if it's not part of a URL or abbreviation
                if i + 1 >= len(text) or text[i + 1].isspace() or text[i + 1] in '\n\r':
                    sentence_end = i + 1
                    break
            elif text[i] in '\n\r' and i + 1 < len(text) and text[i + 1] in '\n\r':
                # Paragraph break
                sentence_end = i
                break
        
        claim = text[sentence_start:sentence_end].strip()
        return claim if len(claim) < 1000 else claim[:1000] + "..."
    
    def _identify_section(self, text: str, position: int) -> Optional[str]:
        """Identify which section the citation appears in."""
        # Look backwards for section headers
        section_patterns = [
            r'^\s*(ABSTRACT|INTRODUCTION|METHODS?|METHODOLOGY|RESULTS?|DISCUSSION|CONCLUSIONS?|ACKNOWLEDGMENTS?|REFERENCES?)\s*$',
            r'^\s*\d+\.?\s+(ABSTRACT|INTRODUCTION|METHODS?|METHODOLOGY|RESULTS?|DISCUSSION|CONCLUSIONS?|ACKNOWLEDGMENTS?|REFERENCES?)\s*$',
        ]
        
        lines = text[:position].split('\n')
        for line in reversed(lines[-20:]):  # Check last 20 lines
            for pattern in section_patterns:
                match = re.match(pattern, line.strip(), re.IGNORECASE)
                if match:
                    return match.group(1).upper()
        
        return None
    
    def _merge_citations(self, citations1: List[CitationContext], citations2: List[CitationContext]) -> List[CitationContext]:
        """Merge and deduplicate citations from different extractions."""
        merged = citations1.copy()
        
        for c2 in citations2:
            # Check if similar citation already exists
            is_duplicate = False
            for c1 in merged:
                if (c1.claim_statement and c2.claim_statement and 
                    abs(len(c1.claim_statement) - len(c2.claim_statement)) < 50 and
                    c1.claim_statement in c2.claim_statement or c2.claim_statement in c1.claim_statement):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                merged.append(c2)
        
        return merged
    
    def extract_paper_metadata(self, text: str) -> Tuple[str, List[str]]:
        """Extract paper title and authors from text."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Better title extraction
        title = ""
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            # Skip very short lines, headers, and obvious non-titles
            if (len(line) > 20 and 
                not re.match(r'^\s*(page|vol|volume|no|number|\d+)\s*$', line, re.IGNORECASE) and
                not re.match(r'^\s*\d+\s*$', line) and
                not line.isupper()):  # Avoid all-caps headers
                title = line
                break
        
        # Enhanced author extraction
        authors = []
        author_patterns = [
            # Standard format: "Smith, J.", "Jones, A.B.", etc.
            r'\b([A-Z][a-zA-Z]+,\s+[A-Z]\.(?:\s*[A-Z]\.)*)\b',
            # Full names: "John Smith", "Mary Jane Watson"
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b',
            # Institutional formats
            r'\b([A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+)\b',
        ]
        
        # Look in first 30 lines for authors
        for line in lines[:30]:
            # Skip lines that are clearly not author lines
            if (len(line) > 100 or 
                re.search(r'\b(abstract|introduction|keywords|copyright|doi|university|department|email)\b', line, re.IGNORECASE)):
                continue
                
            for pattern in author_patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    if len(match.split()) <= 4:  # Reasonable author name length
                        authors.append(match)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_authors = []
        for author in authors:
            if author.lower() not in seen:
                seen.add(author.lower())
                unique_authors.append(author)
        
        return title, unique_authors[:10]  # Limit to 10 authors


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
        
        # Enhanced DOI cleaning
        doi = entry.get('doi', '').strip()
        if doi:
            # Remove common prefixes and clean up
            doi = re.sub(r'^(doi:?|https?://(?:dx\.)?doi\.org/)', '', doi, flags=re.IGNORECASE)
            doi = doi.strip('/')
        
        return CitationMetadata(
            title=entry.get('title', '').strip('{}'),
            authors=authors,
            year=year,
            journal=entry.get('journal') or entry.get('booktitle'),
            volume=entry.get('volume'),
            pages=entry.get('pages'),
            doi=doi if doi else None,
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
        
        # Enhanced DOI cleaning
        doi = entry.get('DOI', '').strip()
        if doi:
            doi = re.sub(r'^(doi:?|https?://(?:dx\.)?doi\.org/)', '', doi, flags=re.IGNORECASE)
            doi = doi.strip('/')
        
        return CitationMetadata(
            title=entry.get('title'),
            authors=authors,
            year=year,
            journal=entry.get('container-title'),
            volume=entry.get('volume'),
            pages=entry.get('page'),
            doi=doi if doi else None,
            pmid=entry.get('PMID'),
            url=entry.get('URL')
        )


class TextExtractor:
    """Extract text and metadata from PDF documents."""
    
    def __init__(self):
        """Initialize the text extractor."""
        # Enhanced citation patterns for better coverage
        self.citation_patterns = [
            # Numbered citations: [1], [2,3], [1-5], [1,3-5,7]
            r'\[(\d+(?:[-,]\s*\d+)*)\]',
            
            # Author-year citations: (Smith, 2021), (Smith et al., 2021)
            r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?(?:,\s*\d{4})?(?:;\s*[A-Z][a-z]+(?:\s+et\s+al\.)?(?:,\s*\d{4})?)*)\)',
            
            # Inline author citations: Smith (2021), Smith et al. (2021)
            r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4}[a-z]?)\)',
            
            # Superscript citations: word^1, word^1,2
            r'\w+\^(\d+(?:,\d+)*)',
            
            # Nature style: word1, word2,3
            r'\w+(\d+(?:,\d+)*)',
            
            # Harvard/APA style with page numbers: (Smith, 2021, p. 15)
            r'\(([A-Z][a-z]+(?:\s+et\s+al\.)?),\s*(\d{4}[a-z]?),\s*(?:p\.?\s*\d+|pp\.?\s*\d+-\d+)\)',
            
            # Multiple authors with years: (Smith & Jones, 2021)
            r'\(([A-Z][a-z]+\s*&\s*[A-Z][a-z]+),\s*(\d{4}[a-z]?)\)',
            
            # Citation with specific format variations
            r'\(([A-Z][a-z]+(?:\s+[A-Z]\.)*(?:\s+et\s+al\.)?),?\s*(\d{4}[a-z]?)\)',
            
            # DOI patterns in text
            r'(?:doi:|DOI:)\s*(10\.\d+/[^\s]+)',
            
            # PMID patterns
            r'(?:PMID|pmid):\s*(\d+)',
            
            # arXiv patterns
            r'(?:arXiv:|arxiv:)\s*(\d{4}\.\d{4,5}(?:v\d+)?)',
        ]
        
        # Compile patterns for better performance
        self.compiled_patterns = [re.compile(pattern, re.MULTILINE | re.IGNORECASE) 
                                 for pattern in self.citation_patterns]
        
        # Enhanced reference section headers
        self.reference_headers = [
            r'(?:^|\n)\s*(?:REFERENCES?|BIBLIOGRAPHY|WORKS\s+CITED|LITERATURE\s+CITED|CITATIONS?)\s*(?:\n|$)',
            r'(?:^|\n)\s*\d+\.?\s*(?:REFERENCES?|BIBLIOGRAPHY)\s*(?:\n|$)',
            r'(?:^|\n)\s*(?:References|Bibliography|Works Cited|Literature Cited)\s*(?:\n|$)',
            r'(?:^|\n)\s*R\s*E\s*F\s*E\s*R\s*E\s*N\s*C\s*E\s*S\s*(?:\n|$)',  # Spaced letters
        ]
        
        self.compiled_ref_headers = [re.compile(pattern, re.MULTILINE | re.IGNORECASE) 
                                    for pattern in self.reference_headers]
    
    def extract_text_from_pdf(self, pdf_path: str, include_metadata: bool = True) -> Dict[str, Any]:
        """Extract text and metadata from PDF with enhanced analysis."""
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            pages_text = []
            metadata = {}
            
            # Extract text from all pages
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                pages_text.append(page_text)
                full_text += page_text + "\n"
            
            if include_metadata:
                # Extract document metadata
                metadata = doc.metadata
                
                # Try to extract title from first page if not in metadata
                if not metadata.get('title') and pages_text:
                    title = self._extract_title_from_text(pages_text[0])
                    if title:
                        metadata['title'] = title
                
                # Extract abstract
                abstract = self._extract_abstract(full_text)
                if abstract:
                    metadata['abstract'] = abstract
                
                # Extract authors from text if not in metadata
                if not metadata.get('author'):
                    authors = self._extract_authors_from_text(pages_text[0] if pages_text else "")
                    if authors:
                        metadata['authors'] = authors
            
            doc.close()
            
            # Analyze document structure
            structure_info = self._analyze_document_structure(full_text)
            
            return {
                'full_text': full_text,
                'pages_text': pages_text,
                'page_count': len(pages_text),
                'metadata': metadata,
                'structure': structure_info,
                'word_count': len(full_text.split()),
                'char_count': len(full_text)
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return {
                'full_text': "",
                'pages_text': [],
                'page_count': 0,
                'metadata': {},
                'structure': {},
                'word_count': 0,
                'char_count': 0
            }
    
    def _extract_title_from_text(self, first_page_text: str) -> Optional[str]:
        """Extract title from the first page text."""
        lines = first_page_text.split('\n')
        
        # Look for title in first few lines
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if (len(line) > 10 and 
                len(line) < 200 and 
                not line.lower().startswith(('abstract', 'introduction', 'keywords')) and
                not re.match(r'^\d+$', line) and  # Not just a number
                not re.match(r'^[A-Z\s]{3,}$', line)):  # Not all caps
                
                # Check if next few lines might be part of title
                title_parts = [line]
                for j in range(i+1, min(i+3, len(lines))):
                    next_line = lines[j].strip()
                    if (len(next_line) > 5 and 
                        not next_line.lower().startswith(('abstract', 'author', 'keyword'))):
                        title_parts.append(next_line)
                    else:
                        break
                
                potential_title = ' '.join(title_parts).strip()
                if 20 <= len(potential_title) <= 300:  # Reasonable title length
                    return potential_title
        
        return None
    
    def _extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract from document text."""
        # Pattern to find abstract section
        abstract_pattern = r'(?i)(?:^|\n)\s*ABSTRACT\s*(?:\n|:)\s*(.*?)(?=\n\s*(?:Keywords|Introduction|1\.|I\.|Background|\n\n))'
        
        match = re.search(abstract_pattern, text, re.DOTALL | re.MULTILINE)
        if match:
            abstract = match.group(1).strip()
            # Clean up the abstract
            abstract = re.sub(r'\s+', ' ', abstract)
            abstract = re.sub(r'\n+', ' ', abstract)
            
            if 50 <= len(abstract) <= 2000:  # Reasonable abstract length
                return abstract
        
        return None
    
    def _extract_authors_from_text(self, first_page_text: str) -> List[str]:
        """Extract authors from first page text."""
        authors = []
        
        # Common patterns for author names
        author_patterns = [
            r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # Full names
            r'([A-Z]\.\s*[A-Z][a-z]+)',  # Initial + Last name
            r'([A-Z][a-z]+,\s*[A-Z]\.)',  # Last, Initial
        ]
        
        lines = first_page_text.split('\n')[:15]  # Check first 15 lines
        
        for line in lines:
            line = line.strip()
            if len(line) > 5 and len(line) < 100:
                for pattern in author_patterns:
                    matches = re.findall(pattern, line)
                    for match in matches:
                        if match not in authors and len(match) > 3:
                            authors.append(match)
        
        # Filter out common false positives
        filtered_authors = []
        false_positives = {'Abstract', 'Introduction', 'Keywords', 'Article', 'Paper', 'Journal'}
        
        for author in authors:
            if not any(fp.lower() in author.lower() for fp in false_positives):
                filtered_authors.append(author)
        
        return filtered_authors[:10]  # Limit to reasonable number
    
    def _analyze_document_structure(self, text: str) -> Dict[str, Any]:
        """Analyze document structure to understand layout."""
        structure = {
            'has_abstract': bool(re.search(r'(?i)\babstract\b', text)),
            'has_introduction': bool(re.search(r'(?i)\bintroduction\b', text)),
            'has_conclusion': bool(re.search(r'(?i)\b(?:conclusion|summary)\b', text)),
            'has_references': bool(re.search(r'(?i)\breferences?\b', text)),
            'section_count': len(re.findall(r'(?i)^\s*(?:\d+\.|\d+\s+)[A-Z]', text, re.MULTILINE)),
            'figure_count': len(re.findall(r'(?i)\bfigure\s+\d+', text)),
            'table_count': len(re.findall(r'(?i)\btable\s+\d+', text)),
            'equation_count': len(re.findall(r'\(\d+\)', text)),
        }
        
        # Estimate document type
        if structure['has_abstract'] and structure['section_count'] > 3:
            structure['document_type'] = 'research_paper'
        elif structure['section_count'] > 10:
            structure['document_type'] = 'technical_document'
        else:
            structure['document_type'] = 'general_document'
        
        return structure
    
    def extract_citations_and_contexts(self, text: str, use_full_text: bool = True) -> Tuple[List[CitationMetadata], List[CitationContext]]:
        """Extract citations and their contexts with enhanced detection."""
        citations = []
        contexts = []
        
        # Choose text to analyze
        analysis_text = text if use_full_text else self._extract_abstract(text) or text[:5000]
        
        # Extract citations using all patterns
        citation_matches = []
        for i, pattern in enumerate(self.compiled_patterns):
            matches = pattern.finditer(analysis_text)
            for match in matches:
                citation_matches.append({
                    'pattern_id': i,
                    'match': match,
                    'text': match.group(0),
                    'groups': match.groups()
                })
        
        # Process unique citations
        seen_citations = set()
        
        for citation_match in citation_matches:
            citation_text = citation_match['text']
            if citation_text in seen_citations:
                continue
            
            seen_citations.add(citation_text)
            
            # Extract context around citation
            start = max(0, citation_match['match'].start() - 200)
            end = min(len(analysis_text), citation_match['match'].end() + 200)
            context_text = analysis_text[start:end]
            
            # Create citation context
            context = CitationContext(
                before_text=analysis_text[start:citation_match['match'].start()],
                citation_text=citation_text,
                after_text=analysis_text[citation_match['match'].end():end],
                full_sentence=self._extract_full_sentence(analysis_text, citation_match['match'].start()),
                claim_statement=self._extract_claim_statement(analysis_text, citation_match['match'].start())
            )
            contexts.append(context)
        
        # Extract references from reference section
        references = self._extract_references_enhanced(text)
        
        # Create citation metadata from references
        for ref in references:
            citation = self._parse_reference_to_metadata(ref)
            if citation:
                citations.append(citation)
        
        # Remove duplicates based on title similarity
        unique_citations = self._deduplicate_citations(citations)
        
        logger.info(f"Extracted {len(unique_citations)} unique citations from {len(contexts)} contexts")
        
        return unique_citations, contexts
    
    def _extract_references_enhanced(self, text: str) -> List[str]:
        """Extract references with enhanced pattern matching."""
        references = []
        
        # Find reference section
        ref_start = None
        for pattern in self.compiled_ref_headers:
            match = pattern.search(text)
            if match:
                ref_start = match.end()
                break
        
        if ref_start is None:
            logger.warning("No reference section found")
            return references
        
        # Extract references section
        ref_text = text[ref_start:]
        
        # Split into individual references using multiple strategies
        ref_candidates = []
        
        # Strategy 1: Numbered references
        numbered_refs = re.split(r'\n\s*\[?\d+\]?\.?\s+', ref_text)
        if len(numbered_refs) > 3:  # Likely numbered format
            ref_candidates.extend([ref.strip() for ref in numbered_refs[1:] if len(ref.strip()) > 20])
        
        # Strategy 2: Author-started references (new line with capital letter)
        author_refs = re.split(r'\n(?=[A-Z][a-z]+,?\s)', ref_text)
        if len(author_refs) > len(ref_candidates):  # Better split
            ref_candidates = [ref.strip() for ref in author_refs if len(ref.strip()) > 20]
        
        # Strategy 3: Double newline separation
        if not ref_candidates:
            double_newline_refs = re.split(r'\n\s*\n', ref_text)
            ref_candidates = [ref.strip() for ref in double_newline_refs if len(ref.strip()) > 20]
        
        # Clean and validate references
        for ref in ref_candidates[:100]:  # Limit to reasonable number
            cleaned_ref = self._clean_reference_text(ref)
            if self._is_valid_reference(cleaned_ref):
                references.append(cleaned_ref)
        
        logger.info(f"Found {len(references)} references in document")
        return references
    
    def _clean_reference_text(self, ref_text: str) -> str:
        """Clean reference text by removing common artifacts."""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', ref_text.strip())
        
        # Remove page numbers at the end (if they look like artifact)
        cleaned = re.sub(r'\s+\d+\s*$', '', cleaned)
        
        # Remove leading numbers or brackets
        cleaned = re.sub(r'^\[?\d+\]?\.\s*', '', cleaned)
        
        # Remove trailing periods if there are multiple
        cleaned = re.sub(r'\.+$', '.', cleaned)
        
        return cleaned
    
    def _is_valid_reference(self, ref_text: str) -> bool:
        """Check if text looks like a valid reference."""
        if len(ref_text) < 20 or len(ref_text) > 1000:
            return False
        
        # Should contain author-like pattern
        has_author = bool(re.search(r'[A-Z][a-z]+,?\s+[A-Z]\.?', ref_text))
        
        # Should contain year
        has_year = bool(re.search(r'\b(19|20)\d{2}\b', ref_text))
        
        # Should not be mostly numbers or special characters
        letter_ratio = len(re.findall(r'[a-zA-Z]', ref_text)) / len(ref_text)
        
        return has_author and has_year and letter_ratio > 0.5
    
    def _parse_reference_to_metadata(self, ref_text: str) -> Optional[CitationMetadata]:
        """Parse reference text into structured metadata with enhanced extraction."""
        try:
            metadata = CitationMetadata()
            
            # Extract DOI with multiple patterns
            doi_patterns = [
                r'(?:doi:|DOI:)?\s*(10\.\d+/[^\s,]+)',
                r'https?://(?:dx\.)?doi\.org/(10\.\d+/[^\s,]+)',
                r'DOI\s+(10\.\d+/[^\s,]+)',
            ]
            
            for pattern in doi_patterns:
                doi_match = re.search(pattern, ref_text, re.IGNORECASE)
                if doi_match:
                    metadata.doi = doi_match.group(1)
                    break
            
            # Extract PMID
            pmid_match = re.search(r'(?:PMID|pmid):\s*(\d+)', ref_text, re.IGNORECASE)
            if pmid_match:
                metadata.pmid = pmid_match.group(1)
            
            # Extract arXiv ID
            arxiv_match = re.search(r'(?:arXiv:|arxiv:)\s*(\d{4}\.\d{4,5}(?:v\d+)?)', ref_text, re.IGNORECASE)
            if arxiv_match:
                metadata.arxiv_id = arxiv_match.group(1)
            
            # Extract URL
            url_match = re.search(r'https?://[^\s,]+', ref_text)
            if url_match:
                metadata.url = url_match.group(0)
            
            # Enhanced title extraction
            title = self._extract_title_from_reference(ref_text)
            if title:
                metadata.title = title
            
            # Enhanced author extraction
            authors = self._extract_authors_from_reference(ref_text)
            if authors:
                metadata.authors = authors
            
            # Enhanced year extraction
            year = self._extract_year_from_reference(ref_text)
            if year:
                metadata.year = year
            
            # Enhanced journal extraction
            journal = self._extract_journal_from_reference(ref_text)
            if journal:
                metadata.journal = journal
            
            # Only return if we have at least title or DOI
            if metadata.title or metadata.doi:
                return metadata
            else:
                return None
                
        except Exception as e:
            logger.warning(f"Error parsing reference: {e}")
            return None
    
    def _extract_title_from_reference(self, ref_text: str) -> Optional[str]:
        """Extract title from reference with multiple strategies."""
        # Strategy 1: Title in quotes
        quoted_match = re.search(r'["""]([^"""]+)["""]', ref_text)
        if quoted_match:
            title = quoted_match.group(1).strip()
            if 10 <= len(title) <= 300:
                return title
        
        # Strategy 2: Title after authors and before journal/year
        # Pattern: Authors. Title. Journal
        author_title_pattern = r'([A-Z][a-z]+(?:,\s*[A-Z]\.?)+.*?)\.\s*([^.]+)\.\s*(?:[A-Z][a-z]+|\d{4})'
        match = re.search(author_title_pattern, ref_text)
        if match:
            potential_title = match.group(2).strip()
            if 10 <= len(potential_title) <= 300 and not re.match(r'^\d{4}', potential_title):
                return potential_title
        
        # Strategy 3: After year, before journal
        year_title_pattern = r'\b(19|20)\d{2}\b[^.]*\.\s*([^.]+)\.\s*[A-Z]'
        match = re.search(year_title_pattern, ref_text)
        if match:
            potential_title = match.group(2).strip()
            if 10 <= len(potential_title) <= 300:
                return potential_title
        
        return None
    
    def _extract_authors_from_reference(self, ref_text: str) -> List[str]:
        """Extract authors from reference with enhanced patterns."""
        authors = []
        
        # Common author patterns in references
        patterns = [
            r'([A-Z][a-z]+,\s*[A-Z]\.(?:\s*[A-Z]\.)*)',  # Last, F.M.
            r'([A-Z]\.\s*[A-Z]\.?\s*[A-Z][a-z]+)',      # F.M. Last
            r'([A-Z][a-z]+\s+[A-Z]\.[A-Z]?\.?)',        # Last F.M.
        ]
        
        # Split by common separators first
        author_text = ref_text.split('.')[0]  # Usually authors are before first period
        
        for pattern in patterns:
            matches = re.findall(pattern, author_text)
            for match in matches:
                if match not in authors and len(match) > 3:
                    authors.append(match.strip())
        
        # If no authors found, try simpler pattern
        if not authors:
            simple_pattern = r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            matches = re.findall(simple_pattern, author_text[:100])  # First 100 chars
            for match in matches[:3]:  # Max 3 authors
                if len(match) > 3 and not match.lower() in ['abstract', 'introduction']:
                    authors.append(match)
        
        return authors[:5]  # Limit to 5 authors
    
    def _extract_year_from_reference(self, ref_text: str) -> Optional[int]:
        """Extract year from reference."""
        year_pattern = r'\b(19\d{2}|20[0-2]\d)\b'
        matches = re.findall(year_pattern, ref_text)
        
        if matches:
            # Return the most reasonable year (prefer recent years)
            years = [int(year) for year in matches]
            reasonable_years = [year for year in years if 1950 <= year <= 2030]
            if reasonable_years:
                return max(reasonable_years)  # Most recent year
        
        return None
    
    def _extract_journal_from_reference(self, ref_text: str) -> Optional[str]:
        """Extract journal name from reference."""
        # Common patterns for journal names
        patterns = [
            r'\.\s*([A-Z][^.]+?)\s*,?\s*\d+',  # After period, before volume number
            r'\.\s*([A-Z][^.]+?)\s*\(\d{4}\)', # Before year in parentheses
            r'In\s+([A-Z][^.]+?)(?:\.|,|\d)',   # After "In"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, ref_text)
            if match:
                journal = match.group(1).strip()
                # Clean journal name
                journal = re.sub(r'\s+', ' ', journal)
                if 3 <= len(journal) <= 100 and not re.match(r'^\d+', journal):
                    return journal
        
        return None
    
    def _deduplicate_citations(self, citations: List[CitationMetadata]) -> List[CitationMetadata]:
        """Remove duplicate citations based on title similarity."""
        if not citations:
            return citations
        
        unique_citations = []
        
        for citation in citations:
            is_duplicate = False
            
            for existing in unique_citations:
                # Check DOI match
                if (citation.doi and existing.doi and 
                    citation.doi.lower() == existing.doi.lower()):
                    is_duplicate = True
                    break
                
                # Check title similarity
                if citation.title and existing.title:
                    similarity = fuzz.ratio(citation.title.lower(), existing.title.lower())
                    if similarity > 85:  # 85% similarity threshold
                        is_duplicate = True
                        # Keep the citation with more metadata
                        if (len(str(citation.authors or [])) + len(str(citation.journal or '')) > 
                            len(str(existing.authors or [])) + len(str(existing.journal or ''))):
                            # Replace existing with more complete citation
                            idx = unique_citations.index(existing)
                            unique_citations[idx] = citation
                        break
            
            if not is_duplicate:
                unique_citations.append(citation)
        
        return unique_citations
    
    def _extract_full_sentence(self, text: str, position: int) -> str:
        """Extract the full sentence containing the citation."""
        # Find sentence boundaries
        sentence_start = position
        sentence_end = position
        
        # Find start of sentence
        while sentence_start > 0 and text[sentence_start] not in '.!?':
            sentence_start -= 1
        if sentence_start > 0:
            sentence_start += 1
        
        # Find end of sentence
        while sentence_end < len(text) and text[sentence_end] not in '.!?':
            sentence_end += 1
        if sentence_end < len(text):
            sentence_end += 1
        
        sentence = text[sentence_start:sentence_end].strip()
        return sentence
    
    def _extract_claim_statement(self, text: str, position: int) -> str:
        """Extract the claim statement that the citation supports."""
        # Extract a broader context that includes the claim
        start = max(0, position - 500)
        end = min(len(text), position + 100)
        
        context = text[start:end]
        
        # Find the sentence with the strongest claim indicators
        sentences = re.split(r'[.!?]+', context)
        
        claim_indicators = [
            'show', 'demonstrate', 'prove', 'indicate', 'suggest', 'reveal',
            'confirm', 'establish', 'conclude', 'find', 'report', 'observe'
        ]
        
        best_sentence = ""
        max_score = 0
        
        for sentence in sentences:
            if len(sentence.strip()) < 10:
                continue
                
            score = sum(1 for indicator in claim_indicators 
                       if indicator in sentence.lower())
            
            if score > max_score:
                max_score = score
                best_sentence = sentence.strip()
        
        return best_sentence or context.strip()[:200] 