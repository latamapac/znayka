"""Crawler for arXiv.org - Physics, math, CS papers."""
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import AsyncGenerator, Optional, List, Dict, Any
from urllib.parse import urlencode

from crawlers.sources.base import BaseCrawler, PaperData

logger = logging.getLogger(__name__)


class ArxivCrawler(BaseCrawler):
    """Crawler for arXiv.org using their API."""
    
    SOURCE_NAME = "arXiv"
    SOURCE_CODE = "ARXV"
    BASE_URL = "http://export.arxiv.org"
    API_URL = "http://export.arxiv.org/api/query"
    
    # arXiv categories relevant to Russian research
    RUSSIAN_CATEGORIES = [
        "cs.",      # Computer Science
        "math.",    # Mathematics
        "physics.", # Physics
        "q-bio.",   # Quantitative Biology
        "q-fin.",   # Quantitative Finance
        "stat.",    # Statistics
        "econ.",    # Economics
        "eess.",    # Electrical Engineering and Systems Science
    ]
    
    async def search_papers(
        self,
        query: str,
        limit: int = 100,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> AsyncGenerator[PaperData, None]:
        """Search arXiv for papers."""
        
        # Build search query
        search_query = query
        
        # Add Russian institutions to query if searching for Russian authors
        if 'russia' in query.lower() or 'russian' in query.lower():
            search_query += " AND (affiliation:russia OR affiliation:moscow OR affiliation:saint+petersburg)"
        
        start = 0
        max_results_per_request = min(limit, 100)  # arXiv limit
        papers_found = 0
        
        while papers_found < limit:
            params = {
                "search_query": search_query,
                "start": start,
                "max_results": max_results_per_request,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            
            try:
                url = f"{self.API_URL}?{urlencode(params)}"
                response = await self._make_request(url)
                xml_content = await response.text()
                
                # Parse XML
                root = ET.fromstring(xml_content)
                
                # Define namespace
                ns = {
                    'atom': 'http://www.w3.org/2005/Atom',
                    'arxiv': 'http://arxiv.org/schemas/atom'
                }
                
                entries = root.findall('atom:entry', ns)
                
                if not entries:
                    break
                
                for entry in entries:
                    if papers_found >= limit:
                        break
                    
                    paper_data = self._parse_entry(entry, ns)
                    if paper_data:
                        # Filter by year if specified
                        if year_from and paper_data.publication_year and paper_data.publication_year < year_from:
                            continue
                        if year_to and paper_data.publication_year and paper_data.publication_year > year_to:
                            continue
                        
                        yield paper_data
                        papers_found += 1
                
                if len(entries) < max_results_per_request:
                    break
                
                start += max_results_per_request
                
            except Exception as e:
                logger.error(f"Error searching arXiv: {e}")
                break
    
    async def get_paper_by_id(self, paper_id: str) -> Optional[PaperData]:
        """Get paper details from arXiv."""
        
        # Clean paper ID
        paper_id = paper_id.replace('arxiv:', '').strip()
        
        params = {
            "id_list": paper_id,
            "max_results": 1
        }
        
        try:
            url = f"{self.API_URL}?{urlencode(params)}"
            response = await self._make_request(url)
            xml_content = await response.text()
            
            root = ET.fromstring(xml_content)
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            entry = root.find('atom:entry', ns)
            if entry is not None:
                return self._parse_entry(entry, ns)
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching paper {paper_id} from arXiv: {e}")
            return None
    
    def _parse_entry(self, entry: ET.Element, ns: Dict[str, str]) -> Optional[PaperData]:
        """Parse arXiv Atom entry to PaperData."""
        
        try:
            # Extract title
            title_elem = entry.find('atom:title', ns)
            title = self.clean_text(title_elem.text) if title_elem is not None else None
            
            if not title:
                return None
            
            # Extract arXiv ID
            id_elem = entry.find('atom:id', ns)
            arxiv_id = None
            if id_elem is not None:
                arxiv_url = id_elem.text
                arxiv_id = arxiv_url.split('/abs/')[-1] if '/abs/' in arxiv_url else arxiv_url
            
            # Extract abstract
            summary_elem = entry.find('atom:summary', ns)
            abstract = self.clean_text(summary_elem.text) if summary_elem is not None else None
            
            # Extract authors
            authors: List[Dict[str, Any]] = []
            author_elems = entry.findall('atom:author', ns)
            for author_elem in author_elems:
                name_elem = author_elem.find('atom:name', ns)
                if name_elem is not None:
                    authors.append({"full_name": name_elem.text})
            
            # Extract categories/keywords
            keywords = []
            category_elems = entry.findall('atom:category', ns)
            for cat_elem in category_elems:
                term = cat_elem.get('term')
                if term:
                    keywords.append(term)
            
            # Extract publication date
            published_elem = entry.find('atom:published', ns)
            publication_year = None
            if published_elem is not None:
                try:
                    pub_date = datetime.fromisoformat(published_elem.text.replace('Z', '+00:00'))
                    publication_year = pub_date.year
                except:
                    pass
            
            # Extract DOI if available
            doi_elem = entry.find('arxiv:doi', ns)
            doi = doi_elem.text if doi_elem is not None else None
            
            # Extract journal reference if available
            journal_elem = entry.find('arxiv:journal_ref', ns)
            journal = journal_elem.text if journal_elem is not None else None
            
            # Build PDF URL
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None
            
            # Check if Russian-affiliated
            is_russian = self._has_russian_affiliation(entry, ns)
            
            return PaperData(
                title=title,
                source_type=self.SOURCE_NAME.lower(),
                source_id=arxiv_id,
                source_url=f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None,
                abstract=abstract,
                authors=authors,
                journal=journal,
                publication_year=publication_year,
                doi=doi,
                arxiv_id=arxiv_id,
                keywords=keywords,
                pdf_url=pdf_url,
                language="en"
            )
            
        except Exception as e:
            logger.error(f"Error parsing arXiv entry: {e}")
            return None
    
    def _has_russian_affiliation(self, entry: ET.Element, ns: Dict[str, str]) -> bool:
        """Check if paper has Russian author affiliations."""
        
        russian_keywords = [
            'russia', 'russian', 'moscow', 'saint petersburg', 'novosibirsk',
            'ekaterinburg', 'kazan', 'nizhny novgorod', 'красноярск', 'москва',
            'петербург', 'россия', 'сибирь'
        ]
        
        # Check affiliation elements
        for author in entry.findall('atom:author', ns):
            affil_elem = author.find('arxiv:affiliation', ns)
            if affil_elem is not None and affil_elem.text:
                affil_lower = affil_elem.text.lower()
                if any(kw in affil_lower for kw in russian_keywords):
                    return True
        
        # Check summary/abstract for Russian clues
        summary_elem = entry.find('atom:summary', ns)
        if summary_elem is not None and summary_elem.text:
            summary_lower = summary_elem.text.lower()
            if any(kw in summary_lower for kw in russian_keywords):
                return True
        
        return False
