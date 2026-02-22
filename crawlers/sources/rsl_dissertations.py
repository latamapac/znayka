"""Crawler for Russian State Library Dissertations (diss.rsl.ru)."""
import logging
import re
from datetime import datetime
from typing import AsyncGenerator, Optional, List, Dict, Any
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)


class RSLDissertationsCrawler(BaseCrawler):
    """Crawler for РГБ - Электронная библиотека диссертаций."""
    
    SOURCE_NAME = "RSL_Dissertations"
    SOURCE_CODE = "RSLD"
    BASE_URL = "https://diss.rsl.ru"
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """Search RSL dissertations database."""
        
        page = 1
        papers_found = 0
        
        while papers_found < limit:
            # RSL uses a search form
            search_params = {
                "search": quote(query),
                "page": page,
            }
            
            if year_from:
                search_params["year_from"] = year_from
            if year_to:
                search_params["year_to"] = year_to
            
            search_url = f"{self.BASE_URL}/ru/search/dissertation/?{'&'.join(f'{k}={v}' for k, v in search_params.items())}"
            
            try:
                html = await self._get_html(search_url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find dissertation cards
                dissertations = soup.select('.dissertation-item, .search-item, .result-item')
                
                if not dissertations:
                    # Try alternative selectors
                    dissertations = soup.find_all('div', class_=re.compile(r'diss|result|item'))
                
                if not dissertations:
                    break
                
                for diss_elem in dissertations:
                    if papers_found >= limit:
                        break
                    
                    # Extract link to dissertation
                    link_elem = diss_elem.find('a', href=re.compile(r'/ru/dissertation/\d+'))
                    if not link_elem:
                        continue
                    
                    href = link_elem.get('href')
                    if not href:
                        continue
                    
                    diss_id = self._extract_diss_id(href)
                    if not diss_id:
                        continue
                    
                    paper_data = await self.get_paper_by_id(diss_id)
                    if paper_data:
                        yield paper_data
                        papers_found += 1
                
                # Check for next page
                next_page = soup.find('a', text=re.compile(r'след|next|→', re.I))
                if not next_page:
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error searching RSL page {page}: {e}")
                break
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """Get dissertation details from RSL."""
        
        url = f"{self.BASE_URL}/ru/dissertation/{paper_id}"
        
        try:
            html = await self._get_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = None
            title_elem = soup.select_one('h1, .dissertation-title, .title')
            if title_elem:
                title = self.clean_text(title_elem.get_text())
            
            if not title:
                logger.warning(f"Could not extract title for dissertation {paper_id}")
                return None
            
            # Extract author
            authors = []
            author_elem = soup.select_one('.author, .dissertation-author, [class*="author"]')
            if author_elem:
                author_name = self.clean_text(author_elem.get_text())
                if author_name:
                    authors.append({"full_name": author_name})
            
            # Extract abstract
            abstract = None
            abstract_elem = soup.select_one('.abstract, .annotation, [class*="abstract"]')
            if abstract_elem:
                abstract = self.clean_text(abstract_elem.get_text())
            
            # Extract degree info
            degree = None
            degree_elem = soup.select_one('.degree, .academic-degree, [class*="degree"]')
            if degree_elem:
                degree = self.clean_text(degree_elem.get_text())
            
            # Extract specialty code (код специальности ВАК)
            specialty_code = None
            specialty_elem = soup.select_one('.specialty, .specialnost, [class*="specialty"]')
            if specialty_elem:
                specialty_code = self.clean_text(specialty_elem.get_text())
            
            # Extract year
            year = None
            year_elem = soup.select_one('.year, .defense-year, [class*="year"]')
            if year_elem:
                year_text = year_elem.get_text()
                year_match = re.search(r'(\d{4})', year_text)
                if year_match:
                    year = int(year_match.group(1))
            
            # Extract organization
            organization = None
            org_elem = soup.select_one('.organization, .institution, .university')
            if org_elem:
                organization = self.clean_text(org_elem.get_text())
            
            # Extract keywords
            keywords = []
            keywords_elem = soup.select_one('.keywords, .key-words')
            if keywords_elem:
                kw_text = keywords_elem.get_text()
                keywords = [k.strip() for k in re.split(r'[,;]', kw_text) if k.strip()]
            
            # PDF link (if available)
            pdf_url = None
            pdf_link = soup.select_one('a[href*=".pdf"], a[href*="/download/"]')
            if pdf_link:
                pdf_href = pdf_link.get('href')
                if pdf_href:
                    pdf_url = urljoin(self.BASE_URL, pdf_href)
            
            return PaperData(
                title=title,
                title_ru=title,
                source_type=self.SOURCE_NAME.lower(),
                source_id=paper_id,
                source_url=url,
                abstract=abstract,
                abstract_ru=abstract,
                authors=authors,
                journal=f"{degree} - {specialty_code}" if degree and specialty_code else degree,
                publication_year=year,
                keywords=keywords,
                pdf_url=pdf_url,
                language="ru"
            )
            
        except Exception as e:
            logger.error(f"Error fetching dissertation {paper_id} from RSL: {e}")
            return None
    
    def _extract_diss_id(self, href: str) -> Optional[str]:
        """Extract dissertation ID from URL."""
        match = re.search(r'/dissertation/(\d+)', href)
        return match.group(1) if match else None
