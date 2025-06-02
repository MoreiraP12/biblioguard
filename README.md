# Paper Reference Auditor

A comprehensive Python tool for auditing the references of research papers. This tool verifies the existence, relevance, and justification of citations to help ensure academic integrity and quality.

## Features

- ✅ **Citation Verification**: Checks if citations actually exist online using multiple databases
- 🔍 **Relevance Assessment**: Uses LLM to evaluate topical relevance of citations (0-5 scale)
- ⚖️ **Justification Analysis**: Determines if citations properly support the claims they accompany
- 🌐 **Multiple APIs**: Integrates with CrossRef, PubMed, arXiv, and Google Scholar
- 🤖 **LLM Support**: Works with OpenAI GPT and Anthropic Claude models
- 📊 **Rich Reports**: Generates detailed Markdown or JSON reports
- ⚡ **Caching**: Built-in API response caching to respect rate limits

## Installation

### Prerequisites

- Python 3.8 or higher
- API key for either OpenAI or Anthropic (for LLM evaluation)

### Install from source

```bash
git clone https://github.com/paper-auditor/paper-auditor.git
cd paper-auditor
pip install -r requirements.txt
pip install -e .
```

### Install via pip (when available)

```bash
pip install paper-auditor
```

## Quick Start

### 1. Set up API keys

```bash
export OPENAI_API_KEY="your-openai-api-key"
# OR
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### 2. Basic usage

```bash
# Audit a paper with embedded references
paper-auditor paper.pdf

# Audit with separate BibTeX file
paper-auditor paper.pdf --references refs.bib

# Use Claude instead of GPT
paper-auditor paper.pdf --model claude-3-sonnet-20240229

# Save report to file
paper-auditor paper.pdf --output report.md --format markdown
```

## Usage Examples

### Command Line Interface

```bash
# Basic audit
paper-auditor research_paper.pdf

# Audit with external references
paper-auditor paper.pdf --references references.bib

# Use specific model
paper-auditor paper.pdf --model gpt-4

# Generate JSON report
paper-auditor paper.pdf --format json --output audit_report.json

# Dry run (extract citations without API calls)
paper-auditor paper.pdf --dry-run

# Verbose output
paper-auditor paper.pdf --verbose
```

### Python API

```python
from paper_auditor import PaperAuditor
from paper_auditor.reporters import generate_report

# Initialize auditor
auditor = PaperAuditor(model_type="gpt-3.5-turbo")

# Audit a paper
report = auditor.audit_paper("paper.pdf", "references.bib")

# Generate report
markdown_report = generate_report(report, "markdown")
print(markdown_report)

# Access individual results
for citation in report.audited_citations:
    print(f"Citation: {citation.metadata.title}")
    print(f"Status: {citation.status.value}")
    print(f"Relevance: {citation.relevance.score}/5")
    print(f"Justified: {citation.justification.justified}")
```

## Supported Input Formats

### Papers
- **PDF files** (.pdf) - Extracted using pdfplumber
- **Plain text** (.txt) - Direct text processing

### References
- **BibTeX** (.bib) - Standard academic reference format
- **CSL JSON** (.json) - Citation Style Language JSON format
- **Embedded in paper** - Extracted from References section

## LLM Models

### OpenAI Models
- `gpt-3.5-turbo` (default, fast and cost-effective)
- `gpt-4` (higher quality, slower)
- `gpt-4-turbo`

### Anthropic Models
- `claude-3-sonnet-20240229` (balanced performance)
- `claude-3-opus-20240229` (highest quality)
- `claude-3-haiku-20240307` (fastest)

## Output Formats

### Markdown Report
```markdown
# Paper Reference Audit Report

**Generated**: 2024-01-15 10:30:00

## Paper Information
**Title**: Machine Learning in Healthcare
**Total Citations**: 25

## Summary
- ✅ **Passed**: 20 citations
- ⚠️ **Suspect**: 3 citations  
- ❌ **Missing**: 2 citations
```

### JSON Report
```json
{
  "metadata": {
    "generated_at": "2024-01-15T10:30:00",
    "tool_version": "1.0.0"
  },
  "paper": {
    "title": "Machine Learning in Healthcare",
    "total_citations": 25
  },
  "summary": {
    "passed_count": 20,
    "suspect_count": 3,
    "missing_count": 2,
    "pass_rate": 80.0
  },
  "citations": [...]
}
```

## Configuration

### Environment Variables
```bash
OPENAI_API_KEY="your-openai-key"
ANTHROPIC_API_KEY="your-anthropic-key"
```

### Config File
```bash
paper-auditor config default_model gpt-4
paper-auditor config cache_size 2000
```

## API Integration

The tool integrates with several academic databases:

- **CrossRef**: DOI resolution and metadata
- **PubMed**: Biomedical literature
- **arXiv**: Preprint repository
- **Google Scholar**: Broad academic search (rate limited)

## Rate Limiting

Built-in rate limiting respects API guidelines:
- CrossRef: 1 request/second
- PubMed: 3 requests/second
- arXiv: 1 request/3 seconds

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

### Development Setup

```bash
# Quick setup with all development tools
make dev-setup

# Manual setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
make install-dev
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration

# Traditional pytest
python -m pytest tests/
```

### Code Quality

```bash
# Format and lint code
make format
make lint

# Individual tools
black paper_auditor/
flake8 paper_auditor/
```

### Development Workflow

For detailed development information, see [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

Available make commands:
- `make help` - Show all available commands
- `make install` - Install package and dependencies
- `make test` - Run all tests
- `make lint` - Run code quality checks
- `make format` - Format code
- `make clean` - Clean build artifacts
- `make build` - Build package for distribution

## Project Structure

```
paper_auditor/
├── docs/                    # Documentation
├── examples/                # Example usage and sample data
│   ├── demo_scripts/        # Demo scripts
│   └── sample_data/         # Sample papers and references
├── paper_auditor/           # Main package
├── tests/                   # Test suite
├── Makefile                 # Development commands
├── pytest.ini             # Test configuration
└── requirements.txt        # Dependencies
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Citation

If you use this tool in academic work, please cite:

```bibtex
@software{paper_auditor,
  title={Paper Reference Auditor},
  author={Paper Auditor Team},
  url={https://github.com/paper-auditor/paper-auditor},
  version={1.0.0},
  year={2024}
}
```

## Support

- 📖 [Documentation](https://paper-auditor.readthedocs.io)
- 🐛 [Issue Tracker](https://github.com/paper-auditor/paper-auditor/issues)
- 💬 [Discussions](https://github.com/paper-auditor/paper-auditor/discussions)

## Roadmap

- [ ] Web interface
- [ ] Integration with reference managers (Zotero, Mendeley)
- [ ] Support for more LLM providers
- [ ] Advanced citation matching algorithms
- [ ] Batch processing capabilities
- [ ] Citation network analysis 