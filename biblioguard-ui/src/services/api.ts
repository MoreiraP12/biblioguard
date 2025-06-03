import { AnalysisReport } from '../App';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface AnalysisRequest {
  file: File;
  model?: string;
  format?: string;
}

export interface AnalysisProgress {
  status: 'processing' | 'completed' | 'error';
  progress: number;
  message: string;
  report?: AnalysisReport;
  error?: string;
}

class ApiService {
  async uploadAndAnalyzePDF(request: AnalysisRequest): Promise<AnalysisReport> {
    const formData = new FormData();
    formData.append('file', request.file);
    
    if (request.model) {
      formData.append('model', request.model);
    }
    
    if (request.format) {
      formData.append('format', request.format);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        body: formData,
        // Don't set Content-Type header, let browser set it with boundary for FormData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return this.transformBackendResponse(result);
    } catch (error) {
      console.error('API Error:', error);
      throw new Error('Failed to analyze PDF. Please try again.');
    }
  }

  async getAnalysisProgress(taskId: string): Promise<AnalysisProgress> {
    try {
      const response = await fetch(`${API_BASE_URL}/analysis/${taskId}/status`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Progress check error:', error);
      throw new Error('Failed to check analysis progress.');
    }
  }

  private transformBackendResponse(backendData: any): AnalysisReport {
    // Transform the Python backend response to match our frontend interface
    return {
      paper_title: backendData.paper?.title || 'Unknown Title',
      paper_authors: backendData.paper?.authors || [],
      total_citations: backendData.total_citations || 0,
      passed_count: backendData.summary?.passed_count || 0,
      suspect_count: backendData.summary?.suspect_count || 0,
      missing_count: backendData.summary?.missing_count || 0,
      audited_citations: (backendData.citations || []).map((citation: any) => ({
        citation_key: citation.citation_key,
        original_text: citation.original_text,
        metadata: {
          title: citation.metadata?.title,
          authors: citation.metadata?.authors || [],
          year: citation.metadata?.year,
          journal: citation.metadata?.journal,
          doi: citation.metadata?.doi,
          url: citation.metadata?.url,
        },
        contexts: (citation.contexts || []).map((context: any) => ({
          page_number: context.page_number,
          section: context.section,
          surrounding_text: context.surrounding_text,
          claim_statement: context.claim_statement,
        })),
        exists_online: citation.exists_online,
        existence_details: citation.existence_details,
        relevance: citation.relevance ? {
          score: citation.relevance.score,
          explanation: citation.relevance.explanation,
        } : undefined,
        justification: citation.justification ? {
          justified: citation.justification.justified,
          rationale: citation.justification.rationale,
        } : undefined,
        status: this.mapBackendStatus(citation.status),
        source_database: citation.source_database,
      })),
    };
  }

  private mapBackendStatus(backendStatus: string): 'PASS' | 'SUSPECT' | 'MISSING' {
    // Map backend status values to frontend enum values
    switch (backendStatus?.toLowerCase()) {
      case 'pass':
      case 'valid':
      case 'passed':
        return 'PASS';
      case 'suspect':
      case 'warning':
      case 'questionable':
        return 'SUSPECT';
      case 'missing':
      case 'error':
      case 'failed':
      case 'not_found':
        return 'MISSING';
      default:
        return 'MISSING';
    }
  }

  // Utility method to check if the backend is available
  async checkHealth(): Promise<boolean> {
    try {
      // Create an AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(`${API_BASE_URL}/health`, {
        method: 'GET',
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      return response.ok;
    } catch (error) {
      console.warn('Backend health check failed:', error);
      return false;
    }
  }

  // Method to get supported models from backend
  async getSupportedModels(): Promise<string[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/models`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      return data.models || ['gpt-3.5-turbo', 'claude-3-sonnet-20240229'];
    } catch (error) {
      console.warn('Failed to fetch models:', error);
      // Return default models if API call fails
      return ['gpt-3.5-turbo', 'claude-3-sonnet-20240229'];
    }
  }
}

export const apiService = new ApiService();
export default apiService; 