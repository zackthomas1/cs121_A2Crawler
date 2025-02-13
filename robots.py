import re
from utils.config import Config
from logging import Logger
from utils import get_logger
from utils.download import download
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET
from bs4 import BeautifulSoup

#
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
    
    # if parser for domain already exist and is cached, retrieve it
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

