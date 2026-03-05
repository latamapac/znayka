"""Crawler sources for Russian academic databases."""
from crawlers.sources.base import BaseCrawler, PaperData
from crawlers.sources.elibrary import ElibraryCrawler
from crawlers.sources.cyberleninka import CyberLeninkaCrawler
from crawlers.sources.arxiv import ArxivCrawler
from crawlers.sources.rsl_dissertations import RSLDissertationsCrawler
from crawlers.sources.rusneb import RusNEBCrawler
from crawlers.sources.inion import INIONCrawler
from crawlers.sources.hse_scientometrics import HSEScientometricsCrawler
from crawlers.sources.presidential_library import PresidentialLibraryCrawler
from crawlers.sources.rosstat_emiss import RosstatEMISSCrawler
from crawlers.sources.elibrary_scholar import ElibraryScholarCrawler

__all__ = [
    "BaseCrawler",
    "PaperData",
    "ElibraryCrawler",
    "CyberLeninkaCrawler",
    "ArxivCrawler",
    "RSLDissertationsCrawler",
    "RusNEBCrawler",
    "INIONCrawler",
    "HSEScientometricsCrawler",
    "PresidentialLibraryCrawler",
    "RosstatEMISSCrawler",
    "ElibraryScholarCrawler",
]

# Registry of all available crawlers
CRAWLER_REGISTRY = {
    "elibrary": ElibraryCrawler,
    "cyberleninka": CyberLeninkaCrawler,
    "arxiv": ArxivCrawler,
    "rsl_dissertations": RSLDissertationsCrawler,
    "rusneb": RusNEBCrawler,
    "inion": INIONCrawler,
    "hse_scientometrics": HSEScientometricsCrawler,
    "presidential_library": PresidentialLibraryCrawler,
    "rosstat": RosstatEMISSCrawler,
    "elibrary_scholar": ElibraryScholarCrawler,
}

# Source metadata for UI/documentation
SOURCE_METADATA = {
    "elibrary": {
        "name": "eLibrary.ru",
        "name_ru": "eLibrary.ru",
        "description": "Российский индекс научного цитирования (РИНЦ)",
        "url": "https://elibrary.ru",
        "type": "academic",
        "language": "ru",
        "has_fulltext": True,
    },
    "cyberleninka": {
        "name": "CyberLeninka",
        "name_ru": "КиберЛенинка",
        "description": "Открытая научная электронная библиотека",
        "url": "https://cyberleninka.ru",
        "type": "academic",
        "language": "ru",
        "has_fulltext": True,
    },
    "arxiv": {
        "name": "arXiv",
        "name_ru": "arXiv",
        "description": "Препринты по физике, математике, информатике",
        "url": "https://arxiv.org",
        "type": "academic",
        "language": "en",
        "has_fulltext": True,
    },
    "rsl_dissertations": {
        "name": "RSL Dissertations",
        "name_ru": "РГБ Диссертации",
        "description": "Электронная библиотека диссертаций Российской государственной библиотеки",
        "url": "https://diss.rsl.ru",
        "type": "dissertation",
        "language": "ru",
        "has_fulltext": True,
    },
    "rusneb": {
        "name": "NEB",
        "name_ru": "НЭБ",
        "description": "Национальная электронная библиотека",
        "url": "https://rusneb.ru",
        "type": "library",
        "language": "ru",
        "has_fulltext": True,
    },
    "inion": {
        "name": "INION RAN",
        "name_ru": "ИНИОН РАН",
        "description": "Институт научной информации по общественным наукам РАН",
        "url": "https://inion.ru",
        "type": "academic",
        "language": "ru",
        "has_fulltext": False,
    },
    "hse_scientometrics": {
        "name": "HSE Scientometrics",
        "name_ru": "ВШЭ Наукометрика",
        "description": "Научометрические данные НИУ ВШЭ",
        "url": "https://scientometrics.hse.ru",
        "type": "academic",
        "language": "ru",
        "has_fulltext": False,
    },
    "presidential_library": {
        "name": "Presidential Library",
        "name_ru": "Президентская библиотека",
        "description": "Президентская библиотека имени Б.Н. Ельцина",
        "url": "https://www.prlib.ru",
        "type": "library",
        "language": "ru",
        "has_fulltext": True,
    },
    "rosstat": {
        "name": "Rosstat",
        "name_ru": "Росстат",
        "description": "Федеральная служба государственной статистики",
        "url": "https://rosstat.gov.ru",
        "type": "government",
        "language": "ru",
        "has_fulltext": True,
    },
    "elibrary_scholar": {
        "name": "eLibrary (via Scholar)",
        "name_ru": "eLibrary (через Google Scholar)",
        "description": "Поиск статей eLibrary.ru через Google Scholar — обход блокировки по IP",
        "url": "https://elibrary.ru",
        "type": "academic",
        "language": "ru",
        "has_fulltext": True,
    },
}


def get_crawler_class(source: str):
    """Get crawler class by source name."""
    return CRAWLER_REGISTRY.get(source.lower())


def get_available_sources():
    """Get list of all available sources."""
    return list(CRAWLER_REGISTRY.keys())


def get_source_info(source: str):
    """Get metadata for a source."""
    return SOURCE_METADATA.get(source.lower())
