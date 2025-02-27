"""
@file: news_ingestion.py
@description:
Service for ingesting unstructured data from various sports news sources
such as ESPN, NBA.com, Twitter, and more. This module handles fetching,
parsing, and preprocessing news articles, injury reports, and other
unstructured data that can be used to enhance prediction models.

@dependencies:
- httpx: For HTTP requests
- beautifulsoup4: For HTML parsing and web scraping
- feedparser: For RSS feed parsing
- tenacity: For retry mechanisms
- app.core.logger: For structured logging
- html2text: For converting HTML to plain text

@notes:
- Uses caching to avoid duplicate processing of the same articles
- Implements rate limiting to respect website terms of service
- Provides text preprocessing for LLM consumption
- Handles various news sources in a unified way
- Error handling is comprehensive with fallback mechanisms
"""

import httpx
import feedparser
import re
import time
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import html2text
from urllib.parse import urlparse

from app.core.logger import setup_logger

# Create a component-specific logger
logger = setup_logger("app.services.news_ingestion")

# Constants
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
DEFAULT_REQUEST_TIMEOUT = 30  # seconds
CACHE_TTL = 3600  # Cache time to live in seconds (1 hour)

# NBA News Sources
ESPN_NBA_RSS = "https://www.espn.com/espn/rss/nba/news"
NBA_COM_NEWS_URL = "https://www.nba.com/news"
BLEACHER_REPORT_NBA_RSS = "https://bleacherreport.com/articles/feed?tag_id=19"

# In-memory cache for articles to avoid duplicate processing
# Format: {url: (timestamp, content)}
article_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

# Track already seen article URLs to avoid duplicates
seen_urls: Set[str] = set()


class NewsIngestionError(Exception):
    """Custom exception for news ingestion errors"""
    pass


