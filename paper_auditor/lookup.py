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

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import arxiv
from cachetools import TTLCache

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
            'crossref': 1.0,  # 1 second between requests
            'pubmed': 0.34,   # 3 requests per second max
            'arxiv': 3.0,     # 3 second delay for arXiv
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
    
    def lookup_citation(self, metadata: CitationMetadata) -> Dict[str, Any]:
        """Look up a citation across multiple databases."""
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
            'details': {}
        }
        
        # Try different lookup strategies
        lookup_methods = [
            ('doi', self._lookup_by_doi),
            ('pmid', self._lookup_by_pmid),
            ('arxiv', self._lookup_by_arxiv),
            ('crossref', self._lookup_by_crossref),
            ('pubmed', self._lookup_by_pubmed_search),
        ]
        
        for method_name, lookup_func in lookup_methods:
            try:
                method_result = lookup_func(metadata)
                if method_result and method_result.get('found'):
                    result = method_result
                    logger.info(f"Found citation via {method_name}: {metadata.title}")
                    break
            except Exception as e:
                logger.warning(f"Error in {method_name} lookup: {e}")
                continue
        
        # Cache the result
        self.cache[cache_key] = result
        return result
    
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
        
        # Build query
        query_parts = [metadata.title]
        if metadata.authors:
            query_parts.append(metadata.authors[0])  # First author
        
        query = " ".join(query_parts)
        
        url = "https://api.crossref.org/works"
        params = {
            'query': query,
            'rows': 5,
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
                
                # Find best match
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
            score = self._calculate_similarity_score(target, work)
            if score > best_score and score > 0.7:  # Minimum threshold
                best_score = score
                best_match = work
        
        if best_match:
            return {'work': best_match, 'confidence': best_score}
        
        return None
    
    def _calculate_similarity_score(self, target: CitationMetadata, work: Dict) -> float:
        """Calculate similarity score between target metadata and CrossRef work."""
        score = 0.0
        factors = 0
        
        # Title similarity
        if target.title and 'title' in work and work['title']:
            title1 = target.title.lower().strip()
            title2 = work['title'][0].lower().strip() if isinstance(work['title'], list) else work['title'].lower().strip()
            
            # Simple Jaccard similarity on words
            words1 = set(re.findall(r'\w+', title1))
            words2 = set(re.findall(r'\w+', title2))
            
            if words1 and words2:
                title_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
                score += title_similarity * 0.6  # Title is most important
                factors += 0.6
        
        # Year similarity
        if target.year and 'published-print' in work:
            work_year = work['published-print']['date-parts'][0][0]
            if abs(target.year - work_year) <= 1:  # Allow 1 year difference
                score += 0.2
            factors += 0.2
        
        # Author similarity (simplified)
        if target.authors and 'author' in work and work['author']:
            target_surnames = []
            for author in target.authors:
                surname = author.split(',')[0].strip() if ',' in author else author.split()[-1]
                target_surnames.append(surname.lower())
            
            work_surnames = []
            for author in work['author']:
                if 'family' in author:
                    work_surnames.append(author['family'].lower())
            
            if target_surnames and work_surnames:
                common_surnames = set(target_surnames).intersection(set(work_surnames))
                author_similarity = len(common_surnames) / max(len(target_surnames), len(work_surnames))
                score += author_similarity * 0.2
            factors += 0.2
        
        return score / factors if factors > 0 else 0.0
    
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