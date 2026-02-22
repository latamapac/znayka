"""Crawler for Presidential Library (prlib.ru)."""
import logging
import re
from typing import AsyncGenerator, Optional, List, Dict, Any
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)


class PresidentialLibraryCrawler(BaseCrawler):
    """Crawler for Президентская библиотека им. Б.Н. Ельцина."""
    
    SOURCE_NAME = "Presidential_Library"
    SOURCE_CODE = "PRLB"
    BASE_URL = "https://www.prlib.ru"
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """Search Presidential Library catalog."""
        
        page = 1
        papers_found = 0
        
        while papers_found < limit:
            params = {
                "search": quote(query),
                "page": page,
            }
            
            if year_from:
                params["year[from]"] = year_from
            if year_to:
                params["year[to]"] = year_to
            
            # Focus on scientific/educational materials
            params["type"] = "scientific"
            
            search_url = f"{self.BASE_URL}/search?{'&'.join(f'{k}={v}' for k, v in params.items())}"
            
            try:
                html = await self._get_html(search_url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find result items
                items = soup.select('.search-result-item, .catalog-item, .document-item')
                
                if not items:
                    break
                
                for item in items:
                    if papers_found >= limit:
                        break
                    
                    link_elem = item.find('a', href=re.compile(r'/item/|/document/'))
                    if not link_elem:
                        continue
                    
                    href = link_elem.get('href')
                    item_id = self._extract_item_id(href)
                    
                    if not item_id:
                        continue
                    
                    paper_data = await self.get_paper_by_id(item_id)
                    if paper_data:
                        yield paper_data
                        papers_found += 1
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error searching Presidential Library page {page}: {e}")
                break
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """Get document details from Presidential Library."""
        
        url = f"{self.BASE_URL}/item/{paper_id}"
        
        try:
            html = await self._get_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = None
            title_elem = soup.select_one('h1, .document-title, .item-title')
            if title_elem:
                title = self.clean_text(title_elem.get_text())
            
            if not title:
                return None
            
            # Extract authors
            authors = []
            author_elems = soup.select('.author, .creator')
            for elem in author_elems:
                name = self.clean_text(elem.get_text())
                if name:
                    authors.append({"full_name": name})
            
            # Extract description
            abstract = None
            desc_elem = soup.select_one('.description, .annotation, .summary')
            if desc_elem:
                abstract = self.clean_text(desc_elem.get_text())
            
            # Extract year
            year = None
            year_elem = soup.select_one('.year, .date')
            if year_elem:
                year_text = year_elem.get_text()
                year_match = re.search(r'(\d{4})', year_text)
                if year_match:
                    year = int(year_match.group(1))
            
            # Extract publisher
            publisher = None
            pub_elem = soup.select_one('.publisher, .organization')
            if pub_elem:
                publisher = self.clean_text(pub_elem.get_text())
            
            # Subject headings
            keywords = []
            subject_elems = soup.select('.subject, .category, .theme')
            for elem in subject_elems:
                kw = self.clean_text(elem.get_text())
                if kw:
                    keywords.append(kw)
            
            # Digital copy
            pdf_url = None
            digital_elem = soup.select_one('a[href*="/download/"], a[href*=".pdf"]')
            if digital_elem:
                pdf_href = digital_elem.get('href')
                if pdf_href:
                    pdf_url = urljoin(self.BASE_URL, pdf_href)
            
            return PaperData(
                title=title,
                title_ru=title,
                source_type=self.SOURCE_NAME.lower(),
                source_id=paper_id,
                source_url=url,
                abstract=abstract,
                authors=authors,
                publisher=publisher or "Президентская библиотека",
                publication_year=year,
                keywords=keywords,
                pdf_url=pdf_url,
                language="ru"
            )
            
        except Exception as e:
            logger.error(f"Error fetching item {paper_id} from Presidential Library: {e}")
            return None
    
    def _extract_item_id(self, href: str) -> Optional[str]:
        """Extract item ID from URL."""
        if not href:
            return None
        match = re.search(r'/(?:item|document)/(\d+)', href)
        return match.group(1) if match else None
