"""Crawler for HSE Scientometrics (scientometrics.hse.ru)."""
import logging
import re
from typing import AsyncGenerator, Optional, List, Dict, Any
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)


class HSEScientometricsCrawler(BaseCrawler):
    """Crawler for НИУ ВШЭ - Научометрика."""
    
    SOURCE_NAME = "HSE_Scientometrics"
    SOURCE_CODE = "HSE"
    BASE_URL = "https://scientometrics.hse.ru"
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """Search HSE scientometrics database."""
        
        page = 1
        papers_found = 0
        
        # HSE has different lists/pages for publications
        urls_to_check = [
            f"{self.BASE_URL}/lists/",
            f"{self.BASE_URL}/search?q={quote(query)}",
        ]
        
        for search_url in urls_to_check:
            if papers_found >= limit:
                break
            
            try:
                html = await self._get_html(search_url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find publication items
                items = soup.select('.publication-item, .article-item, .research-item, tr')
                
                for item in items:
                    if papers_found >= limit:
                        break
                    
                    # Try to extract title and link
                    link_elem = item.find('a', href=re.compile(r'/publication/|/article/|/research/'))
                    if not link_elem:
                        # Try extracting from table row
                        title_elem = item.find('td', class_=re.compile(r'title|name'))
                        if title_elem:
                            link_elem = title_elem.find('a')
                    
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
                
            except Exception as e:
                logger.error(f"Error searching HSE: {e}")
                continue
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """Get publication details from HSE."""
        
        url = f"{self.BASE_URL}/publication/{paper_id}"
        
        try:
            html = await self._get_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = None
            title_elem = soup.select_one('h1, .publication-title, .page-title')
            if title_elem:
                title = self.clean_text(title_elem.get_text())
            
            if not title:
                return None
            
            # Extract authors (HSE researchers)
            authors = []
            author_elems = soup.select('.author, .hse-author, .researcher')
            for elem in author_elems:
                name = self.clean_text(elem.get_text())
                if name:
                    authors.append({
                        "full_name": name,
                        "affiliations": ["НИУ ВШЭ"]
                    })
            
            # Extract abstract
            abstract = None
            abstract_elem = soup.select_one('.abstract, .description, .summary')
            if abstract_elem:
                abstract = self.clean_text(abstract_elem.get_text())
            
            # Extract journal
            journal = None
            journal_elem = soup.select_one('.journal, .source-title, .publication-source')
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
            
            # Extract DOI
            doi = None
            doi_elem = soup.select_one('.doi, a[href*="doi.org"]')
            if doi_elem:
                doi_text = doi_elem.get_text() if doi_elem.name != 'a' else doi_elem.get('href', '')
                doi = self.normalize_doi(doi_text)
            
            # Keywords
            keywords = []
            keywords_elem = soup.select_one('.keywords, .tags, .subjects')
            if keywords_elem:
                kw_text = keywords_elem.get_text()
                keywords = [k.strip() for k in re.split(r'[,;]', kw_text) if k.strip()]
            
            # Research areas at HSE
            research_area = None
            area_elem = soup.select_one('.research-area, .field, .department')
            if area_elem:
                research_area = self.clean_text(area_elem.get_text())
            
            return PaperData(
                title=title,
                title_ru=title if self._is_russian(title) else None,
                source_type=self.SOURCE_NAME.lower(),
                source_id=paper_id,
                source_url=url,
                abstract=abstract,
                authors=authors,
                journal=journal or research_area,
                publication_year=year,
                doi=doi,
                keywords=keywords,
                language="ru" if self._is_russian(title) else "en"
            )
            
        except Exception as e:
            logger.error(f"Error fetching publication {paper_id} from HSE: {e}")
            return None
    
    def _extract_pub_id(self, href: str) -> Optional[str]:
        """Extract publication ID from URL."""
        if not href:
            return None
        match = re.search(r'/(?:publication|article|research)/(\d+)', href)
        return match.group(1) if match else None
    
    def _is_russian(self, text: str) -> bool:
        """Check if text contains Russian characters."""
        return bool(re.search(r'[а-яА-ЯёЁ]', text))
