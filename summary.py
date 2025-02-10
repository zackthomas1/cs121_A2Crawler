import os
import re
import shelve
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def unique_pages(frontier_save_path):
    """
    Counts the number of unique urls crawled in the frontier database
    """
    unique_urls = set()

    # check first that the path to the frontier save file exist
    if not os.path.exists(frontier_save_path): 
        return None
    
    with shelve.open(frontier_save_path, 'r') as db: 
        for url, completed in db.values(): 
            if completed: 
                # There should not be a need to remove a query or fragment from url.
                # This should have already been done in extract_next_link method.
                unique_urls.add(url)

    return len(unique_urls) 

def longest_page(crawled_pages_dir): 
    """
    Find the longest page based on word count, excludes html markup text
    """
    longest_page = (None, 0)

    for filename in os.listdir(crawled_pages_dir):
        file_path = os.path.join(crawled_pages_dir, filename)
        with open(file_path, "r", encoding="utf-8") as file: 
            try:
                soup = BeautifulSoup(file, 'html.parser')
                text = soup.get_text(separator= " ", strip=True)

                # Use regular expression to search for words
                # letters a-z and at least 1 letter
                word_count = re.findall(r'\b[a-zA-Z]{1,}\b, text')
                
                if word_count > longest_page[1]:
                    longest_page = (filename, word_count)
            except Exception as e:
                return None
    return longest_page

def common_words(): 
    """
    Gets 50 most common words across all the crawled pages
    """


def ics_subdomains(frontier_save_path):
    """
    Counts all the subdomains of ics.uci.edu
    """
    subdomains = {}

    # check first that the path to the frontier save file exist
    if not os.path.exists(frontier_save_path): 
        return None
    
    with shelve.open(frontier_save_path, 'r') as db: 
        for url, completed in db.values(): 
            if completed: 
                parsed_url = urlparse(url)
                domain = parsed_url.netloc
                if "ics.uci.edu" in domain:
                    subdomains[domain] += 1

    


