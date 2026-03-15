"""
权威地缘政治新闻收集器
从多个权威新闻源收集地缘政治相关新闻报道
支持NewsAPI、RSS订阅、官方新闻机构等数据源
"""

import asyncio
import aiohttp
import logging
import xml.etree.ElementTree as ET
import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
import json
import hashlib
from urllib.parse import urlparse, urlencode

from ..base_collector import DataCollector, CollectorConfig, DataSourceType, DataRecord

logger = logging.getLogger(__name__)


class NewsSource:
    """新闻源基类"""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config

    async def fetch_articles(self, max_articles: int = 50) -> List[Dict[str, Any]]:
        """获取文章列表"""
        raise NotImplementedError

    async def test_connection(self) -> bool:
        """测试连接"""
        raise NotImplementedError


class NewsAPISource(NewsSource):
    """NewsAPI源"""

    BASE_URL = "https://newsapi.org/v2"

    async def fetch_articles(self, max_articles: int = 50) -> List[Dict[str, Any]]:
        """从NewsAPI获取文章"""
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            logger.error("NEWS_API_KEY环境变量未设置")
            return []

        params = {
            "apiKey": api_key,
            "pageSize": min(max_articles, 100),
            "language": "en",
            "sortBy": "publishedAt"
        }

        # 地缘政治相关关键词
        keywords = self.config.get("keywords", [
            "geopolitics", "conflict", "war", "sanctions", "diplomacy",
            "international relations", "foreign policy", "military",
            "trade war", "sanctions", "treaty", "summit"
        ])

        articles = []

        # 尝试多种查询方式
        queries = [
            {"q": "geopolitics"},
            {"category": "politics"},
            {"sources": "reuters,bbc-news,cnn,al-jazeera-english"}
        ]

        async with aiohttp.ClientSession() as session:
            for query in queries:
                if len(articles) >= max_articles:
                    break

                query_params = params.copy()
                query_params.update(query)

                try:
                    url = f"{self.BASE_URL}/everything"
                    async with session.get(url, params=query_params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("status") == "ok":
                                for article in data.get("articles", []):
                                    if self._is_geopolitics_related(article):
                                        articles.append(article)
                                        if len(articles) >= max_articles:
                                            break
                        else:
                            logger.warning(f"NewsAPI请求失败: {response.status}")
                except Exception as e:
                    logger.error(f"NewsAPI请求错误: {str(e)}")

        return articles[:max_articles]

    def _is_geopolitics_related(self, article: Dict[str, Any]) -> bool:
        """判断文章是否与地缘政治相关"""
        title = article.get("title", "").lower()
        description = article.get("description", "").lower()
        content = article.get("content", "").lower()

        geopolitics_keywords = [
            "geopolitics", "conflict", "war", "sanctions", "diplomacy",
            "international", "foreign policy", "military", "nato",
            "united nations", "security council", "trade war",
            "embargo", "treaty", "summit", "alliance", "tension",
            "crisis", "protest", "revolution", "election", "government"
        ]

        text = f"{title} {description} {content}"
        return any(keyword in text for keyword in geopolitics_keywords)

    async def test_connection(self) -> bool:
        """测试NewsAPI连接"""
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/top-headlines"
                params = {"apiKey": api_key, "country": "us", "pageSize": 1}
                async with session.get(url, params=params) as response:
                    return response.status == 200
        except:
            return False


class RSSSource(NewsSource):
    """RSS源（使用feedparser解析）"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.feed_url = config.get("feed_url", "")

    async def fetch_articles(self, max_articles: int = 50) -> List[Dict[str, Any]]:
        """从RSS源获取文章"""
        if not self.feed_url:
            return []

        articles = []

        try:
            # 使用feedparser解析RSS
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, self.feed_url)

            if feed.bozo:  # 解析错误
                logger.warning(f"RSS解析错误: {feed.bozo_exception}")
                return []

            for entry in feed.entries[:max_articles]:
                article = {
                    "title": entry.get("title", ""),
                    "description": entry.get("description", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": self.name,
                    "feed_title": feed.feed.get("title", "")
                }

                # 尝试获取内容
                content = entry.get("content")
                if content:
                    if isinstance(content, list):
                        # 取第一个content元素的值
                        article["content"] = content[0].get("value", "")
                    else:
                        article["content"] = str(content)

                articles.append(article)

        except Exception as e:
            logger.error(f"RSS请求错误: {str(e)}")

        return articles

    async def test_connection(self) -> bool:
        """测试RSS连接"""
        if not self.feed_url:
            return False

        try:
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, self.feed_url)
            return not feed.bozo  # 没有解析错误表示连接成功
        except:
            return False


class OfficialNewsSource(NewsSource):
    """官方新闻机构源（如新华社、路透社等）"""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.base_url = config.get("base_url", "")
        self.api_key = os.getenv(f"{name.upper()}_API_KEY", "")

    async def fetch_articles(self, max_articles: int = 50) -> List[Dict[str, Any]]:
        """从官方新闻机构获取文章"""
        # 这里需要根据具体API实现
        # 暂时返回空列表，需要后续扩展
        logger.info(f"官方新闻源 {self.name} 需要具体API实现")
        return []

    async def test_connection(self) -> bool:
        """测试连接"""
        # 暂时返回True，需要具体实现
        return True


class NewsCollector(DataCollector):
    """权威地缘政治新闻收集器"""

    def __init__(self, config: CollectorConfig):
        super().__init__(config)
        self.sources: List[NewsSource] = []
        self._init_sources()

    def _init_sources(self):
        """初始化新闻源"""
        sources_config = self.config.params.get("sources", [])

        for source_config in sources_config:
            source_type = source_config.get("type")
            name = source_config.get("name")
            config = source_config.get("config", {})

            if source_type == "newsapi":
                source = NewsAPISource(name, config)
                self.sources.append(source)
            elif source_type == "rss":
                source = RSSSource(name, config)
                self.sources.append(source)
            elif source_type == "official":
                source = OfficialNewsSource(name, config)
                self.sources.append(source)
            else:
                logger.warning(f"未知的新闻源类型: {source_type}")

        logger.info(f"初始化了 {len(self.sources)} 个新闻源")

    async def collect(self) -> List[DataRecord]:
        """收集新闻数据"""
        all_articles = []

        # 并行从所有源获取数据
        tasks = []
        for source in self.sources:
            task = source.fetch_articles(max_articles=20)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        for source, result in zip(self.sources, results):
            if isinstance(result, Exception):
                logger.error(f"新闻源 {source.name} 收集失败: {str(result)}")
                continue

            articles = result
            logger.info(f"从 {source.name} 收集到 {len(articles)} 篇文章")

            for article in articles:
                # 创建唯一ID
                article_id = self._generate_article_id(article)

                record = DataRecord(
                    id=article_id,
                    source_type=DataSourceType.NEWS,
                    raw_data=article,
                    metadata={
                        "source": source.name,
                        "collector": self.name,
                        "collected_at": datetime.utcnow().isoformat(),
                        "article_title": article.get("title", ""),
                        "article_url": article.get("url") or article.get("link", ""),
                        "published_at": article.get("publishedAt") or article.get("pubDate", "")
                    }
                )
                all_articles.append(record)

        logger.info(f"总共收集到 {len(all_articles)} 篇新闻文章")
        return all_articles

    def _generate_article_id(self, article: Dict[str, Any]) -> str:
        """生成文章唯一ID"""
        # 使用标题、来源和发布时间生成哈希ID
        title = article.get("title", "")
        source = article.get("source", {}).get("name", "") if isinstance(article.get("source"), dict) else str(article.get("source", ""))
        # 尝试多个可能的发布时间字段
        published = (article.get("publishedAt") or article.get("pubDate") or
                    article.get("published") or article.get("date") or "")

        id_string = f"{title}|{source}|{published}"
        return hashlib.md5(id_string.encode()).hexdigest()

    def validate(self, record: DataRecord) -> bool:
        """验证新闻记录"""
        article = record.raw_data

        # 检查必要字段
        if not article:
            return False

        title = article.get("title", "")
        if not title or len(title.strip()) < 5:
            return False

        # 检查地缘政治相关性
        if not self._is_geopolitics_related(article):
            return False

        # 检查发布时间（不要太旧，比如超过30天）
        published_str = article.get("publishedAt") or article.get("pubDate") or article.get("published") or article.get("date")
        if published_str:
            try:
                # 尝试解析发布时间
                published = self._parse_date(published_str)
                if published:
                    # 如果文章超过30天，认为无效
                    if datetime.utcnow() - published > timedelta(days=30):
                        return False
            except:
                pass

        return True

    def _is_geopolitics_related(self, article: Dict[str, Any]) -> bool:
        """判断文章是否与地缘政治相关"""
        title = article.get("title", "").lower()
        description = article.get("description", "").lower()
        content = article.get("content", "").lower()

        geopolitics_keywords = [
            "geopolitics", "conflict", "war", "sanctions", "diplomacy",
            "international", "foreign policy", "military", "nato",
            "united nations", "security council", "trade war",
            "embargo", "treaty", "summit", "alliance", "tension",
            "crisis", "protest", "revolution", "election", "government",
            "china", "russia", "usa", "europe", "middle east", "asia",
            "africa", "latin america", "ukraine", "taiwan", "south china sea",
            "iran", "north korea", "syria", "yemen", "libya", "afghanistan"
        ]

        text = f"{title} {description} {content}"
        return any(keyword in text for keyword in geopolitics_keywords)

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串"""
        from dateutil import parser
        try:
            return parser.parse(date_str)
        except:
            return None

    async def _test_connection(self) -> bool:
        """测试所有新闻源的连接"""
        if not self.sources:
            return False

        tasks = [source.test_connection() for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 只要有一个源连接成功就返回True
        for result in results:
            if isinstance(result, bool) and result:
                return True

        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取收集器统计信息"""
        base_stats = super().get_stats()
        base_stats.update({
            "sources_count": len(self.sources),
            "sources": [source.name for source in self.sources]
        })
        return base_stats


# 默认新闻源配置
DEFAULT_NEWS_SOURCES = [
    {
        "type": "newsapi",
        "name": "newsapi",
        "config": {
            "keywords": [
                "geopolitics", "conflict", "war", "sanctions", "diplomacy",
                "international relations", "foreign policy", "military"
            ]
        }
    },
    {
        "type": "rss",
        "name": "reuters_world",
        "config": {
            "feed_url": "http://feeds.reuters.com/Reuters/worldNews"
        }
    },
    {
        "type": "rss",
        "name": "bbc_world",
        "config": {
            "feed_url": "http://feeds.bbci.co.uk/news/world/rss.xml"
        }
    },
    {
        "type": "rss",
        "name": "al_jazeera",
        "config": {
            "feed_url": "https://www.aljazeera.com/xml/rss/all.xml"
        }
    }
]