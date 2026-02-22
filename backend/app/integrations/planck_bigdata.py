"""Planck Big Data Analytics Integration.

This module provides integration with Planck's Big Data analytics platform
including Apache Superset dashboards and analytics queries.
"""
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime

import httpx
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class AnalyticsQuery:
    """Analytics query structure for Planck."""
    query: str
    database: str = "russia_science_hub"
    schema: str = "public"
    
    
@dataclass
class DashboardConfig:
    """Superset dashboard configuration."""
    dashboard_id: str
    title: str
    charts: List[Dict[str, Any]]


class PlanckBigDataClient:
    """
    Client for Planck Big Data Analytics integration.
    
    Features:
    - Query data from Superset/Analytics
    - Create dashboards for paper statistics
    - Export data for analysis
    - Run big data queries
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.base_url = base_url or getattr(settings, 'PLANCK_URL', None) or "http://localhost:3001"
        self.api_key = api_key or getattr(settings, 'PLANCK_API_KEY', None)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
            timeout=60.0
        )
    
    async def query_papers(
        self,
        query: str,
        limit: int = 100,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Query papers using Planck analytics engine.
        
        Args:
            query: SQL query or natural language query
            limit: Maximum results
            filters: Additional filters
            
        Returns:
            List of paper records
        """
        try:
            payload = {
                "query": query,
                "limit": limit,
                "filters": filters or {}
            }
            
            response = await self.client.post(
                "/api/analytics/query",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("results", [])
            
        except Exception as e:
            logger.error(f"Planck query error: {e}")
            return []
    
    async def get_paper_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive paper statistics from Planck analytics.
        
        Returns:
            Statistics including counts, trends, sources
        """
        try:
            response = await self.client.get("/api/analytics/statistics/papers")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return self._get_fallback_statistics()
    
    async def create_dashboard(
        self,
        name: str,
        config: DashboardConfig
    ) -> Optional[str]:
        """
        Create a Superset dashboard for paper analytics.
        
        Args:
            name: Dashboard name
            config: Dashboard configuration
            
        Returns:
            Dashboard URL or None
        """
        try:
            payload = {
                "name": name,
                "type": "superset",
                "config": {
                    "dashboard_id": config.dashboard_id,
                    "title": config.title,
                    "charts": config.charts
                }
            }
            
            response = await self.client.post(
                "/api/analytics/dashboards",
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("url")
            
        except Exception as e:
            logger.error(f"Failed to create dashboard: {e}")
            return None
    
    async def export_data(
        self,
        format: str = "csv",
        filters: Optional[Dict] = None
    ) -> Optional[bytes]:
        """
        Export paper data in various formats.
        
        Args:
            format: Export format (csv, json, parquet)
            filters: Export filters
            
        Returns:
            Exported data as bytes
        """
        try:
            params = {"format": format}
            if filters:
                params["filters"] = json.dumps(filters)
            
            response = await self.client.get(
                "/api/analytics/export",
                params=params,
                timeout=120.0
            )
            response.raise_for_status()
            
            return response.content
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None
    
    async def run_bigdata_query(
        self,
        query_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run big data analytics query.
        
        Query types:
        - "trends": Paper publication trends
        - "citations": Citation analysis
        - "authors": Author collaboration networks
        - "topics": Topic modeling
        
        Args:
            query_type: Type of analytics query
            params: Query parameters
            
        Returns:
            Query results
        """
        try:
            payload = {
                "type": query_type,
                "params": params,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = await self.client.post(
                "/api/analytics/bigdata",
                json=payload,
                timeout=300.0  # 5 minutes for big queries
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Big data query failed: {e}")
            return {"error": str(e), "results": []}
    
    async def get_research_trends(
        self,
        field: Optional[str] = None,
        year_from: int = 2020,
        year_to: int = 2024
    ) -> Dict[str, Any]:
        """
        Get research trends analysis.
        
        Args:
            field: Research field (optional)
            year_from: Start year
            year_to: End year
            
        Returns:
            Trends data
        """
        return await self.run_bigdata_query(
            "trends",
            {
                "field": field,
                "year_from": year_from,
                "year_to": year_to
            }
        )
    
    async def get_citation_network(
        self,
        paper_id: str,
        depth: int = 2
    ) -> Dict[str, Any]:
        """
        Get citation network for a paper.
        
        Args:
            paper_id: Paper ID
            depth: Network depth (1-3)
            
        Returns:
            Citation network data
        """
        return await self.run_bigdata_query(
            "citations",
            {
                "paper_id": paper_id,
                "depth": depth
            }
        )
    
    def _get_fallback_statistics(self) -> Dict[str, Any]:
        """Fallback statistics when Planck is unavailable."""
        return {
            "total_papers": 0,
            "by_source": {},
            "by_year": {},
            "planck_connected": False,
            "note": "Planck analytics unavailable - using local data"
        }
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Global client instance
_planck_client: Optional[PlanckBigDataClient] = None


def get_planck_client() -> PlanckBigDataClient:
    """Get or create Planck client instance."""
    global _planck_client
    if _planck_client is None:
        _planck_client = PlanckBigDataClient()
    return _planck_client
