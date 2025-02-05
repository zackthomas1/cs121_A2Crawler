import scraper
import unittest
from unittest.mock import patch

class MockResponse: 
    def __init__(self, url, status, content): 
        self.url = url 
        self.status = status
        self.raw_response = self.RawResponse(content)
    
    class RawResponse: 
        def __init__(self, content):
            self.content = content

class TestExtractNextLinks(unittest.TestCase):
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
        self.assertTrue(scraper.is_valid("http://.stat.uci.edu/page1"))
        
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
        import time
        start_time = t