async def fetch_url(url: str, headers: Optional[Dict[str, str]] = None) -> str:
    """
    Fetch content from a URL with proper error handling.
    
    Args:
        url: The URL to fetch
        headers: Optional HTTP headers
        
    Returns:
        String containing the response text
        
    Raises:
        NewsIngestionError: If the request fails
    """
    if not headers:
        headers = {"User-Agent": USER_AGENT}
        
    try:
        logger.debug(f"Fetching URL: {url}")
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, timeout=DEFAULT_REQUEST_TIMEOUT)
            response.raise_for_status()
            logger.debug(f"Successfully fetched URL: {url}")
            return response.text
    except httpx.RequestError as e:
        logger.error(f"Request error for URL {url}: {str(e)}")
        raise NewsIngestionError(f"Failed to fetch URL {url}: {str(e)}")
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} for URL {url}: {e.response.text}")
        raise NewsIngestionError(f"HTTP error {e.response.status_code} for URL {url}")
    except Exception as e:
        logger.error(f"Unexpected error fetching URL {url}: {str(e)}")
        raise NewsIngestionError(f"Unexpected error fetching URL {url}: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(NewsIngestionError)
)
async def fetch_espn_nba_news() -> List[Dict[str, Any]]:
    """
    Fetch NBA news articles from ESPN's RSS feed.
    
    Returns:
        List of dictionaries containing article data with the following keys:
        - title: Article title
        - url: Article URL
        - published_date: Publication date
        - source: Source name (ESPN)
        - content: Article content text (preprocessed)
        - summary: Short summary of the article
        
    Raises:
        NewsIngestionError: If fetching or parsing fails
    """
    try:
        logger.info("Fetching NBA news from ESPN RSS feed")
        # Parse the RSS feed
        feed = feedparser.parse(ESPN_NBA_RSS)
        
        articles = []
        for entry in feed.entries:
            url = entry.link
            
            # Skip if we've already processed this URL
            if url in seen_urls:
                logger.debug(f"Skipping already processed URL: {url}")
                continue
                
            # Check cache
            current_time = time.time()
            if url in article_cache:
                cache_time, article_data = article_cache[url]
                if current_time - cache_time < CACHE_TTL:
                    logger.debug(f"Using cached data for URL: {url}")
                    articles.append(article_data)
                    continue
            
            # Fetch the full article content
            try:
                logger.debug(f"Fetching full article content from ESPN: {url}")
                html_content = await fetch_url(url)
                
                # Parse HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find and extract article content
                article_body = soup.find('div', class_='article-body')
                if not article_body:
                    # Fallback to other potential content containers
                    article_body = soup.find('div', class_='story-container')
                
                if article_body:
                    # Convert HTML to plain text
                    converter = html2text.HTML2Text()
                    converter.ignore_links = False
                    converter.ignore_images = True
                    converter.ignore_tables = True
                    content_text = converter.handle(str(article_body))
                    
                    # Clean up the text
                    content_text = re.sub(r'\n{3,}', '\n\n', content_text)
                    content_text = re.sub(r'\s+', ' ', content_text)
                    content_text = content_text.strip()
                else:
                    logger.warning(f"Could not find article body for URL: {url}")
                    content_text = entry.summary if hasattr(entry, 'summary') else ""
                
                # Create article data
                published_date = datetime(*entry.published_parsed[:6]).isoformat() if hasattr(entry, 'published_parsed') else None
                
                article_data = {
                    'title': entry.title,
                    'url': url,
                    'published_date': published_date,
                    'source': 'ESPN',
                    'content': content_text,
                    'summary': entry.summary if hasattr(entry, 'summary') else ""
                }
                
                # Cache the article data
                article_cache[url] = (current_time, article_data)
                seen_urls.add(url)
                
                articles.append(article_data)
                logger.debug(f"Successfully processed article: {entry.title}")
                
                # Be nice to the server - add small delay between requests
                await asyncio.sleep(0.5)
                
            except NewsIngestionError as e:
                logger.warning(f"Skipping article {url} due to error: {str(e)}")
                continue
        
        logger.info(f"Successfully fetched {len(articles)} NBA news articles from ESPN")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to fetch ESPN NBA news: {str(e)}")
        raise NewsIngestionError(f"Failed to fetch ESPN NBA news: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(NewsIngestionError)
)
async def fetch_nba_com_news() -> List[Dict[str, Any]]:
    """
    Fetch news articles from NBA.com.
    
    Returns:
        List of dictionaries containing article data with the following keys:
        - title: Article title
        - url: Article URL
        - published_date: Publication date (if available)
        - source: Source name (NBA.com)
        - content: Article content text (preprocessed)
        - summary: Short summary or excerpt of the article
        
    Raises:
        NewsIngestionError: If fetching or parsing fails
    """
    try:
        logger.info("Fetching news from NBA.com")
        html_content = await fetch_url(NBA_COM_NEWS_URL)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        articles = []
        
        # Find article containers
        article_elements = soup.select('article.ArticleCard') or soup.select('.article-card')
        logger.debug(f"Found {len(article_elements)} article elements on NBA.com")
        
        for article_elem in article_elements:
            # Extract article details
            title_elem = article_elem.select_one('.title, .headline, h2, h3')
            title = title_elem.text.strip() if title_elem else "Untitled"
            
            link_elem = article_elem.select_one('a')
            if not link_elem or not link_elem.get('href'):
                logger.debug(f"Skipping article with no link: {title}")
                continue
                
            href = link_elem['href']
            
            # Make sure we have an absolute URL
            if href.startswith('/'):
                url = f"https://www.nba.com{href}"
            else:
                url = href
                
            # Skip if we've already processed this URL
            if url in seen_urls:
                logger.debug(f"Skipping already processed URL: {url}")
                continue
                
            # Check cache
            current_time = time.time()
            if url in article_cache:
                cache_time, article_data = article_cache[url]
                if current_time - cache_time < CACHE_TTL:
                    logger.debug(f"Using cached data for URL: {url}")
                    articles.append(article_data)
                    continue
            
            # Fetch the full article content
            try:
                logger.debug(f"Fetching full article content from NBA.com: {url}")
                article_html = await fetch_url(url)
                article_soup = BeautifulSoup(article_html, 'html.parser')
                
                # Try to find publication date
                date_elem = article_soup.select_one('.Article-articleDate, .date, time')
                published_date = None
                if date_elem:
                    date_text = date_elem.text.strip()
                    try:
                        # Attempt to parse the date (format may vary)
                        for fmt in ['%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d']:
                            try:
                                published_date = datetime.strptime(date_text, fmt).isoformat()
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.warning(f"Failed to parse date '{date_text}': {str(e)}")
                        published_date = None
                
                # Extract article content
                content_elem = article_soup.select_one('.Article-content, .article-content, .story-content')
                
                if content_elem:
                    # Convert HTML to plain text
                    converter = html2text.HTML2Text()
                    converter.ignore_links = False
                    converter.ignore_images = True
                    converter.ignore_tables = True
                    content_text = converter.handle(str(content_elem))
                    
                    # Clean up the text
                    content_text = re.sub(r'\n{3,}', '\n\n', content_text)
                    content_text = re.sub(r'\s+', ' ', content_text)
                    content_text = content_text.strip()
                else:
                    logger.warning(f"Could not find article content for URL: {url}")
                    content_text = ""
                
                # Try to extract summary
                summary_elem = article_soup.select_one('.Article-summary, .summary, .excerpt')
                summary = summary_elem.text.strip() if summary_elem else ""
                
                article_data = {
                    'title': title,
                    'url': url,
                    'published_date': published_date,
                    'source': 'NBA.com',
                    'content': content_text,
                    'summary': summary
                }
                
                # Cache the article data
                article_cache[url] = (current_time, article_data)
                seen_urls.add(url)
                
                articles.append(article_data)
                logger.debug(f"Successfully processed article: {title}")
                
                # Be nice to the server - add small delay between requests
                await asyncio.sleep(0.5)
                
            except NewsIngestionError as e:
                logger.warning(f"Skipping article {url} due to error: {str(e)}")
                continue
                
        logger.info(f"Successfully fetched {len(articles)} news articles from NBA.com")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to fetch NBA.com news: {str(e)}")
        raise NewsIngestionError(f"Failed to fetch NBA.com news: {str(e)}")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(NewsIngestionError)
)
async def fetch_bleacher_report_nba_news() -> List[Dict[str, Any]]:
    """
    Fetch NBA news articles from Bleacher Report's RSS feed.
    
    Returns:
        List of dictionaries containing article data with the following keys:
        - title: Article title
        - url: Article URL
        - published_date: Publication date
        - source: Source name (Bleacher Report)
        - content: Article content text (preprocessed)
        - summary: Short summary of the article
        
    Raises:
        NewsIngestionError: If fetching or parsing fails
    """
    try:
        logger.info("Fetching NBA news from Bleacher Report RSS feed")
        # Parse the RSS feed
        feed = feedparser.parse(BLEACHER_REPORT_NBA_RSS)
        
        articles = []
        for entry in feed.entries:
            url = entry.link
            
            # Skip if we've already processed this URL
            if url in seen_urls:
                logger.debug(f"Skipping already processed URL: {url}")
                continue
                
            # Check cache
            current_time = time.time()
            if url in article_cache:
                cache_time, article_data = article_cache[url]
                if current_time - cache_time < CACHE_TTL:
                    logger.debug(f"Using cached data for URL: {url}")
                    articles.append(article_data)
                    continue
            
            # Fetch the full article content
            try:
                logger.debug(f"Fetching full article content from Bleacher Report: {url}")
                html_content = await fetch_url(url)
                
                # Parse HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find and extract article content
                article_body = soup.find('div', class_='articleContent')
                if not article_body:
                    # Fallback to other potential content containers
                    article_body = soup.find('div', class_='entry-content')
                
                if article_body:
                    # Convert HTML to plain text
                    converter = html2text.HTML2Text()
                    converter.ignore_links = False
                    converter.ignore_images = True
                    converter.ignore_tables = True
                    content_text = converter.handle(str(article_body))
                    
                    # Clean up the text
                    content_text = re.sub(r'\n{3,}', '\n\n', content_text)
                    content_text = re.sub(r'\s+', ' ', content_text)
                    content_text = content_text.strip()
                else:
                    logger.warning(f"Could not find article body for URL: {url}")
                    content_text = entry.summary if hasattr(entry, 'summary') else ""
                
                # Create article data
                published_date = datetime(*entry.published_parsed[:6]).isoformat() if hasattr(entry, 'published_parsed') else None
                
                article_data = {
                    'title': entry.title,
                    'url': url,
                    'published_date': published_date,
                    'source': 'Bleacher Report',
                    'content': content_text,
                    'summary': entry.summary if hasattr(entry, 'summary') else ""
                }
                
                # Cache the article data
                article_cache[url] = (current_time, article_data)
                seen_urls.add(url)
                
                articles.append(article_data)
                logger.debug(f"Successfully processed article: {entry.title}")
                
                # Be nice to the server - add small delay between requests
                await asyncio.sleep(0.5)
                
            except NewsIngestionError as e:
                logger.warning(f"Skipping article {url} due to error: {str(e)}")
                continue
        
        logger.info(f"Successfully fetched {len(articles)} NBA news articles from Bleacher Report")
        return articles
        
    except Exception as e:
        logger.error(f"Failed to fetch Bleacher Report NBA news: {str(e)}")
        raise NewsIngestionError(f"Failed to fetch Bleacher Report NBA news: {str(e)}")


