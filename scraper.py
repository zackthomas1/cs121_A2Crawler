import re
import hashlib
from utils.config import Config
from logging import Logger
from bs4 import BeautifulSoup
from utils import get_logger, get_urlhash, normalize
from utils.download import download
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

scrap_logger = get_logger("SCRAPER")

# # Set to track domains that have been processed for sitemaps
# processed_domains = set()

# Tracks visited urls to avoid duplicates
visited_content_checksums = set()

# Dictionary to store parsed robots.txt files for different domains
robots_parsers = {}

def compute_content_checksum(content: str) -> str:
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def scraper(url, resp):

    # Check that the response status is ok and that the raw response has content
    if resp.status != 200 or resp.raw_response is None:
        scrap_logger.warning(f"Skipping URL {url}: Invalid response or status {resp.status}")
        return []

    # Check that the EXACT content of this page has not already been scrapped 
    content_checksum = compute_content_checksum(resp.raw_response.content)
    if content_checksum in visited_content_checksums:
        scrap_logger.warning(f"Skipping URL {url}: Exact Content Match")
        return []
    else:
        visited_content_checksums.add(content_checksum)

    links = extract_next_links(url, resp)
    
    # Filter out duplicate and invalid urls
    unique_links = set()
    for link in links:
        link_norm = normalize(link)

        if link_norm not in unique_links and is_valid(link_norm):
            unique_links.add(link_norm)
        else: 
            scrap_logger.info(f"Filtered out duplicate or invalid URL: {link}")

    return list(unique_links)

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content   
    links = []

    try:
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
        for anchor in soup.find_all('a', href=True):
            link = anchor.get('href')
            
            # convert relative url to absolute url
            abs_url = urljoin(url, link)
            
            # Defragment: remove anything after '#'
            parsed = urlparse(abs_url)
            defrag_url = parsed._replace(fragment="").geturl()

            #TODO: Consider stripping queries here

            links.append(defrag_url)
    except Exception as e:
        scrap_logger.fatal(f"Error parsing {url}: {e}")

    return links

def is_valid(url: str) -> bool:
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    
    allowed_domains = {"ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"}
    
    try:
        parsed_url = urlparse(url)

        # Check if url scheme is valid
        if parsed_url.scheme not in set(["http", "https"]):
            return False
        
        # check host is in URL is in allowed domains
        if parsed_url.netloc and not any(domain in parsed_url.netloc for domain in allowed_domains): 
            return False
        
        # Avoid query strings (potential duplicate content)
        if parsed_url.query:
            return False

        # Avoid infinite trap pattern
        MAX_DEPTH = 6
        path_segments = [segment for segment in parsed_url.path.split('/') if segment]
        if len(path_segments) > MAX_DEPTH:
            return False

        # Filter out calendar pages which are potentially low-information pages.
        if "calendar" in parsed_url.path.lower() or "calendar" in parsed_url.netloc.lower():
            return False

        # Check robot.txt rules to follow politeness 
        # and do not fetch from paths we are not allowed
        if not can_fetch(url):
            return False
       
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed_url.path.lower())

    except TypeError:
        print ("TypeError for ", parsed_url)
        return False

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
        scrap_logger.info(f"Loaded robots.txt for {robots_url}")
    except Exception as e:
        scrap_logger.warning(f"Failed to load robots.txt for {robots_url}")
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
        scrap_logger.info(f"Found sitemaps for {domain}: {sitemaps_urls}")
        return sitemaps_urls
    else:
        return []
    
def fetch_sitemap_urls(sitemap_url: str, config: Config, logger: Logger) -> list[str]: 
    urls = set()

    # use downloader
    scrap_logger.info(f"Downloading sitemap: {sitemap_url}")
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

def intialize_scrap_from_sitemap(url: str, config: Config, logger: Logger) -> list[str]:
    parsed_url = urlparse(url)
    sitemap_urls = get_sitemap_urls(parsed_url.netloc)

    links = []

    if sitemap_urls:
        for sitemap in sitemap_urls:
            sitemap_links = fetch_sitemap_urls(sitemap, config, logger)
            links.extend(sitemap_links)

    return links