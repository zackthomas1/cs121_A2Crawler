from utils.config import Config
from logging import Logger
from utils import get_logger
from utils.download import download
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

robots_logger = get_logger("ROBOTS")

# Dictionary to store parsed robots.txt files for different domains
robots_parsers = {}

def can_fetch(url: str, user_agent: str = "*") -> bool:
    """
    Checks if URL can be crawled based on robots.txt rules
    """ 
    parsed_url = urlparse(url)
    parser = get_robots_parser(parsed_url)

    # if get_robots_parser is unable to read a robots.txt file for 
    # domain, then it will return None. In this case it is assumed that there
    # are no restriction and the crawler can fetch any page in domain.
    if parser:
        return parser.can_fetch(user_agent, url)  
    else: 
        return True

def get_robots_parser(parsed_url: str) -> RobotFileParser:
    """
    """
    scheme = parsed_url.scheme
    domain = parsed_url.netloc
    
    # Check for cached parser
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

def get_sitemap_urls(domain: str) -> list[str]: 
    """
    Extracts sitemap url from robots.txt
    """

    parser = get_robots_parser(domain)
    sitemaps_urls = parser.site_maps()

    # is the sitemaps list empty?
    if sitemaps_urls: 
        robots_logger.info(f"Found sitemaps for {domain}: {sitemaps_urls}")
        return sitemaps_urls
    else:
        return []
    
def fetch_sitemap_urls(sitemap_url: str, config: Config, logger: Logger) -> list[str]: 
    urls = set()

    # use downloader
    logger.info(f"Downloading sitemap: {sitemap_url}")
    resp = download(sitemap_url, config, logger)

    # invalid response return empty list
    if resp. status != 200 or not resp.raw_response:
        return []
    
    try: 
        tree = ET.fromstring(resp.raw_response.content)

        # Iterate over <loc> tags in xml
        for url_element in tree.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            url = url_element.text.strip()
            if url:
                urls.add(url)
        logger.info(f"Extracted {len(urls)} urls from {sitemap_url}")
    except Exception as e:
        logger.error(f"Error parsing sitemap {sitemap_url}: {e}")

    return list(urls)

def seed_frontier_from_sitemap(url: str, config: Config, logger: Logger) -> list[str]:
    parsed_url = urlparse(url)
    sitemap_urls = get_sitemap_urls(parsed_url.netloc)

    links = []

    if sitemap_urls:
        for sitemap in sitemap_urls:
            sitemap_links = fetch_sitemap_urls(sitemap, config, logger)
            links.extend(sitemap_links)

    return links