# Using DeepSeek API with BiblioGuard 🚀

BiblioGuard now supports DeepSeek AI models, offering competitive performance at significantly lower costs compared to other providers.

## What is DeepSeek?

[DeepSeek](https://www.deepseek.com/) is an AI research company that provides high-performance language models at competitive prices. Their models are particularly strong at:
- Reasoning and analysis tasks
- Code understanding and generation
- Academic and technical content evaluation

## Cost Comparison 💰

| Provider | Model | Cost per 1M tokens | Relative Cost |
|----------|-------|-------------------|---------------|
| OpenAI | GPT-4 | ~$30 | 15x |
| OpenAI | GPT-3.5-turbo | ~$2 | 1x |
| Anthropic | Claude-3 Sonnet | ~$15 | 7.5x |
| **DeepSeek** | **deepseek-chat** | **~$2** | **1x** |
| **DeepSeek** | **deepseek-coder** | **~$2** | **1x** |

*Prices are approximate and may vary. DeepSeek offers similar performance to GPT-4 at a fraction of the cost.*

## Setup Instructions

### 1. Get DeepSeek API Key

1. Visit [DeepSeek's website](https://www.deepseek.com/)
2. Sign up for an account
3. Navigate to the API section
4. Generate your API key

### 2. Configure Environment

Add your DeepSeek API key to your environment:

```bash
# Option 1: Export in your shell
export DEEPSEEK_API_KEY="your-deepseek-api-key-here"

# Option 2: Add to .env file
echo "DEEPSEEK_API_KEY=your-deepseek-api-key-here" >> .env
```

### 3. Update Dependencies

DeepSeek uses the OpenAI SDK for compatibility, so ensure you have it installed:

```bash
pip install openai>=1.0.0
```

## Available Models

### deepseek-chat
- **Best for**: General citation analysis, relevance evaluation, justification reasoning
- **Strengths**: Balanced performance across all tasks
- **Use when**: You want the best overall performance for citation analysis

### deepseek-coder  
- **Best for**: Technical papers, code-related citations, formal academic writing
- **Strengths**: Enhanced understanding of technical and scientific content
- **Use when**: Analyzing papers with significant technical/mathematical content

## Using DeepSeek in BiblioGuard

### Via Web Interface

1. Start the backend API server
2. Open the BiblioGuard web interface
3. In the "AI Model Configuration" section, select:
   - `DeepSeek Chat 💰` for general papers
   - `DeepSeek Coder 💰` for technical papers
4. Upload your PDF and start analysis

### Via Command Line

```bash
# Using deepseek-chat model
python -m paper_auditor.cli --model deepseek --input paper.pdf --output report.json

# Using deepseek-coder model  
python -m paper_auditor.cli --model deepseek-coder --input technical_paper.pdf --output report.json
```

### Via Python API

```python
from paper_auditor import PaperAuditor

# Initialize with DeepSeek model
auditor = PaperAuditor(
    model_type="deepseek",
    model="deepseek-chat",
    api_key="your-deepseek-api-key"
)

# Or for technical papers
auditor = PaperAuditor(
    model_type="deepseek", 
    model="deepseek-coder",
    api_key="your-deepseek-api-key"
)

# Analyze paper
report = auditor.audit_paper("path/to/paper.pdf")
```

### Backend API

The Flask API automatically supports DeepSeek models when you select them in the dropdown. The API will:

1. Check for `DEEPSEEK_API_KEY` environment variable
2. Initialize the DeepSeek evaluator with OpenAI SDK compatibility
3. Route requests to DeepSeek's API endpoints

## Performance Expectations

### Accuracy
- **Citation Relevance**: Comparable to GPT-4 for most academic domains
- **Justification Analysis**: Strong performance on logical reasoning tasks
- **Technical Content**: Excellent performance on STEM papers (especially with deepseek-coder)

### Speed
- **Response Time**: ~2-5 seconds per citation (similar to other providers)
- **Rate Limits**: Generally more generous than OpenAI
- **Throughput**: Good for batch processing of multiple papers

### Cost Efficiency
- **Typical Paper**: 50-100 citations = $0.10-0.30 vs $1.50-4.50 with GPT-4
- **Large Survey**: 200+ citations = $0.50-1.00 vs $6.00-15.00 with GPT-4
- **Monthly Usage**: Analyze 100 papers/month for ~$20-50 vs $300-800 with GPT-4

## Troubleshooting

### Common Issues

**Authentication Error**
```
Error: DeepSeek API key not found
```
**Solution**: Ensure `DEEPSEEK_API_KEY` is properly set in environment

**Rate Limiting**  
```
Error: Rate limit exceeded
```
**Solution**: DeepSeek has generous rate limits, but add delays between requests if needed

**Model Not Found**
```
Error: Model 'deepseek-chat' not found
```
**Solution**: Ensure you're using the correct model names: `deepseek-chat` or `deepseek-coder`

### Getting Help

1. Check [DeepSeek's documentation](https://platform.deepseek.com/docs)
2. Verify your API key is active and has sufficient credits
3. Test the API key with a simple request:

```python
import openai

client = openai.OpenAI(
    api_key="your-deepseek-api-key",
    base_url="https://api.deepseek.com/v1"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=50
)
print(response.choices[0].message.content)
```

## Best Practices

### Model Selection
- Use `deepseek-chat` for humanities, social sciences, and general academic papers
- Use `deepseek-coder` for computer science, engineering, mathematics, and technical papers
- Both models work well for medical and life sciences papers

### Prompt Engineering
- DeepSeek responds well to clear, structured prompts (already optimized in BiblioGuard)
- Works effectively with the same prompts used for GPT models
- No special prompt modifications needed

### Cost Optimization
- DeepSeek is already very cost-effective
- Consider batching multiple papers for analysis
- Monitor usage through DeepSeek's dashboard

## Migration from Other Providers

### From OpenAI GPT Models
- No code changes required - just select DeepSeek in the model dropdown
- Expect similar quality results at much lower cost
- Response format is identical (OpenAI SDK compatibility)

### From Claude Models  
- Switch to DeepSeek for significant cost savings
- DeepSeek often provides more detailed technical analysis
- May prefer DeepSeek for STEM papers, Claude for humanities

### Hybrid Approach
- Use DeepSeek for initial analysis and bulk processing
- Use GPT-4 for final validation of critical papers
- Best of both worlds: cost efficiency + premium quality when needed

---

🎯 **Ready to save costs while maintaining quality?** Set up your DeepSeek API key and start analyzing papers with BiblioGuard today! 