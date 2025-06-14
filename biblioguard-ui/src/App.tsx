import React, { useState, useRef } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Container, Box, Typography, Card, CardContent, Select, MenuItem, FormControl, InputLabel, Paper, Stack, Tooltip, IconButton, Alert } from '@mui/material';
import { motion } from 'framer-motion';
import PdfUploader from './components/PdfUploader';
import CitationAnalysis from './components/CitationAnalysis';
import apiService from './services/api';
import './App.css';
import { Info as InfoIcon } from '@mui/icons-material';

// New type definitions
interface Bubble {
  delay: string;
  size: string;
  color: string;
  borderRadius: string;
}

interface Ripple {
  x: number;
  y: number;
  id: number;
  bubbles: Bubble[];
}

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#0052ff', // Coinbase blue
      light: '#4285f4',
      dark: '#0041cc',
    },
    secondary: {
      main: '#00d4aa', // Coinbase teal accent
      light: '#26e3c0',
      dark: '#00b894',
    },
    background: {
      default: '#ffffff',
      paper: '#ffffff',
    },
    success: {
      main: '#00d4aa',
    },
    warning: {
      main: '#ff9500',
    },
    error: {
      main: '#ff4747',
    },
    text: {
      primary: '#0e1116',
      secondary: '#5b616e',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontWeight: 600,
      fontSize: '3rem',
      lineHeight: 1.2,
    },
    h2: {
      fontWeight: 500,
      fontSize: '2rem',
      lineHeight: 1.3,
    },
    h3: {
      fontWeight: 500,
      fontSize: '1.5rem',
      lineHeight: 1.4,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          borderRadius: 8,
          border: '1px solid #e6e8ea',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
          borderRadius: 8,
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

// Simple Error Boundary Component
class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error?: Error }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('CitationAnalysis rendering error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <Alert severity="error" sx={{ m: 2 }}>
          <Typography variant="h6" gutterBottom>
            Analysis Display Error
          </Typography>
          <Typography variant="body2">
            There was an error displaying the analysis results. This might be due to unexpected data format from the backend.
          </Typography>
          <Typography variant="body2" sx={{ mt: 1, fontFamily: 'monospace', fontSize: '0.8rem' }}>
            Error: {this.state.error?.message}
          </Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            Please check the browser console for more details and try again.
          </Typography>
        </Alert>
      );
    }

    return this.props.children;
  }
}

