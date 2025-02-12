import re
from utils.config import Config
from logging import Logger
from utils import get_logger
from utils.download import download
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup
import requests

robots_logger = get_logger("ROBOTS")

# Dictionary to store parsed robots.txt files for different domains
robots_parsers = {}

def is_xml_doc(url): 
    parsed_url = urlparse(url)
    return re.match(
            r".*\.(xml)$", parsed_url.path.lower())

def can_fetch(url: str, user_agent: str = "*") -> bool:
    """
    Checks if URL can be crawled based on robots.txt rules
    """ 
    # parsed_url = urlparse(url)
    parser = get_robots_parser(url)

    # if get_robots_parser is unable to read a robots.txt file for 
    # domain, then it will return None. In this case it is assumed that there
    # are no restriction and the crawler can fetch any page in domain.
    if parser:
        return parser.can_fetch(user_agent, url)  
    else: 
        return True

def get_robots_parser(url: str) -> RobotFileParser:
    """
    Returns and caches a 'RobotFileParser' for a given URL, NONE if doesn't exist
    """
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme
    domain = parsed_url.netloc
    
    # Return cached parser if exists    
    if domain in robots_parsers:
        return robots_parsers[domain] # return cached parser

    robots_url = f"{scheme}://{domain}/robots.txt"
    parser = RobotFileParser()

    try:
        parser.set_url(robots_url)
        parser.read()
        robots_logger.info(f"Loaded robots.txt for {robots_url}")
    except Exception as e:
        robots_logger.warning(f"Failed to load robots.txt for {robots_url}")
        parser = None

    robots_parsers[domain] = parser # Cache parser
    return parser

def get_sitemap_urls(url: str) -> list[str]: 
    """
    Extracts urls of sitemaps from robots.txt
    """

    parser = get_robots_parser(url)

    # If no parser returned, no robots.txt exists
    if not parser:
        return []

    # Parses the sitemap parameter in 'robots' files and return the sitemap urls
    sitemaps_urls = parser.site_maps()

    # is the sitemaps list empty?
    if sitemaps_urls: 
        robots_logger.info(f"Found sitemaps for {url}: {sitemaps_urls}")
        return sitemaps_urls
    else:
        return []

def fetch_sitemap_urls(sitemap_url: str, config: Config, logger: Logger) -> list[str]: 
    logger.info(f"Downloading sitemap: {sitemap_url}")
    resp = download(sitemap_url, config, logger)

    # If sitemap is invalid, return empty list
    if resp.status != 200 or not resp.raw_response:
        logger.warning(f"Failed to download sitemap: {sitemap_url}, status: {resp.status}")
        return []

    try: 
        tree = ET.fromstring(resp.raw_response.content)
        urls = set()
        # Iterate over <loc> tags in xml
        for url_element in tree.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            url = url_element.text.strip()
            
            # If it's a nested XML file within the sitemap, process it. Otherwise, add to urls
            if url:
                if is_xml_doc(url):
                    urls.update(get_sitemap_urls(url, config, logger))
                else:
                    urls.add(url)

        logger.info(f"Extracted {len(urls)} URLs from {sitemap_url}")
        return list(urls)

    except ParseError as e:
        logger.error(f"XML parsing error for sitemap {sitemap_url}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error parsing sitemap {sitemap_url}: {e}")

    return []

def fetch_sitemap_urls(sitemap_url: str, config: Config, logger: Logger) -> list[str]:
    # Use requests to download url
    logger.info(f"Downloading sitemap: {sitemap_url}")
    response = 




def seed_frontier_from_sitemap(url: str, config: Config, logger: Logger) -> list[str]:
    sitemap_urls = get_sitemap_urls(url)

    links = []
    if sitemap_urls:
        for sitemap in sitemap_urls:
            sitemap_links = fetch_sitemap_urls(sitemap, config, logger)
            links.extend(sitemap_links)

    return links