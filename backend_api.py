#!/usr/bin/env python3
"""
Flask API for BiblioGuard - Paper Citation Analysis
Integrates with the existing paper_auditor tool
"""

import os
import tempfile
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.exceptions import BadRequest, InternalServerError

# Import your existing paper auditor modules
try:
    from paper_auditor import PaperAuditor
    from paper_auditor.models import PaperAuditReport, CitationStatus
    from paper_auditor.reporters import generate_report
except ImportError as e:
    print(f"Warning: Could not import paper_auditor modules: {e}")
    print("Make sure you're running this from the project root directory")
    PaperAuditor = None

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"])  # Allow React dev server

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = tempfile.mkdtemp()

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def transform_citation_status(status: CitationStatus) -> str:
    """Transform CitationStatus enum to string for JSON serialization."""
    if hasattr(status, 'value'):
        if status == CitationStatus.PASS:
            return 'PASS'
        elif status == CitationStatus.SUSPECT:
            return 'SUSPECT'
        elif status == CitationStatus.MISSING:
            return 'MISSING'
    return 'MISSING'

def transform_audit_report_to_json(report: PaperAuditReport) -> Dict[str, Any]:
    """Transform PaperAuditReport to JSON-serializable dictionary."""
    return {
        "paper": {
            "title": report.paper_title,
            "authors": report.paper_authors
        },
        "total_citations": report.total_citations,
        "summary": {
            "passed_count": report.passed_count,
            "suspect_count": report.suspect_count,
            "missing_count": report.missing_count,
            "pass_rate": round((report.passed_count / report.total_citations) * 100, 1) if report.total_citations > 0 else 0
        },
        "citations": [
            {
                "citation_key": citation.citation_key,
                "original_text": citation.original_text,
                "metadata": {
                    "title": citation.metadata.title,
                    "authors": citation.metadata.authors,
                    "year": citation.metadata.year,
                    "journal": citation.metadata.journal,
                    "volume": citation.metadata.volume,
                    "pages": citation.metadata.pages,
                    "doi": citation.metadata.doi,
                    "pmid": citation.metadata.pmid,
                    "arxiv_id": citation.metadata.arxiv_id,
                    "url": citation.metadata.url,
                    "abstract": citation.metadata.abstract
                },
                "contexts": [
                    {
                        "page_number": context.page_number,
                        "section": context.section,
                        "surrounding_text": context.surrounding_text,
                        "claim_statement": context.claim_statement
                    }
                    for context in citation.contexts
                ],
                "exists_online": citation.exists_online,
                "existence_details": citation.existence_details,
                "relevance": {
                    "score": citation.relevance.score,
                    "explanation": citation.relevance.explanation
                } if citation.relevance else None,
                "justification": {
                    "justified": citation.justification.justified,
                    "rationale": citation.justification.rationale
                } if citation.justification else None,
                "status": transform_citation_status(citation.status),
                "source_database": citation.source_database
            }
            for citation in report.audited_citations
        ],
        "generated_at": datetime.now().isoformat(),
        "tool_version": "1.0.0"
    }

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "paper_auditor_available": PaperAuditor is not None
    })

@app.route('/models', methods=['GET'])
def get_supported_models():
    """Get list of supported LLM models."""
    models = {
        "openai": [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini"
        ],
        "anthropic": [
            "claude-3-sonnet-20240229",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022"
        ],
        "deepseek": [
            "deepseek-chat",
            "deepseek-coder"
        ]
    }
    
    # Flat list for backward compatibility
    all_models = []
    for provider_models in models.values():
        all_models.extend(provider_models)
    
    return jsonify({
        "models": all_models,
        "models_by_provider": models,
        "api_keys_required": {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY", 
            "deepseek": "DEEPSEEK_API_KEY"
        },
        "instructions": {
            "deepseek": "To use DeepSeek models, set DEEPSEEK_API_KEY environment variable or pass api_key parameter. DeepSeek offers competitive performance at lower costs."
        }
    })

