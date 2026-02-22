"""Translation service - adapted from 626 translator for academic papers."""
import os
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
import json


class TranslationService:
    """
    Translation service for academic papers.
    Based on 626 translator - translates abstracts and papers.
    """
    
    def __init__(self):
        self.request_count = 0
        self.last_request_time = 0
        self.min_delay = 0.5
        
    async def translate_text(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "ru",
        context: str = ""
    ) -> str:
        """
        Translate text using available LLM APIs.
        
        Args:
            text: Text to translate
            source_lang: Source language code (en, ko, zh, etc.)
            target_lang: Target language code (ru, en, etc.)
            context: Optional context for better translation
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
            
        # Rate limiting
        import time
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)
        
        # Try translation APIs
        result = await self._try_translate(text, source_lang, target_lang, context)
        self.last_request_time = time.time()
        self.request_count += 1
        
        return result
    
    async def _try_translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str
    ) -> str:
        """Try different translation APIs."""
        
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")
        
        if anthropic_key:
            result = await self._translate_claude(
                text, source_lang, target_lang, context, anthropic_key
            )
            if result:
                return result
        
        if openai_key:
            result = await self._translate_openai(
                text, source_lang, target_lang, context, openai_key
            )
            if result:
                return result
        
        # Fallback: return original
        return text
    
    async def _translate_claude(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str,
        api_key: str
    ) -> Optional[str]:
        """Translate using Anthropic Claude (from 626)."""
        try:
            import aiohttp
            
            system_prompt = f"""You are a professional translator specializing in academic papers.
Translate from {source_lang} to {target_lang} preserving scientific terminology.
Output ONLY the translation, no explanations."""
            
            user_prompt = f"""Context: {context or 'Academic paper translation'}

Text to translate:
{text}

Translation:"""
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "claude-3-5-haiku-20241022",
                        "max_tokens": 2000,
                        "temperature": 0.3,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_prompt}]
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["content"][0]["text"].strip()
            return None
        except Exception as e:
            print(f"Claude translation error: {e}")
            return None
    
    async def _translate_openai(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str,
        api_key: str
    ) -> Optional[str]:
        """Translate using OpenAI."""
        try:
            import aiohttp
            
            prompt = f"""Translate the following academic text from {source_lang} to {target_lang}.
Preserve scientific terminology and academic style.

Context: {context or 'Academic paper'}

Text:
{text}

Translation:"""
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": "You are a professional academic translator."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"].strip()
            return None
        except Exception as e:
            print(f"OpenAI translation error: {e}")
            return None
    
    async def translate_paper_fields(
        self,
        title: str,
        abstract: str,
        keywords: List[str],
        source_lang: str = "en",
        target_lang: str = "ru"
    ) -> Dict[str, Any]:
        """
        Translate all paper fields.
        
        Returns:
            Dict with translated fields
        """
        context = f"Academic paper title: {title[:100]}"
        
        # Translate in parallel
        results = await asyncio.gather(
            self.translate_text(title, source_lang, target_lang, context),
            self.translate_text(abstract, source_lang, target_lang, context),
            asyncio.gather(*[
                self.translate_text(kw, source_lang, target_lang, context)
                for kw in keywords
            ]) if keywords else asyncio.gather(*[])
        )
        
        return {
            "title_translated": results[0],
            "abstract_translated": results[1],
            "keywords_translated": list(results[2]) if keywords else [],
            "source_language": source_lang,
            "target_language": target_lang,
            "translated_at": datetime.utcnow().isoformat()
        }
