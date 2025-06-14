"""
Command-line interface for the paper auditor tool.
"""

import os
import sys
import logging
from pathlib import Path

import click
from dotenv import load_dotenv

from .auditor import PaperAuditor
from .reporters import generate_report

# Load environment variables
load_dotenv()


def setup_logging(verbose: bool):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )


@click.command()
@click.argument('paper_path', type=click.Path(exists=True))
@click.option(
    '--references', '-r',
    type=click.Path(exists=True),
    help='Path to BibTeX (.bib) or CSL JSON (.json) reference file'
)
@click.option(
    '--model', '-m',
    default='gpt-3.5-turbo',
    help='LLM model to use for evaluation (gpt-3.5-turbo, gpt-4, claude-3-sonnet-20240229, etc.)',
    show_default=True
)
@click.option(
    '--output', '-o',
    type=click.Path(),
    help='Output file path (default: stdout)'
)
@click.option(
    '--format', 'output_format',
    type=click.Choice(['markdown', 'json'], case_sensitive=False),
    default='markdown',
    help='Output format',
    show_default=True
)
@click.option(
    '--api-key',
    help='API key for LLM service (can also use OPENAI_API_KEY or ANTHROPIC_API_KEY env vars)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose logging'
)
@click.option(
    '--cache-size',
    type=int,
    default=1000,
    help='Cache size for API responses',
    show_default=True
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Extract and show citations without making API calls'
)
def audit(
    paper_path: str,
    references: str,
    model: str,
    output: str,
    output_format: str,
    api_key: str,
    verbose: bool,
    cache_size: int,
    dry_run: bool
):
    """
    Audit the references of a research paper.
    
    PAPER_PATH: Path to the research paper (PDF or text file)
    
    Examples:
    
        # Audit with separate BibTeX file
        paper-auditor paper.pdf --references refs.bib
        
        # Use Claude model
        paper-auditor paper.pdf --model claude-3-sonnet-20240229
        
        # Output to JSON file
        paper-auditor paper.pdf --format json --output report.json
        
        # Dry run to see extracted citations
        paper-auditor paper.pdf --dry-run
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Validate inputs
        if not Path(paper_path).exists():
            click.echo(f"Error: Paper file '{paper_path}' not found", err=True)
            sys.exit(1)
        
        if references and not Path(references).exists():
            click.echo(f"Error: References file '{references}' not found", err=True)
            sys.exit(1)
        
        # Setup model kwargs
        model_kwargs = {}
        if api_key:
            model_kwargs['api_key'] = api_key
        
        # Determine model type for factory
        if model.startswith(('gpt', 'openai')):
            model_type = 'openai'
            model_kwargs['model'] = model
        elif model.startswith(('claude', 'anthropic')):
            model_type = 'anthropic'
            model_kwargs['model'] = model
        else:
            model_type = model  # Pass through for other models
        
        # Check for API keys
        if not dry_run:
            if model_type == 'openai' and not (api_key or os.getenv('OPENAI_API_KEY')):
                click.echo("Error: OpenAI API key required. Set OPENAI_API_KEY environment variable or use --api-key", err=True)
                sys.exit(1)
            elif model_type == 'anthropic' and not (api_key or os.getenv('ANTHROPIC_API_KEY')):
                click.echo("Error: Anthropic API key required. Set ANTHROPIC_API_KEY environment variable or use --api-key", err=True)
                sys.exit(1)
        
        logger.info(f"Starting audit of {paper_path}")
        
        if dry_run:
            click.echo("🔍 Dry run mode - extracting citations without API calls...")
            # TODO: Implement dry run functionality
            from .extractors import PaperExtractor, ReferenceExtractor
            
            extractor = PaperExtractor()
            if paper_path.endswith('.pdf'):
                text, contexts = extractor.extract_from_pdf(paper_path)
            else:
                text, contexts = extractor.extract_from_text(paper_path)
            
            title, authors = extractor.extract_paper_metadata(text)
            
            click.echo(f"\n📄 Paper: {title}")
            click.echo(f"👥 Authors: {', '.join(authors) if authors else 'Unknown'}")
            click.echo(f"🔗 Found {len(contexts)} citation contexts")
            
            if references:
                ref_extractor = ReferenceExtractor()
                if references.endswith('.bib'):
                    refs = ref_extractor.extract_from_bibtex(references)
                else:
                    refs = ref_extractor.extract_from_csl_json(references)
                click.echo(f"📚 Found {len(refs)} references")
            
            return
        
        # Initialize auditor
        auditor = PaperAuditor(use_fallback_lookups=True, use_advanced_nlp=True)
        
        # Run audit
        click.echo("🔍 Auditing paper references...")
        with click.progressbar(length=100, label='Processing') as bar:
            report = auditor.audit_paper(paper_path, references, output_format)
            bar.update(100)
        
        # Generate report
        report_content = generate_report(report, output_format)
        
        # Output results
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(report_content)
            click.echo(f"✅ Report saved to {output}")
        else:
            click.echo(report_content)
        
        # Summary
        click.echo(f"\n📊 Summary: {report.passed_count} passed, "
                  f"{report.suspect_count} suspect, {report.missing_count} missing")
        
        # Exit with error code if there are issues
        if report.suspect_count > 0 or report.missing_count > 0:
            sys.exit(1)
        
    except KeyboardInterrupt:
        click.echo("\n❌ Audit cancelled by user", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument('config_name')
@click.argument('config_value')
def config(config_name: str, config_value: str):
    """Set configuration values."""
    config_file = Path.home() / '.paper-auditor' / 'config'
    config_file.parent.mkdir(exist_ok=True)
    
    # Simple key=value config file
    configs = {}
    if config_file.exists():
        with open(config_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    configs[key] = value
    
    configs[config_name] = config_value
    
    with open(config_file, 'w') as f:
        for key, value in configs.items():
            f.write(f"{key}={value}\n")
    
    click.echo(f"✅ Set {config_name} = {config_value}")


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    Paper Reference Auditor
    
    A tool for auditing the references of research papers to verify their
    existence, relevance, and justification for claims made in the paper.
    """
    pass


cli.add_command(audit)
cli.add_command(config)


if __name__ == '__main__':
    cli() 