"""Crawler for INION RAN (inion.ru) - Institute of Scientific Information."""
import logging
import re
from typing import AsyncGenerator, Optional, List, Dict, Any
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)


class INIONCrawler(BaseCrawler):
    """Crawler for ИНИОН РАН - Институт научной информации."""
    
    SOURCE_NAME = "INION_RAN"
    SOURCE_CODE = "INION"
    BASE_URL = "https://inion.ru"
    SEARCH_URL = "https://inion.ru/search"
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """Search INION database."""
        
        page = 1
        papers_found = 0
        
        while papers_found < limit:
            params = {
                "query": quote(query),
                "page": page,
            }
            
            if year_from:
                params["year_from"] = year_from
            if year_to:
                params["year_to"] = year_to
            
            search_url = f"{self.SEARCH_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
            
            try:
                html = await self._get_html(search_url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find result items
                items = soup.select('.search-item, .publication-item, .result-item')
                
                if not items:
                    break
                
                for item in items:
                    if papers_found >= limit:
                        break
                    
                    link_elem = item.find('a', href=re.compile(r'/publication/|/item/'))
                    if not link_elem:
                        continue
                    
                    href = link_elem.get('href')
                    pub_id = self._extract_pub_id(href)
                    
                    if not pub_id:
                        continue
                    
                    paper_data = await self.get_paper_by_id(pub_id)
                    if paper_data:
                        yield paper_data
                        papers_found += 1
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error searching INION page {page}: {e}")
                break
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """Get publication details from INION."""
        
        url = f"{self.BASE_URL}/publication/{paper_id}"
        
        try:
            html = await self._get_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = None
            title_elem = soup.select_one('h1, .publication-title, .title')
            if title_elem:
                title = self.clean_text(title_elem.get_text())
            
            if not title:
                return None
            
            # Extract authors
            authors = []
            author_elems = soup.select('.author, .authors-list li')
            for elem in author_elems:
                name = self.clean_text(elem.get_text())
                if name and len(name) > 2:
                    authors.append({"full_name": name})
            
            # Extract abstract
            abstract = None
            abstract_elem = soup.select_one('.abstract, .annotation, .summary')
            if abstract_elem:
                abstract = self.clean_text(abstract_elem.get_text())
            
            # Extract journal/source
            journal = None
            journal_elem = soup.select_one('.journal, .source, .publication-source')
            if journal_elem:
                journal = self.clean_text(journal_elem.get_text())
            
            # Extract year
            year = None
            year_elem = soup.select_one('.year, .publication-year')
            if year_elem:
                year_text = year_elem.get_text()
                year_match = re.search(r'(\d{4})', year_text)
                if year_match:
                    year = int(year_match.group(1))
            
            # Extract keywords
            keywords = []
            keywords_elem = soup.select_one('.keywords, .tags')
            if keywords_elem:
                kw_text = keywords_elem.get_text()
                keywords = [k.strip() for k in re.split(r'[,;]', kw_text) if k.strip()]
            
            # UDC/BBK codes
            udc = None
            udc_elem = soup.select_one('.udc, .udk, [class*="udc"]')
            if udc_elem:
                udc = self.clean_text(udc_elem.get_text())
            
            return PaperData(
                title=title,
                title_ru=title,
                source_type=self.SOURCE_NAME.lower(),
                source_id=paper_id,
                source_url=url,
                abstract=abstract,
                abstract_ru=abstract,
                authors=authors,
                journal=journal,
                publication_year=year,
                keywords=keywords + ([f"УДК: {udc}"] if udc else []),
                language="ru"
            )
            
        except Exception as e:
            logger.error(f"Error fetching publication {paper_id} from INION: {e}")
            return None
    
    def _extract_pub_id(self, href: str) -> Optional[str]:
        """Extract publication ID from URL."""
        if not href:
            return None
        match = re.search(r'/(?:publication|item)/(\d+)', href)
        return match.group(1) if match else None
