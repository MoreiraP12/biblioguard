"""
Citation relevance evaluation using content analysis.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher
from collections import Counter

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    ADVANCED_NLP_AVAILABLE = True
except ImportError:
    ADVANCED_NLP_AVAILABLE = False

from .models import CitationMetadata, RelevanceScore

logger = logging.getLogger(__name__)

class RelevanceEvaluator:
    """Evaluate citation relevance using multiple methods."""
    
    def __init__(self, use_advanced_nlp: bool = None):
        """Initialize evaluator with optional advanced NLP models."""
        if use_advanced_nlp is None:
            use_advanced_nlp = ADVANCED_NLP_AVAILABLE
        
        self.use_advanced_nlp = use_advanced_nlp and ADVANCED_NLP_AVAILABLE
        
        if self.use_advanced_nlp:
            try:
                # Load a lightweight sentence transformer model
                self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Advanced NLP models loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load advanced NLP models: {e}")
                self.use_advanced_nlp = False
                self.sentence_model = None
        else:
            self.sentence_model = None
        
        # Keywords that indicate research relevance
        self.relevance_keywords = {
            'method': ['method', 'approach', 'technique', 'algorithm', 'procedure', 'framework'],
            'result': ['result', 'finding', 'outcome', 'conclusion', 'evidence', 'data'],
            'comparison': ['compare', 'comparison', 'versus', 'vs', 'similar', 'different'],
            'theory': ['theory', 'model', 'hypothesis', 'concept', 'principle'],
            'application': ['application', 'implementation', 'use', 'applied', 'practice'],
            'analysis': ['analysis', 'study', 'investigation', 'examination', 'evaluation']
        }
    
    def evaluate_relevance(
        self, 
        paper_title: str, 
        paper_content: str, 
        citation_metadata: CitationMetadata,
        use_full_text: bool = True,
        context_sentences: List[str] = None
    ) -> RelevanceScore:
        """
        Evaluate citation relevance with enhanced analysis.
        
        Args:
            paper_title: Title of the paper being analyzed
            paper_content: Full text or abstract of the paper
            citation_metadata: Metadata of the cited paper
            use_full_text: Whether to use full text or just abstract
            context_sentences: Sentences where citations appear
        """
        try:
            # Prepare content for analysis
            analysis_content = self._prepare_content_for_analysis(
                paper_content, use_full_text
            )
            
            # Calculate multiple relevance scores
            scores = self._calculate_relevance_scores(
                paper_title, 
                analysis_content, 
                citation_metadata,
                context_sentences or []
            )
            
            # Determine content type analysis
            content_analysis = self._analyze_content_type(
                analysis_content, use_full_text
            )
            
            # Calculate final relevance score
            final_score = self._combine_relevance_scores(scores)
            
            return RelevanceScore(
                overall_score=final_score,
                title_similarity=scores.get('title_similarity', 0.0),
                content_similarity=scores.get('content_similarity', 0.0),
                keyword_overlap=scores.get('keyword_overlap', 0.0),
                context_relevance=scores.get('context_relevance', 0.0),
                semantic_similarity=scores.get('semantic_similarity', 0.0),
                details={
                    'content_analysis': content_analysis,
                    'use_full_text': use_full_text,
                    'citation_title': citation_metadata.title,
                    'citation_abstract': citation_metadata.abstract,
                    'all_scores': scores
                }
            )
            
        except Exception as e:
            logger.error(f"Error evaluating relevance: {e}")
            return RelevanceScore(
                overall_score=0.5,  # Default neutral score
                title_similarity=0.0,
                content_similarity=0.0,
                keyword_overlap=0.0,
                context_relevance=0.0,
                semantic_similarity=0.0,
                details={'error': str(e)}
            )
    
    def _prepare_content_for_analysis(self, content: str, use_full_text: bool) -> str:
        """Prepare content for analysis based on full-text vs abstract preference."""
        if not use_full_text:
            # Extract abstract if available
            abstract = self._extract_abstract_from_content(content)
            if abstract:
                return abstract
            else:
                # Fall back to first 1000 words if no abstract found
                words = content.split()
                return ' '.join(words[:1000])
        else:
            # Use full text but clean it
            return self._clean_content_for_analysis(content)
    
    def _extract_abstract_from_content(self, content: str) -> Optional[str]:
        """Extract abstract from full content."""
        # Look for abstract section
        abstract_patterns = [
            r'(?i)(?:^|\n)\s*ABSTRACT\s*(?:\n|:)\s*(.*?)(?=\n\s*(?:Keywords|Introduction|1\.|I\.|Background|\n\n))',
            r'(?i)(?:^|\n)\s*Abstract\s*(?:\n|:)\s*(.*?)(?=\n\s*(?:Keywords|Introduction|1\.|I\.|Background|\n\n))',
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, content, re.DOTALL | re.MULTILINE)
            if match:
                abstract = match.group(1).strip()
                # Clean up the abstract
                abstract = re.sub(r'\s+', ' ', abstract)
                abstract = re.sub(r'\n+', ' ', abstract)
                
                if 50 <= len(abstract) <= 2000:  # Reasonable abstract length
                    return abstract
        
        return None
    
    def _clean_content_for_analysis(self, content: str) -> str:
        """Clean content for better analysis."""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', content)
        
        # Remove page numbers and headers/footers (common artifacts)
        cleaned = re.sub(r'\n\s*\d+\s*\n', '\n', cleaned)
        
        # Remove very short lines (likely artifacts)
        lines = cleaned.split('\n')
        filtered_lines = [line for line in lines if len(line.strip()) > 10]
        
        return '\n'.join(filtered_lines)
    
    def _analyze_content_type(self, content: str, use_full_text: bool) -> Dict[str, Any]:
        """Analyze the type and characteristics of content being used."""
        word_count = len(content.split())
        char_count = len(content)
        
        # Estimate content type
        if word_count < 500:
            content_type = 'abstract_or_excerpt'
        elif word_count < 2000:
            content_type = 'extended_abstract'
        else:
            content_type = 'full_text'
        
        # Check for research paper indicators
        has_methodology = bool(re.search(r'(?i)\b(?:method|methodology|approach)\b', content))
        has_results = bool(re.search(r'(?i)\b(?:result|finding|conclusion)\b', content))
        has_references = bool(re.search(r'(?i)\breferences?\b', content))
        
        return {
            'word_count': word_count,
            'char_count': char_count,
            'content_type': content_type,
            'use_full_text_requested': use_full_text,
            'has_methodology': has_methodology,
            'has_results': has_results,
            'has_references': has_references,
            'estimated_completeness': min(1.0, word_count / 5000) if use_full_text else min(1.0, word_count / 300)
        }
    
    def _calculate_relevance_scores(
        self, 
        paper_title: str, 
        paper_content: str, 
        citation_metadata: CitationMetadata,
        context_sentences: List[str]
    ) -> Dict[str, float]:
        """Calculate multiple relevance scores."""
        scores = {}
        
        # 1. Title similarity
        if paper_title and citation_metadata.title:
            scores['title_similarity'] = self._calculate_text_similarity(
                paper_title, citation_metadata.title
            )
        else:
            scores['title_similarity'] = 0.0
        
        # 2. Content similarity (against abstract if available, else title)
        citation_content = citation_metadata.abstract or citation_metadata.title or ""
        if paper_content and citation_content:
            scores['content_similarity'] = self._calculate_text_similarity(
                paper_content[:2000],  # Use first 2000 chars to avoid overwhelming
                citation_content
            )
        else:
            scores['content_similarity'] = 0.0
        
        # 3. Keyword overlap
        scores['keyword_overlap'] = self._calculate_keyword_overlap(
            paper_content, citation_content
        )
        
        # 4. Context relevance (if context sentences provided)
        if context_sentences:
            scores['context_relevance'] = self._calculate_context_relevance(
                context_sentences, citation_content
            )
        else:
            scores['context_relevance'] = 0.0
        
        # 5. Semantic similarity (if advanced NLP available)
        if self.use_advanced_nlp:
            scores['semantic_similarity'] = self._calculate_semantic_similarity(
                paper_content, citation_content
            )
        else:
            scores['semantic_similarity'] = 0.0
        
        # 6. Field/domain relevance
        scores['domain_relevance'] = self._calculate_domain_relevance(
            paper_content, citation_metadata
        )
        
        # 7. Citation context quality
        scores['citation_quality'] = self._assess_citation_quality(
            context_sentences, citation_metadata
        )
        
        return scores
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using multiple methods."""
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        def normalize_text(text):
            # Convert to lowercase and remove extra whitespace
            normalized = re.sub(r'[^\w\s]', ' ', text.lower())
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            return normalized
        
        norm_text1 = normalize_text(text1)
        norm_text2 = normalize_text(text2)
        
        # SequenceMatcher similarity
        seq_similarity = SequenceMatcher(None, norm_text1, norm_text2).ratio()
        
        # Word-level Jaccard similarity
        words1 = set(norm_text1.split())
        words2 = set(norm_text2.split())
        
        if words1 and words2:
            jaccard_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
        else:
            jaccard_similarity = 0.0
        
        # Combined similarity (weighted average)
        combined_similarity = (seq_similarity * 0.4 + jaccard_similarity * 0.6)
        
        return combined_similarity
    
    def _calculate_keyword_overlap(self, text1: str, text2: str) -> float:
        """Calculate keyword overlap focusing on research-relevant terms."""
        if not text1 or not text2:
            return 0.0
        
        # Extract keywords from both texts
        keywords1 = self._extract_research_keywords(text1)
        keywords2 = self._extract_research_keywords(text2)
        
        if not keywords1 or not keywords2:
            return 0.0
        
        # Calculate overlap
        overlap = len(keywords1.intersection(keywords2))
        total_unique = len(keywords1.union(keywords2))
        
        return overlap / total_unique if total_unique > 0 else 0.0
    
    def _extract_research_keywords(self, text: str) -> set:
        """Extract research-relevant keywords from text."""
        keywords = set()
        
        # Normalize text
        normalized = re.sub(r'[^\w\s]', ' ', text.lower())
        words = normalized.split()
        
        # Extract multi-word phrases and important single words
        for i, word in enumerate(words):
            # Single important words (longer than 4 chars, not common words)
            if (len(word) > 4 and 
                word not in {'paper', 'study', 'research', 'analysis', 'using', 'based', 'approach'}):
                keywords.add(word)
            
            # Bigrams
            if i < len(words) - 1:
                bigram = f"{word} {words[i+1]}"
                if any(category_words for category_words in self.relevance_keywords.values() 
                      if any(kw in bigram for kw in category_words)):
                    keywords.add(bigram)
        
        # Add specific domain keywords
        for category, category_keywords in self.relevance_keywords.items():
            for keyword in category_keywords:
                if keyword in normalized:
                    keywords.add(keyword)
        
        return keywords
    
    def _calculate_context_relevance(self, context_sentences: List[str], citation_content: str) -> float:
        """Calculate how relevant the citation is based on its usage context."""
        if not context_sentences or not citation_content:
            return 0.0
        
        total_relevance = 0.0
        
        for sentence in context_sentences:
            # Check for strong citation indicators
            strong_indicators = [
                'show', 'demonstrate', 'prove', 'establish', 'confirm',
                'according to', 'as shown by', 'consistent with',
                'similar to', 'based on', 'following'
            ]
            
            weak_indicators = [
                'see', 'also', 'however', 'although', 'but'
            ]
            
            sentence_lower = sentence.lower()
            
            # Calculate relevance score for this sentence
            sentence_score = 0.5  # Base score
            
            # Boost for strong indicators
            for indicator in strong_indicators:
                if indicator in sentence_lower:
                    sentence_score += 0.2
            
            # Reduce for weak indicators
            for indicator in weak_indicators:
                if indicator in sentence_lower:
                    sentence_score -= 0.1
            
            # Boost for content similarity
            if citation_content:
                content_sim = self._calculate_text_similarity(sentence, citation_content[:200])
                sentence_score += content_sim * 0.3
            
            total_relevance += min(1.0, max(0.0, sentence_score))
        
        return total_relevance / len(context_sentences)
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity using sentence transformers."""
        if not self.use_advanced_nlp or not text1 or not text2:
            return 0.0
        
        try:
            # Truncate texts to reasonable length
            text1_truncated = text1[:1000] if len(text1) > 1000 else text1
            text2_truncated = text2[:1000] if len(text2) > 1000 else text2
            
            # Get embeddings
            embeddings = self.sentence_model.encode([text1_truncated, text2_truncated])
            
            # Calculate cosine similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            # Ensure similarity is between 0 and 1
            return max(0.0, min(1.0, float(similarity)))
            
        except Exception as e:
            logger.warning(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def _calculate_domain_relevance(self, paper_content: str, citation_metadata: CitationMetadata) -> float:
        """Calculate domain/field relevance between papers."""
        relevance_score = 0.0
        
        # Check journal similarity
        if citation_metadata.journal:
            journal_keywords = self._extract_research_keywords(citation_metadata.journal)
            paper_keywords = self._extract_research_keywords(paper_content[:1000])
            
            if journal_keywords and paper_keywords:
                journal_overlap = len(journal_keywords.intersection(paper_keywords))
                journal_total = len(journal_keywords.union(paper_keywords))
                relevance_score += (journal_overlap / journal_total) * 0.3 if journal_total > 0 else 0.0
        
        # Check author overlap (same field often has overlapping authors)
        if citation_metadata.authors:
            # This is a simplified check - in reality, you'd want author disambiguation
            paper_authors = self._extract_potential_authors(paper_content[:500])
            cited_authors = set(citation_metadata.authors)
            
            if paper_authors and cited_authors:
                author_surnames = set()
                for author in cited_authors:
                    if ',' in author:
                        surname = author.split(',')[0].strip().lower()
                        author_surnames.add(surname)
                
                paper_surnames = set()
                for author in paper_authors:
                    if ',' in author:
                        surname = author.split(',')[0].strip().lower()
                        paper_surnames.add(surname)
                    else:
                        # Try to get last word as surname
                        words = author.strip().split()
                        if words:
                            paper_surnames.add(words[-1].lower())
                
                if author_surnames and paper_surnames:
                    author_overlap = len(author_surnames.intersection(paper_surnames))
                    if author_overlap > 0:
                        relevance_score += 0.4  # Strong indicator of same field
        
        # Check methodological similarity
        method_keywords = ['method', 'approach', 'technique', 'algorithm', 'framework', 'model']
        paper_methods = set()
        citation_methods = set()
        
        for keyword in method_keywords:
            if keyword in paper_content.lower():
                paper_methods.add(keyword)
            if citation_metadata.title and keyword in citation_metadata.title.lower():
                citation_methods.add(keyword)
            if citation_metadata.abstract and keyword in citation_metadata.abstract.lower():
                citation_methods.add(keyword)
        
        if paper_methods and citation_methods:
            method_overlap = len(paper_methods.intersection(citation_methods))
            method_total = len(paper_methods.union(citation_methods))
            relevance_score += (method_overlap / method_total) * 0.3 if method_total > 0 else 0.0
        
        return min(1.0, relevance_score)
    
    def _extract_potential_authors(self, text: str) -> List[str]:
        """Extract potential author names from text."""
        # Simple pattern matching for author-like names
        author_patterns = [
            r'([A-Z][a-z]+,\s*[A-Z]\.)',  # Last, F.
            r'([A-Z][a-z]+\s+[A-Z][a-z]+)',  # First Last
        ]
        
        authors = []
        for pattern in author_patterns:
            matches = re.findall(pattern, text)
            authors.extend(matches)
        
        return authors[:10]  # Limit to reasonable number
    
    def _assess_citation_quality(self, context_sentences: List[str], citation_metadata: CitationMetadata) -> float:
        """Assess the quality of the citation based on context and metadata completeness."""
        quality_score = 0.0
        
        # Metadata completeness (0.4 weight)
        metadata_score = 0.0
        if citation_metadata.title:
            metadata_score += 0.3
        if citation_metadata.authors:
            metadata_score += 0.2
        if citation_metadata.year:
            metadata_score += 0.1
        if citation_metadata.journal:
            metadata_score += 0.2
        if citation_metadata.doi:
            metadata_score += 0.2
        
        quality_score += metadata_score * 0.4
        
        # Context quality (0.6 weight)
        if context_sentences:
            context_quality = 0.0
            for sentence in context_sentences:
                sentence_len = len(sentence.split())
                
                # Prefer medium-length sentences (5-30 words)
                if 5 <= sentence_len <= 30:
                    context_quality += 0.3
                
                # Check for specific citation purposes
                purpose_indicators = {
                    'method': ['method', 'approach', 'technique', 'following'],
                    'result': ['showed', 'demonstrated', 'found', 'reported'],
                    'comparison': ['similar', 'different', 'compared', 'versus'],
                    'support': ['supports', 'confirms', 'consistent', 'agrees']
                }
                
                for purpose, indicators in purpose_indicators.items():
                    if any(indicator in sentence.lower() for indicator in indicators):
                        context_quality += 0.2
                        break
            
            # Average context quality
            context_quality = context_quality / len(context_sentences)
            quality_score += context_quality * 0.6
        else:
            # No context available, moderate score
            quality_score += 0.3
        
        return min(1.0, quality_score)
    
    def _combine_relevance_scores(self, scores: Dict[str, float]) -> float:
        """Combine individual scores into final relevance score."""
        # Weights for different score components
        weights = {
            'title_similarity': 0.20,
            'content_similarity': 0.25,
            'keyword_overlap': 0.15,
            'context_relevance': 0.15,
            'semantic_similarity': 0.10,
            'domain_relevance': 0.10,
            'citation_quality': 0.05
        }
        
        # Calculate weighted average
        total_score = 0.0
        total_weight = 0.0
        
        for score_type, weight in weights.items():
            if score_type in scores:
                total_score += scores[score_type] * weight
                total_weight += weight
        
        # Normalize by actual weights used
        final_score = total_score / total_weight if total_weight > 0 else 0.5
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, final_score))
    
    def compare_full_text_vs_abstract_performance(
        self, 
        paper_title: str, 
        paper_full_text: str, 
        citations: List[CitationMetadata]
    ) -> Dict[str, Any]:
        """Compare relevance evaluation performance using full text vs abstract only."""
        results = {
            'full_text_results': [],
            'abstract_results': [],
            'comparison_stats': {}
        }
        
        for citation in citations:
            try:
                # Evaluate with full text
                full_text_relevance = self.evaluate_relevance(
                    paper_title, paper_full_text, citation, use_full_text=True
                )
                results['full_text_results'].append({
                    'citation_title': citation.title,
                    'relevance_score': full_text_relevance.overall_score,
                    'details': full_text_relevance.details
                })
                
                # Evaluate with abstract only
                abstract_relevance = self.evaluate_relevance(
                    paper_title, paper_full_text, citation, use_full_text=False
                )
                results['abstract_results'].append({
                    'citation_title': citation.title,
                    'relevance_score': abstract_relevance.overall_score,
                    'details': abstract_relevance.details
                })
                
            except Exception as e:
                logger.warning(f"Error comparing relevance for citation {citation.title}: {e}")
        
        # Calculate comparison statistics
        if results['full_text_results'] and results['abstract_results']:
            full_text_scores = [r['relevance_score'] for r in results['full_text_results']]
            abstract_scores = [r['relevance_score'] for r in results['abstract_results']]
            
            results['comparison_stats'] = {
                'full_text_avg_score': sum(full_text_scores) / len(full_text_scores),
                'abstract_avg_score': sum(abstract_scores) / len(abstract_scores),
                'score_differences': [ft - ab for ft, ab in zip(full_text_scores, abstract_scores)],
                'avg_difference': sum(full_text_scores) / len(full_text_scores) - sum(abstract_scores) / len(abstract_scores),
                'full_text_advantage_count': sum(1 for ft, ab in zip(full_text_scores, abstract_scores) if ft > ab),
                'abstract_advantage_count': sum(1 for ft, ab in zip(full_text_scores, abstract_scores) if ab > ft),
                'equal_count': sum(1 for ft, ab in zip(full_text_scores, abstract_scores) if abs(ft - ab) < 0.01)
            }
        
        return results 