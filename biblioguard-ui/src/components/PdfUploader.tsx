import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  Box, 
  Typography, 
  Button, 
  Paper, 
  CircularProgress,
  Chip,
  Stack
} from '@mui/material';
import { 
  CloudUpload as CloudUploadIcon,
  Description as DescriptionIcon,
  Analytics as AnalyticsIcon
} from '@mui/icons-material';
import { motion } from 'framer-motion';

interface PdfUploaderProps {
  onFileUpload: (file: File) => void;
  onStartAnalysis: () => void;
  uploadedFile: File | null;
  isAnalyzing: boolean;
}

const PdfUploader: React.FC<PdfUploaderProps> = ({
  onFileUpload,
  onStartAnalysis,
  uploadedFile,
  isAnalyzing
}) => {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileUpload(acceptedFiles[0]);
    }
  }, [onFileUpload]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf']
    },
    multiple: false
  });

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <Box>
      <Typography variant="h4" component="h2" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
        Upload Your Research Paper
      </Typography>

      {!uploadedFile ? (
        <motion.div
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
        >
          <Paper
            {...getRootProps()}
            sx={{
              p: 6,
              textAlign: 'center',
              cursor: 'pointer',
              border: '2px dashed',
              borderColor: isDragActive ? 'primary.main' : 'grey.300',
              backgroundColor: isDragActive ? 'primary.50' : 'grey.50',
              transition: 'all 0.3s ease',
              borderRadius: 3,
              '&:hover': {
                borderColor: 'primary.main',
                backgroundColor: 'primary.50',
              }
            }}
          >
            <input {...getInputProps()} />
            <CloudUploadIcon 
              sx={{ 
                fontSize: 64, 
                color: isDragActive ? 'primary.main' : 'grey.400',
                mb: 2
              }} 
            />
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
              {isDragActive ? 'Drop your PDF here' : 'Drag & drop your PDF here'}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              or click to browse your files
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Supports PDF files up to 50MB
            </Typography>
          </Paper>
        </motion.div>
      ) : (
        <Box>
          <Paper 
            sx={{ 
              p: 3, 
              mb: 3,
              backgroundColor: 'success.50',
              border: '1px solid',
              borderColor: 'success.200'
            }}
          >
            <Stack direction="row" alignItems="center" spacing={2}>
              <DescriptionIcon sx={{ color: 'success.main', fontSize: 32 }} />
              <Box flex={1}>
                <Typography variant="h6" sx={{ fontWeight: 500 }}>
                  {uploadedFile.name}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  <Chip 
                    label={formatFileSize(uploadedFile.size)} 
                    size="small" 
                    color="success" 
                    variant="outlined"
                  />
                  <Chip 
                    label="PDF" 
                    size="small" 
                    color="success" 
                    variant="outlined"
                  />
                </Stack>
              </Box>
              <Button
                variant="outlined"
                color="success"
                onClick={() => onFileUpload(null as any)}
                sx={{ minWidth: 'auto' }}
              >
                Change File
              </Button>
            </Stack>
          </Paper>

          <Box textAlign="center">
            <motion.div
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Button
                variant="contained"
                size="large"
                onClick={onStartAnalysis}
                disabled={isAnalyzing}
                startIcon={isAnalyzing ? <CircularProgress size={20} /> : <AnalyticsIcon />}
                sx={{
                  py: 2,
                  px: 4,
                  fontSize: '1.1rem',
                  fontWeight: 600,
                  background: 'linear-gradient(45deg, #3b82f6 30%, #1d4ed8 90%)',
                  boxShadow: '0 8px 32px rgba(59, 130, 246, 0.3)',
                  '&:hover': {
                    background: 'linear-gradient(45deg, #1d4ed8 30%, #1e40af 90%)',
                    boxShadow: '0 12px 40px rgba(59, 130, 246, 0.4)',
                  }
                }}
              >
                {isAnalyzing ? 'Analyzing Citations...' : 'Start Citation Analysis'}
              </Button>
            </motion.div>
            
            {isAnalyzing && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <Typography 
                  variant="body2" 
                  color="text.secondary" 
                  sx={{ mt: 2 }}
                >
                  This may take a few minutes depending on the number of citations...
                </Typography>
              </motion.div>
            )}
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default PdfUploader; 