"""Crawler for eLibrary.ru - Russian Science Citation Index."""
import logging
import re
from typing import AsyncGenerator, Optional
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)


class ElibraryCrawler(BaseCrawler):
    """Crawler for eLibrary.ru."""
    
    SOURCE_NAME = "eLibrary"
    SOURCE_CODE = "ELIB"
    BASE_URL = "https://elibrary.ru"
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """Search eLibrary for papers."""
        
        params = {
            "query": query,
            "pagenum": 1,
        }
        
        if year_from:
            params["yearfrom"] = year_from
        if year_to:
            params["yearto"] = year_to
        
        papers_found = 0
        page = 1
        
        while papers_found < limit:
            params["pagenum"] = page
            search_url = f"{self.BASE_URL}/query_results.asp?{urlencode(params)}"
            
            try:
                html = await self._get_html(search_url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find paper links
                paper_links = soup.select('a[href*="item.asp?id="]')
                
                if not paper_links:
                    break
                
                for link in paper_links:
                    if papers_found >= limit:
                        break
                    
                    href = link.get('href')
                    if not href:
                        continue
                    
                    paper_id = self._extract_paper_id(href)
                    if paper_id:
                        paper_data = await self.get_paper_by_id(paper_id)
                        if paper_data:
                            yield paper_data
                            papers_found += 1
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error searching eLibrary page {page}: {e}")
                break
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """Get paper details from eLibrary."""
        
        url = f"{self.BASE_URL}/item.asp?id={paper_id}"
        
        try:
            html = await self._get_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title_elem = soup.select_one('h1, .title, [class*="title"]')
            title = self.clean_text(title_elem.get_text()) if title_elem else None
            
            if not title:
                logger.warning(f"Could not extract title for paper {paper_id}")
                return None
            
            # Extract authors
            authors = []
            author_elems = soup.select('a[href*="author_profile.asp"], .author')
            for elem in author_elems:
                author_name = self.clean_text(elem.get_text())
                if author_name:
                    authors.append({"full_name": author_name})
            
            # Extract abstract
            abstract = None
            abstract_elem = soup.select_one('[class*="abstract"], .abstract, #abstract')
            if abstract_elem:
                abstract = self.clean_text(abstract_elem.get_text())
            
            # Extract journal
            journal = None
            journal_elem = soup.select_one('a[href*="journal_profile"], .journal')
            if journal_elem:
                journal = self.clean_text(journal_elem.get_text())
            
            # Extract year
            year = None
            year_match = re.search(r'20\d{2}|19\d{2}', html)
            if year_match:
                year = int(year_match.group())
            
            # Extract DOI
            doi = None
            doi_match = re.search(r'10\.\d{4,}/[^\s"<>]+', html)
            if doi_match:
                doi = self.normalize_doi(doi_match.group())
            
            # Extract keywords
            keywords = []
            keywords_elem = soup.select_one('[class*="keyword"], .keywords')
            if keywords_elem:
                keywords_text = keywords_elem.get_text()
                keywords = [k.strip() for k in re.split(r'[,;]', keywords_text) if k.strip()]
            
            # Extract PDF link
            pdf_url = None
            pdf_link = soup.select_one('a[href*=".pdf"], a[href*="download"], a[title*="PDF"]')
            if pdf_link:
                pdf_href = pdf_link.get('href')
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
                journal=journal,
                publication_year=year,
                doi=doi,
                keywords=keywords,
                pdf_url=pdf_url,
                language="ru" if self._is_russian(title) else "en"
            )
            
        except Exception as e:
            logger.error(f"Error fetching paper {paper_id} from eLibrary: {e}")
            return None
    
    def _extract_paper_id(self, href: str) -> Optional[str]:
        """Extract paper ID from URL."""
        match = re.search(r'id=(\d+)', href)
        return match.group(1) if match else None
    
    def _is_russian(self, text: str) -> bool:
        """Check if text contains Russian characters."""
        return bool(re.search(r'[а-яА-ЯёЁ]', text))