function App() {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [analysisReport, setAnalysisReport] = useState<AnalysisReport | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string>('gpt-3.5-turbo');
  const [ripples, setRipples] = useState<Ripple[]>([]);
  const rippleTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (rippleTimeoutRef.current) {
        return;
    }

    // Limit total number of ripples for performance
    if (ripples.length >= 6) {
      setRipples(prev => prev.slice(1)); // Remove oldest ripple
    }

    const createBubbles = (): Bubble[] => {
        const baseSize = 300;
        
        // Blue to green color palette
        const colors = [
            'rgba(37, 99, 235, 0.6)',   // Pure Blue
            'rgba(59, 130, 246, 0.6)',  // Light Blue
            'rgba(14, 165, 233, 0.6)',  // Sky Blue
            'rgba(6, 182, 212, 0.6)',   // Cyan
            'rgba(20, 184, 166, 0.6)',  // Teal
            'rgba(16, 185, 129, 0.6)',  // Emerald
            'rgba(34, 197, 94, 0.6)',   // Green
            'rgba(0, 150, 136, 0.6)',   // Deep Teal
        ];
        
        const randomColor = colors[Math.floor(Math.random() * colors.length)];
        
        return [{
            delay: '0s',
            color: randomColor,
            size: `${baseSize + Math.random() * 100}px`,
            borderRadius: `${Math.floor(Math.random() * 25 + 40)}% ${Math.floor(Math.random() * 25 + 40)}% ${Math.floor(Math.random() * 25 + 40)}% ${Math.floor(Math.random() * 25 + 40)}%`,
        }];
    };

    const newRipple: Ripple = {
      x: e.clientX,
      y: e.clientY,
      id: Date.now(),
      bubbles: createBubbles(),
    };

    setRipples(prev => [...prev, newRipple]);

    rippleTimeoutRef.current = setTimeout(() => {
        if (rippleTimeoutRef.current) {
            clearTimeout(rippleTimeoutRef.current);
        }
        rippleTimeoutRef.current = null;
    }, 200); // Even more throttling for performance
  };

  const handleAnimationEnd = (id: number) => {
    setRipples(prev => prev.filter(r => r.id !== id));
  };

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
      console.log('Report structure check:', {
        paper_title: typeof apiReport.paper_title,
        paper_authors: Array.isArray(apiReport.paper_authors),
        total_citations: typeof apiReport.total_citations,
        audited_citations: Array.isArray(apiReport.audited_citations),
        first_citation: apiReport.audited_citations?.[0]
      });
      
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
      <Box 
        onMouseMove={handleMouseMove}
        sx={{ 
          minHeight: '100vh',
          position: 'relative',
          overflow: 'hidden',
          pt: 8,
          pb: 4,
          backgroundColor: '#f1f5f9'
        }}
      >
        {/* Ripple Effect Container */}
        <Box sx={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', overflow: 'hidden', zIndex: 0, pointerEvents: 'none' }}>
          {ripples.map(ripple => (
            <React.Fragment key={ripple.id}>
              {ripple.bubbles.map((bubble, index) => (
                <Box
                  key={index}
                  onAnimationEnd={() => handleAnimationEnd(ripple.id)}
                  sx={{
                    position: 'absolute',
                    left: ripple.x,
                    top: ripple.y,
                    borderRadius: bubble.borderRadius,
                    transform: 'translate(-50%, -50%) scale(0)',
                    width: '1px',
                    height: '1px',
                    boxShadow: `0 0 25px 25px ${bubble.color}`,
                    animation: `ripple-wave 1.2s ease-out ${bubble.delay} forwards`,
                    '@keyframes ripple-wave': {
                      '0%': {
                        transform: `translate(-50%, -50%) scale(0)`,
                        opacity: 1,
                      },
                      '100%': {
                        transform: `translate(-50%, -50%) scale(1)`,
                        width: bubble.size,
                        height: bubble.size,
                        opacity: 0,
                      }
                    }
                  }}
                />
              ))}
            </React.Fragment>
          ))}
        </Box>

        <Container maxWidth="lg" sx={{ position: 'relative', zIndex: 2 }}>
          {/* Clean Header Section */}
          <Box textAlign="center" mb={8}>
            <Typography 
              variant="h1" 
              component="h1" 
              sx={{ 
                color: 'text.primary',
                mb: 3,
                fontWeight: 600
              }}
            >
              BiblioGuard
            </Typography>
            <Typography 
              variant="h3" 
              component="h2" 
              sx={{ 
                color: 'text.secondary',
                fontWeight: 400,
                mb: 2,
                maxWidth: '600px',
                mx: 'auto'
              }}
            >
              AI-powered citation verification for academic papers
            </Typography>
            <Typography 
              variant="body1" 
              sx={{ 
                color: 'text.secondary',
                fontSize: '1.1rem',
                maxWidth: '500px',
                mx: 'auto'
              }}
            >
              Upload your PDF and get instant analysis of citation quality and accuracy
            </Typography>
          </Box>

          {/* Model Selection - Clean Design */}
          <Paper 
            sx={{ 
              p: 4, 
              mb: 4,
              border: '1px solid #e6e8ea',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
              backgroundColor: 'rgba(255, 255, 255, 0.9)',
              backdropFilter: 'blur(12px)',
              borderRadius: 4
            }}
          >
            <Stack spacing={3}>
              <Stack direction="row" alignItems="center" spacing={2}>
                <Typography variant="h6" sx={{ fontWeight: 500, color: 'text.primary' }}>
                  AI Model
                </Typography>
                <Tooltip 
                  title="Choose your preferred AI model for citation analysis"
                  arrow
                >
                  <IconButton size="small" sx={{ color: 'text.secondary' }}>
                    <InfoIcon />
                  </IconButton>
                </Tooltip>
              </Stack>
              
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={4} alignItems="flex-start">
                <FormControl sx={{ minWidth: 220 }}>
                  <InputLabel>Select Model</InputLabel>
                  <Select
                    value={selectedModel}
                    label="Select Model"
                    onChange={(e) => setSelectedModel(e.target.value)}
                    disabled={isAnalyzing}
                    sx={{
                      '& .MuiOutlinedInput-root': {
                        '& fieldset': {
                          borderColor: '#e6e8ea',
                        },
                      },
                    }}
                  >
                    <MenuItem value="gpt-3.5-turbo">GPT-3.5 Turbo</MenuItem>
                    <MenuItem value="gpt-4">GPT-4</MenuItem>
                    <MenuItem value="gpt-4-turbo">GPT-4 Turbo</MenuItem>
                    <MenuItem value="gpt-4o">GPT-4o</MenuItem>
                    <MenuItem value="claude-3-haiku-20240307">Claude 3 Haiku</MenuItem>
                    <MenuItem value="claude-3-sonnet-20240229">Claude 3 Sonnet</MenuItem>
                    <MenuItem value="deepseek-ai/deepseek-r1">DeepSeek R1</MenuItem>
                  </Select>
                </FormControl>
                
                <Box sx={{ flex: 1, pt: 1 }}>
                  {selectedModel.startsWith('deepseek') && (
                    <Typography variant="body2" color="success.main" sx={{ fontWeight: 500 }}>
                      Cost-effective option with excellent performance
                    </Typography>
                  )}
                  {selectedModel.startsWith('gpt-4') && (
                    <Typography variant="body2" color="primary.main" sx={{ fontWeight: 500 }}>
                      Premium accuracy for complex citation analysis
                    </Typography>
                  )}
                  {selectedModel.startsWith('claude') && (
                    <Typography variant="body2" color="secondary.main" sx={{ fontWeight: 500 }}>
                      Advanced reasoning and detailed explanations
                    </Typography>
                  )}
                  {selectedModel === 'gpt-3.5-turbo' && (
                    <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                      Fast and reliable for most analysis tasks
                    </Typography>
                  )}
                </Box>
              </Stack>
            </Stack>
          </Paper>

          {/* Main Content Card */}
          <Card sx={{ 
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(12px)',
            borderRadius: 4
          }}>
            <CardContent sx={{ p: 6 }}>
              {!analysisReport ? (
                <PdfUploader
                  onFileUpload={handleFileUpload}
                  onStartAnalysis={handleStartAnalysis}
                  uploadedFile={uploadedFile}
                  isAnalyzing={isAnalyzing}
                />
              ) : (
                <ErrorBoundary>
                  <CitationAnalysis report={analysisReport} />
                </ErrorBoundary>
              )}
            </CardContent>
          </Card>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;
