"""
Main auditor class that orchestrates the citation auditing process.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from tqdm import tqdm

from .models import CitationMetadata, CitationContext, CitationAudit, PaperAuditReport, CitationStatus
from .extractors import TextExtractor
from .lookup import CitationLookup
from .evaluator import RelevanceEvaluator
from .llm_evaluator import create_evaluator, LLMEvaluator

logger = logging.getLogger(__name__)


class PaperAuditor:
    """Main class for auditing research paper references."""
    
    def __init__(self, use_fallback_lookups: bool = True, use_advanced_nlp: bool = True):
        """Initialize the auditor with specified LLM model."""
        self.extractor = TextExtractor()
        self.lookup = CitationLookup()
        self.evaluator = RelevanceEvaluator(use_advanced_nlp=use_advanced_nlp)
        self.use_fallback_lookups = use_fallback_lookups
        
        logger.info("PaperAuditor initialized with enhanced extraction and lookup capabilities")
    
    def audit_paper(
        self, 
        pdf_path: str, 
        output_format: str = "json",
        use_full_text: bool = True,
        compare_full_vs_abstract: bool = False
    ) -> Dict[str, Any]:
        """
        Audit a paper's citations with enhanced analysis.
        
        Args:
            pdf_path: Path to the PDF file
            output_format: Format for output ("json", "text", "html")
            use_full_text: Whether to use full text for analysis
            compare_full_vs_abstract: Whether to compare full-text vs abstract performance
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")
            
            logger.info(f"Starting enhanced audit of {pdf_path}")
            
            # Step 1: Extract text and metadata with enhanced extraction
            document_data = self.extractor.extract_text_from_pdf(str(pdf_path))
            
            paper_title = self._extract_paper_title(document_data)
            paper_content = document_data['full_text']
            
            if not paper_content:
                logger.error("No text could be extracted from the PDF")
                return {
                    'error': 'Failed to extract text from PDF',
                    'document_info': document_data
                }
            
            logger.info(f"Extracted {document_data['word_count']} words from {document_data['page_count']} pages")
            
            # Step 2: Extract citations and contexts with enhanced detection
            citations, contexts = self.extractor.extract_citations_and_contexts(
                paper_content, use_full_text=use_full_text
            )
            
            logger.info(f"Found {len(citations)} citations and {len(contexts)} contexts")
            
            # Step 3: Audit citations with enhanced lookup
            audited_citations = self._audit_citations_enhanced(
                citations, contexts, paper_title, paper_content, use_full_text
            )
            
            # Step 4: Generate analysis report
            analysis_report = self._generate_analysis_report(
                audited_citations, document_data, use_full_text
            )
            
            # Step 5: Compare full-text vs abstract performance if requested
            comparison_results = None
            if compare_full_vs_abstract and len(citations) > 0:
                logger.info("Comparing full-text vs abstract performance...")
                comparison_results = self.evaluator.compare_full_text_vs_abstract_performance(
                    paper_title, paper_content, citations
                )
            
            # Step 6: Compile final results
            results = {
                'document_info': {
                    'filename': pdf_path.name,
                    'page_count': document_data['page_count'],
                    'word_count': document_data['word_count'],
                    'structure': document_data['structure'],
                    'extracted_metadata': document_data['metadata']
                },
                'paper_title': paper_title,
                'citations_found': len(citations),
                'contexts_found': len(contexts),
                'audited_citations': audited_citations,
                'analysis_report': analysis_report,
                'processing_info': {
                    'use_full_text': use_full_text,
                    'fallback_lookups_enabled': self.use_fallback_lookups,
                    'advanced_nlp_enabled': self.evaluator.use_advanced_nlp
                }
            }
            
            if comparison_results:
                results['full_text_vs_abstract_comparison'] = comparison_results
            
            logger.info(f"Audit completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error during paper audit: {e}")
            return {
                'error': str(e),
                'document_info': {},
                'citations_found': 0,
                'audited_citations': []
            }
    
    def _extract_paper_title(self, document_data: Dict[str, Any]) -> str:
        """Extract paper title from document data."""
        # Try metadata first
        if document_data['metadata'].get('title'):
            return document_data['metadata']['title']
        
        # Try to extract from first page
        if document_data['pages_text']:
            first_page = document_data['pages_text'][0]
            lines = first_page.split('\n')[:10]  # Check first 10 lines
            for line in lines:
                line = line.strip()
                if (20 <= len(line) <= 200 and 
                    not line.lower().startswith(('abstract', 'introduction', 'keywords'))):
                    return line
        
        # Fallback to filename
        return "Unknown Title"
    
    def _audit_citations_enhanced(
        self, 
        citations: List[CitationMetadata],
        contexts: List[CitationContext],
        paper_title: str,
        paper_content: str,
        use_full_text: bool
    ) -> List[CitationAudit]:
        """Audit citations with enhanced lookup and evaluation."""
        audited_citations = []
        
        # Create a mapping of citations to contexts (simplified for this example)
        citation_context_map = {}
        for i, context in enumerate(contexts):
            citation_context_map[i] = context
        
        for i, citation in enumerate(tqdm(citations, desc="Auditing citations")):
            audit = CitationAudit(
                citation_key=f"citation_{i+1}",
                original_text=citation.title or f"Citation {i+1}",
                metadata=citation,
                contexts=[citation_context_map.get(i)] if i in citation_context_map else []
            )
            
            # Step 1: Enhanced online lookup
            lookup_result = self.lookup.lookup_citation(
                citation, 
                enable_fallbacks=self.use_fallback_lookups
            )
            
            audit.exists_online = lookup_result['found']
            audit.existence_details = lookup_result.get('details', {})
            audit.source_database = lookup_result.get('source')
            
            # Update metadata with found information
            if lookup_result['found'] and lookup_result['metadata']:
                # Merge found metadata with original
                found_metadata = lookup_result['metadata']
                audit.metadata = self._merge_citation_metadata(citation, found_metadata)
                
                # Check if full text is available
                audit.full_text_available = lookup_result.get('full_text_available', False)
            
            # Step 2: Enhanced relevance evaluation
            if audit.exists_online and audit.metadata:
                try:
                    # Prepare context sentences for evaluation
                    context_sentences = []
                    for context in audit.contexts:
                        if context:
                            context_sentences.extend([
                                context.full_sentence,
                                context.claim_statement
                            ])
                    
                    # Evaluate relevance
                    audit.relevance = self.evaluator.evaluate_relevance(
                        paper_title, 
                        paper_content, 
                        audit.metadata,
                        use_full_text=use_full_text,
                        context_sentences=context_sentences
                    )
                    
                except Exception as e:
                    logger.warning(f"Relevance evaluation failed for {citation.title}: {e}")
                    audit.relevance = RelevanceScore(
                        overall_score=0.5,
                        title_similarity=0.0,
                        content_similarity=0.0,
                        keyword_overlap=0.0,
                        context_relevance=0.0,
                        semantic_similarity=0.0,
                        details={'error': str(e)}
                    )
            
            audited_citations.append(audit)
        
        return audited_citations
    
    def _merge_citation_metadata(
        self, 
        original: CitationMetadata, 
        found: CitationMetadata
    ) -> CitationMetadata:
        """Merge original citation metadata with found metadata, preferring found data."""
        merged = CitationMetadata()
        
        # Use found data if available, otherwise use original
        merged.title = found.title or original.title
        merged.authors = found.authors or original.authors
        merged.year = found.year or original.year
        merged.journal = found.journal or original.journal
        merged.doi = found.doi or original.doi
        merged.pmid = found.pmid or original.pmid
        merged.arxiv_id = found.arxiv_id or original.arxiv_id
        merged.url = found.url or original.url
        merged.abstract = found.abstract or original.abstract
        
        return merged
    
    def _generate_analysis_report(
        self, 
        audited_citations: List[CitationAudit],
        document_data: Dict[str, Any],
        use_full_text: bool
    ) -> Dict[str, Any]:
        """Generate comprehensive analysis report."""
        if not audited_citations:
            return {
                'total_citations': 0,
                'online_availability': 0.0,
                'average_relevance': 0.0,
                'summary': "No citations found for analysis"
            }
        
        # Basic statistics
        total_citations = len(audited_citations)
        online_citations = sum(1 for audit in audited_citations if audit.exists_online)
        
        # Relevance statistics
        relevance_scores = [
            audit.relevance.overall_score for audit in audited_citations 
            if audit.relevance and audit.relevance.overall_score is not None
        ]
        
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
        
        # Source distribution
        source_distribution = {}
        for audit in audited_citations:
            if audit.source_database:
                source_distribution[audit.source_database] = source_distribution.get(audit.source_database, 0) + 1
        
        # Full text availability
        full_text_available = sum(1 for audit in audited_citations if audit.full_text_available)
        
        # Quality assessment
        high_quality_citations = sum(
            1 for audit in audited_citations 
            if (audit.relevance and audit.relevance.overall_score and 
                audit.relevance.overall_score > 0.7)
        )
        
        # Coverage analysis
        coverage_analysis = {
            'citation_detection_rate': f"{total_citations} citations found",
            'online_availability_rate': f"{online_citations}/{total_citations} ({online_citations/total_citations*100:.1f}%)" if total_citations > 0 else "0%",
            'average_relevance_score': f"{avg_relevance:.3f}",
            'high_quality_citations': f"{high_quality_citations}/{total_citations} ({high_quality_citations/total_citations*100:.1f}%)" if total_citations > 0 else "0%",
            'full_text_available': f"{full_text_available}/{total_citations} ({full_text_available/total_citations*100:.1f}%)" if total_citations > 0 else "0%"
        }
        
        # Document analysis
        document_analysis = {
            'document_type': document_data['structure'].get('document_type', 'unknown'),
            'has_abstract': document_data['structure'].get('has_abstract', False),
            'has_references': document_data['structure'].get('has_references', False),
            'analysis_mode': 'full_text' if use_full_text else 'abstract_only',
            'content_completeness': document_data['structure'].get('estimated_completeness', 0.0)
        }
        
        return {
            'total_citations': total_citations,
            'online_availability': online_citations / total_citations if total_citations > 0 else 0.0,
            'average_relevance': avg_relevance,
            'source_distribution': source_distribution,
            'coverage_analysis': coverage_analysis,
            'document_analysis': document_analysis,
            'quality_metrics': {
                'high_quality_citations': high_quality_citations,
                'full_text_available': full_text_available,
                'avg_title_similarity': sum(
                    audit.relevance.title_similarity for audit in audited_citations
                    if audit.relevance and audit.relevance.title_similarity is not None
                ) / len(audited_citations) if audited_citations else 0.0,
                'avg_content_similarity': sum(
                    audit.relevance.content_similarity for audit in audited_citations
                    if audit.relevance and audit.relevance.content_similarity is not None
                ) / len(audited_citations) if audited_citations else 0.0
            },
            'summary': self._generate_summary(total_citations, online_citations, avg_relevance, use_full_text)
        }
    
    def _generate_summary(
        self, 
        total_citations: int, 
        online_citations: int, 
        avg_relevance: float,
        use_full_text: bool
    ) -> str:
        """Generate a summary of the analysis."""
        if total_citations == 0:
            return "No citations were found in the document."
        
        availability_rate = online_citations / total_citations * 100
        analysis_mode = "full text" if use_full_text else "abstract"
        
        summary_parts = []
        
        summary_parts.append(f"Found {total_citations} citations in the document.")
        
        if availability_rate >= 90:
            summary_parts.append(f"Excellent online availability: {online_citations}/{total_citations} ({availability_rate:.1f}%) citations found online.")
        elif availability_rate >= 70:
            summary_parts.append(f"Good online availability: {online_citations}/{total_citations} ({availability_rate:.1f}%) citations found online.")
        elif availability_rate >= 50:
            summary_parts.append(f"Moderate online availability: {online_citations}/{total_citations} ({availability_rate:.1f}%) citations found online.")
        else:
            summary_parts.append(f"Low online availability: {online_citations}/{total_citations} ({availability_rate:.1f}%) citations found online.")
        
        if avg_relevance >= 0.8:
            summary_parts.append(f"High relevance quality: average relevance score of {avg_relevance:.3f}.")
        elif avg_relevance >= 0.6:
            summary_parts.append(f"Good relevance quality: average relevance score of {avg_relevance:.3f}.")
        elif avg_relevance >= 0.4:
            summary_parts.append(f"Moderate relevance quality: average relevance score of {avg_relevance:.3f}.")
        else:
            summary_parts.append(f"Low relevance quality: average relevance score of {avg_relevance:.3f}.")
        
        summary_parts.append(f"Analysis performed using {analysis_mode}.")
        
        return " ".join(summary_parts)
    
    def batch_audit_papers(
        self, 
        pdf_directory: str, 
        output_directory: str = None,
        use_full_text: bool = True,
        compare_modes: bool = False
    ) -> Dict[str, Any]:
        """Audit multiple papers in a directory."""
        pdf_dir = Path(pdf_directory)
        if not pdf_dir.exists():
            raise FileNotFoundError(f"Directory not found: {pdf_dir}")
        
        pdf_files = list(pdf_dir.glob("*.pdf"))
        if not pdf_files:
            logger.warning(f"No PDF files found in {pdf_dir}")
            return {'processed_files': 0, 'results': []}
        
        results = []
        batch_stats = {
            'total_files': len(pdf_files),
            'processed_files': 0,
            'failed_files': 0,
            'total_citations': 0,
            'total_online_citations': 0,
            'processing_errors': []
        }
        
        for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
            try:
                logger.info(f"Processing {pdf_file.name}")
                
                result = self.audit_paper(
                    str(pdf_file), 
                    use_full_text=use_full_text,
                    compare_full_vs_abstract=compare_modes
                )
                
                if 'error' not in result:
                    batch_stats['processed_files'] += 1
                    batch_stats['total_citations'] += result['citations_found']
                    batch_stats['total_online_citations'] += sum(
                        1 for audit in result['audited_citations'] if audit.exists_online
                    )
                else:
                    batch_stats['failed_files'] += 1
                    batch_stats['processing_errors'].append({
                        'file': pdf_file.name,
                        'error': result['error']
                    })
                
                results.append({
                    'filename': pdf_file.name,
                    'result': result
                })
                
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
                batch_stats['failed_files'] += 1
                batch_stats['processing_errors'].append({
                    'file': pdf_file.name,
                    'error': str(e)
                })
        
        # Calculate overall statistics
        if batch_stats['total_citations'] > 0:
            batch_stats['overall_availability_rate'] = (
                batch_stats['total_online_citations'] / batch_stats['total_citations']
            )
        else:
            batch_stats['overall_availability_rate'] = 0.0
        
        return {
            'batch_statistics': batch_stats,
            'individual_results': results
        } 