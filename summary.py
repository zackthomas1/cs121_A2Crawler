import os
import re
import shelve
from collections import Counter
from bs4 import BeautifulSoup

from argparse import ArgumentParser
from configparser import ConfigParser

from utils import normalize, get_logger
from utils.config import Config
from utils.download import download
from utils.server_registration import get_cache_server

from urllib.parse import urljoin, urlparse

"""
Crawlinging thresholds
------------------------
We should be crawling at least 15-20k url pages, 
but no more than 100k.
"""

stop_words = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's",
    "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't",
    "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so",
    "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's",
    "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's",
    "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
}

def restart_summary_stats(summary_save_path: str, restart: bool) -> None:
    if restart:
        with shelve.open(summary_save_path) as db:
            db.clear()

def update_page_lengths(summary_save_path: str, url: str, tokens: list[str]) -> None:
    with shelve.open(summary_save_path) as db:
        page_lengths = db.get("page_lengths", {})

        # update
        token_count = len(tokens)
        page_lengths[url] = token_count

        # store back
        db["page_lengths"] = page_lengths
        db.sync()   # force disk write

def update_token_frequency(summary_save_path: str, tokens: list[str]) -> None: 
    with shelve.open(summary_save_path) as db:
        token_frequencies = db.get("token_frequencies", Counter())
        
        # update
        filtered_words = [token for token in tokens if token not in stop_words]
        token_frequencies.update(filtered_words)

        # store back
        db["token_frequencies"] = token_frequencies
        db.sync()   # force disk write

def unique_pages(frontier_save_path: str) -> int:
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
                # Additionally all the urls in the frontier should be uniuqe. Doing a set comparison is 
                # another level of checking
                unique_urls.add(url)

    return len(unique_urls) 

def get_longest_page(summary_save_path: str) -> tuple[str, int]: 
    """
    Find the longest page based on word count, excludes html markup text
    """
    longest_page = (None, 0)

    with shelve.open(summary_save_path) as db:
        page_lengths = db.get("page_lengths", {})

        for key, value in page_lengths.items():
            if value > longest_page[1]:
                longest_page = (key, value)
        
        return longest_page

def get_common_words(summary_save_path: str, k: int) -> dict[str, int]: 
    """
    Gets 50 most common words across all the crawled pages
    """
    # Load existing save file, or create one if it does not exist.
    with shelve.open(summary_save_path) as db:
        token_frequencies = db.get("token_frequencies", Counter())
        return token_frequencies.most_common(k)

def ics_subdomains(frontier_save_path: str) -> dict[str, int]:
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
                base_url = normalize(parsed_url._replace(query="", fragment="").geturl())
                if "ics.uci.edu" in parsed_url.netloc:
                    subdomain = parsed_url.netloc
                    if subdomain in subdomains:
                        subdomains[subdomain] += 1
                    else:
                        subdomains[subdomain] = 1

    return dict(sorted(subdomains.items()))

if __name__ == "__main__":
    # Unique pages
    print(f"There are {unique_pages('frontier.shelve')} unique pages")
    
    # Longest page
    page, word_count = get_longest_page('summary.shelve')
    print(f"The longest page is {page} with {word_count} words.")
    
    # Most common words
    print(f"The most common words are:")
    for word, count in get_common_words('summary.shelve',50):
        print(f"\t{word} - {count}")

    # ICS subdomains
    print(f"ICS Subdomains:")
    for key, value in ics_subdomains('frontier.shelve').items():
        print(f"\t{key} - {value}")