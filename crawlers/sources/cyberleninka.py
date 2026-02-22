"""Crawler for CyberLeninka - Open access Russian scientific library."""
import logging
import re
from typing import AsyncGenerator, Optional, List, Dict, Any
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)


class CyberLeninkaCrawler(BaseCrawler):
    """Crawler for CyberLeninka.ru."""
    
    SOURCE_NAME = "CyberLeninka"
    SOURCE_CODE = "CYBL"
    BASE_URL = "https://cyberleninka.ru"
    API_URL = "https://cyberleninka.ru/api"
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """Search CyberLeninka for papers using their API."""
        
        page = 1
        papers_found = 0
        
        while papers_found < limit:
            # CyberLeninka uses a form-based search
            search_url = f"{self.BASE_URL}/article/search"
            
            payload = {
                "q": query,
                "page": page,
            }
            
            if year_from:
                payload["date_from"] = year_from
            if year_to:
                payload["date_to"] = year_to
            
            try:
                html = await self._get_html(f"{search_url}?{urlencode(payload)}")
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find paper cards
                paper_cards = soup.select('.title, h2, h3, .paper-title, a[href*="/article/n/"]')
                
                if not paper_cards:
                    break
                
                processed_urls = set()
                
                for card in paper_cards:
                    if papers_found >= limit:
                        break
                    
                    link = card if card.name == 'a' else card.find_parent('a')
                    if not link:
                        link = card.find('a')
                    
                    if not link:
                        continue
                    
                    href = link.get('href', '')
                    if '/article/n/' not in href:
                        continue
                    
                    full_url = urljoin(self.BASE_URL, href)
                    if full_url in processed_urls:
                        continue
                    
                    processed_urls.add(full_url)
                    
                    # Extract paper slug
                    slug = href.split('/article/n/')[-1].split('?')[0].split('#')[0]
                    
                    paper_data = await self.get_paper_by_id(slug)
                    if paper_data:
                        yield paper_data
                        papers_found += 1
                
                # Check if there's a next page
                next_page = soup.select_one('a[rel="next"], .next, .pagination-next')
                if not next_page:
                    break
                
                page += 1
                
            except Exception as e:
                logger.error(f"Error searching CyberLeninka page {page}: {e}")
                break
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """Get paper details from CyberLeninka."""
        
        url = f"{self.BASE_URL}/article/n/{paper_id}"
        
        try:
            html = await self._get_html(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = None
            title_elem = soup.select_one('h1, .main-title, .article-title')
            if title_elem:
                title = self.clean_text(title_elem.get_text())
            
            if not title:
                # Try alternative selectors
                title_elem = soup.select_one('meta[property="og:title"]')
                if title_elem:
                    title = title_elem.get('content')
            
            if not title:
                logger.warning(f"Could not extract title for paper {paper_id}")
                return None
            
            # Extract authors
            authors: List[Dict[str, Any]] = []
            author_elems = soup.select('.author, .author-name, a[href*="/author/"]')
            for elem in author_elems:
                author_name = self.clean_text(elem.get_text())
                if author_name and len(author_name) > 2:
                    authors.append({"full_name": author_name})
            
            # Extract abstract
            abstract = None
            abstract_elem = soup.select_one('.abstract, .full-abstract, [itemprop="description"]')
            if abstract_elem:
                abstract = self.clean_text(abstract_elem.get_text())
            
            # Extract journal
            journal = None
            journal_elem = soup.select_one('.journal, .article-journal, a[href*="/journal/"]')
            if journal_elem:
                journal = self.clean_text(journal_elem.get_text())
            
            # Extract year
            year = None
            year_elem = soup.select_one('.year, .article-year, [itemprop="datePublished"]')
            if year_elem:
                year_text = year_elem.get_text()
                year_match = re.search(r'(\d{4})', year_text)
                if year_match:
                    year = int(year_match.group(1))
            
            # Extract keywords
            keywords = []
            keyword_elems = soup.select('.keyword, .tag, a[href*="/tag/"]')
            for elem in keyword_elems:
                kw = self.clean_text(elem.get_text())
                if kw:
                    keywords.append(kw)
            
            # Extract PDF link - CyberLeninka provides direct PDF access
            pdf_url = f"{self.BASE_URL}/article/n/{paper_id}.pdf"
            
            # Extract DOI if available
            doi = None
            doi_elem = soup.select_one('[href*="doi.org"]')
            if doi_elem:
                doi_href = doi_elem.get('href', '')
                doi = self.normalize_doi(doi_href)
            
            # Determine language
            is_russian = self._is_russian(title) or self._is_russian(abstract or '')
            
            return PaperData(
                title=title,
                title_ru=title if is_russian else None,
                source_type=self.SOURCE_NAME.lower(),
                source_id=paper_id,
                source_url=url,
                abstract=abstract,
                abstract_ru=abstract if is_russian else None,
                authors=authors,
                journal=journal,
                publication_year=year,
                doi=doi,
                keywords=keywords,
                pdf_url=pdf_url,
                language="ru" if is_russian else "en"
            )
            
        except Exception as e:
            logger.error(f"Error fetching paper {paper_id} from CyberLeninka: {e}")
            return None
    
    def _is_russian(self, text: str) -> bool:
        """Check if text contains Russian characters."""
        return bool(re.search(r'[а-яА-ЯёЁ]', text))
