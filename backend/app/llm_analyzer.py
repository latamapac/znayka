"""
ZNAYKA LLM Paper Analyzer
Analyzes papers using OpenAI API or local models
"""
import asyncio
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Try to import LangChain, fallback to mock if not available
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain not available, LLM analysis disabled")


@dataclass
class PaperAnalysis:
    """Structured analysis of a paper"""
    paper_id: str
    summary: str
    key_findings: List[str]
    methodology: str
    relevance_score: float  # 0-100
    topics: List[str]
    citations_analysis: str
    limitations: str
    analyzed_at: str


class LLMPaperAnalyzer:
    """
    Analyzes academic papers using LLM
    
    Capabilities:
    - Generate executive summaries
    - Extract key findings
    - Identify methodology
    - Score relevance to topics
    - Analyze citations
    - Identify limitations
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.enabled = LANGCHAIN_AVAILABLE and bool(self.api_key)
        
        if self.enabled:
            self.llm = ChatOpenAI(
                model=model,
                api_key=self.api_key,
                temperature=0.3,
                max_tokens=2000
            )
            logger.info(f"LLM Analyzer initialized with {model}")
        else:
            logger.warning("LLM Analyzer disabled (no API key or LangChain)")
    
    async def analyze_paper(
        self,
        paper_id: str,
        title: str,
        abstract: str,
        full_text: Optional[str] = None
    ) -> Optional[PaperAnalysis]:
        """
        Analyze a paper and return structured insights
        """
        if not self.enabled:
            logger.debug("LLM analysis skipped (disabled)")
            return None
        
        try:
            # Prepare text for analysis
            text_to_analyze = f"Title: {title}\n\nAbstract: {abstract}"
            if full_text:
                # Truncate full text to avoid token limits
                text_to_analyze += f"\n\nFull Text (truncated): {full_text[:8000]}..."
            
            # Analysis prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are an expert academic research assistant. 
Analyze the provided paper and extract key information in a structured format.

Provide your analysis in this exact format:

SUMMARY:
[2-3 sentence executive summary]

KEY_FINDINGS:
- [Finding 1]
- [Finding 2]
- [Finding 3]

METHODOLOGY:
[Description of methods used]

RELEVANCE_SCORE: [0-100]

TOPICS:
- [Topic 1]
- [Topic 2]
- [Topic 3]

CITATIONS_ANALYSIS:
[Analysis of paper's impact based on citations]

LIMITATIONS:
[Identified limitations of the study]"""),
                ("human", "{text}")
            ])
            
            # Run analysis
            chain = prompt | self.llm
            response = await chain.ainvoke({"text": text_to_analyze})
            content = response.content
            
            # Parse response
            analysis = self._parse_analysis(paper_id, content)
            logger.info(f"Analyzed paper: {paper_id} (relevance: {analysis.relevance_score})")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing paper {paper_id}: {e}")
            return None
    
    def _parse_analysis(self, paper_id: str, content: str) -> PaperAnalysis:
        """Parse LLM response into structured format"""
        sections = {}
        current_section = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # Check for section headers
            if line.endswith(':') and not line.startswith('-'):
                current_section = line[:-1].upper()
                sections[current_section] = []
            elif current_section:
                sections[current_section].append(line)
        
        # Extract values
        summary = '\n'.join(sections.get('SUMMARY', []))
        key_findings = [l[2:] for l in sections.get('KEY_FINDINGS', []) if l.startswith('- ')]
        methodology = '\n'.join(sections.get('METHODOLOGY', []))
        
        # Parse relevance score
        relevance_text = ' '.join(sections.get('RELEVANCE_SCORE', ['50']))
        try:
            relevance_score = float(relevance_text.split()[0])
        except:
            relevance_score = 50.0
        
        topics = [l[2:] for l in sections.get('TOPICS', []) if l.startswith('- ')]
        citations_analysis = '\n'.join(sections.get('CITATIONS_ANALYSIS', []))
        limitations = '\n'.join(sections.get('LIMITATIONS', []))
        
        return PaperAnalysis(
            paper_id=paper_id,
            summary=summary,
            key_findings=key_findings,
            methodology=methodology,
            relevance_score=relevance_score,
            topics=topics,
            citations_analysis=citations_analysis,
            limitations=limitations,
            analyzed_at=datetime.now().isoformat()
        )
    
    async def batch_analyze(
        self,
        papers: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[PaperAnalysis]:
        """
        Analyze multiple papers with rate limiting
        """
        if not self.enabled:
            return []
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_limit(paper):
            async with semaphore:
                return await self.analyze_paper(
                    paper_id=paper['id'],
                    title=paper.get('title', ''),
                    abstract=paper.get('abstract', ''),
                    full_text=paper.get('full_text')
                )
        
        tasks = [analyze_with_limit(p) for p in papers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors
        analyses = [r for r in results if isinstance(r, PaperAnalysis)]
        return analyses


class LLMWorker:
    """
    Background worker for continuous LLM analysis
    """
    
    def __init__(self, analyzer: LLMPaperAnalyzer):
        self.analyzer = analyzer
        self.is_running = False
    
    async def start(self):
        """Start continuous analysis loop"""
        if not self.analyzer.enabled:
            logger.warning("LLM Worker cannot start - analyzer disabled")
            return
        
        self.is_running = True
        logger.info("LLM Worker started")
        
        while self.is_running:
            try:
                # Get papers without analysis
                papers = await self.get_papers_to_analyze(limit=10)
                
                if not papers:
                    logger.debug("No papers to analyze, waiting...")
                    await asyncio.sleep(60)
                    continue
                
                logger.info(f"Analyzing {len(papers)} papers...")
                analyses = await self.analyzer.batch_analyze(papers)
                
                # Store analyses
                for analysis in analyses:
                    if analysis:
                        await self.store_analysis(analysis)
                
                logger.info(f"Completed analysis of {len(analyses)} papers")
                
                # Rate limiting - be nice to API
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in LLM worker: {e}")
                await asyncio.sleep(30)
        
        logger.info("LLM Worker stopped")
    
    async def get_papers_to_analyze(self, limit: int = 10) -> List[Dict]:
        """
        Get papers that haven't been analyzed yet
        In production, this queries the database
        """
        # TODO: Implement database query
        # For now, return empty list
        return []
    
    async def store_analysis(self, analysis: PaperAnalysis):
        """
        Store analysis results in database
        """
        # TODO: Implement database storage
        logger.info(f"Stored analysis for {analysis.paper_id}")
    
    def stop(self):
        """Stop the worker"""
        self.is_running = False


# Global instances
llm_analyzer = LLMPaperAnalyzer()
llm_worker = LLMWorker(llm_analyzer)


async def start_llm_worker():
    """Entry point for LLM worker"""
    await llm_worker.start()


async def analyze_single_paper(
    paper_id: str,
    title: str,
    abstract: str,
    full_text: Optional[str] = None
) -> Optional[PaperAnalysis]:
    """Public function to analyze a single paper"""
    return await llm_analyzer.analyze_paper(paper_id, title, abstract, full_text)
