import re
from utils import get_logger, get_urlhash, normalize
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

scrap_logger = get_logger("SCRAPER")

# Tracks visited urls to avoid duplicates
visited_urls = set()

# Dictionary to store parsed robots.txt files for different domains
robots_parsers = {}

def scraper(url, resp):

    # Check that the response status is ok and that the raw response has content
    if resp.status != 200 or resp.raw_response is None:
        scrap_logger.warning(f"Skipping URL {url}: Invalid response or status {resp.status}")
        return []

    links = extract_next_links(url, resp)
    
    # Filter out duplicate and invalid urls
    unique_links = []
    for link in links:
        normalized_link = normalize_link(link)

        if normalized_link and normalized_link not in visited_urls and is_valid(normalized_link):
            visited_urls.add(normalized_link)    # Mark visited
            unique_links.append(link)
        else: 
            scrap_logger.info(f"Filtered out duplicate or invalid URL: {link}")

    return unique_links

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

def is_valid(url):
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

def normalize_link(url): 
    """
    Ensures standardized URL format.
    Removes fragments and unnesessary parameters.
    """

    try:
        parsed_url = urlparse(url)
        clean_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        return clean_url
    except Exception as e:
        return None

def can_fetch(url, user_agent="*"):
    """
    Checks if URL can be crawled based on robots.txt rules
    """ 
    parsed_url = urlparse(url)
    parser = get_robots_parser(parsed_url)

    # if get_robots_parser is unable to read a robots.txt file for 
    # domain, then it will return None. In this case it is assumed that there
    # are no restriction and the crawler can fetch any page in domain.
    return parser.can_fetch(user_agent, url)

def get_sitemap_urls(domain)

def get_robots_parser(parsed_url):
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

    robots_parsers[domain] = parser # Cache parser
    return parser

def get_sitemap_urls(domain):
    """
    Extract sitemap URL from robot.txt file 
    """

    parser = get_robots_parser(domain)
    sitemap_urls = parser.site_maps()
    if sitemap_urls: 
        return sitemap_urls
    else:
        return []