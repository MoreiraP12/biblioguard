# BiblioGuard - AI-Powered Citation Analysis UI

A beautiful, modern React interface for analyzing PDF citations with AI-powered evaluation. This UI connects to the BiblioGuard Python backend to provide real-time citation quality assessment.

## ✨ Features

- 🎨 **Beautiful Modern UI** - Clean, responsive design with smooth animations
- 📁 **Drag & Drop PDF Upload** - Simple file upload interface
- 🤖 **AI-Powered Analysis** - LLM evaluation of citation quality and relevance
- 💰 **Multiple AI Providers** - Support for OpenAI, Anthropic, and DeepSeek models
- 🔍 **Citation Highlighting** - Visual highlighting of problematic citations in context
- 📊 **Interactive Results** - Expandable citation details with comprehensive analysis
- ⚡ **Real-time Processing** - Live analysis with progress indicators
- 🎯 **Status Indicators** - Clear visual status for each citation (Pass/Suspect/Missing)
- 📈 **Analytics Dashboard** - Citation quality metrics and pass rates
- 🧠 **Smart Model Selection** - Choose the best AI model for your needs and budget

## 🖥️ Screenshots

### Main Interface
The main interface features a gradient background with a clean upload area:
- Drag and drop PDF files
- Beautiful file preview with size and type indicators
- Prominent analysis button with loading states

### Analysis Results
Comprehensive results display including:
- Overall citation quality metrics
- Interactive accordion-style citation details
- Highlighted problematic text passages
- AI evaluator explanations and rationales

## 🚀 Quick Start

### Prerequisites

- Node.js 16+ and npm
- Python 3.8+ (for backend)
- API keys for OpenAI or Anthropic (for LLM analysis)

### 1. Setup the React Frontend

```bash
# Navigate to the UI directory
cd biblioguard-ui

# Install dependencies
npm install

# Start the development server
npm start
```

The frontend will be available at `http://localhost:3000`

### 2. Setup the Python Backend

```bash
# Install backend dependencies
pip install -r api_requirements.txt

# Install the paper auditor package
pip install -e .

# Set up your API keys
export OPENAI_API_KEY="your-openai-api-key"
# OR
export ANTHROPIC_API_KEY="your-anthropic-api-key"
# OR
export DEEPSEEK_API_KEY="your-deepseek-api-key"

# Start the Flask API server
python backend_api.py
```

The backend API will be available at `http://localhost:8000`

### 3. Test the Integration

1. Open `http://localhost:3000` in your browser
2. Select your preferred AI model from the dropdown (including cost-effective DeepSeek options)
3. Upload a PDF file using the drag-and-drop interface
4. Click "Start Citation Analysis"
5. View the comprehensive results with AI-powered insights

### 💡 Using DeepSeek for Cost-Effective Analysis

BiblioGuard supports DeepSeek AI models that provide excellent performance at ~10x lower cost than GPT-4. See the detailed [DeepSeek Setup Guide](README_DEEPSEEK.md) for:
- Cost comparisons and savings calculations
- Setup instructions and API key configuration
- Model selection recommendations (deepseek-chat vs deepseek-coder)
- Performance expectations and best practices

## 🛠️ Development

### Frontend Structure

```
biblioguard-ui/
├── src/
│   ├── components/
│   │   ├── PdfUploader.tsx      # File upload component
│   │   └── CitationAnalysis.tsx # Results display component
│   ├── services/
│   │   └── api.ts               # API integration service
│   ├── App.tsx                  # Main application component
│   └── App.css                  # Custom styles and animations
├── public/
└── package.json
```

### Key Components

#### PdfUploader
- Drag-and-drop file upload
- File validation and preview
- Analysis trigger with loading states
- Beautiful Material-UI styling with custom animations

#### CitationAnalysis
- Interactive results display
- Citation status indicators
- Text highlighting for problematic citations
- Expandable detailed analysis sections
- AI explanation integration

#### API Service
- RESTful API integration
- Automatic fallback to demo data
- Error handling and retries
- Type-safe interfaces

### Backend API Endpoints

- `GET /health` - Health check and system status
- `GET /models` - Available LLM models
- `POST /analyze` - Upload and analyze PDF
- `GET /demo` - Demo data for testing

## 🎨 Design Features

### Visual Design
- **Modern Gradient Background** - Beautiful purple-blue gradient
- **Glass Morphism Effects** - Subtle transparency and blur effects
- **Smooth Animations** - Framer Motion powered interactions
- **Responsive Layout** - Mobile-friendly responsive design
- **Custom Material-UI Theme** - Consistent color scheme and typography

### User Experience
- **Progressive Disclosure** - Expandable sections for detailed information
- **Visual Status Indicators** - Color-coded citation status
- **Context Highlighting** - Red highlighting for problematic citations
- **Loading States** - Clear feedback during processing
- **Error Handling** - Graceful fallbacks and error messages

### Citation Analysis Display
- **Summary Statistics** - At-a-glance citation quality metrics
- **Progress Indicators** - Visual representation of citation quality
- **Detailed Breakdown** - Per-citation analysis with AI explanations
- **Context Preservation** - Original text with highlighted citations
- **Metadata Display** - Complete citation information and sources

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `biblioguard-ui` directory:

```env
REACT_APP_API_URL=http://localhost:8000
```

### API Configuration

The frontend automatically detects backend availability and falls back to demo data if needed.

## 📊 Citation Analysis Features

### Status Categories
- **✅ Pass** - Valid, properly justified citations
- **⚠️ Suspect** - Citations with potential issues
- **❌ Missing** - Citations not found in databases

### AI Evaluation Metrics
- **Relevance Score** (1-5) - How relevant the citation is to the claim
- **Justification Analysis** - Whether the citation supports the claim
- **Existence Verification** - Database lookup results
- **Context Analysis** - Evaluation of citation usage in context

### Detailed Information
- Complete citation metadata
- Source database information
- AI explanation and rationale
- Page numbers and sections
- Surrounding text context

## 🚀 Deployment

### Frontend Deployment

```bash
# Build for production
npm run build

# Deploy to your preferred hosting service
# (Netlify, Vercel, AWS S3, etc.)
```

### Backend Deployment

```bash
# For production deployment, consider using:
# - Gunicorn for WSGI server
# - Docker for containerization
# - Cloud services (AWS, GCP, Azure)

# Example with Gunicorn:
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 backend_api:app
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Material-UI for the component library
- Framer Motion for smooth animations
- React Dropzone for file upload functionality
- The paper-auditor backend for citation analysis logic 