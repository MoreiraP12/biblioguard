# API Logging for Paper Auditor

This feature logs all API calls made to external services (CrossRef, PubMed, and arXiv) to help you monitor usage, debug issues, and analyze performance.

## Features

The API logging system captures:
- **Service**: Which API was called (crossref, pubmed, arxiv)
- **Timestamp**: When the call was made
- **URL & Parameters**: Full request details
- **Response Time**: How long the call took (in milliseconds)
- **Status Code**: HTTP response status (for HTTP APIs)
- **Success/Failure**: Whether the call was successful
- **Result Count**: Number of results returned
- **Error Details**: Specific error messages for failed calls

## Log File Location

All API calls are logged to: `logs/api_calls.log`

The logs directory is automatically created when the first API call is made.

## Log Format

Each log entry is a JSON object containing:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456",
  "service": "crossref",
  "method": "GET",
  "url": "https://api.crossref.org/works/10.1038/nature12373",
  "params": {"doi": "10.1038/nature12373"},
  "response_status": 200,
  "response_time_ms": 1234.56,
  "success": true,
  "result_count": 1,
  "error": null
}
```

## Usage

### 1. Automatic Logging

API logging is automatically enabled when you use the `CitationLookup` class. No additional configuration is needed:

```python
from paper_auditor.lookup import CitationLookup
from paper_auditor.models import CitationMetadata

# Initialize lookup service
lookup = CitationLookup()

# Any lookup will be automatically logged
metadata = CitationMetadata(doi="10.1038/nature12373")
result = lookup.lookup_citation(metadata)
```

### 2. Test the Logging

Run the test script to generate sample logs:

```bash
python test_api_logging.py
```

This will make several API calls to demonstrate the logging functionality.

### 3. Analyze the Logs

Use the provided log analyzer to view statistics and insights:

#### Basic Analysis
```bash
python api_log_analyzer.py
```

#### Detailed Statistics
```bash
python api_log_analyzer.py --stats
```

#### Service-Specific Analysis
```bash
python api_log_analyzer.py --service crossref --stats
python api_log_analyzer.py --service pubmed --stats
python api_log_analyzer.py --service arxiv --stats
```

#### View Only Errors
```bash
python api_log_analyzer.py --errors-only
```

#### Custom Log File
```bash
python api_log_analyzer.py --log-file /path/to/custom/log.log --stats
```

## Analysis Output Examples

### Basic Statistics
```
============================================================
                    API CALL STATISTICS                    
============================================================

Total API Calls: 25
Success Rate: 84.0%
Average Response Time: 1,234.56 ms
Min Response Time: 456.78 ms
Max Response Time: 3,456.78 ms

Total Results Retrieved: 18

Calls by Service:
  crossref: 15
  pubmed: 8
  arxiv: 2

HTTP Methods:
  GET: 23
  SEARCH: 2

Error Types:
  HTTP 404: 2
  Connection timeout: 1
  Invalid DOI format: 1
```

### Service Summary
```
============================================================
                    SERVICE SUMMARY                        
============================================================

ARXIV:
  Total calls: 2
  Success rate: 100.0%
  Average response time: 2,345.67 ms
  Total results: 2

CROSSREF:
  Total calls: 15
  Success rate: 86.7%
  Average response time: 1,123.45 ms
  Total results: 13

PUBMED:
  Total calls: 8
  Success rate: 75.0%
  Average response time: 987.65 ms
  Total results: 6
```

## Monitored APIs

### CrossRef
- **DOI Lookups**: `https://api.crossref.org/works/{doi}`
- **Title/Author Search**: `https://api.crossref.org/works?query=...`
- **Rate Limit**: 1 second between requests
- **Logged Parameters**: DOI, search query, filters

### PubMed (NCBI E-utilities)
- **PMID Lookups**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi`
- **Title/Author Search**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi`
- **Rate Limit**: 3 requests per second maximum
- **Logged Parameters**: PMID, search terms, database

### arXiv
- **Paper Lookups**: `http://export.arxiv.org/api/query`
- **Rate Limit**: 3 seconds between requests
- **Logged Parameters**: arXiv ID, search query

## Log Management

### Log Rotation
The current implementation uses a simple append-only log file. For production use, consider implementing log rotation:

```python
import logging.handlers

# Add this to paper_auditor/lookup.py for log rotation
api_handler = logging.handlers.RotatingFileHandler(
    api_log_file, 
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

### Log Retention
Consider implementing automatic cleanup of old logs:

```bash
# Example: Keep only last 30 days of logs
find logs/ -name "*.log" -mtime +30 -delete
```

## Troubleshooting

### No Logs Generated
1. Check if the `logs/` directory exists and is writable
2. Verify that API calls are actually being made
3. Check for Python permission issues

### Log Analysis Errors
1. Verify the log file path is correct
2. Check that the log file contains valid JSON entries
3. Ensure the log analyzer script has read permissions

### High Log Volume
1. Consider filtering logs by log level
2. Implement log rotation
3. Use the analyzer to identify high-volume sources

## Integration with Monitoring

The JSON log format makes it easy to integrate with monitoring systems:

### ELK Stack (Elasticsearch, Logstash, Kibana)
```json
# Logstash configuration
input {
  file {
    path => "/path/to/logs/api_calls.log"
    codec => json
  }
}
```

### Prometheus + Grafana
Extract metrics from logs for time-series monitoring:
- API call rate by service
- Success/failure rates
- Response time percentiles
- Error frequency

### Custom Monitoring
Parse the JSON logs with any monitoring tool that supports JSON log ingestion.

## Best Practices

1. **Monitor Regularly**: Check logs periodically for errors or performance issues
2. **Set Up Alerts**: Monitor for high error rates or slow response times
3. **Respect Rate Limits**: The logging will help you track if you're hitting rate limits
4. **Archive Old Logs**: Implement a log retention policy
5. **Security**: Be careful about logging sensitive parameters (though none are currently logged)

## API Rate Limits

The system respects API rate limits automatically:
- **CrossRef**: 1 second between requests
- **PubMed**: 0.34 seconds between requests (3/second max)
- **arXiv**: 3 seconds between requests

Rate limit timing is not logged but can be inferred from timestamps between consecutive calls to the same service. 