"""PDF processing - extract text and convert to Markdown."""
import io
import logging
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Process PDFs - extract text, metadata, convert to Markdown."""
    
    def __init__(self):
        self.supported_extractors = ["pymupdf", "pdfplumber", "pypdf2"]
    
    async def extract_text(self, pdf_bytes: bytes, method: str = "auto") -> Dict[str, Any]:
        """
        Extract text from PDF bytes.
        
        Returns:
            {
                "full_text": str,
                "pages": [str],
                "metadata": dict,
                "method_used": str
            }
        """
        methods_to_try = [method] if method != "auto" else ["pymupdf", "pdfplumber", "pypdf2"]
        
        for method_name in methods_to_try:
            try:
                if method_name == "pymupdf":
                    return await self._extract_with_pymupdf(pdf_bytes)
                elif method_name == "pdfplumber":
                    return await self._extract_with_pdfplumber(pdf_bytes)
                elif method_name == "pypdf2":
                    return await self._extract_with_pypdf2(pdf_bytes)
            except Exception as e:
                logger.warning(f"{method_name} extraction failed: {e}")
                continue
        
        # All methods failed
        return {
            "full_text": "",
            "pages": [],
            "metadata": {},
            "method_used": "failed"
        }
    
    async def _extract_with_pymupdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extract using PyMuPDF (fitz) - best quality."""
        import fitz  # PyMuPDF
        import asyncio
        
        loop = asyncio.get_event_loop()
        
        def _extract():
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages = []
            metadata = {
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                pages.append(text)
            
            doc.close()
            full_text = "\n\n".join(pages)
            
            return {
                "full_text": full_text,
                "pages": pages,
                "metadata": metadata,
                "method_used": "pymupdf"
            }
        
        return await loop.run_in_executor(None, _extract)
    
    async def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extract using pdfplumber."""
        import pdfplumber
        import asyncio
        
        loop = asyncio.get_event_loop()
        
        def _extract():
            pages = []
            metadata = {}
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                metadata["page_count"] = len(pdf.pages)
                
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages.append(text)
            
            full_text = "\n\n".join(pages)
            
            return {
                "full_text": full_text,
                "pages": pages,
                "metadata": metadata,
                "method_used": "pdfplumber"
            }
        
        return await loop.run_in_executor(None, _extract)
    
    async def _extract_with_pypdf2(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """Extract using PyPDF2 (fallback)."""
        import PyPDF2
        import asyncio
        
        loop = asyncio.get_event_loop()
        
        def _extract():
            reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            pages = []
            metadata = {
                "page_count": len(reader.pages),
            }
            
            for page in reader.pages:
                text = page.extract_text() or ""
                pages.append(text)
            
            full_text = "\n\n".join(pages)
            
            return {
                "full_text": full_text,
                "pages": pages,
                "metadata": metadata,
                "method_used": "pypdf2"
            }
        
        return await loop.run_in_executor(None, _extract)
    
    async def to_markdown(self, pdf_bytes: bytes, paper_metadata: Optional[Dict] = None) -> str:
        """
        Convert PDF to Markdown format.
        
        Args:
            pdf_bytes: PDF file bytes
            paper_metadata: Optional paper metadata (title, authors, etc.)
            
        Returns:
            Markdown string
        """
        extraction = await self.extract_text(pdf_bytes)
        full_text = extraction["full_text"]
        pdf_meta = extraction["metadata"]
        
        # Build Markdown
        md_parts = []
        
        # Header with metadata
        if paper_metadata:
            title = paper_metadata.get("title", "Untitled")
            md_parts.append(f"# {title}\n")
            
            if paper_metadata.get("authors"):
                authors = ", ".join(paper_metadata["authors"])
                md_parts.append(f"**Authors:** {authors}\n")
            
            if paper_metadata.get("doi"):
                md_parts.append(f"**DOI:** {paper_metadata['doi']}\n")
            
            if paper_metadata.get("publication_year"):
                md_parts.append(f"**Year:** {paper_metadata['publication_year']}\n")
            
            md_parts.append("---\n")
        
        # Clean up text for Markdown
        cleaned_text = self._clean_text_for_markdown(full_text)
        md_parts.append(cleaned_text)
        
        # Footer
        md_parts.append("\n---\n")
        md_parts.append(f"*Extracted from PDF using {extraction['method_used']}*\n")
        
        return "\n".join(md_parts)
    
    def _clean_text_for_markdown(self, text: str) -> str:
        """Clean text for Markdown output."""
        # Remove excessive whitespace
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        
        # Fix broken lines (lines that end without punctuation)
        text = re.sub(r'([^\.\!\?\n])\n(?=[a-z])', r'\1 ', text)
        
        # Detect headers (all caps lines)
        lines = text.split('\n')
        result = []
        for line in lines:
            stripped = line.strip()
            if stripped.isupper() and len(stripped) > 3 and len(stripped) < 100:
                # Convert to Markdown header
                result.append(f"## {stripped.title()}")
            else:
                result.append(line)
        
        return '\n'.join(result)
    
    async def extract_chunks(self, pdf_bytes: bytes, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
        """
        Extract text in overlapping chunks for better search.
        
        Returns:
            List of chunks with metadata:
            [{"text": str, "page": int, "chunk_index": int}, ...]
        """
        extraction = await self.extract_text(pdf_bytes)
        pages = extraction["pages"]
        
        chunks = []
        chunk_index = 0
        
        for page_num, page_text in enumerate(pages, 1):
            # Simple sentence-based chunking
            sentences = re.split(r'(?<=[.!?])\s+', page_text)
            
            current_chunk = []
            current_length = 0
            
            for sentence in sentences:
                sentence_length = len(sentence)
                
                if current_length + sentence_length > chunk_size and current_chunk:
                    # Save current chunk
                    chunks.append({
                        "text": " ".join(current_chunk),
                        "page": page_num,
                        "chunk_index": chunk_index,
                        "char_count": current_length
                    })
                    chunk_index += 1
                    
                    # Start new chunk with overlap
                    overlap_text = " ".join(current_chunk[-3:]) if len(current_chunk) >= 3 else " ".join(current_chunk)
                    current_chunk = [overlap_text, sentence]
                    current_length = len(overlap_text) + sentence_length
                else:
                    current_chunk.append(sentence)
                    current_length += sentence_length
            
            # Save remaining chunk
            if current_chunk:
                chunks.append({
                    "text": " ".join(current_chunk),
                    "page": page_num,
                    "chunk_index": chunk_index,
                    "char_count": current_length
                })
                chunk_index += 1
        
        return chunks


# Singleton instance
_pdf_processor: Optional[PDFProcessor] = None


def get_pdf_processor() -> PDFProcessor:
    """Get or create PDF processor."""
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PDFProcessor()
    return _pdf_processor
