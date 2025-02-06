import scraper
from crawler.frontier import Frontier
from crawler.worker import Worker
from utils import get_logger
import unittest
import time
from unittest.mock import patch

class MockConfig: 
    def __init__(self, seeds):
        self.user_agent = "IR UW25 47642149"
        self.host = "styx.ics.uci.edu"
        self.port = 9000
        self.save_file = "test_crawler"
        self.seed_urls = seeds
        self.time_delay = 0.5
        self.thread_count = 1
        self.cache_server = None

class MockResponse: 
    def __init__(self, url, status, content): 
        self.url = url 
        self.status = status
        self.raw_response = self.RawResponse(content)
    
    class RawResponse: 
        def __init__(self, content):
            self.content = content

class TestCrawler(unittest.TestCase): 
    def setUp(self): 
        pass

class TestWorker(unittest.TestCase):
    def setUp(self): 
        self.config = MockConfig(["https://www.ics.uci.edu", 
                          "https://www.cs.uci.edu",
                          "https://www.informatics.uci.edu",
                          "https://www.stat.uci.edu"])
        self.frontier = Frontier(self.config, restart=True)
        self.logger = get_logger("TEST WORKER")

    def test_worker_respects_politness_delay(self):
        pass

    def test_worker_proces_url(self):
        pass

class TestFrontier(unittest.TestCase): 
    # def setUp(self): 
    #     self.config = MockConfig([])
    #     self.frontier = Frontier(self.config, restart=True)
    #     self.logger = get_logger("TEST FRONTIER")

    def test_frontier_add_and_get_url(self):
        pass

    def test_frontier_duplicate_url(self): 
        test_url = "https://www.ics.uci.edu"
        self.frontier.add_url(test_url)
        self.frontier.add_url(test_url)

        retrieved_url = self.frontier.get_tbd_url()
        self.assertEqual(retrieved_url, test_url, "Duplicate url should not be added twice")
        self.assertIsNone(self.frontier.get_tbd_url(), "Frontier should be empty after retrieving the only url.")
 
    def test_trap_detection(self): 
        trap_url_1 = "https://www.ics.uci.edu/path/1234"
        trap_url_2 = "https://www.ics.uci.edu/path/5678"

        self.frontier.add_url(trap_url_1)
        self.frontier.add_url(trap_url_2)   # Should be detected as a trap and ignored

        retrieved_url = self.frontier.get_tbd_url()
        self.assertEqual(retrieved_url, trap_url_1, "The First url should be added and retrieved from the frontier")
        self.assertIsNone(self.frontier.get_tbd_url(), "Trap url should be ignored, the frontier should be empty.")

class TestScraper(unittest.TestCase):
    def test_extract_basic_links(self):
        html_content = '''
        <html>
            <body>
                <a href="http://ics.uci.edu/page1">Page 1</a>
                <a href="/page2">Page 2</a>
                <a href="https://cs.uci.edu/page3">Page 3</a>
            </body>
        </html>
        '''
        resp = MockResponse("http://ics.uci.edu", 200, html_content)
        links = scraper.extract_next_links("http://ics.uci.edu", resp)
        expected_links = [
        'http://ics.uci.edu/page1',
        'http://ics.uci.edu/page2',  # Converted from relative
        'https://cs.uci.edu/page3'
        ]

        self.assertEqual(links, expected_links)

    def test_bad_response_status(self):
        html_content = ''' '''

        resp = MockResponse("http://ics.uci.edu", 403, html_content)
        links = scraper.extract_next_links("http://ics.uci.edu", resp)

        expected_links = []
        self.assertEqual(links, expected_links)

        resp = MockResponse("http://ics.uci.edu", 404, html_content)
        links = scraper.extract_next_links("http://ics.uci.edu", resp)
        self.assertEqual(links, expected_links)

        resp = MockResponse("http://ics.uci.edu", 301, html_content)
        links = scraper.extract_next_links("http://ics.uci.edu", resp)
        self.assertEqual(links, expected_links)


    def test_extract_no_links(self):
        html_content = '''
        <html>
            <body>
                <p> No Links!!!</p>
            </body>
        </html>
        '''
        resp = MockResponse("http://ics.uci.edu", 200, html_content)
        links = scraper.extract_next_links("http://ics.uci.edu", resp)
        expected_links = []
        self.assertEqual(links, expected_links)

    def test_extract_malformed_html(self):
        html_content = '''
        <html>
            <body>
                <a href='http://ics.uci.edu/page1'><p>Link without closing tags
        '''
        resp = MockResponse("http://ics.uci.edu", 200, html_content)
        links = scraper.extract_next_links("http://ics.uci.edu", resp)
        expected_links = ["http://ics.uci.edu/page1"]
        self.assertIn("http://ics.uci.edu/page1", links)

    def test_valid_url(self):
        self.assertTrue(scraper.is_valid("http://ics.uci.edu/page1"))
        self.assertTrue(scraper.is_valid("http://cs.uci.edu/page1"))
        self.assertTrue(scraper.is_valid("http://informatics.uci.edu/page1"))
        self.assertTrue(scraper.is_valid("http://stat.uci.edu/page1"))
        
    def test_disallowed_domain(self):
        self.assertFalse(scraper.is_valid("https://www.cs.ucla.edu/history/"))
        self.assertFalse(scraper.is_valid("https://www.cs.usc.edu/about/news/"))
        self.assertFalse(scraper.is_valid("https://eecs.berkeley.edu/about/"))

    def test_avoid_large_files(self): 
        self.assertTrue(False)

    def test_invalid_scheme(self):
        self.assertFalse(scraper.is_valid("ftp://ics.uci.edu/page1"))

    def test_duplicate_url(self): 
        url = "http://ics.uci.edu/page1"

        # Should be true the first time and False the second time
        self.assertTrue(scraper.is_valid(url))
        self.assertFalse(scraper.is_valid(url))

    def test_infinite_trap_pattern(self):
        url = "http://ics.uci.edu/a/b/c/d/e/f"
        self.assertFalse(scraper.is_valid(url))

    def test_rate_limiting(self):
        start_time = time.time()
        for _ in range(65): # Exceed the rate limit
            scraper.is_valid("http://ics.uci.edu/page1'")
        end_time = time.time()
        self.assertGreaterEqual(end_time - start_time, 1, "Rate limiting should have caused delay")
