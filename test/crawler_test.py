import time

import unittest
from unittest.mock import patch, MagicMock

import scraper
from crawler.frontier import Frontier
from crawler.worker import Worker

from utils import get_logger
from utils.download import download

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

class MockRawResponse: 
    def __init__(self, content):
        self.content = content

class TestCrawler(unittest.TestCase): 
    def setUp(self): 
        pass

class TestWorker(unittest.TestCase):
    def setUp(self): 
        self.config = MockConfig([])
        self.frontier = Frontier(self.config, restart=True)
        self.logger = get_logger("TEST WORKER")

    @patch("utils.download.requests.get")  # Mock requests.get() inside download()
    @patch("utils.download.cbor.loads")  # Mock CBOR decoding
    @patch("pickle.loads")
    def test_worker_run(self, mock_pickle_loads, mock_cbor_loads, mock_requests_get):
        """Tests that Worker.run() correctly processes URLs and marks them complete."""
        
        html_content = """
        <html>
            <body>
                <a href='https://www.ics.uci.edu/page2'>Next</a>
            </body>
        </html>"""

        # Mock Response Object (to simulate cache server response)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"mocked CBOR response"

        # Mock requests.get() to return our fake response
        mock_requests_get.return_value = mock_resp

        # Mock CBOR Decoded Response
        mock_cbor_loads.return_value = {
            "url": "https://www.ics.uci.edu/page1",
            "status": 200,
            "response": {
                "content": html_content.encode()
            }
        }

        # Mock pickle.loads
        mock_pickle_loads.return_value = MockRawResponse(html_content)

        # Mock the Frontier methods
        mock_frontier = MagicMock(spec=Frontier)
        mock_frontier.get_tbd_url.side_effect = ["https://www.ics.uci.edu/page1", None]  # One URL, then stop
        mock_frontier.add_url = MagicMock()
        mock_frontier.mark_url_complete = MagicMock()

        # Mock config object
        mock_config = MagicMock()
        mock_config.cache_server = ("localhost", 8000)  # Mock cache server address
        mock_config.user_agent = "TestAgent"
        mock_config.time_delay = 0  # Avoid sleep delay

        # Create the Worker instance
        worker = Worker(worker_id=1, config=mock_config, frontier=mock_frontier)

        # Run the worker in the main thread (not as a daemon)
        worker.run()

        # Assertions
        mock_requests_get.assert_called_once_with(
            "http://localhost:8000/",
            params=[("q", "https://www.ics.uci.edu/page1"), ("u", "TestAgent")]
        )  # Verifies the correct request was made

        mock_cbor_loads.assert_called_once_with(b"mocked CBOR response")  # Ensures CBOR decoding happened
        mock_frontier.add_url.assert_called_with("https://www.ics.uci.edu/page2")  # Link extraction check
        mock_frontier.mark_url_complete.assert_called_with("https://www.ics.uci.edu/page1")  # URL processed check

    @patch("utils.download.requests.get")  # Mock requests.get() inside download()
    @patch("utils.download.cbor.loads")  # Mock CBOR decoding
    @patch("pickle.loads")
    @patch("time.sleep", side_effect=lambda x: None)
    def test_worker_run_politeness(self, mock_sleep, mock_pickle_loads, mock_cbor_loads, mock_requests_get):
        """Tests that Worker.run() correctly processes URLs and marks them complete."""
        
        html_content = """
        <html>
            <body>
                <a href='https://www.ics.uci.edu/page2'>Next</a>
            </body>
        </html>"""

        # Mock Response Object (to simulate cache server response)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"mocked CBOR response"

        # Mock requests.get() to return our fake response
        mock_requests_get.return_value = mock_resp

        # Mock CBOR Decoded Response
        mock_cbor_loads.return_value = {
            "url": "https://www.ics.uci.edu/page1",
            "status": 200,
            "response": {
                "content": html_content.encode()
            }
        }

        # Mock pickle.loads
        mock_pickle_loads.return_value = MockRawResponse(html_content)

        # Mock the Frontier methods
        mock_frontier = MagicMock(spec=Frontier)
        mock_frontier.get_tbd_url.side_effect = ["https://www.ics.uci.edu/page1", None]  # One URL, then stop
        mock_frontier.add_url = MagicMock()
        mock_frontier.mark_url_complete = MagicMock()

        # Mock config object
        mock_config = MagicMock()
        mock_config.cache_server = ("localhost", 8000)  # Mock cache server address
        mock_config.user_agent = "TestAgent"
        mock_config.time_delay = 1 # Politeness delay

        # Create the Worker instance
        worker = Worker(worker_id=1, config=mock_config, frontier=mock_frontier)

        # Run the worker in the main thread (not as a daemon)
        worker.run()

        # Assertions
        self.assertEqual(mock_sleep.call_count, 1)
        mock_sleep.assert_called_with(mock_config.time_delay) 

