"""
Citation lookup and verification using online databases.
"""

import re
import time
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import quote
from pathlib import Path
from difflib import SequenceMatcher

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import arxiv
from cachetools import TTLCache
from jellyfish import jaro_winkler_similarity
from scholarly import scholarly
from fuzzywuzzy import fuzz

from .models import CitationMetadata

logger = logging.getLogger(__name__)

# API logging setup
api_logger = logging.getLogger('api_calls')
api_logger.setLevel(logging.INFO)

# Create logs directory if it doesn't exist
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Create file handler for API logs
api_log_file = logs_dir / 'api_calls.log'
api_handler = logging.FileHandler(api_log_file)
api_handler.setLevel(logging.INFO)

# Create formatter for API logs
api_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
api_handler.setFormatter(api_formatter)

# Add handler to api_logger if not already added
if not api_logger.handlers:
    api_logger.addHandler(api_handler)

class CitationLookup:
    """Look up citations in online databases."""
    
    def __init__(self, cache_size: int = 1000, cache_ttl: int = 3600):
        """Initialize with caching."""
        self.cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)
        self.session = self._create_session()
        
        # Rate limiting
        self.last_request_time = {}
        self.min_delay = {
            'crossref': 1.0,          # 1 second between requests
            'pubmed': 0.34,           # 3 requests per second max
            'arxiv': 3.0,             # 3 second delay for arXiv
            'semantic_scholar': 1.0,  # 1 second for Semantic Scholar
            'openalex': 0.1,          # 10 requests per second for OpenAlex
            'google_scholar': 10.0,   # 10 second delay to avoid blocking
        }
    
    def _log_api_call(self, service: str, method: str, url: str, params: Dict = None, 
                      response_status: int = None, response_time: float = None, 
                      error: str = None, success: bool = False, result_count: int = 0):
        """Log API call details to the API log file."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'service': service,
            'method': method,
            'url': url,
            'params': params or {},
            'response_status': response_status,
            'response_time_ms': round(response_time * 1000, 2) if response_time else None,
            'success': success,
            'result_count': result_count,
            'error': error
        }
        
        api_logger.info(f"API_CALL: {json.dumps(log_entry)}")
    
    def _create_session(self) -> requests.Session:
        """Create a robust HTTP session with retries."""
        session = requests.Session()
        
        try:
            # Try the newer parameter name first
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
        except TypeError:
            # Fallback to older parameter name for older urllib3 versions
            retry_strategy = Retry(
                total=3,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "OPTIONS"],
                backoff_factor=1
            )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        session.headers.update({
            'User-Agent': 'PaperAuditor/1.0 (https://github.com/user/paper-auditor; mailto:user@example.com)'
        })
        
        return session
    
    def _rate_limit(self, service: str):
        """Enforce rate limiting for API calls."""
        if service in self.last_request_time:
            elapsed = time.time() - self.last_request_time[service]
            delay = self.min_delay.get(service, 1.0)
            if elapsed < delay:
                time.sleep(delay - elapsed)
        
        self.last_request_time[service] = time.time()
    
    def lookup_citation(self, metadata: CitationMetadata, enable_fallbacks: bool = True) -> Dict[str, Any]:
        """Look up a citation across multiple databases with advanced fallback strategies."""
        # Create cache key
        cache_key = self._create_cache_key(metadata)
        
        if cache_key in self.cache:
            logger.debug(f"Cache hit for citation: {metadata.title}")
            return self.cache[cache_key]
        
        result = {
            'found': False,
            'metadata': None,
            'source': None,
            'confidence': 0.0,
            'details': {},
            'full_text_available': False
        }
        
        # Enhanced lookup strategy with more sources and better fallbacks
        primary_methods = [
            ('doi', self._lookup_by_doi),
            ('pmid', self._lookup_by_pmid),
            ('arxiv', self._lookup_by_arxiv),
            ('semantic_scholar_doi', self._lookup_by_semantic_scholar_doi),
            ('openalex_doi', self._lookup_by_openalex_doi),
        ]
        
        secondary_methods = [
            ('semantic_scholar_title', self._lookup_by_semantic_scholar_title),
            ('openalex_title', self._lookup_by_openalex_title),
            ('crossref', self._lookup_by_crossref),
            ('pubmed', self._lookup_by_pubmed_search),
            ('google_scholar', self._lookup_by_google_scholar),
        ]
        
        fallback_methods = [
            ('fuzzy_title_search', self._fuzzy_title_search),
            ('partial_doi_search', self._partial_doi_search),
            ('author_year_search', self._author_year_search),
        ]
        
        # Try primary methods first (direct ID lookups)
        for method_name, lookup_func in primary_methods:
            try:
                method_result = lookup_func(metadata)
                if method_result and method_result.get('found'):
                    result = method_result
                    logger.info(f"Found citation via {method_name}: {metadata.title}")
                    break
            except Exception as e:
                logger.warning(f"Error in {method_name} lookup: {e}")
                continue
        
        # If not found, try secondary methods
        if not result['found']:
            for method_name, lookup_func in secondary_methods:
                try:
                    method_result = lookup_func(metadata)
                    if method_result and method_result.get('found'):
                        result = method_result
                        logger.info(f"Found citation via {method_name}: {metadata.title}")
                        break
                except Exception as e:
                    logger.warning(f"Error in {method_name} lookup: {e}")
                    continue
        
        # If still not found and fallbacks enabled, try aggressive fallback methods
        if not result['found'] and enable_fallbacks:
            for method_name, lookup_func in fallback_methods:
                try:
                    method_result = lookup_func(metadata)
                    if method_result and method_result.get('found'):
                        result = method_result
                        logger.info(f"Found citation via fallback {method_name}: {metadata.title}")
                        break
                except Exception as e:
                    logger.warning(f"Error in fallback {method_name} lookup: {e}")
                    continue
        
        # Try to get full text if we found the paper
        if result['found'] and result['metadata']:
            result['full_text_available'] = self._check_full_text_availability(result['metadata'])
        
        # Cache the result
        self.cache[cache_key] = result
        return result
    
    def _check_full_text_availability(self, metadata: CitationMetadata) -> bool:
        """Check if full text is available for the paper."""
        # Check for open access indicators
        if metadata.url:
            # ArXiv papers have full text
            if 'arxiv.org' in metadata.url.lower():
                return True
            # PMC papers often have full text
            if 'pmc' in metadata.url.lower():
                return True
            # DOI links might lead to full text
            if metadata.doi and 'doi.org' in metadata.url:
                return True
        
        # Could be extended to check specific publisher policies
        return False
    
    def _lookup_by_google_scholar(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation using Google Scholar (with caution due to rate limits)."""
        if not metadata.title or len(metadata.title.strip()) < 10:
            return None
        
        self._rate_limit('google_scholar')
        
        start_time = time.time()
        
        try:
            # Build search query
            search_query = metadata.title
            if metadata.authors:
                search_query += f" {metadata.authors[0]}"
            
            # Search using scholarly
            search_query = scholarly.search_pubs(search_query)
            results = []
            
            # Get first few results
            for i, pub in enumerate(search_query):
                if i >= 3:  # Limit to avoid long searches
                    break
                results.append(pub)
            
            response_time = time.time() - start_time
            
            self._log_api_call(
                service='google_scholar',
                method='SEARCH',
                url='https://scholar.google.com',
                params={'query': search_query},
                response_time=response_time,
                success=True,
                result_count=len(results)
            )
            
            if results:
                # Find best match
                best_match = self._find_best_scholar_match(metadata, results)
                if best_match:
                    return {
                        'found': True,
                        'metadata': self._scholar_to_metadata(best_match['pub']),
                        'source': 'google_scholar',
                        'confidence': best_match['confidence'],
                        'details': {'query': search_query, 'scholar_data': best_match['pub']}
                    }
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            self._log_api_call(
                service='google_scholar',
                method='SEARCH',
                url='https://scholar.google.com',
                params={'query': search_query},
                response_time=response_time,
                success=False,
                error=error_msg
            )
            
            logger.warning(f"Google Scholar search failed for {metadata.title}: {e}")
        
        return None
    
    def _fuzzy_title_search(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Fuzzy search across multiple APIs with relaxed matching."""
        if not metadata.title or len(metadata.title.strip()) < 8:
            return None
        
        # Try fuzzy search with progressively more relaxed queries
        title_variants = self._generate_title_variants(metadata.title)
        
        for variant in title_variants:
            variant_metadata = CitationMetadata(
                title=variant,
                authors=metadata.authors,
                year=metadata.year
            )
            
            # Try semantic scholar with relaxed threshold
            try:
                result = self._lookup_by_semantic_scholar_title_relaxed(variant_metadata)
                if result and result.get('found'):
                    result['source'] = f"fuzzy_{result.get('source', 'unknown')}"
                    return result
            except Exception as e:
                logger.debug(f"Fuzzy search failed for variant '{variant}': {e}")
                continue
        
        return None
    
    def _generate_title_variants(self, title: str) -> List[str]:
        """Generate variants of a title for fuzzy matching."""
        variants = [title]
        
        # Remove common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = title.lower().split()
        filtered_words = [w for w in words if w not in common_words]
        if len(filtered_words) >= 3:
            variants.append(' '.join(filtered_words))
        
        # Remove punctuation
        clean_title = re.sub(r'[^\w\s]', ' ', title)
        clean_title = re.sub(r'\s+', ' ', clean_title).strip()
        if clean_title != title:
            variants.append(clean_title)
        
        # First half of title
        if len(words) > 6:
            variants.append(' '.join(words[:len(words)//2]))
        
        # Core keywords (longest words)
        long_words = [w for w in words if len(w) > 4]
        if len(long_words) >= 2:
            variants.append(' '.join(long_words[:3]))
        
        return list(set(variants))  # Remove duplicates
    
    def _partial_doi_search(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Search for papers with partial DOI patterns."""
        if not metadata.doi:
            return None
        
        # Extract DOI prefix for broader search
        doi_parts = metadata.doi.split('/')
        if len(doi_parts) >= 2:
            doi_prefix = doi_parts[0]
            
            # Search for papers from same publisher
            try:
                url = "https://api.crossref.org/works"
                params = {
                    'filter': f'prefix:{doi_prefix}',
                    'query': metadata.title[:50] if metadata.title else '',
                    'rows': 5
                }
                
                response = self.session.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    works = data['message']['items']
                    
                    # Find best match
                    best_match = self._find_best_crossref_match_relaxed(metadata, works)
                    if best_match:
                        return {
                            'found': True,
                            'metadata': self._crossref_to_metadata(best_match['work']),
                            'source': 'partial_doi_crossref',
                            'confidence': best_match['confidence'],
                            'details': {'doi_prefix': doi_prefix, 'crossref_data': best_match['work']}
                        }
            except Exception as e:
                logger.debug(f"Partial DOI search failed: {e}")
        
        return None
    
    def _author_year_search(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Search based on author and year when title matching fails."""
        if not metadata.authors or not metadata.year:
            return None
        
        # Extract first author surname
        first_author = metadata.authors[0]
        if ',' in first_author:
            surname = first_author.split(',')[0].strip()
        else:
            parts = first_author.strip().split()
            surname = parts[-1] if parts else first_author
        
        try:
            # Try OpenAlex author-year search
            url = "https://api.openalex.org/works"
            params = {
                'filter': f'publication_year:{metadata.year},author.display_name:{surname}',
                'per-page': 10
            }
            
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                works = data.get('results', [])
                
                if works and metadata.title:
                    # Find works with similar titles
                    for work in works:
                        work_title = work.get('title', '')
                        if work_title:
                            similarity = self._enhanced_title_similarity(metadata.title, work_title)
                            if similarity > 0.6:  # Relaxed threshold
                                return {
                                    'found': True,
                                    'metadata': self._openalex_to_metadata(work),
                                    'source': 'author_year_openalex',
                                    'confidence': similarity,
                                    'details': {'author': surname, 'year': metadata.year, 'openalex_data': work}
                                }
        except Exception as e:
            logger.debug(f"Author-year search failed: {e}")
        
        return None
    
    def _lookup_by_semantic_scholar_title_relaxed(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Semantic Scholar title search with relaxed matching thresholds."""
        if not metadata.title or len(metadata.title.strip()) < 5:
            return None
        
        self._rate_limit('semantic_scholar')
        
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': metadata.title,
            'limit': 10,  # Increased for better matching
            'fields': 'title,authors,year,journal,abstract,citationCount,referenceCount,url,venue,publicationTypes,externalIds'
        }
        start_time = time.time()
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                
                # Find best match with relaxed threshold
                best_match = self._find_best_semantic_scholar_match_relaxed(metadata, papers)
                if best_match:
                    return {
                        'found': True,
                        'metadata': self._semantic_scholar_to_metadata(best_match['paper']),
                        'source': 'semantic_scholar_title_relaxed',
                        'confidence': best_match['confidence'],
                        'details': {'query': metadata.title, 'semantic_scholar_data': best_match['paper']}
                    }
        except Exception as e:
            logger.debug(f"Relaxed Semantic Scholar search failed: {e}")
        
        return None
    
    def _find_best_semantic_scholar_match_relaxed(self, target: CitationMetadata, papers: List[Dict]) -> Optional[Dict]:
        """Find best match with relaxed similarity thresholds."""
        if not papers:
            return None
        
        best_match = None
        best_score = 0.0
        
        for paper in papers:
            score = self._calculate_enhanced_similarity_score(target, paper, 'semantic_scholar')
            if score > best_score and score > 0.5:  # Lowered threshold from 0.7
                best_score = score
                best_match = paper
        
        if best_match:
            return {'paper': best_match, 'confidence': best_score}
        
        return None
    
    def _find_best_crossref_match_relaxed(self, target: CitationMetadata, works: List[Dict]) -> Optional[Dict]:
        """Find best CrossRef match with relaxed thresholds."""
        if not works:
            return None
        
        best_match = None
        best_score = 0.0
        
        for work in works:
            score = self._calculate_enhanced_similarity_score(target, work, 'crossref')
            if score > best_score and score > 0.5:  # Lowered threshold
                best_score = score
                best_match = work
        
        if best_match:
            return {'work': best_match, 'confidence': best_score}
        
        return None
    
    def _find_best_scholar_match(self, target: CitationMetadata, pubs: List[Dict]) -> Optional[Dict]:
        """Find best Google Scholar match."""
        if not pubs:
            return None
        
        best_match = None
        best_score = 0.0
        
        for pub in pubs:
            # Calculate similarity for Google Scholar results
            score = 0.0
            factors = 0
            
            # Title similarity
            if target.title and 'bib' in pub and 'title' in pub['bib']:
                pub_title = pub['bib']['title']
                title_similarity = self._enhanced_title_similarity(target.title, pub_title)
                score += title_similarity * 0.7
                factors += 0.7
            
            # Year similarity
            if target.year and 'bib' in pub and 'pub_year' in pub['bib']:
                try:
                    pub_year = int(pub['bib']['pub_year'])
                    year_diff = abs(target.year - pub_year)
                    if year_diff == 0:
                        score += 0.2
                    elif year_diff <= 1:
                        score += 0.15
                    elif year_diff <= 2:
                        score += 0.1
                    factors += 0.2
                except ValueError:
                    pass
            
            # Author similarity
            if target.authors and 'bib' in pub and 'author' in pub['bib']:
                pub_authors = []
                author_data = pub['bib']['author']
                if isinstance(author_data, list):
                    pub_authors = [str(author) for author in author_data]
                elif isinstance(author_data, str):
                    pub_authors = [author_data]
                
                if pub_authors:
                    author_similarity = self._calculate_author_similarity(target.authors, pub_authors)
                    score += author_similarity * 0.1
                    factors += 0.1
            
            final_score = score / factors if factors > 0 else 0.0
            
            if final_score > best_score and final_score > 0.6:
                best_score = final_score
                best_match = pub
        
        if best_match:
            return {'pub': best_match, 'confidence': best_score}
        
        return None
    
    def _scholar_to_metadata(self, pub: Dict) -> CitationMetadata:
        """Convert Google Scholar publication to CitationMetadata."""
        bib = pub.get('bib', {})
        
        title = bib.get('title', '')
        
        # Extract authors
        authors = []
        author_data = bib.get('author', [])
        if isinstance(author_data, list):
            authors = [str(author) for author in author_data]
        elif isinstance(author_data, str):
            authors = [author_data]
        
        # Extract year
        year = None
        if 'pub_year' in bib:
            try:
                year = int(bib['pub_year'])
            except ValueError:
                pass
        
        # Extract journal/venue
        venue = bib.get('venue', '')
        
        # Extract URL
        url = pub.get('pub_url') or pub.get('eprint_url')
        
        return CitationMetadata(
            title=title,
            authors=authors,
            year=year,
            journal=venue,
            url=url
        )
    
    def _create_cache_key(self, metadata: CitationMetadata) -> str:
        """Create a cache key for the citation."""
        key_parts = []
        if metadata.doi:
            key_parts.append(f"doi:{metadata.doi}")
        if metadata.pmid:
            key_parts.append(f"pmid:{metadata.pmid}")
        if metadata.arxiv_id:
            key_parts.append(f"arxiv:{metadata.arxiv_id}")
        if metadata.title:
            # Use first 50 chars of title
            title_key = re.sub(r'[^\w\s]', '', metadata.title.lower())[:50]
            key_parts.append(f"title:{title_key}")
        
        return "|".join(key_parts) or "unknown"
    
    def _lookup_by_semantic_scholar_doi(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by DOI using Semantic Scholar."""
        if not metadata.doi:
            return None
        
        self._rate_limit('semantic_scholar')
        
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{metadata.doi}"
        params = {
            'fields': 'title,authors,year,journal,abstract,citationCount,referenceCount,url,venue,publicationTypes'
        }
        start_time = time.time()
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                self._log_api_call(
                    service='semantic_scholar',
                    method='GET',
                    url=url,
                    params=params,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=True,
                    result_count=1
                )
                
                return {
                    'found': True,
                    'metadata': self._semantic_scholar_to_metadata(data),
                    'source': 'semantic_scholar_doi',
                    'confidence': 0.95,
                    'details': {'doi': metadata.doi, 'semantic_scholar_data': data}
                }
            else:
                self._log_api_call(
                    service='semantic_scholar',
                    method='GET',
                    url=url,
                    params=params,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            self._log_api_call(
                service='semantic_scholar',
                method='GET',
                url=url,
                params=params,
                response_time=response_time,
                success=False,
                error=error_msg
            )
            
            logger.warning(f"Semantic Scholar DOI lookup failed for {metadata.doi}: {e}")
        
        return None

    def _lookup_by_semantic_scholar_title(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by title using Semantic Scholar."""
        if not metadata.title or len(metadata.title.strip()) < 10:
            return None
        
        self._rate_limit('semantic_scholar')
        
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': metadata.title,
            'limit': 5,
            'fields': 'title,authors,year,journal,abstract,citationCount,referenceCount,url,venue,publicationTypes,externalIds'
        }
        start_time = time.time()
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                papers = data.get('data', [])
                
                self._log_api_call(
                    service='semantic_scholar',
                    method='GET',
                    url=url,
                    params=params,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=True,
                    result_count=len(papers)
                )
                
                # Find best match using enhanced similarity
                best_match = self._find_best_semantic_scholar_match(metadata, papers)
                if best_match:
                    return {
                        'found': True,
                        'metadata': self._semantic_scholar_to_metadata(best_match['paper']),
                        'source': 'semantic_scholar_title',
                        'confidence': best_match['confidence'],
                        'details': {'query': metadata.title, 'semantic_scholar_data': best_match['paper']}
                    }
            else:
                self._log_api_call(
                    service='semantic_scholar',
                    method='GET',
                    url=url,
                    params=params,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            self._log_api_call(
                service='semantic_scholar',
                method='GET',
                url=url,
                params=params,
                response_time=response_time,
                success=False,
                error=error_msg
            )
            
            logger.warning(f"Semantic Scholar title search failed for {metadata.title}: {e}")
        
        return None

    def _lookup_by_openalex_doi(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by DOI using OpenAlex."""
        if not metadata.doi:
            return None
        
        self._rate_limit('openalex')
        
        # OpenAlex expects DOI in URL format
        doi_url = f"https://doi.org/{metadata.doi}"
        url = f"https://api.openalex.org/works/{doi_url}"
        start_time = time.time()
        
        try:
            response = self.session.get(url, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                self._log_api_call(
                    service='openalex',
                    method='GET',
                    url=url,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=True,
                    result_count=1
                )
                
                return {
                    'found': True,
                    'metadata': self._openalex_to_metadata(data),
                    'source': 'openalex_doi',
                    'confidence': 0.95,
                    'details': {'doi': metadata.doi, 'openalex_data': data}
                }
            else:
                self._log_api_call(
                    service='openalex',
                    method='GET',
                    url=url,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            self._log_api_call(
                service='openalex',
                method='GET',
                url=url,
                response_time=response_time,
                success=False,
                error=error_msg
            )
            
            logger.warning(f"OpenAlex DOI lookup failed for {metadata.doi}: {e}")
        
        return None

    def _lookup_by_openalex_title(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by title using OpenAlex."""
        if not metadata.title or len(metadata.title.strip()) < 10:
            return None
        
        self._rate_limit('openalex')
        
        url = "https://api.openalex.org/works"
        params = {
            'search': metadata.title,
            'per-page': 5
        }
        start_time = time.time()
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                works = data.get('results', [])
                
                self._log_api_call(
                    service='openalex',
                    method='GET',
                    url=url,
                    params=params,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=True,
                    result_count=len(works)
                )
                
                # Find best match using enhanced similarity
                best_match = self._find_best_openalex_match(metadata, works)
                if best_match:
                    return {
                        'found': True,
                        'metadata': self._openalex_to_metadata(best_match['work']),
                        'source': 'openalex_title',
                        'confidence': best_match['confidence'],
                        'details': {'query': metadata.title, 'openalex_data': best_match['work']}
                    }
            else:
                self._log_api_call(
                    service='openalex',
                    method='GET',
                    url=url,
                    params=params,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            self._log_api_call(
                service='openalex',
                method='GET',
                url=url,
                params=params,
                response_time=response_time,
                success=False,
                error=error_msg
            )
            
            logger.warning(f"OpenAlex title search failed for {metadata.title}: {e}")
        
        return None

    def _enhanced_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate enhanced title similarity using multiple algorithms."""
        if not title1 or not title2:
            return 0.0
        
        # Normalize titles
        def normalize_title(title):
            # Remove common punctuation and convert to lowercase
            normalized = re.sub(r'[^\w\s]', ' ', title.lower())
            # Remove extra whitespace
            normalized = re.sub(r'\s+', ' ', normalized).strip()
            return normalized
        
        norm_title1 = normalize_title(title1)
        norm_title2 = normalize_title(title2)
        
        # Sequence matcher
        seq_similarity = SequenceMatcher(None, norm_title1, norm_title2).ratio()
        
        # Jaro-Winkler similarity
        jw_similarity = jaro_winkler_similarity(norm_title1, norm_title2)
        
        # Fuzzy ratio
        fuzzy_ratio = fuzz.ratio(norm_title1, norm_title2) / 100.0
        
        # Word-based Jaccard similarity
        words1 = set(norm_title1.split())
        words2 = set(norm_title2.split())
        if words1 and words2:
            jaccard_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
        else:
            jaccard_similarity = 0.0
        
        # Weighted average with enhanced fuzzy matching
        combined_similarity = (seq_similarity * 0.25 + jw_similarity * 0.35 + 
                              fuzzy_ratio * 0.25 + jaccard_similarity * 0.15)
        
        return combined_similarity

    def _find_best_semantic_scholar_match(self, target: CitationMetadata, papers: List[Dict]) -> Optional[Dict]:
        """Find the best matching paper from Semantic Scholar results."""
        if not papers:
            return None
        
        best_match = None
        best_score = 0.0
        
        for paper in papers:
            score = self._calculate_enhanced_similarity_score(target, paper, 'semantic_scholar')
            if score > best_score and score > 0.65:  # Slightly relaxed threshold
                best_score = score
                best_match = paper
        
        if best_match:
            return {'paper': best_match, 'confidence': best_score}
        
        return None

    def _find_best_openalex_match(self, target: CitationMetadata, works: List[Dict]) -> Optional[Dict]:
        """Find the best matching work from OpenAlex results."""
        if not works:
            return None
        
        best_match = None
        best_score = 0.0
        
        for work in works:
            score = self._calculate_enhanced_similarity_score(target, work, 'openalex')
            if score > best_score and score > 0.65:  # Slightly relaxed threshold
                best_score = score
                best_match = work
        
        if best_match:
            return {'work': best_match, 'confidence': best_score}
        
        return None

    def _calculate_enhanced_similarity_score(self, target: CitationMetadata, item: Dict, source: str) -> float:
        """Calculate enhanced similarity score between target metadata and API result."""
        score = 0.0
        factors = 0
        
        # Title similarity (most important)
        target_title = target.title
        if source == 'semantic_scholar':
            item_title = item.get('title')
        elif source == 'openalex':
            item_title = item.get('title')
        elif source == 'crossref':
            item_title = item['title'][0] if isinstance(item.get('title'), list) and item['title'] else item.get('title', '')
        else:
            item_title = item.get('title', '')
        
        if target_title and item_title:
            title_similarity = self._enhanced_title_similarity(target_title, item_title)
            score += title_similarity * 0.6  # Title is most important
            factors += 0.6
        
        # Year similarity
        target_year = target.year
        item_year = None
        
        if source == 'semantic_scholar':
            item_year = item.get('year')
        elif source == 'openalex':
            item_year = item.get('publication_year')
        elif source == 'crossref':
            if 'published-print' in item and 'date-parts' in item['published-print']:
                try:
                    item_year = item['published-print']['date-parts'][0][0]
                except (IndexError, TypeError):
                    pass
        
        if target_year and item_year:
            year_diff = abs(target_year - item_year)
            if year_diff == 0:
                score += 0.2
            elif year_diff == 1:
                score += 0.15
            elif year_diff <= 2:
                score += 0.1
            factors += 0.2
        
        # Author similarity
        target_authors = target.authors or []
        item_authors = []
        
        if source == 'semantic_scholar':
            item_authors = [author.get('name', '') for author in item.get('authors', [])]
        elif source == 'openalex':
            item_authors = [author.get('display_name', '') for author in item.get('authorships', [])]
        elif source == 'crossref':
            for author in item.get('author', []):
                if 'family' in author and 'given' in author:
                    item_authors.append(f"{author['family']}, {author['given']}")
                elif 'family' in author:
                    item_authors.append(author['family'])
        
        if target_authors and item_authors:
            author_similarity = self._calculate_author_similarity(target_authors, item_authors)
            score += author_similarity * 0.2
            factors += 0.2
        
        return score / factors if factors > 0 else 0.0

    def _calculate_author_similarity(self, authors1: List[str], authors2: List[str]) -> float:
        """Calculate similarity between two author lists."""
        if not authors1 or not authors2:
            return 0.0
        
        # Extract surnames for comparison
        def extract_surnames(authors):
            surnames = []
            for author in authors:
                # Handle "Last, First" format
                if ',' in author:
                    surname = author.split(',')[0].strip()
                else:
                    # Handle "First Last" format
                    parts = author.strip().split()
                    surname = parts[-1] if parts else author
                surnames.append(surname.lower())
            return surnames
        
        surnames1 = extract_surnames(authors1)
        surnames2 = extract_surnames(authors2)
        
        # Calculate both exact and fuzzy matches
        exact_matches = len(set(surnames1).intersection(set(surnames2)))
        
        # Fuzzy matching for similar names
        fuzzy_matches = 0
        for s1 in surnames1:
            for s2 in surnames2:
                if s1 != s2 and fuzz.ratio(s1, s2) > 80:  # 80% similarity threshold
                    fuzzy_matches += 0.5  # Partial credit for fuzzy matches
        
        total_matches = exact_matches + fuzzy_matches
        max_authors = max(len(surnames1), len(surnames2))
        
        return total_matches / max_authors if max_authors > 0 else 0.0

    def _semantic_scholar_to_metadata(self, paper: Dict) -> CitationMetadata:
        """Convert Semantic Scholar paper to CitationMetadata."""
        authors = []
        if 'authors' in paper:
            authors = [author.get('name', '') for author in paper['authors']]
        
        # Extract DOI from external IDs
        doi = None
        if 'externalIds' in paper and paper['externalIds']:
            doi = paper['externalIds'].get('DOI')
        
        # Extract arXiv ID
        arxiv_id = None
        if 'externalIds' in paper and paper['externalIds']:
            arxiv_id = paper['externalIds'].get('ArXiv')
        
        # Extract PMID
        pmid = None
        if 'externalIds' in paper and paper['externalIds']:
            pmid = paper['externalIds'].get('PubMed')
        
        return CitationMetadata(
            title=paper.get('title', ''),
            authors=authors,
            year=paper.get('year'),
            journal=paper.get('venue') or paper.get('journal', ''),
            doi=doi,
            pmid=str(pmid) if pmid else None,
            arxiv_id=arxiv_id,
            url=paper.get('url'),
            abstract=paper.get('abstract')
        )

    def _openalex_to_metadata(self, work: Dict) -> CitationMetadata:
        """Convert OpenAlex work to CitationMetadata."""
        authors = []
        if 'authorships' in work:
            authors = [authorship.get('author', {}).get('display_name', '') 
                      for authorship in work['authorships']]
        
        # Extract DOI
        doi = None
        if 'doi' in work:
            doi = work['doi'].replace('https://doi.org/', '') if work['doi'] else None
        
        # Extract journal/venue
        journal = ''
        if 'primary_location' in work and work['primary_location']:
            source = work['primary_location'].get('source', {})
            journal = source.get('display_name', '') if source else ''
        
        return CitationMetadata(
            title=work.get('title', ''),
            authors=authors,
            year=work.get('publication_year'),
            journal=journal,
            doi=doi,
            url=work.get('id')  # OpenAlex ID as URL
        )

    def _lookup_by_pmid(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by PMID using PubMed."""
        if not metadata.pmid:
            return None
        
        self._rate_limit('pubmed')
        
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {
            'db': 'pubmed',
            'id': metadata.pmid,
            'retmode': 'json'
        }
        start_time = time.time()
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and metadata.pmid in data['result']:
                    article = data['result'][metadata.pmid]
                    
                    self._log_api_call(
                        service='pubmed',
                        method='GET',
                        url=url,
                        params=params,
                        response_status=response.status_code,
                        response_time=response_time,
                        success=True,
                        result_count=1
                    )
                    
                    return {
                        'found': True,
                        'metadata': self._pubmed_to_metadata(article),
                        'source': 'pubmed_pmid',
                        'confidence': 0.95,
                        'details': {'pmid': metadata.pmid, 'pubmed_data': article}
                    }
        except Exception as e:
            logger.warning(f"PMID lookup failed for {metadata.pmid}: {e}")
        
        return None

    def _lookup_by_arxiv(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by arXiv ID."""
        if not metadata.arxiv_id:
            return None
        
        self._rate_limit('arxiv')
        
        start_time = time.time()
        
        try:
            search = arxiv.Search(id_list=[metadata.arxiv_id])
            papers = list(search.results())
            
            if papers:
                paper = papers[0]
                
                arxiv_metadata = CitationMetadata(
                    title=paper.title,
                    authors=[str(author) for author in paper.authors],
                    year=paper.published.year,
                    arxiv_id=metadata.arxiv_id,
                    url=paper.entry_id,
                    abstract=paper.summary
                )
                
                return {
                    'found': True,
                    'metadata': arxiv_metadata,
                    'source': 'arxiv',
                    'confidence': 0.95,
                    'details': {'arxiv_id': metadata.arxiv_id, 'arxiv_data': paper}
                }
        except Exception as e:
            logger.warning(f"arXiv lookup failed for {metadata.arxiv_id}: {e}")
        
        return None

    def _lookup_by_doi(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by DOI using CrossRef."""
        if not metadata.doi:
            return None
        
        self._rate_limit('crossref')
        
        url = f"https://api.crossref.org/works/{metadata.doi}"
        start_time = time.time()
        
        try:
            response = self.session.get(url, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                work = data['message']
                
                self._log_api_call(
                    service='crossref',
                    method='GET',
                    url=url,
                    params={'doi': metadata.doi},
                    response_status=response.status_code,
                    response_time=response_time,
                    success=True,
                    result_count=1
                )
                
                return {
                    'found': True,
                    'metadata': self._crossref_to_metadata(work),
                    'source': 'crossref_doi',
                    'confidence': 0.95,
                    'details': {'doi': metadata.doi, 'crossref_data': work}
                }
            else:
                self._log_api_call(
                    service='crossref',
                    method='GET',
                    url=url,
                    params={'doi': metadata.doi},
                    response_status=response.status_code,
                    response_time=response_time,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            self._log_api_call(
                service='crossref',
                method='GET',
                url=url,
                params={'doi': metadata.doi},
                response_time=response_time,
                success=False,
                error=error_msg
            )
            
            logger.warning(f"DOI lookup failed for {metadata.doi}: {e}")
        
        return None
    
    def _lookup_by_pmid(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by PMID using PubMed."""
        if not metadata.pmid:
            return None
        
        self._rate_limit('pubmed')
        
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        params = {
            'db': 'pubmed',
            'id': metadata.pmid,
            'retmode': 'json'
        }
        start_time = time.time()
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data and metadata.pmid in data['result']:
                    article = data['result'][metadata.pmid]
                    
                    self._log_api_call(
                        service='pubmed',
                        method='GET',
                        url=url,
                        params=params,
                        response_status=response.status_code,
                        response_time=response_time,
                        success=True,
                        result_count=1
                    )
                    
                    return {
                        'found': True,
                        'metadata': self._pubmed_to_metadata(article),
                        'source': 'pubmed_pmid',
                        'confidence': 0.95,
                        'details': {'pmid': metadata.pmid, 'pubmed_data': article}
                    }
                else:
                    self._log_api_call(
                        service='pubmed',
                        method='GET',
                        url=url,
                        params=params,
                        response_status=response.status_code,
                        response_time=response_time,
                        success=False,
                        error="PMID not found in response"
                    )
            else:
                self._log_api_call(
                    service='pubmed',
                    method='GET',
                    url=url,
                    params=params,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            self._log_api_call(
                service='pubmed',
                method='GET',
                url=url,
                params=params,
                response_time=response_time,
                success=False,
                error=error_msg
            )
            
            logger.warning(f"PMID lookup failed for {metadata.pmid}: {e}")
        
        return None
    
    def _lookup_by_arxiv(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by arXiv ID."""
        if not metadata.arxiv_id:
            return None
        
        self._rate_limit('arxiv')
        
        start_time = time.time()
        
        try:
            search = arxiv.Search(id_list=[metadata.arxiv_id])
            papers = list(search.results())
            response_time = time.time() - start_time
            
            if papers:
                paper = papers[0]
                
                self._log_api_call(
                    service='arxiv',
                    method='SEARCH',
                    url='http://export.arxiv.org/api/query',
                    params={'id_list': metadata.arxiv_id},
                    response_time=response_time,
                    success=True,
                    result_count=len(papers)
                )
                
                arxiv_metadata = CitationMetadata(
                    title=paper.title,
                    authors=[str(author) for author in paper.authors],
                    year=paper.published.year,
                    arxiv_id=metadata.arxiv_id,
                    url=paper.entry_id,
                    abstract=paper.summary
                )
                
                return {
                    'found': True,
                    'metadata': arxiv_metadata,
                    'source': 'arxiv',
                    'confidence': 0.95,
                    'details': {'arxiv_id': metadata.arxiv_id, 'arxiv_data': paper}
                }
            else:
                self._log_api_call(
                    service='arxiv',
                    method='SEARCH',
                    url='http://export.arxiv.org/api/query',
                    params={'id_list': metadata.arxiv_id},
                    response_time=response_time,
                    success=False,
                    result_count=0,
                    error="No papers found"
                )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            self._log_api_call(
                service='arxiv',
                method='SEARCH',
                url='http://export.arxiv.org/api/query',
                params={'id_list': metadata.arxiv_id},
                response_time=response_time,
                success=False,
                error=error_msg
            )
            
            logger.warning(f"arXiv lookup failed for {metadata.arxiv_id}: {e}")
        
        return None
    
    def _lookup_by_crossref(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by title/author using CrossRef."""
        if not metadata.title:
            return None
        
        self._rate_limit('crossref')
        
        # Build enhanced query with better search terms
        query_parts = [metadata.title]
        if metadata.authors:
            # Add first author for better matching
            query_parts.append(metadata.authors[0])
        if metadata.year:
            # Add year to improve matching
            query_parts.append(str(metadata.year))
        
        query = " ".join(query_parts)
        
        url = "https://api.crossref.org/works"
        params = {
            'query': query,
            'rows': 10,  # Increased from 5 to get more candidates
            'sort': 'relevance'
        }
        start_time = time.time()
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                works = data['message']['items']
                
                self._log_api_call(
                    service='crossref',
                    method='GET',
                    url=url,
                    params=params,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=True,
                    result_count=len(works)
                )
                
                # Find best match using enhanced similarity
                best_match = self._find_best_crossref_match(metadata, works)
                if best_match:
                    return {
                        'found': True,
                        'metadata': self._crossref_to_metadata(best_match['work']),
                        'source': 'crossref_search',
                        'confidence': best_match['confidence'],
                        'details': {'query': query, 'crossref_data': best_match['work']}
                    }
            else:
                self._log_api_call(
                    service='crossref',
                    method='GET',
                    url=url,
                    params=params,
                    response_status=response.status_code,
                    response_time=response_time,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            self._log_api_call(
                service='crossref',
                method='GET',
                url=url,
                params=params,
                response_time=response_time,
                success=False,
                error=error_msg
            )
            
            logger.warning(f"CrossRef search failed for {metadata.title}: {e}")
        
        return None
    
    def _lookup_by_pubmed_search(self, metadata: CitationMetadata) -> Optional[Dict]:
        """Look up citation by title/author using PubMed search."""
        if not metadata.title:
            return None
        
        self._rate_limit('pubmed')
        
        # Build search query
        query_parts = [f'"{metadata.title}"[Title]']
        if metadata.authors:
            author = metadata.authors[0].split(',')[0].strip()  # Last name only
            query_parts.append(f'"{author}"[Author]')
        
        query = " AND ".join(query_parts)
        
        # Search for PMIDs
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            'db': 'pubmed',
            'term': query,
            'retmax': 5,
            'retmode': 'json'
        }
        search_start_time = time.time()
        
        try:
            response = self.session.get(search_url, params=search_params, timeout=10)
            search_response_time = time.time() - search_start_time
            
            if response.status_code == 200:
                data = response.json()
                pmids = data.get('esearchresult', {}).get('idlist', [])
                
                self._log_api_call(
                    service='pubmed',
                    method='GET',
                    url=search_url,
                    params=search_params,
                    response_status=response.status_code,
                    response_time=search_response_time,
                    success=True,
                    result_count=len(pmids)
                )
                
                if pmids:
                    # Get details for first PMID
                    pmid = pmids[0]
                    summary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                    summary_params = {
                        'db': 'pubmed',
                        'id': pmid,
                        'retmode': 'json'
                    }
                    summary_start_time = time.time()
                    
                    response = self.session.get(summary_url, params=summary_params, timeout=10)
                    summary_response_time = time.time() - summary_start_time
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'result' in data and pmid in data['result']:
                            article = data['result'][pmid]
                            
                            self._log_api_call(
                                service='pubmed',
                                method='GET',
                                url=summary_url,
                                params=summary_params,
                                response_status=response.status_code,
                                response_time=summary_response_time,
                                success=True,
                                result_count=1
                            )
                            
                            return {
                                'found': True,
                                'metadata': self._pubmed_to_metadata(article),
                                'source': 'pubmed_search',
                                'confidence': 0.8,
                                'details': {'query': query, 'pmid': pmid, 'pubmed_data': article}
                            }
                        else:
                            self._log_api_call(
                                service='pubmed',
                                method='GET',
                                url=summary_url,
                                params=summary_params,
                                response_status=response.status_code,
                                response_time=summary_response_time,
                                success=False,
                                error="Article not found in summary response"
                            )
                    else:
                        self._log_api_call(
                            service='pubmed',
                            method='GET',
                            url=summary_url,
                            params=summary_params,
                            response_status=response.status_code,
                            response_time=summary_response_time,
                            success=False,
                            error=f"HTTP {response.status_code}"
                        )
            else:
                self._log_api_call(
                    service='pubmed',
                    method='GET',
                    url=search_url,
                    params=search_params,
                    response_status=response.status_code,
                    response_time=search_response_time,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
        except Exception as e:
            response_time = time.time() - search_start_time
            error_msg = str(e)
            
            self._log_api_call(
                service='pubmed',
                method='GET',
                url=search_url,
                params=search_params,
                response_time=response_time,
                success=False,
                error=error_msg
            )
            
            logger.warning(f"PubMed search failed for {metadata.title}: {e}")
        
        return None
    
    def _find_best_crossref_match(self, target: CitationMetadata, works: List[Dict]) -> Optional[Dict]:
        """Find the best matching work from CrossRef results."""
        if not works:
            return None
        
        best_match = None
        best_score = 0.0
        
        for work in works:
            score = self._calculate_enhanced_similarity_score(target, work, 'crossref')
            if score > best_score and score > 0.65:  # Slightly lower threshold for more matches
                best_score = score
                best_match = work
        
        if best_match:
            return {'work': best_match, 'confidence': best_score}
        
        return None
    
    def _crossref_to_metadata(self, work: Dict) -> CitationMetadata:
        """Convert CrossRef work to CitationMetadata."""
        title = ""
        if 'title' in work and work['title']:
            title = work['title'][0] if isinstance(work['title'], list) else work['title']
        
        authors = []
        if 'author' in work:
            for author in work['author']:
                if 'family' in author and 'given' in author:
                    authors.append(f"{author['family']}, {author['given']}")
                elif 'family' in author:
                    authors.append(author['family'])
        
        year = None
        if 'published-print' in work and 'date-parts' in work['published-print']:
            try:
                year = work['published-print']['date-parts'][0][0]
            except (IndexError, TypeError):
                pass
        
        journal = ""
        if 'container-title' in work and work['container-title']:
            journal = work['container-title'][0] if isinstance(work['container-title'], list) else work['container-title']
        
        return CitationMetadata(
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            volume=work.get('volume'),
            pages=work.get('page'),
            doi=work.get('DOI'),
            url=work.get('URL')
        )
    
    def _pubmed_to_metadata(self, article: Dict) -> CitationMetadata:
        """Convert PubMed article to CitationMetadata."""
        title = article.get('title', '')
        
        authors = []
        if 'authors' in article:
            for author in article['authors']:
                authors.append(author.get('name', ''))
        
        year = None
        if 'pubdate' in article:
            try:
                # Parse date string like "2021 Jun 15"
                date_parts = article['pubdate'].split()
                if date_parts:
                    year = int(date_parts[0])
            except (ValueError, IndexError):
                pass
        
        journal = article.get('source', '')
        
        return CitationMetadata(
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            volume=article.get('volume'),
            pages=article.get('pages'),
            pmid=str(article.get('uid', ''))
        ) 