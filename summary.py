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
                # Additionally all the urls in the frontier should be uniuqe. Doing a set comparison is 
                # another level of checking
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
                word_count = re.findall(r'\b[a-zA-Z]\b, text')
                
                if word_count > longest_page[1]:
                    longest_page = (filename, word_count)
            except Exception as e:
                return None
    return longest_page

def get_common_words(frontier_save_path, config, logger, words_count): 
    """
    Gets 50 most common words across all the crawled pages
    """
   
    # check first that the path to the frontier save file exist
    if not os.path.exists(frontier_save_path): 
        return None
    
    crawled_pages_dir = []
    with shelve.open(frontier_save_path, 'r') as db: 
        for url, completed in db.values(): 
            if completed: 
                crawled_pages_dir.append(url)

    word_frequencies = Counter()
    for page_url in crawled_pages_dir:
        try:
            resp = download(page_url, config, logger)
            soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
            text = soup.get_text(separator=" ", strip=True)
            words = re.findall(r'\b{a-zA-Z}{2,}\b', text.lower())
            filtered_words = [word for word in words if word not in stop_words]
            word_frequencies.update(filtered_words)
        except Exception as e:
            return None
    
    return word_frequencies.most_common(words_count)

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
                base_url = normalize(parsed_url._replace(query="", fragment="").geturl())
                if "ics.uci.edu" in parsed_url.netloc:
                    subdomain = parsed_url.netloc
                    if subdomain in subdomains:
                        subdomains[subdomain] += 1
                    else:
                        subdomains[subdomain] = 1

    return dict(sorted(subdomains.items()))

if __name__ == "__main__":
    # parser = ArgumentParser()
    # parser.add_argument("--config_file", type=str, default="config.ini")
    # args = parser.parse_args()
    
    # cparser = ConfigParser()
    # cparser.read(args.config_file)
    # config = Config(cparser)
    # config.cache_server = get_cache_server(config, False)

    # logger = get_logger("Summary")

    print(f" There are {unique_pages('frontier.shelve')} unique pages")
    # print(f"The longest page is {longest_page('frontier.shelve', config, logger, 50)}")
    # print(f"The most common words are:\n {get_common_words('frontier.shelve', config, logger, 50)}")
    print(f"{ics_subdomains('frontier.shelve')}")

