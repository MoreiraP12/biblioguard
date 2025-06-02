"""
LLM-based evaluation of citation relevance and justification.
"""

import os
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from .models import CitationMetadata, CitationContext, RelevanceScore, JustificationCheck

logger = logging.getLogger(__name__)


class LLMEvaluator(ABC):
    """Abstract base class for LLM evaluators."""
    
    @abstractmethod
    def evaluate_relevance(
        self, 
        paper_title: str, 
        paper_abstract: str,
        citation_metadata: CitationMetadata
    ) -> RelevanceScore:
        """Evaluate topical relevance of citation to paper (0-5 scale)."""
        pass
    
    @abstractmethod
    def evaluate_justification(
        self, 
        citation_context: CitationContext,
        citation_metadata: CitationMetadata
    ) -> JustificationCheck:
        """Evaluate if citation justifies the claim it supports."""
        pass


class OpenAIEvaluator(LLMEvaluator):
    """OpenAI GPT-based evaluator."""
    
    def __init__(self, model: str = "gpt-3.5-turbo", api_key: Optional[str] = None):
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key or os.getenv('OPENAI_API_KEY'))
            self.model = model
        except ImportError:
            raise ImportError("openai package is required for OpenAI evaluator")
    
    def evaluate_relevance(
        self, 
        paper_title: str, 
        paper_abstract: str,
        citation_metadata: CitationMetadata
    ) -> RelevanceScore:
        """Evaluate topical relevance using OpenAI."""
        
        prompt = self._create_relevance_prompt(paper_title, paper_abstract, citation_metadata)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert academic researcher evaluating citation relevance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            return self._parse_relevance_response(content)
            
        except Exception as e:
            logger.error(f"OpenAI relevance evaluation failed: {e}")
            return RelevanceScore(score=3, explanation="Evaluation failed due to API error")
    
    def evaluate_justification(
        self, 
        citation_context: CitationContext,
        citation_metadata: CitationMetadata
    ) -> JustificationCheck:
        """Evaluate citation justification using OpenAI."""
        
        prompt = self._create_justification_prompt(citation_context, citation_metadata)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert academic researcher evaluating citation appropriateness."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            return self._parse_justification_response(content)
            
        except Exception as e:
            logger.error(f"OpenAI justification evaluation failed: {e}")
            return JustificationCheck(justified=True, rationale="Evaluation failed due to API error")
    
    def _create_relevance_prompt(self, paper_title: str, paper_abstract: str, citation_metadata: CitationMetadata) -> str:
        """Create prompt for relevance evaluation."""
        citation_info = f"Title: {citation_metadata.title or 'Unknown'}\n"
        if citation_metadata.authors:
            citation_info += f"Authors: {', '.join(citation_metadata.authors[:3])}\n"
        if citation_metadata.abstract:
            citation_info += f"Abstract: {citation_metadata.abstract[:500]}...\n"
        elif citation_metadata.journal:
            citation_info += f"Journal: {citation_metadata.journal}\n"
        if citation_metadata.year:
            citation_info += f"Year: {citation_metadata.year}\n"
        
        return f"""
Please evaluate the topical relevance of the following citation to the target paper on a scale of 0-5:

0 = Completely irrelevant
1 = Tangentially related
2 = Somewhat related but not directly relevant
3 = Moderately relevant
4 = Highly relevant
5 = Extremely relevant and directly on-topic

TARGET PAPER:
Title: {paper_title}
Abstract: {paper_abstract[:1000]}...

CITATION TO EVALUATE:
{citation_info}

Please provide your evaluation in this exact format:
SCORE: [0-5]
EXPLANATION: [Brief explanation of why you gave this score]
"""
    
    def _create_justification_prompt(self, citation_context: CitationContext, citation_metadata: CitationMetadata) -> str:
        """Create prompt for justification evaluation."""
        citation_info = f"Title: {citation_metadata.title or 'Unknown'}\n"
        if citation_metadata.abstract:
            citation_info += f"Abstract: {citation_metadata.abstract[:500]}...\n"
        elif citation_metadata.journal:
            citation_info += f"Journal: {citation_metadata.journal}\n"
        
        return f"""
Please evaluate whether the following citation appropriately supports the claim being made in the paper.

CLAIM FROM PAPER:
"{citation_context.claim_statement}"

CITATION BEING USED:
{citation_info}

SURROUNDING CONTEXT:
{citation_context.surrounding_text}

Does this citation appropriately support the claim being made? Consider:
1. Does the citation provide evidence for the specific claim?
2. Is the citation being used accurately (not misrepresented)?
3. Is the citation sufficient to support the claim?

Please provide your evaluation in this exact format:
JUSTIFIED: [YES/NO]
RATIONALE: [Brief explanation of your decision]
"""
    
    def _parse_relevance_response(self, content: str) -> RelevanceScore:
        """Parse relevance evaluation response."""
        lines = content.strip().split('\n')
        score = 3  # Default
        explanation = "Unable to parse response"
        
        for line in lines:
            if line.startswith('SCORE:'):
                try:
                    score = int(line.split(':')[1].strip())
                    score = max(0, min(5, score))  # Clamp to 0-5
                except ValueError:
                    pass
            elif line.startswith('EXPLANATION:'):
                explanation = line.split(':', 1)[1].strip()
        
        return RelevanceScore(score=score, explanation=explanation)
    
    def _parse_justification_response(self, content: str) -> JustificationCheck:
        """Parse justification evaluation response."""
        lines = content.strip().split('\n')
        justified = True  # Default to conservative
        rationale = "Unable to parse response"
        
        for line in lines:
            if line.startswith('JUSTIFIED:'):
                response = line.split(':')[1].strip().upper()
                justified = response.startswith('YES')
            elif line.startswith('RATIONALE:'):
                rationale = line.split(':', 1)[1].strip()
        
        return JustificationCheck(justified=justified, rationale=rationale)