async def fetch_injury_reports() -> List[Dict[str, Any]]:
    """
    Fetch NBA injury reports from reliable sources.
    
    Returns:
        List of dictionaries containing injury report data with the following keys:
        - team: Team name
        - player: Player name
        - injury: Injury description
        - status: Player status (Out, Questionable, etc.)
        - source: Source of the information
        - updated_date: Date when the information was updated
        
    Raises:
        NewsIngestionError: If fetching or parsing fails
    """
    try:
        logger.info("Fetching NBA injury reports")
        # ESPN has a dedicated NBA injuries page
        url = "https://www.espn.com/nba/injuries"
        html_content = await fetch_url(url)
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        injury_reports = []
        
        # Process each team's injury report
        team_sections = soup.select('.Card')
        logger.debug(f"Found {len(team_sections)} team sections in injury report")
        
        for section in team_sections:
            team_header = section.select_one('.CardHeader')
            if not team_header:
                logger.debug("Skipping section with no team header")
                continue
                
            team_name = team_header.text.strip()
            logger.debug(f"Processing injury report for team: {team_name}")
            
            # Process player injuries
            player_rows = section.select('tr.Table__TR')
            for row in player_rows:
                cells = row.select('td.Table__TD')
                if len(cells) < 3:
                    continue
                    
                player_name = cells[0].text.strip()
                position = cells[1].text.strip() if len(cells) > 1 else ""
                injury_status = cells[2].text.strip() if len(cells) > 2 else ""
                
                # Some sources have additional details or expected return date
                additional_info = cells[3].text.strip() if len(cells) > 3 else ""
                
                injury_data = {
                    'team': team_name,
                    'player': player_name,
                    'position': position,
                    'injury': injury_status,
                    'status': additional_info,
                    'source': 'ESPN',
                    'updated_date': datetime.now().isoformat()
                }
                
                logger.debug(f"Recorded injury for {player_name}: {injury_status}")
                injury_reports.append(injury_data)
        
        logger.info(f"Successfully fetched {len(injury_reports)} NBA injury reports")
        return injury_reports
        
    except Exception as e:
        logger.error(f"Failed to fetch injury reports: {str(e)}")
        raise NewsIngestionError(f"Failed to fetch injury reports: {str(e)}")


