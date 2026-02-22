"""Crawler for National Electronic Library (НЭБ) - rusneb.ru."""
import logging
import re
from typing import AsyncGenerator, Optional, List, Dict, Any
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)


class RusNEBCrawler(BaseCrawler):
    """Crawler for Национальная электронная библиотека (НЭБ)."""
    
    SOURCE_NAME = "RusNEB"
    SOURCE_CODE = "RNEB"
    BASE_URL = "https://rusneb.ru"
    SEARCH_URL = "https://rusneb.ru/search"
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """Search National Electronic Library."""
        
        page = 1
        papers_found = 0
        
        while papers_found < limit:
            params = {
                "q": quote(query),
                "page": page,
                "sort": "relevance",
            }
            
            if year_from:
                params["year_from"] = year_from
            if year_to:
                params["year_to"] = year_to
            
            # Filter for scientific works
            params["type"] = "scientific"
            
            search_url = f"{self.SEARCH_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
            
            try:
                html = await self._get_html(search_url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find result items
                items = soup.select('.search-result-item, .item, .result')
                
                if not items:
                    break
                
                for item in items:
                    if papers_found >= limit:
                        break
                    
                    link_elem = item.find('a', href=re.compile(r'/item/|/catalog/'))
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
                
                # Check for next page
                next_btn = soup.select_one('.next, .pagination-next, a[rel="next"]')
                if not next_btn or 'disabled' in str(next_btn.get('class', [])):
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error searching RusNEB page {page}: {e}")
                break
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """Get item details from RusNEB."""
        
        url = f"{self.BASE_URL}/item/{paper_id}"
        
        try:
            html = await self._get_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = None
            title_elem = soup.select_one('h1, .item-title, .title, [property="name"]')
            if title_elem:
                title = self.clean_text(title_elem.get_text())
            
            if not title:
                return None
            
            # Extract authors
            authors = []
            author_elems = soup.select('.author, .creator, [property="author"]')
            for elem in author_elems:
                name = self.clean_text(elem.get_text())
                if name:
                    authors.append({"full_name": name})
            
            # Extract description/abstract
            abstract = None
            desc_elem = soup.select_one('.description, .abstract, [property="description"]')
            if desc_elem:
                abstract = self.clean_text(desc_elem.get_text())
            
            # Extract year
            year = None
            year_elem = soup.select_one('.year, .date, [property="datePublished"]')
            if year_elem:
                year_text = year_elem.get_text()
                year_match = re.search(r'(\d{4})', year_text)
                if year_match:
                    year = int(year_match.group(1))
            
            # Extract publisher
            publisher = None
            pub_elem = soup.select_one('.publisher, [property="publisher"]')
            if pub_elem:
                publisher = self.clean_text(pub_elem.get_text())
            
            # Extract subjects/keywords
            keywords = []
            subject_elems = soup.select('.subject, .keyword, [property="about"]')
            for elem in subject_elems:
                kw = self.clean_text(elem.get_text())
                if kw:
                    keywords.append(kw)
            
            # Digital copy link
            pdf_url = None
            digital_link = soup.select_one('a[href*="/digital/"], a[href*=".pdf"]')
            if digital_link:
                pdf_href = digital_link.get('href')
                if pdf_href:
                    pdf_url = urljoin(self.BASE_URL, pdf_href)
            
            return PaperData(
                title=title,
                title_ru=title if self._is_russian(title) else None,
                source_type=self.SOURCE_NAME.lower(),
                source_id=paper_id,
                source_url=url,
                abstract=abstract,
                authors=authors,
                publisher=publisher,
                publication_year=year,
                keywords=keywords,
                pdf_url=pdf_url,
                language="ru" if self._is_russian(title) else "en"
            )
            
        except Exception as e:
            logger.error(f"Error fetching item {paper_id} from RusNEB: {e}")
            return None
    
    def _extract_item_id(self, href: str) -> Optional[str]:
        """Extract item ID from URL."""
        if not href:
            return None
        match = re.search(r'/(?:item|catalog)/(\d+)', href)
        return match.group(1) if match else None
    
    def _is_russian(self, text: str) -> bool:
        """Check if text contains Russian characters."""
        return bool(re.search(r'[а-яА-ЯёЁ]', text))
