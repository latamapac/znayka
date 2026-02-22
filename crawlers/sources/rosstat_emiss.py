"""Crawler for Rosstat and EMISS (Unified Interdepartmental Statistical Information System)."""
import logging
import re
from typing import AsyncGenerator, Optional, List, Dict, Any
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)


class RosstatEMISSCrawler(BaseCrawler):
    """Crawler for Росстат и ЕМИСС - статистические сборники."""
    
    SOURCE_NAME = "Rosstat_EMISS"
    SOURCE_CODE = "RSTS"
    BASE_URL = "https://rosstat.gov.ru"
    EMISS_URL = "https://fedstat.ru"
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """Search Rosstat publications and statistical collections."""
        
        # Rosstat has different publication sections
        sections = [
            "/publications",
            "/statistics/publications",
            "/documents",
        ]
        
        papers_found = 0
        
        for section in sections:
            if papers_found >= limit:
                break
            
            try:
                url = f"{self.BASE_URL}{section}"
                html = await self._get_html(url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find publication links
                items = soup.select('.publication-item, .document-item, .news-item')
                
                for item in items:
                    if papers_found >= limit:
                        break
                    
                    link_elem = item.find('a', href=re.compile(r'/(?:publication|document|download)/'))
                    if not link_elem:
                        continue
                    
                    href = link_elem.get('href')
                    pub_id = self._extract_pub_id(href) or self._generate_id_from_url(href)
                    
                    if not pub_id:
                        continue
                    
                    paper_data = await self.get_paper_by_id(pub_id, href)
                    if paper_data:
                        yield paper_data
                        papers_found += 1
                
            except Exception as e:
                logger.error(f"Error searching Rosstat section {section}: {e}")
                continue
    
    async def get_paper_by_id(self, paper_id: str, href: Optional[str] = None) -> Optional[PaperData]:
        """Get publication details from Rosstat."""
        
        if href and href.startswith('/'):
            href = f"{self.BASE_URL}{href}"
        elif href and not href.startswith('http'):
            href = f"{self.BASE_URL}/{href}"
        
        url = href or f"{self.BASE_URL}/publication/{paper_id}"
        
        try:
            html = await self._get_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = None
            title_elem = soup.select_one('h1, .publication-title, .page-title, .document-title')
            if title_elem:
                title = self.clean_text(title_elem.get_text())
            
            if not title:
                # Try to get from meta
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    title = meta_title.get('content')
            
            if not title:
                return None
            
            # Extract description/abstract
            abstract = None
            desc_elem = soup.select_one('.publication-description, .document-content, .description')
            if desc_elem:
                abstract = self.clean_text(desc_elem.get_text())
            
            if not abstract:
                meta_desc = soup.find('meta', property='og:description')
                if meta_desc:
                    abstract = meta_desc.get('content')
            
            # Extract year
            year = None
            year_elem = soup.select_one('.year, .publication-date')
            if year_elem:
                year_text = year_elem.get_text()
                year_match = re.search(r'(\d{4})', year_text)
                if year_match:
                    year = int(year_match.group(1))
            
            # Extract document type
            doc_type = None
            type_elem = soup.select_one('.document-type, .publication-type')
            if type_elem:
                doc_type = self.clean_text(type_elem.get_text())
            
            # PDF link
            pdf_url = None
            pdf_link = soup.select_one('a[href*=".pdf"], a[href*="/download/"]')
            if pdf_link:
                pdf_href = pdf_link.get('href')
                if pdf_href:
                    pdf_url = urljoin(self.BASE_URL, pdf_href)
            
            # Keywords from Rosstat categories
            keywords = ["статистика", "Росстат", "Россия"]
            if doc_type:
                keywords.append(doc_type)
            
            return PaperData(
                title=title,
                title_ru=title,
                source_type=self.SOURCE_NAME.lower(),
                source_id=paper_id,
                source_url=url,
                abstract=abstract,
                authors=[{"full_name": "Росстат"}],
                publisher="Федеральная служба государственной статистики (Росстат)",
                publication_year=year,
                keywords=keywords,
                pdf_url=pdf_url,
                language="ru"
            )
            
        except Exception as e:
            logger.error(f"Error fetching publication {paper_id} from Rosstat: {e}")
            return None
    
    def _extract_pub_id(self, href: str) -> Optional[str]:
        """Extract publication ID from URL."""
        if not href:
            return None
        match = re.search(r'/(?:publication|document|download)/(\d+)', href)
        return match.group(1) if match else None
    
    def _generate_id_from_url(self, href: str) -> str:
        """Generate ID from URL if no ID found."""
        import hashlib
        return hashlib.md5(href.encode()).hexdigest()[:12]