def preprocess_text_for_llm(text: str) -> str:
    """
    Preprocess text to make it more suitable for LLM consumption.
    
    This function:
    - Removes excessive whitespace and newlines
    - Removes special characters and HTML artifacts
    - Normalizes quotation marks and apostrophes
    - Truncates text if too long
    
    Args:
        text: Raw text to preprocess
        
    Returns:
        Preprocessed text ready for LLM input
    """
    if not text:
        return ""
    
    logger.debug("Preprocessing text for LLM input")
    
    # Remove HTML artifacts
    text = re.sub(r'&[a-zA-Z]+;', ' ', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize quotation marks and apostrophes
    text = text.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
    
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    
    # Remove Twitter handles
    text = re.sub(r'@\w+', '', text)
    
    # Remove hashtags
    text = re.sub(r'#\w+', '', text)
    
    # Clean up paragraph breaks
    text = re.sub(r'\n{2,}', '\n\n', text)
    
    # Truncate if too long (100,000 characters is a reasonable limit for most LLMs)
    original_length = len(text)
    if original_length > 100000:
        logger.warning(f"Truncating text from {original_length} to 100,000 characters")
        text = text[:100000] + "..."
    
    logger.debug(f"Text preprocessing complete. Original length: {original_length}, New length: {len(text)}")
    return text.strip()


def extract_entities_from_text(text: str) -> Dict[str, List[str]]:
    """
    Extract relevant basketball entities from text such as team names, 
    player names, coaches, etc. This is a simplified version that uses
    regex patterns to identify potential entities.
    
    A more sophisticated approach would use NER models.
    
    Args:
        text: The text to extract entities from
        
    Returns:
        Dictionary with entity types as keys and lists of extracted entities as values
    """
    logger.debug("Extracting entities from text")
    
    # Common NBA team names and abbreviations
    team_patterns = [
        r'\b(?:Atlanta|Hawks)\b',
        r'\b(?:Boston|Celtics)\b',
        r'\b(?:Brooklyn|Nets)\b',
        r'\b(?:Charlotte|Hornets)\b',
        r'\b(?:Chicago|Bulls)\b',
        r'\b(?:Cleveland|Cavaliers|Cavs)\b',
        r'\b(?:Dallas|Mavericks|Mavs)\b',
        r'\b(?:Denver|Nuggets)\b',
        r'\b(?:Detroit|Pistons)\b',
        r'\b(?:Golden State|Warriors)\b',
        r'\b(?:Houston|Rockets)\b',
        r'\b(?:Indiana|Pacers)\b',
        r'\b(?:Los Angeles|LA|Clippers)\b',
        r'\b(?:Los Angeles|LA|Lakers)\b',
        r'\b(?:Memphis|Grizzlies)\b',
        r'\b(?:Miami|Heat)\b',
        r'\b(?:Milwaukee|Bucks)\b',
        r'\b(?:Minnesota|Timberwolves|Wolves)\b',
        r'\b(?:New Orleans|Pelicans)\b',
        r'\b(?:New York|Knicks)\b',
        r'\b(?:Oklahoma City|Thunder)\b',
        r'\b(?:Orlando|Magic)\b',
        r'\b(?:Philadelphia|76ers|Sixers)\b',
        r'\b(?:Phoenix|Suns)\b',
        r'\b(?:Portland|Trail Blazers|Blazers)\b',
        r'\b(?:Sacramento|Kings)\b',
        r'\b(?:San Antonio|Spurs)\b',
        r'\b(?:Toronto|Raptors)\b',
        r'\b(?:Utah|Jazz)\b',
        r'\b(?:Washington|Wizards)\b'
    ]
    
    # Patterns for basketball terms
    basketball_terms = [
        r'\b(?:points|rebounds|assists|steals|blocks|turnovers)\b',
        r'\bPPG\b',
        r'\bRPG\b',
        r'\bAPG\b',
        r'\bSPG\b',
        r'\bBPG\b',
        r'\b(?:double-double|triple-double)\b',
        r'\b(?:MVP|All-Star|All-NBA|Rookie of the Year|Defensive Player of the Year|DPOY|Most Improved|Sixth Man)\b'
    ]
    
    # Extract teams
    teams = set()
    for pattern in team_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        teams.update(matches)
    
    # Extract basketball terms
    terms = set()
    for pattern in basketball_terms:
        matches = re.findall(pattern, text, re.IGNORECASE)
        terms.update(matches)
    
    # Simple pattern for detecting potential player names (not comprehensive)
    # This assumes players are mentioned with first and last name
    player_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
    potential_players = set(re.findall(player_pattern, text))
    
    # Filter out obvious non-players (could be improved with a proper NER model)
    non_player_words = {"The NBA", "Los Angeles", "New York", "San Antonio", "Golden State", "Oklahoma City"}
    players = {name for name in potential_players if name not in non_player_words}
    
    logger.debug(f"Extracted {len(teams)} teams, {len(players)} players, and {len(terms)} basketball terms")
    
    return {
        "teams": list(teams),
        "players": list(players),
        "basketball_terms": list(terms)
    }


async def fetch_all_news_sources() -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch news from all available sources and categorize them.
    
    Returns:
        Dictionary with the following structure:
        {
            "articles": [...],  # General news articles
            "injury_reports": [...],  # Injury reports
        }
    """
    try:
        logger.info("Fetching news from all sources")
        # Import asyncio here to prevent circular imports
        import asyncio
        
        # Fetch data from multiple sources concurrently
        tasks = [
            fetch_espn_nba_news(),
            fetch_nba_com_news(),
            fetch_bleacher_report_nba_news(),
            fetch_injury_reports()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle any exceptions
        articles = []
        injury_reports = []
        
        # ESPN NBA News
        if isinstance(results[0], list):
            articles.extend(results[0])
            logger.debug(f"Added {len(results[0])} articles from ESPN")
        else:
            logger.error(f"Failed to fetch ESPN NBA news: {results[0]}")
        
        # NBA.com News
        if isinstance(results[1], list):
            articles.extend(results[1])
            logger.debug(f"Added {len(results[1])} articles from NBA.com")
        else:
            logger.error(f"Failed to fetch NBA.com news: {results[1]}")
        
        # Bleacher Report NBA News
        if isinstance(results[2], list):
            articles.extend(results[2])
            logger.debug(f"Added {len(results[2])} articles from Bleacher Report")
        else:
            logger.error(f"Failed to fetch Bleacher Report NBA news: {results[2]}")
        
        # Injury Reports
        if isinstance(results[3], list):
            injury_reports.extend(results[3])
            logger.debug(f"Added {len(results[3])} injury reports")
        else:
            logger.error(f"Failed to fetch injury reports: {results[3]}")
        
        # Sort articles by publication date (most recent first)
        articles.sort(
            key=lambda x: datetime.fromisoformat(x['published_date']) if x.get('published_date') else datetime.min,
            reverse=True
        )
        
        # Preprocess text for LLM consumption
        for article in articles:
            article['content'] = preprocess_text_for_llm(article['content'])
            article['summary'] = preprocess_text_for_llm(article['summary'])
            article['entities'] = extract_entities_from_text(article['content'])
        
        logger.info(f"Successfully fetched {len(articles)} articles and {len(injury_reports)} injury reports")
        
        return {
            "articles": articles,
            "injury_reports": injury_reports
        }
    
    except Exception as e:
        logger.error(f"Error in fetch_all_news_sources: {str(e)}")
        # Return partial results if available
        return {
            "articles": articles if 'articles' in locals() else [],
            "injury_reports": injury_reports if 'injury_reports' in locals() else []
        }


async def get_recent_news_for_team(team_name: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get recent news specifically about a given team.
    
    Args:
        team_name: The name of the team to fetch news for
        days: Number of days to look back for news
        
    Returns:
        List of articles about the specified team
    """
    try:
        logger.info(f"Getting recent news for team: {team_name} (last {days} days)")
        # Get all news
        all_news = await fetch_all_news_sources()
        articles = all_news["articles"]
        
        # Filter articles by team relevance
        team_articles = []
        for article in articles:
            # Check if team name is mentioned in title, content, or extracted entities
            title_match = team_name.lower() in article['title'].lower()
            content_match = team_name.lower() in article['content'].lower()
            entity_match = any(team_name.lower() in team.lower() for team in article.get('entities', {}).get('teams', []))
            
            if title_match or content_match or entity_match:
                team_articles.append(article)
        
        logger.debug(f"Found {len(team_articles)} articles mentioning {team_name}")
        
        # Filter by date if publication_date is available
        current_date = datetime.now()
        cutoff_date = current_date - timedelta(days=days)
        
        recent_team_articles = []
        for article in team_articles:
            if article.get('published_date'):
                try:
                    pub_date = datetime.fromisoformat(article['published_date'])
                    if pub_date >= cutoff_date:
                        recent_team_articles.append(article)
                        logger.debug(f"Including article from {pub_date.strftime('%Y-%m-%d')}: {article['title']}")
                    else:
                        logger.debug(f"Skipping older article from {pub_date.strftime('%Y-%m-%d')}: {article['title']}")
                except (ValueError, TypeError) as e:
                    # If date parsing fails, include the article anyway
                    logger.warning(f"Date parsing error for {article['title']}: {str(e)}")
                    recent_team_articles.append(article)
            else:
                # If no date available, include the article
                logger.debug(f"Including article with no date: {article['title']}")
                recent_team_articles.append(article)
        
        logger.info(f"Found {len(recent_team_articles)} recent articles about {team_name}")
        return recent_team_articles
        
    except Exception as e:
        logger.error(f"Error getting news for team {team_name}: {str(e)}")
        return []


async def get_team_injury_report(team_name: str) -> List[Dict[str, Any]]:
    """
    Get the latest injury report for a specific team.
    
    Args:
        team_name: The name of the team to fetch injury report for
        
    Returns:
        List of injury reports for the specified team
    """
    try:
        logger.info(f"Getting injury report for team: {team_name}")
        # Get all injury reports
        all_news = await fetch_all_news_sources()
        injury_reports = all_news["injury_reports"]
        
        # Filter by team name
        team_injuries = [
            report for report in injury_reports
            if team_name.lower() in report['team'].lower()
        ]
        
        logger.info(f"Found {len(team_injuries)} injury reports for {team_name}")
        return team_injuries
        
    except Exception as e:
        logger.error(f"Error getting injury report for team {team_name}: {str(e)}")
        return []