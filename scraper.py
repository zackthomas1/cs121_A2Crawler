import re
from simhash import compute_simhash, distance, compute_hash_value
import robots
from bs4 import BeautifulSoup
from utils import get_logger, normalize
from urllib.parse import urljoin, urlparse

scrap_logger = get_logger("SCRAPER")

# # Set to track domains that have been processed for sitemaps
# processed_domains = set()

# Tracks visited urls to avoid duplicates
# visited_content_checksums = set()
visited_content_simhashes = set()

def scraper(url, resp):

    # Check that the response status is ok and that the raw response has content
    if resp.status != 200 or resp.raw_response is None:
        if resp.status >= 300 and resp.status < 400:  # HTTP 3xx Redirection
            redirect_url = resp.raw_response.headers.get("Location")

            scrap_logger.warning(f"Status {resp.status}: Redirecting {url} -> {redirect_url}")
            return  [redirect_url] if is_valid(redirect_url) else []
        else:
            scrap_logger.warning(f"Skipping URL {url}: Invalid response or status {resp.status}")
            return []

    # # Check for EXACT content duplicate (checksum) 
    # content_checksum = compute_hash_value(resp.raw_response.content)
    # if content_checksum in visited_content_checksums:
    #     scrap_logger.warning(f"Skipping URL {url}: Exact Content Match")
    #     return []
    # visited_content_checksums.add(content_checksum)

    # Check for EXACT/NEAR duplicate content using Simhash
    try:
        # Get the text from the html response
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
        text = soup.get_text(separator= " ", strip=True)
        
        THREASHOLD = 6
        current_page_hash = compute_simhash(text)
        for visited_page_hash in visited_content_simhashes:
            dist = distance(current_page_hash, visited_page_hash)
            if dist < THREASHOLD:
                scrap_logger.warning(f"Skipping URL {url}: Near Duplicate Content Match")
                return []
        visited_content_simhashes.add(current_page_hash)
    except Exception as e:
        scrap_logger.fatal(f"Error parsing {url}: {e}")
    
    links = extract_next_links(url, resp)
    
    # Filter out duplicate and invalid urls
    unique_links = set()
    for link in links:
        if link and link not in unique_links and is_valid(link):
            unique_links.add(link)
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
            parsed = urlparse(abs_url)

            # Strip queries and defragment (remove anything after '#')
            clean_url = normalize(parsed._replace(query="", fragment="").geturl())

            links.append(clean_url)
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
        
        # Check for unique identifier segment in path 
        # If segment is alphanumeric and beyond a cut off length 
        # it is highly likely to be an ID and should be ignored. 
        MAX_SEGMENT_LENGTH = 20
        for segment in path_segments: 
            if segment.isalnum() and len(segment) > MAX_SEGMENT_LENGTH:
                return False 

        # Filter out calendar pages which are potentially low-information pages.
        if "calendar" in parsed_url.path.lower() or "calendar" in parsed_url.netloc.lower():
            return False
        
        # Filter out commit pages (gitlab/github) which are potentially low-information pages.
        if "commit" in parsed_url.path.lower():
            return False

        # Check robot.txt rules to follow politeness 
        # and do not fetch from paths we are not allowed
        if not robots.can_fetch(url):
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