import React, { useState } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Stack,
  Paper,
  LinearProgress,
  Divider,
  IconButton,
  Card,
  CardContent,
  Alert,
  AlertTitle
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Visibility as VisibilityIcon,
  School as SchoolIcon,
  Assessment as AssessmentIcon,
  Link as LinkIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { AnalysisReport, CitationAudit } from '../App';

interface CitationAnalysisProps {
  report: AnalysisReport;
}

const CitationAnalysis: React.FC<CitationAnalysisProps> = ({ report }) => {
  const [expandedCitation, setExpandedCitation] = useState<string | false>(false);

  const handleCitationChange = (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedCitation(isExpanded ? panel : false);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'PASS':
        return <CheckCircleIcon sx={{ color: 'success.main' }} />;
      case 'SUSPECT':
        return <WarningIcon sx={{ color: 'warning.main' }} />;
      case 'MISSING':
        return <ErrorIcon sx={{ color: 'error.main' }} />;
      default:
        return <VisibilityIcon sx={{ color: 'info.main' }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PASS':
        return 'success';
      case 'SUSPECT':
        return 'warning';
      case 'MISSING':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'PASS':
        return '✅ Valid';
      case 'SUSPECT':
        return '⚠️ Suspect';
      case 'MISSING':
        return '❌ Missing';
      default:
        return status;
    }
  };

  const highlightCitationInText = (text: string, citationText: string) => {
    if (!citationText) return text;
    
    // Create a case-insensitive regex to find the citation
    const regex = new RegExp(`(${citationText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => 
      regex.test(part) ? (
        <Box
          key={index}
          component="span"
          sx={{
            backgroundColor: 'error.50',
            border: '2px solid',
            borderColor: 'error.main',
            borderRadius: 1,
            px: 0.5,
            py: 0.25,
            fontWeight: 600,
            color: 'error.dark'
          }}
        >
          {part}
        </Box>
      ) : part
    );
  };

  const passRate = Math.round((report.passed_count / report.total_citations) * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      <Card sx={{ mb: 4 }}>
        <CardContent sx={{ p: 4 }}>
          <Box textAlign="center" mb={4}>
            <Typography variant="h4" component="h2" gutterBottom sx={{ fontWeight: 600 }}>
              Analysis Results
            </Typography>
            <Typography variant="h6" color="text.secondary" sx={{ mb: 3 }}>
              {report.paper_title}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Authors: {report.paper_authors.join(', ')}
            </Typography>
          </Box>

          {/* Summary Statistics */}
          <Box sx={{ 
            mb: 4,
            display: 'grid',
            gridTemplateColumns: { 
              xs: '1fr',
              sm: 'repeat(2, 1fr)',
              md: 'repeat(4, 1fr)'
            },
            gap: 3
          }}>
            <Paper 
              sx={{ 
                p: 3, 
                textAlign: 'center',
                background: 'linear-gradient(135deg, #10b981 0%, #047857 100%)',
                color: 'white'
              }}
            >
              <CheckCircleIcon sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {report.passed_count}
              </Typography>
              <Typography variant="body2">Valid Citations</Typography>
            </Paper>
            <Paper 
              sx={{ 
                p: 3, 
                textAlign: 'center',
                background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                color: 'white'
              }}
            >
              <WarningIcon sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {report.suspect_count}
              </Typography>
              <Typography variant="body2">Suspect Citations</Typography>
            </Paper>
            <Paper 
              sx={{ 
                p: 3, 
                textAlign: 'center',
                background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                color: 'white'
              }}
            >
              <ErrorIcon sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {report.missing_count}
              </Typography>
              <Typography variant="body2">Missing Citations</Typography>
            </Paper>
            <Paper 
              sx={{ 
                p: 3, 
                textAlign: 'center',
                background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                color: 'white'
              }}
            >
              <VisibilityIcon sx={{ fontSize: 40, mb: 1 }} />
              <Typography variant="h4" sx={{ fontWeight: 700 }}>
                {passRate}%
              </Typography>
              <Typography variant="body2">Pass Rate</Typography>
            </Paper>
          </Box>

          {/* Overall Progress Bar */}
          <Box sx={{ mb: 4 }}>
            <Typography variant="h6" gutterBottom>
              Citation Quality Overview
            </Typography>
            <LinearProgress
              variant="determinate"
              value={passRate}
              sx={{
                height: 12,
                borderRadius: 6,
                backgroundColor: 'grey.200',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 6,
                  background: passRate >= 80 
                    ? 'linear-gradient(90deg, #10b981 0%, #047857 100%)'
                    : passRate >= 60
                    ? 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)'
                    : 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)'
                }
              }}
            />
            <Box display="flex" justifyContent="space-between" mt={1}>
              <Typography variant="caption" color="text.secondary">
                Poor
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Excellent
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Individual Citation Analysis */}
      <Typography variant="h5" component="h3" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
        Detailed Citation Analysis
      </Typography>

      {report.audited_citations.map((citation, index) => (
        <motion.div
          key={citation.citation_key}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.4, delay: index * 0.1 }}
        >
          <Accordion
            expanded={expandedCitation === citation.citation_key}
            onChange={handleCitationChange(citation.citation_key)}
            sx={{ 
              mb: 2,
              border: '1px solid',
              borderColor: citation.status === 'MISSING' ? 'error.main' 
                : citation.status === 'SUSPECT' ? 'warning.main' 
                : 'success.main',
              borderRadius: 2,
              '&:before': { display: 'none' },
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              sx={{
                backgroundColor: citation.status === 'MISSING' ? 'error.50' 
                  : citation.status === 'SUSPECT' ? 'warning.50' 
                  : 'success.50',
                borderRadius: '8px 8px 0 0',
                minHeight: 64,
                '&.Mui-expanded': {
                  minHeight: 64,
                }
              }}
            >
              <Stack direction="row" alignItems="center" spacing={2} sx={{ width: '100%', pr: 2 }}>
                {getStatusIcon(citation.status)}
                <Box flex={1}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    {citation.citation_key}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {citation.metadata.title || 'No title available'}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1}>
                  <Chip 
                    label={getStatusText(citation.status)}
                    color={getStatusColor(citation.status) as any}
                    size="small"
                    variant="outlined"
                  />
                  {citation.relevance && (
                    <Chip 
                      label={`Relevance: ${citation.relevance.score}/5`}
                      color={citation.relevance.score >= 4 ? 'success' : citation.relevance.score >= 2 ? 'warning' : 'error'}
                      size="small"
                      variant="outlined"
                    />
                  )}
                </Stack>
              </Stack>
            </AccordionSummary>
            
            <AccordionDetails sx={{ p: 3 }}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {/* Citation Details and Analysis Results */}
                <Box sx={{ 
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
                  gap: 3
                }}>
                  {/* Citation Details */}
                  <Box>
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                      <SchoolIcon /> Citation Information
                    </Typography>
                    <Stack spacing={2}>
                      <Box>
                        <Typography variant="subtitle2" color="text.secondary">
                          Authors:
                        </Typography>
                        <Typography variant="body2">
                          {citation.metadata.authors.join(', ') || 'Not available'}
                        </Typography>
                      </Box>
                      
                      <Box>
                        <Typography variant="subtitle2" color="text.secondary">
                          Year:
                        </Typography>
                        <Typography variant="body2">
                          {citation.metadata.year || 'Not available'}
                        </Typography>
                      </Box>
                      
                      {citation.metadata.journal && (
                        <Box>
                          <Typography variant="subtitle2" color="text.secondary">
                            Journal:
                          </Typography>
                          <Typography variant="body2">
                            {citation.metadata.journal}
                          </Typography>
                        </Box>
                      )}
                      
                      {citation.metadata.doi && (
                        <Box>
                          <Typography variant="subtitle2" color="text.secondary">
                            DOI:
                          </Typography>
                          <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {citation.metadata.doi}
                            <IconButton size="small" href={`https://doi.org/${citation.metadata.doi}`} target="_blank">
                              <LinkIcon fontSize="small" />
                            </IconButton>
                          </Typography>
                        </Box>
                      )}
                      
                      <Box>
                        <Typography variant="subtitle2" color="text.secondary">
                          Existence Status:
                        </Typography>
                        <Typography variant="body2">
                          {citation.existence_details || (citation.exists_online ? 'Found online' : 'Not found online')}
                        </Typography>
                      </Box>
                    </Stack>
                  </Box>
                  
                  {/* Analysis Results */}
                  <Box>
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                      <AssessmentIcon /> AI Analysis
                    </Typography>
                    <Stack spacing={3}>
                      {citation.relevance && (
                        <Alert 
                          severity={citation.relevance.score >= 4 ? 'success' : citation.relevance.score >= 2 ? 'warning' : 'error'}
                          variant="outlined"
                        >
                          <AlertTitle>Relevance Score: {citation.relevance.score}/5</AlertTitle>
                          {citation.relevance.explanation}
                        </Alert>
                      )}
                      
                      {citation.justification && (
                        <Alert 
                          severity={citation.justification.justified ? 'success' : 'error'}
                          variant="outlined"
                        >
                          <AlertTitle>
                            {citation.justification.justified ? 'Justification: Valid' : 'Justification: Invalid'}
                          </AlertTitle>
                          {citation.justification.rationale}
                        </Alert>
                      )}
                    </Stack>
                  </Box>
                </Box>
                
                {/* Context with Highlighting */}
                {citation.contexts.map((context, contextIndex) => (
                  <Box key={contextIndex}>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                      Context in Paper
                      {context.page_number && (
                        <Chip 
                          label={`Page ${context.page_number}`} 
                          size="small" 
                          sx={{ ml: 2 }}
                        />
                      )}
                      {context.section && (
                        <Chip 
                          label={context.section} 
                          size="small" 
                          variant="outlined"
                          sx={{ ml: 1 }}
                        />
                      )}
                    </Typography>
                    
                    <Paper 
                      sx={{ 
                        p: 3, 
                        backgroundColor: citation.status === 'SUSPECT' || citation.status === 'MISSING' 
                          ? 'error.50' 
                          : 'grey.50',
                        border: citation.status === 'SUSPECT' || citation.status === 'MISSING' 
                          ? '1px solid' 
                          : 'none',
                        borderColor: 'error.main'
                      }}
                    >
                      <Typography variant="body1" sx={{ lineHeight: 1.8 }}>
                        {citation.status === 'SUSPECT' || citation.status === 'MISSING'
                          ? highlightCitationInText(context.surrounding_text, citation.original_text)
                          : context.surrounding_text
                        }
                      </Typography>
                      
                      {context.claim_statement && (
                        <Box mt={2}>
                          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                            Specific Claim:
                          </Typography>
                          <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                            "{context.claim_statement}"
                          </Typography>
                        </Box>
                      )}
                    </Paper>
                  </Box>
                ))}
              </Box>
            </AccordionDetails>
          </Accordion>
        </motion.div>
      ))}
    </motion.div>
  );
};

export default CitationAnalysis; 