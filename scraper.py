import re
from urllib.parse import urlparse
from utils import get_logger, get_urlhash, normalize
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

def scraper(url, resp):

    # Check that the response status is ok and that the raw response has content
    if resp.status != 200 or resp.raw_response is None:
        return []

    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

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
    logger = get_logger("SCRAPER")
    
    links = []

    try:
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
        # logger.info(soup.prettify())  # Log the entire formatted html document
        # logger.info(f"{soup.a}")  # Log the a tags in the html document
        for anchor in soup.find_all('a', href=True):
            link = anchor.get('href')
            abs_link_url = urljoin(url, link)
            # logger.info(f"{abs_link_url}")
            links.append(abs_link_url)
    except Exception as e:
        logger.fatal(f"Error parsing {url}: {e}")

    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    allowed_domains = {"ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"}
    
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        current_time = time.time()

        # Politeness check
        # last_access= domain_list_access.get(domain)
        # if current_time - last_access_ <  POLITENESS: 


        # Rate Limiting check

        # Remove timestaps older than 1 minute

        # Enforce Rate limit

        # Duplicate URL check

        # Check if url scheme is valid
        if parsed_url.scheme not in set(["http", "https"]):
            return False
        
        # check host is in URL is in allowed domains
        if domain not in allowed_domains: 
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
        raise