class AnthropicEvaluator(LLMEvaluator):
    """Anthropic Claude-based evaluator."""
    
    def __init__(self, model: str = "claude-3-sonnet-20240229", api_key: Optional[str] = None):
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))
            self.model = model
        except ImportError:
            raise ImportError("anthropic package is required for Anthropic evaluator")
    
    def evaluate_relevance(
        self, 
        paper_title: str, 
        paper_abstract: str,
        citation_metadata: CitationMetadata
    ) -> RelevanceScore:
        """Evaluate topical relevance using Anthropic."""
        
        prompt = self._create_relevance_prompt(paper_title, paper_abstract, citation_metadata)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            return self._parse_relevance_response(content)
            
        except Exception as e:
            logger.error(f"Anthropic relevance evaluation failed: {e}")
            return RelevanceScore(score=3, explanation="Evaluation failed due to API error")
    
    def evaluate_justification(
        self, 
        citation_context: CitationContext,
        citation_metadata: CitationMetadata
    ) -> JustificationCheck:
        """Evaluate citation justification using Anthropic."""
        
        prompt = self._create_justification_prompt(citation_context, citation_metadata)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text
            return self._parse_justification_response(content)
            
        except Exception as e:
            logger.error(f"Anthropic justification evaluation failed: {e}")
            return JustificationCheck(justified=True, rationale="Evaluation failed due to API error")
    
    def _create_relevance_prompt(self, paper_title: str, paper_abstract: str, citation_metadata: CitationMetadata) -> str:
        """Create prompt for relevance evaluation."""
        citation_info = f"Title: {citation_metadata.title or 'Unknown'}\n"
        if citation_metadata.authors:
            citation_info += f"Authors: {', '.join(citation_metadata.authors[:3])}\n"
        if citation_metadata.abstract:
            citation_info += f"Abstract: {citation_metadata.abstract[:500]}...\n"
        elif citation_metadata.journal:
            citation_info += f"Journal: {citation_metadata.journal}\n"
        if citation_metadata.year:
            citation_info += f"Year: {citation_metadata.year}\n"
        
        return f"""You are an expert academic researcher evaluating citation relevance.

Please evaluate the topical relevance of the following citation to the target paper on a scale of 0-5:

0 = Completely irrelevant
1 = Tangentially related
2 = Somewhat related but not directly relevant
3 = Moderately relevant
4 = Highly relevant
5 = Extremely relevant and directly on-topic

TARGET PAPER:
Title: {paper_title}
Abstract: {paper_abstract[:1000]}...

CITATION TO EVALUATE:
{citation_info}

Please provide your evaluation in this exact format:
SCORE: [0-5]
EXPLANATION: [Brief explanation of why you gave this score]"""
    
    def _create_justification_prompt(self, citation_context: CitationContext, citation_metadata: CitationMetadata) -> str:
        """Create prompt for justification evaluation."""
        citation_info = f"Title: {citation_metadata.title or 'Unknown'}\n"
        if citation_metadata.abstract:
            citation_info += f"Abstract: {citation_metadata.abstract[:500]}...\n"
        elif citation_metadata.journal:
            citation_info += f"Journal: {citation_metadata.journal}\n"
        
        return f"""You are an expert academic researcher evaluating citation appropriateness.

Please evaluate whether the following citation appropriately supports the claim being made in the paper.

CLAIM FROM PAPER:
"{citation_context.claim_statement}"

CITATION BEING USED:
{citation_info}

SURROUNDING CONTEXT:
{citation_context.surrounding_text}

Does this citation appropriately support the claim being made? Consider:
1. Does the citation provide evidence for the specific claim?
2. Is the citation being used accurately (not misrepresented)?
3. Is the citation sufficient to support the claim?

Please provide your evaluation in this exact format:
JUSTIFIED: [YES/NO]
RATIONALE: [Brief explanation of your decision]"""
    
    def _parse_relevance_response(self, content: str) -> RelevanceScore:
        """Parse relevance evaluation response."""
        lines = content.strip().split('\n')
        score = 3  # Default
        explanation = "Unable to parse response"
        
        for line in lines:
            if line.startswith('SCORE:'):
                try:
                    score = int(line.split(':')[1].strip())
                    score = max(0, min(5, score))  # Clamp to 0-5
                except ValueError:
                    pass
            elif line.startswith('EXPLANATION:'):
                explanation = line.split(':', 1)[1].strip()
        
        return RelevanceScore(score=score, explanation=explanation)
    
    def _parse_justification_response(self, content: str) -> JustificationCheck:
        """Parse justification evaluation response."""
        lines = content.strip().split('\n')
        justified = True  # Default to conservative
        rationale = "Unable to parse response"
        
        for line in lines:
            if line.startswith('JUSTIFIED:'):
                response = line.split(':')[1].strip().upper()
                justified = response.startswith('YES')
            elif line.startswith('RATIONALE:'):
                rationale = line.split(':', 1)[1].strip()
        
        return JustificationCheck(justified=justified, rationale=rationale)


def create_evaluator(model_type: str, **kwargs) -> LLMEvaluator:
    """Factory function to create appropriate evaluator."""
    model_type = model_type.lower()
    
    if model_type.startswith('gpt') or model_type.startswith('openai'):
        return OpenAIEvaluator(model=kwargs.get('model', 'gpt-3.5-turbo'), 
                              api_key=kwargs.get('api_key'))
    elif model_type.startswith('claude') or model_type.startswith('anthropic'):
        return AnthropicEvaluator(model=kwargs.get('model', 'claude-3-sonnet-20240229'),
                                 api_key=kwargs.get('api_key'))
    else:
        raise ValueError(f"Unsupported model type: {model_type}") 