# Examples

This directory contains example usage of the Paper Reference Auditor tool, organized into demo scripts and sample data.

## Directory Structure

```
examples/
├── demo_scripts/           # Demonstration scripts
│   └── demo_script.py     # Main demo script
├── sample_data/           # Sample files for testing and demonstration
│   ├── audit_report.json # Example audit report output
│   ├── sample_paper.txt  # Sample academic paper text
│   └── sample_references.bib # Sample BibTeX references
└── README.md             # This file
```

## Demo Scripts

### `demo_scripts/demo_script.py`

A comprehensive demonstration script showing:
- How to use the Paper Auditor API programmatically
- Different configuration options
- Example workflows for common use cases

**Usage:**
```bash
cd examples/demo_scripts
python demo_script.py
```

**Requirements:**
- Set up API keys (OpenAI or Anthropic)
- Install the paper-auditor package

## Sample Data

### `sample_data/sample_paper.txt`
A sample academic paper in plain text format that includes:
- Multiple citations in various formats
- Different citation contexts
- References section

### `sample_data/sample_references.bib`
A BibTeX file containing:
- Various types of academic references
- Examples of different publication types (journals, conferences, books, etc.)
- Properly formatted BibTeX entries

### `sample_data/audit_report.json`
An example output from the audit tool showing:
- Complete audit results structure
- Citation verification outcomes
- Relevance and justification assessments
- Summary statistics

## Usage Examples

### Basic CLI Usage with Sample Data

```bash
# Audit the sample paper with embedded references
paper-auditor examples/sample_data/sample_paper.txt

# Audit with external BibTeX file
paper-auditor examples/sample_data/sample_paper.txt \
  --references examples/sample_data/sample_references.bib

# Generate different output formats
paper-auditor examples/sample_data/sample_paper.txt \
  --format json \
  --output examples/sample_data/my_audit.json

paper-auditor examples/sample_data/sample_paper.txt \
  --format markdown \
  --output examples/sample_data/my_audit.md
```

### API Usage Examples

```python
from paper_auditor import PaperAuditor
from paper_auditor.reporters import generate_report

# Initialize auditor
auditor = PaperAuditor(model_type="gpt-3.5-turbo")

# Audit sample paper
report = auditor.audit_paper(
    "examples/sample_data/sample_paper.txt",
    "examples/sample_data/sample_references.bib"
)

# Generate report
markdown_report = generate_report(report, "markdown")
print(markdown_report)
```

### Testing Different Models

```bash
# Test with different LLM models
paper-auditor examples/sample_data/sample_paper.txt --model gpt-4
paper-auditor examples/sample_data/sample_paper.txt --model claude-3-sonnet-20240229
paper-auditor examples/sample_data/sample_paper.txt --model gpt-3.5-turbo
```

### Dry Run Mode

Test the extraction and parsing without making API calls:

```bash
paper-auditor examples/sample_data/sample_paper.txt --dry-run
```

## Creating Your Own Examples

### Adding New Sample Papers

1. Place text files in `sample_data/`
2. Use descriptive filenames (e.g., `ml_healthcare_paper.txt`)
3. Ensure papers contain clear citation patterns
4. Include a variety of citation formats

### Adding New Demo Scripts

1. Create scripts in `demo_scripts/`
2. Include clear documentation and comments
3. Show different aspects of the tool
4. Handle API keys gracefully (with fallbacks)

### Sample Data Guidelines

- **Papers**: Should be representative of real academic papers but not copyrighted content
- **References**: Include diverse publication types and formats
- **Reports**: Show both successful and problematic citation examples

## API Key Setup

Before running examples that require LLM evaluation:

```bash
# Option 1: Environment variables
export OPENAI_API_KEY="your-openai-api-key"
# OR
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Option 2: Create .env file in project root
echo "OPENAI_API_KEY=your-openai-api-key" > .env
```

## Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure your API keys are set correctly
2. **Rate Limiting**: Use `--dry-run` to test without API calls
3. **File Paths**: Run commands from the project root directory

### Getting Help

```bash
# Show all available options
paper-auditor --help

# Show detailed help for specific commands
paper-auditor examples/sample_data/sample_paper.txt --help
```

## Contributing Examples

When contributing new examples:

1. Test thoroughly with the sample data
2. Include clear documentation
3. Follow the existing naming conventions
4. Update this README with new examples 