@app.route('/analyze', methods=['POST'])
def analyze_pdf():
    """Main endpoint for PDF citation analysis."""
    if PaperAuditor is None:
        return jsonify({
            "error": "Paper auditor not available. Please check the installation."
        }), 500

    # Check if file is present
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only PDF files are allowed."}), 400

    try:
        # Get optional parameters
        model_type = request.form.get('model', 'gpt-3.5-turbo')
        output_format = request.form.get('format', 'json')
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        temp_filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(temp_filepath)
        
        # Initialize paper auditor
        auditor = PaperAuditor(model_type=model_type)
        
        # Perform analysis
        print(f"Starting analysis of {filename} with model {model_type}")
        report = auditor.audit_paper(temp_filepath)
        
        # Clean up temp file
        os.remove(temp_filepath)
        
        # Transform report to JSON
        json_report = transform_audit_report_to_json(report)
        
        print(f"Analysis completed. Found {report.total_citations} citations.")
        print(f"Results: {report.passed_count} passed, {report.suspect_count} suspect, {report.missing_count} missing")
        
        return jsonify(json_report)
    
    except Exception as e:
        # Clean up temp file if it exists
        if 'temp_filepath' in locals() and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
        
        print(f"Error during analysis: {str(e)}")
        return jsonify({
            "error": f"Analysis failed: {str(e)}"
        }), 500

@app.route('/demo', methods=['GET'])
def get_demo_data():
    """Get demo data for frontend testing."""
    demo_report = {
        "paper": {
            "title": "Machine Learning Applications in Healthcare: A Comprehensive Survey",
            "authors": ["Dr. Jane Smith", "Prof. John Doe", "Dr. Alice Johnson"]
        },
        "total_citations": 15,
        "summary": {
            "passed_count": 10,
            "suspect_count": 3,
            "missing_count": 2,
            "pass_rate": 66.7
        },
        "citations": [
            {
                "citation_key": "smith2023",
                "original_text": "Smith et al. (2023) demonstrated that machine learning algorithms can improve diagnostic accuracy by 25%.",
                "metadata": {
                    "title": "Advanced Machine Learning Techniques for Medical Diagnosis",
                    "authors": ["Smith, J.", "Brown, A.", "Wilson, K."],
                    "year": 2023,
                    "journal": "Journal of Medical AI",
                    "doi": "10.1234/jmai.2023.001"
                },
                "contexts": [{
                    "page_number": 3,
                    "section": "Related Work",
                    "surrounding_text": "Recent advances in medical AI have shown promising results. Smith et al. (2023) demonstrated that machine learning algorithms can improve diagnostic accuracy by 25%. This improvement is particularly significant in radiology applications.",
                    "claim_statement": "machine learning algorithms can improve diagnostic accuracy by 25%"
                }],
                "exists_online": True,
                "existence_details": "Found in PubMed and CrossRef databases",
                "relevance": {
                    "score": 5,
                    "explanation": "Highly relevant to the paper's topic on ML in healthcare diagnostics"
                },
                "justification": {
                    "justified": True,
                    "rationale": "The citation properly supports the claim about diagnostic accuracy improvement with specific quantitative evidence"
                },
                "status": "PASS",
                "source_database": "PubMed"
            },
            {
                "citation_key": "johnson2022",
                "original_text": "Johnson et al. (2022) found that deep learning models outperform traditional methods in all medical domains.",
                "metadata": {
                    "title": "Deep Learning in Medical Image Analysis",
                    "authors": ["Johnson, M.", "Davis, R."],
                    "year": 2022,
                    "journal": "Medical Imaging Review",
                    "doi": "10.1234/mir.2022.045"
                },
                "contexts": [{
                    "page_number": 5,
                    "section": "Methodology",
                    "surrounding_text": "Our approach builds on previous work in medical AI. Johnson et al. (2022) found that deep learning models outperform traditional methods in all medical domains. However, their study focused primarily on image analysis rather than general diagnostics.",
                    "claim_statement": "deep learning models outperform traditional methods in all medical domains"
                }],
                "exists_online": True,
                "existence_details": "Found in CrossRef database",
                "relevance": {
                    "score": 3,
                    "explanation": "Partially relevant - focuses on image analysis while paper discusses broader applications"
                },
                "justification": {
                    "justified": False,
                    "rationale": "The claim is overly broad. The cited paper only covers medical image analysis, not 'all medical domains' as claimed. The citation misrepresents the scope of the original research."
                },
                "status": "SUSPECT",
                "source_database": "CrossRef"
            }
        ],
        "generated_at": datetime.now().isoformat(),
        "tool_version": "1.0.0"
    }
    
    return jsonify(demo_report)

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 50MB."}), 413

@app.errorhandler(400)
def bad_request(e):
    return jsonify({"error": "Bad request"}), 400

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    print("Starting BiblioGuard API server...")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    print(f"Paper auditor available: {PaperAuditor is not None}")
    
    # Create upload directory if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Get port from environment variable or default to 8000
    port = int(os.getenv('PORT', 8000))
    print(f"Server will run on port: {port}")
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True,
        threaded=True
    ) 