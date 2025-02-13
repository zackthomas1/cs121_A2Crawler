import re
from simhash import compute_simhash, distance, compute_hash_value
from robots import *
from bs4 import BeautifulSoup
from utils import get_logger, normalize
from urllib.parse import urljoin, urlparse
import time

scrap_logger = get_logger("SCRAPER")

# Store simhashes of previously visted pages to avoid scraping duplicate content
# For less than 1 million simhashes storing simhashes in memory is preferred
# Time complexity of python set in operation is O(1). 
# For 20,000 SimHashes, the estimated memory usage is: 20,000 × 8 bytes = 160,000 bytes = 160 KB
visited_content_simhashes = set()
# visited_content_checksums = set()

#
visited_sitemaps = set()


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

    # # Check for EXACT content duplicate (Checksum) 
    # content_checksum = compute_hash_value(resp.raw_response.content)
    # if content_checksum in visited_content_checksums:
    #     scrap_logger.warning(f"Skipping URL {url}: Exact Content Match")
    #     return []
    # visited_content_checksums.add(content_checksum)

    # Check for NEAR duplicate content (Simhash)
    try:
        # Get the text from the html response
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')

        # Remove the text of CSS, JS, metadata, alter for JS, embeded websites
        for markup in soup.find_all(["style", "script", "meta", "noscript", "iframe"]):  
            markup.decompose()  # remove all markups stated above

        # soup contains only human-readable texts now to be compared near-duplicate
        text = soup.get_text(separator=" ", strip=True)
        
        # TODO: Save text content to disk (consider partial saving)
        

        # Check for Near-Duplicates using Simhash algorithm
        THREASHOLD = 6  # Hyper-parameter (convention for near-dup threshold is 3~10)
        current_page_hash = compute_simhash(text)
        for visited_page_hash in visited_content_simhashes:
            dist = distance(current_page_hash, visited_page_hash)
            if dist < THREASHOLD:
                scrap_logger.warning(f"Skipping URL {url}: Near Duplicate Content Match with Dist={dist}")
                return []
        visited_content_simhashes.add(current_page_hash)

    except Exception as e:
        scrap_logger.fatal(f"Error parsing {url}: {e}")
    
    # Extract links with another soup
    links = extract_next_links(url, resp)
    
    # Filter out duplicate and invalid urls (message log if needed)
    unique_links = set()
    for link in links:
        if not link:
            scrap_logger.info("Filtered out an empty or none URL")
        elif link in unique_links:
            scrap_logger.info(f"Filtered out duplicate URL: {link}")
        elif not is_valid(link):
            scrap_logger.info(f"Filtered out invalid URL: {link}")
        else:
            unique_links.add(link)

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

        # Filter out "archieve.ics.uci.edu" domain. 
        # This is the machine learning archieve.
        if "archive.ics.uci.edu" in parsed_url.netloc:
            return False

        # Filter out calendar pages which are potentially low-information pages.
        if "calendar" in parsed_url.path.lower() or "calendar" in parsed_url.netloc.lower():
            return False
        
        # Filter out commit pages (gitlab/github) which are potentially low-information pages.
        if "commit" in parsed_url.path.lower():
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
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz"
            + r"|md)$", parsed_url.path.lower())

    except TypeError:
        print ("TypeError for ", parsed_url)
        return False


# Sitemap Helper Methods
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
        scrap_logger.info(f"Found sitemaps for {url}: {sitemaps_urls}")
        return sitemaps_urls
    else:
        return []


def fetch_sitemap_urls(sitemap_url: str, config: Config, logger: Logger) -> list[str]: 

    time.sleep(config.time_delay)
    logger.info(f"Downloading sitemap: {sitemap_url}")
    resp = download(sitemap_url, config, logger)
    visited_sitemaps.add(sitemap_url)

    # If sitemap is invalid, return empty list
    if resp.status != 200 or not resp.raw_response:
        logger.warning(f"Failed to download sitemap: {sitemap_url}, status: {resp.status}")
        return []

    # TODO: NEEDS TESTING, the recursive downloading and adding of sitemap content might become unmanagable
    try: 
        tree = ET.fromstring(resp.raw_response.content)
        urls = set()

        # Gather all URLs in the sitemap
        url_element_stack = [url_element.text.strip() for url_element in tree.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]

        logger.info(f"Extracted URLS from sitemap {sitemap_url}: {url_element_stack}")

        # Process all urls
        while url_element_stack:
            # Pop a url off the stack
            url = url_element_stack.pop().strip()
            logger.info(f"Processing site within sitemap: {url}")

            # If it's another sitemap that's valid, process
            if is_xml_doc(url) and is_valid(url):
                # Download the sitemap
                time.sleep(config.time_delay)
                logger.info(f"Downloading sitemap: {url}")
                new_resp = download(url, config, logger)

                # Mark the sitemap as visited
                visited_sitemaps.add(url)

                # If valid, extend url_element_stack with the additional urls
                if (new_resp.status != 200 or not new_resp.raw_response):
                    logger.warning(f"Failed to download sitemap: {url}, status: {new_resp.status}")
                else:
                    url_element_stack.extend([elem.text.strip() for elem in ET.fromstring(new_resp.raw_response.content).findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")])
            # If just a site, add
            else:
                urls.add(url)

        logger.info(f"Extracted {len(urls)} URLs from {sitemap_url}")
        return list(urls)

    except Exception as e:
        logger.error(f"Unexpected error parsing sitemap {sitemap_url}: {e}")

    return []


def seed_frontier_from_sitemap(url: str, config: Config, logger: Logger) -> list[str]:
    sitemap_urls = get_sitemap_urls(url)

    links = []
    if sitemap_urls:
        for sitemap in sitemap_urls:
            # TODO: This also returns other sitemaps. We need sitemap detection for the purpose of downloading additional
            sitemap_links = fetch_sitemap_urls(sitemap, config, logger)
            links.extend(sitemap_links)

    return links