class TestFrontier(unittest.TestCase): 
    def setUp(self): 
        self.config = MockConfig([])
        self.frontier = Frontier(self.config, restart=True)
        self.logger = get_logger("TEST FRONTIER")

    def test_frontier_add_and_get_url(self):
        test_url_1 = "https://www.ics.uci.edu/page1"
        test_url_2 = "https://www.ics.uci.edu/page2/about"
        
        self.frontier.add_url(test_url_1)
        self.frontier.add_url(test_url_2)
        
        retrieved_url = self.frontier.get_tbd_url()
        self.assertEqual(retrieved_url, test_url_2, "Second test url should be retrieved first")

        retrieved_url = self.frontier.get_tbd_url()
        self.assertEqual(retrieved_url, test_url_1, "First test url should be retrieved second")

        self.assertIsNone(self.frontier.get_tbd_url(), "Frontier should be empty after retrieving 2 test urls.")

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

    def test_defragment(self): 
        html_content = '''
        <html>
            <body>
                <a href="http://ics.uci.edu/page1#aboutme">Page 1</a>
                <a href="/page2#locations">Page 2</a>
                <a href="https://cs.uci.edu/page3#zot">Page 3</a>
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
        html_content = ''''''

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

    def test_can_fetch_robots(self): 
        """
        https://ics.uci.edu/robots.txt
        -----------------------
        User-agent: ClaudeBot
        Disallow: /

        User-agent: *
        Disallow: /people
        Disallow: /happening
        """
        url_people1 = "https://www.ics.uci.edu/~lopes/" 
        url_people2 = "https://ics.uci.edu/people/jenna-lynn-abrams/"
        url_happening1 = "https://ics.uci.edu/happening/"
        url_allowed = "https://ics.uci.edu/academics/undergraduate-programs/#major"
    
        """
        https://statconsulting.uci.edu/robots.txt
        -----------------------
        User-agent: *
        Disallow: /wp-admin/
        Allow: /wp-admin/admin-ajax.php

        Sitemap: https://statconsulting.uci.edu/wp-sitemap.xml
        """
        url_statsconsult1 = "https://statconsulting.uci.edu/"
        url_statsconsult2 = "https://statconsulting.uci.edu/wp-admin/"

        self.assertTrue(scraper.can_fetch(url_people1))
        self.assertFalse(scraper.can_fetch(url_people2))
        self.assertFalse(scraper.can_fetch(url_happening1))
        self.assertTrue(scraper.can_fetch(url_allowed))
        self.assertFalse(scraper.can_fetch(url_allowed, user_agent= "ClaudeBot"))

        self.assertTrue(scraper.can_fetch(url_statsconsult1))
        # self.assertFalse(scraper.can_fetch(url_statsconsult2))

    def test_scraper_duplicate_url(self):
        html_content = '''
        <html>
            <body>
                <a href="https://cs.uci.edu/page1">Page 1</a>      
                <a href="https://cs.uci.edu/page1#aboutme">Page 1 - about me</a>
                <a href="/page1#locations">Page 1 - location</a>
                <a href="https://cs.uci.edu/page1/">Page 1</a>
            </body>
        </html>
        '''
        url = "https://cs.uci.edu"

        resp = MockResponse(url, 200, html_content)
        links = scraper.scraper(url, resp)
        expected_links = ["https://cs.uci.edu/page1"]

        self.assertEqual(links, expected_links)

    def test_exact_duplicate_content(self):
        html_content = '''
        <html>
            <body>
                <a href="https://cs.uci.edu/page1">Page 1</a>      
                <a href="https://cs.uci.edu/page1#aboutme">Page 1 - about me</a>
                <a href="/page1#locations">Page 1 - location</a>
                <a href="https://cs.uci.edu/page1/">Page 1</a>
            </body>
        </html>
        '''
        url_1 = "https://cs.uci.edu"
        url_2 = "https://eecs.berkeley.edu"

        resp_1 = MockResponse(url_1, 200, html_content)
        resp_2 = MockResponse(url_2, 200, html_content)

        links_1 = scraper.scraper(url_1, resp_1)
        links_2 = scraper.scraper(url_2, resp_2)

        expected_links_1 = ["https://cs.uci.edu/page1"]
    
        self.assertEqual(links_1, expected_links_1)
        self.assertEqual(len(links_2), 0)
    
    def test_near_duplicate_content(self):
        html_content_1 = '''
        <html>
            <body>
                <a href="https://cs.uci.edu/page1">Page 1</a>      
                <a href="https://cs.uci.edu/page1#aboutme">Page 1 - about me</a>
                <a href="/page1#locations">Page 1 - location</a>
                <a href="https://cs.uci.edu/page1/">Page 1</a>
            </body>
        </html>
        '''
        html_content_2 = '''
        <html>
            <body>
                <a href="https://cs.uci.edu/page1">Page 1</a>      
                <a href="https://cs.uci.edu/page1#aboutme">Page 1 - about me</a>
                <a href="/page1#locations">Page 1 - location</a>
            </body>
        </html>
        '''

        url_1 = "https://cs.uci.edu"
        url_2 = "https://eecs.berkeley.edu"

        resp_1 = MockResponse(url_1, 200, html_content_1)
        resp_2 = MockResponse(url_2, 200, html_content_2)

        links_1 = scraper.scraper(url_1, resp_1)
        links_2 = scraper.scraper(url_2, resp_2)

        expected_links_1 = ["https://cs.uci.edu/page1"]
    
        self.assertEqual(links_1, expected_links_1)
        self.assertEqual(len(links_2), 0)

    def test_infinite_trap_pattern(self):
        url = "http://ics.uci.edu/a/b/c/d/e/f/g"
        self.assertFalse(scraper.is_valid(url))

    def test_avoid_query_string(self):
        url = "https://ics.uci.edu"
        url_query = "https://ics.uci.edu/?s=news"

        self.assertTrue(scraper.is_valid(url))
        self.assertFalse(scraper.is_valid(url_query))

    def test_avoid_calendar_links (self):
        url = "https://ics.uci.edu"
        url_calendar = "http://calendar.ics.uci.edu/calendar.php"

        self.assertTrue(scraper.is_valid(url))
        self.assertFalse(scraper.is_valid(url_calendar))

    def test_rate_limiting(self):
        start_time = time.time()
        for _ in range(65): # Exceed the rate limit
            scraper.is_valid("http://ics.uci.edu/page1'")
        end_time = time.time()
        self.assertGreaterEqual(end_time - start_time, 1, "Rate limiting should have caused delay")
