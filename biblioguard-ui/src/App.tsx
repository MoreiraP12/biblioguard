import React, { useState } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Container, Box, Typography, Card, CardContent, Select, MenuItem, FormControl, InputLabel, Paper, Stack, Tooltip, IconButton } from '@mui/material';
import { motion } from 'framer-motion';
import PdfUploader from './components/PdfUploader';
import CitationAnalysis from './components/CitationAnalysis';
import apiService from './services/api';
import './App.css';
import { Info as InfoIcon } from '@mui/icons-material';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#3b82f6',
      light: '#60a5fa',
      dark: '#1d4ed8',
    },
    secondary: {
      main: '#f59e0b',
      light: '#fbbf24',
      dark: '#d97706',
    },
    background: {
      default: '#f8fafc',
      paper: '#ffffff',
    },
    success: {
      main: '#10b981',
    },
    warning: {
      main: '#f59e0b',
    },
    error: {
      main: '#ef4444',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 700,
      fontSize: '2.5rem',
    },
    h2: {
      fontWeight: 600,
      fontSize: '2rem',
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.5rem',
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
          borderRadius: 16,
        },
      },
    },
  },
});

export interface CitationAudit {
  citation_key: string;
  original_text: string;
  metadata: {
    title?: string;
    authors: string[];
    year?: number;
    journal?: string;
    doi?: string;
    url?: string;
  };
  contexts: Array<{
    page_number?: number;
    section?: string;
    surrounding_text: string;
    claim_statement: string;
  }>;
  exists_online: boolean;
  existence_details: string;
  relevance?: {
    score: number;
    explanation: string;
  };
  justification?: {
    justified: boolean;
    rationale: string;
  };
  status: 'PASS' | 'SUSPECT' | 'MISSING';
  source_database?: string;
}

export interface AnalysisReport {
  paper_title: string;
  paper_authors: string[];
  total_citations: number;
  audited_citations: CitationAudit[];
  passed_count: number;
  suspect_count: number;
  missing_count: number;
}

function App() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [analysisReport, setAnalysisReport] = useState<AnalysisReport | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('gpt-3.5-turbo');

  const handleFileUpload = (file: File) => {
    setUploadedFile(file);
    setAnalysisReport(null);
  };

  const handleStartAnalysis = async () => {
    if (!uploadedFile) return;
    
    setIsAnalyzing(true);
    
    try {
      // Use real API
      console.log('Starting analysis with real API...');
      const apiReport = await apiService.uploadAndAnalyzePDF({
        file: uploadedFile,
        model: selectedModel,
        format: 'json'
      });
      
      console.log('Analysis completed successfully:', apiReport);
      setAnalysisReport(apiReport);
      
    } catch (error) {
      console.error('Analysis failed:', error);
      
      // Only show error, don't fall back to demo data
      alert(`Analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}. Please check that the backend is running and try again.`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ 
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        py: 4
      }}>
        <Container maxWidth="lg">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Box textAlign="center" mb={4}>
              <Typography 
                variant="h1" 
                component="h1" 
                sx={{ 
                  color: 'white',
                  mb: 2,
                  fontWeight: 800,
                  textShadow: '0 2px 4px rgba(0,0,0,0.3)'
                }}
              >
                BiblioGuard
              </Typography>
              <Typography 
                variant="h3" 
                component="h2" 
                sx={{ 
                  color: 'rgba(255,255,255,0.9)',
                  fontWeight: 400,
                  mb: 1
                }}
              >
                AI-Powered Citation Analysis
              </Typography>
              <Typography 
                variant="body1" 
                sx={{ 
                  color: 'rgba(255,255,255,0.8)',
                  fontSize: '1.1rem'
                }}
              >
                Upload your PDF and let our AI evaluate the quality and accuracy of your citations
              </Typography>
            </Box>
          </motion.div>

          <Typography 
            variant="h2" 
            component="p" 
            sx={{ 
              color: 'white',
              opacity: 0.9,
              fontWeight: 300,
              textShadow: '0 1px 2px rgba(0,0,0,0.2)'
            }}
          >
            AI-Powered Citation Verification
          </Typography>

          {/* Model Selection */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2 }}
          >
            <Paper 
              sx={{ 
                p: 3, 
                mb: 4, 
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                backdropFilter: 'blur(10px)',
                borderRadius: 3,
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
              }}
            >
              <Stack direction="row" alignItems="center" spacing={2} mb={2}>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  AI Model Configuration
                </Typography>
                <Tooltip 
                  title="Choose your preferred AI model. DeepSeek offers competitive performance at lower costs, while GPT-4 provides the highest accuracy."
                  arrow
                >
                  <IconButton size="small">
                    <InfoIcon />
                  </IconButton>
                </Tooltip>
              </Stack>
              
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} alignItems="center">
                <FormControl sx={{ minWidth: 200 }}>
                  <InputLabel>AI Model</InputLabel>
                  <Select
                    value={selectedModel}
                    label="AI Model"
                    onChange={(e) => setSelectedModel(e.target.value)}
                    disabled={isAnalyzing}
                  >
                    <MenuItem value="gpt-3.5-turbo">GPT-3.5 Turbo</MenuItem>
                    <MenuItem value="gpt-4">GPT-4</MenuItem>
                    <MenuItem value="gpt-4-turbo">GPT-4 Turbo</MenuItem>
                    <MenuItem value="gpt-4o">GPT-4o</MenuItem>
                    <MenuItem value="claude-3-haiku-20240307">Claude 3 Haiku</MenuItem>
                    <MenuItem value="claude-3-sonnet-20240229">Claude 3 Sonnet</MenuItem>
                    <MenuItem value="claude-3-opus-20240229">Claude 3 Opus</MenuItem>
                    <MenuItem value="deepseek-chat">DeepSeek Chat 💰</MenuItem>
                    <MenuItem value="deepseek-coder">DeepSeek Coder 💰</MenuItem>
                  </Select>
                </FormControl>
                
                <Box sx={{ flex: 1 }}>
                  {selectedModel.startsWith('deepseek') && (
                    <Typography variant="body2" color="success.main" sx={{ fontWeight: 500 }}>
                      💡 DeepSeek offers excellent performance at ~10x lower cost than GPT-4
                    </Typography>
                  )}
                  {selectedModel.startsWith('gpt-4') && (
                    <Typography variant="body2" color="primary.main" sx={{ fontWeight: 500 }}>
                      🎯 GPT-4 provides the highest accuracy for complex citation analysis
                    </Typography>
                  )}
                  {selectedModel.startsWith('claude') && (
                    <Typography variant="body2" color="secondary.main" sx={{ fontWeight: 500 }}>
                      🧠 Claude excels at nuanced reasoning and detailed explanations
                    </Typography>
                  )}
                  {selectedModel === 'gpt-3.5-turbo' && (
                    <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                      ⚡ Fast and cost-effective for most citation analysis tasks
                    </Typography>
                  )}
                </Box>
              </Stack>
            </Paper>
          </motion.div>

          <Card sx={{ 
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(10px)',
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
          }}>
            <CardContent sx={{ p: 4 }}>
              {!analysisReport ? (
                <PdfUploader
                  onFileUpload={handleFileUpload}
                  onStartAnalysis={handleStartAnalysis}
                  uploadedFile={uploadedFile}
                  isAnalyzing={isAnalyzing}
                />
              ) : (
                <CitationAnalysis report={analysisReport} />
              )}
            </CardContent>
          </Card>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;
