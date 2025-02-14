import unittest
from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

import simhash
import robots
import scraper
import summary
from crawler.frontier import Frontier
from crawler.worker import Worker

class MockConfig: 
    def __init__(self, seeds):
        self.user_agent = "IR UW25 47642149"
        self.cache_server = ("localhost", 8000)
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
            self.headers = {}
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

    @patch("utils.download.download")
    def test_worker_run(self, mock_download):
        """Tests that Worker.run() correctly processes URLs and marks them complete."""
        
        url = "https://www.ics.uci.edu/page1"
        html_content = """
        <html>
            <body>
                <a href='https://www.ics.uci.edu/page2'>Next</a>
            </body>
        </html>"""
        resp = MockResponse(url, 200, html_content)

        # Mock the Frontier methods
        mock_frontier = MagicMock(spec=Frontier)
        mock_frontier.get_tbd_url.side_effect = [url, None]
        mock_frontier.add_url = MagicMock()
        mock_frontier.mark_url_complete = MagicMock()

        mock_download.return_value = resp

        # Create the Worker instance
        worker = Worker(worker_id=1, config=self.config, frontier=mock_frontier)

        # Run the worker in the main thread (not as a daemon)
        worker.run()

        # Assertions
        self.assertEqual(mock_download.call_count, 1)
        mock_frontier.add_url.assert_called_with("https://www.ics.uci.edu/page2")  # Link extraction check
        mock_frontier.mark_url_complete.assert_called_with("https://www.ics.uci.edu/page1")  # URL processed check

    @patch("utils.download.download")
    @patch("time.sleep", side_effect=lambda x: None)
    def test_worker_run_politeness(self, mock_sleep, mock_download):
        """Tests that Worker.run() correctly processes URLs and marks them complete."""
        url_1 = "https://www.ics.uci.edu/page1"
        url_2 = "https://www.ics.uci.edu/page2"

        html_content_1 = """
        <html>
            <body>
                <a href='https://www.ics.uci.edu/page2'>Next</a>
            </body>
        </html>"""
        html_content_2 = """
        <html>
            <body>
                <p>Hello World</p>
            </body>
        </html>"""

        resp_1 = MockResponse(url_1, 200, html_content_1)
        resp_2 = MockResponse(url_2, 200, html_content_2)

        mock_download.side_effect = [resp_1, resp_2]

        # Mock the Frontier methods
        frontier = Frontier(self.config, restart=True)
        frontier.add_url(url_1)

        # Create the Worker instance
        worker = Worker(worker_id=1, config=self.config, frontier=frontier)

        # Run the worker in the main thread (not as a daemon)
        worker.run()

        # Assertions
        mock_sleep.assert_called_with(self.config.time_delay) 

    @patch("utils.download.download")
    def test_circular_link_trap_detection(self, mock_download):
        html_content_1 = '''
        <html>
            <body>
                <a href="https://ics.uci.edu/page2">Page 2</a>
            </body>
        </html>
        '''
        html_content_2 = '''
        <html>
            <body>
                <a href="http://ics.uci.edu/page1">Page 1</a>
            </body>
        </html>
        '''

        url_1 = "https://ics.uci.edu/page1"
        url_2 = "https://ics.uci.edu/page2"

        page1_resp = MockResponse(url_1, 200, html_content_1)
        page2_resp = MockResponse(url_2, 200, html_content_2)

        def mock_download_response(url, config, logger):
            if url == url_1:
                return page1_resp
            elif url == url_2:
                return page2_resp
            return None

        # Circular Trap: page1 links to page2, and page2 links back to page1
        mock_download.side_effect = mock_download_response

        self.frontier.add_url(url_1)

        worker = Worker(worker_id=1, config=self.config, frontier=self.frontier)

        worker.run()

        mock_download.assert_any_call(url_1, self.config, worker.logger) 
        mock_download.assert_any_call(url_2, self.config, worker.logger)
        self.assertEqual(mock_download.call_count, 2)

class TestFrontier(unittest.TestCase): 
    def setUp(self): 
        self.config = MockConfig([])
        self.frontier = Frontier(self.config, restart=True)

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
 
    def test_seed_with_site_map(self):
        self.assertTrue(False)

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

    def test_redirect_response_status(self):
        html_content = ''''''

        expected_links = ["http://cs.uci.edu"]
        resp = MockResponse("http://ics.uci.edu", 301, html_content)
        resp.raw_response.headers = {"Location": "http://cs.uci.edu"}

        links = scraper.scraper("http://ics.uci.edu", resp)
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
        self.assertTrue(scraper.is_valid("https://ics.uci.edu/2023/09/06/uc-national-center-for-free-speech-and-civic-engagement-ask-the-experts-artificial-intelligence-and-education"))
        self.assertTrue(scraper.is_valid("https://ics.uci.edu/author/kaphan2/page/4"))
        self.assertTrue(scraper.is_valid("https://www.ics.uci.edu/~thornton/inf45"))

        self.assertTrue(scraper.is_valid("https://gitlab.ics.uci.edu/mars-research/kvstore/Jellyfish/-/tree/feature/mer_dna_mem"))

        self.assertFalse(scraper.is_valid("https://connectedlearning.uci.edu/media"))
        self.assertFalse(scraper.is_valid("https://ics.uci.edu/people"))

    def test_disallowed_domain(self):
        self.assertFalse(scraper.is_valid("https://www.cs.ucla.edu/history/"))
        self.assertFalse(scraper.is_valid("https://www.cs.usc.edu/about/news/"))
        self.assertFalse(scraper.is_valid("https://eecs.berkeley.edu/about/"))

    def test_avoid_large_files(self): 
        self.assertTrue(False)

    def test_invalid_scheme(self):
        self.assertFalse(scraper.is_valid("ftp://ics.uci.edu/page1"))

    def test_can_robots_fetch(self): 
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

        self.assertTrue(robots.can_fetch(url_people1))
        self.assertFalse(robots.can_fetch(url_people2))
        self.assertFalse(robots.can_fetch(url_happening1))
        self.assertTrue(robots.can_fetch(url_allowed))
        self.assertFalse(robots.can_fetch(url_allowed, user_agent= "ClaudeBot"))

        self.assertTrue(robots.can_fetch(url_statsconsult1))
        # self.assertFalse(robots.can_fetch(url_statsconsult2))

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
        url_2 = "https://ics.uci.edu"

        resp_1 = MockResponse(url_1, 200, html_content)
        resp_2 = MockResponse(url_2, 200, html_content)

        links_1 = scraper.scraper(url_1, resp_1)
        links_2 = scraper.scraper(url_2, resp_2)

        expected_links_1 = ["https://cs.uci.edu/page1"]
    
        self.assertEqual(links_1, expected_links_1)
        self.assertEqual(len(links_2), 0)
    
    def test_near_duplicate_content(self):
        html_content_1 = '''
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"><head>
            <meta http-equiv="content-type" content="text/html; charset=iso-8859-1">
            <link rel="stylesheet" href="course2.css" type="text/css">

            <title>Informatics 45 Spring 2010</title>
            </head>
            <body>
            <div class="navbar">
            <p>
            Informatics 45 Spring 2010 |
            <a href="index.html">News</a> |
            <a href="CourseReference.html">Course Reference</a> |
            <a href="Schedule.html">Schedule</a> |
            <a href="LabManual">Lab Manual</a> |
            <a href="CodeExamples">Code Examples</a> |
            <a href="http://www.ics.uci.edu/~thornton/">About Alex</a>
            </p>
            <hr>
            </div>
            <div class="header">
            <p>Informatics 45 Spring 2010<br>
            Course News</p>
            </div>
            <div class="section">
            <hr>
            <p>Check back here every day or so.  I will generally post important coursewide announcements here.  They will be listed in reverse-chronological order (i.e., newest items first).</p>

            <table class="normal">
            <tbody><tr class="top">
                <td>Date&nbsp;Added</td>
                <td>News Item</td>
            </tr>
            <tr>
                <td>Su 6/13</td>
                <td>The <a href="FinalGrades.html">final course grades</a> are now available.</td>
            </tr>
            <tr>
                <td>Tu 6/1</td>
                <td>The <a href="Schedule.html">Schedule</a> has been updated to reflect the topics to be covered for the remainder of the quarter.</td>
            </tr>
            <tr>
                <td>Th 5/27</td>
                <td>The ball animation and ball-and-paddle game <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>Su 5/23</td>
                <td><a href="LabManual/GamesWithoutFrontiers">Project #4</a> is now available.</td>
            </tr>
            <tr>
                <td>W 5/19</td>
                <td>The Othello game we wrote in lecture is now available as a commented <a href="CodeExamples">code example</a>.</td>
            </tr>
            <tr>
                <td>Th 5/13</td>
                <td>To accommodate a due date that many of you have in Informatics 43, I've postponed the <a href="LabManual/TheGreatBeyond">Project #3</a> due date a bit.  Because of the fourth project, I can't postpone it further than I have, but I hope that this at least provides some relief.</td>
            </tr>
            <tr>
                <td>M 5/10</td>
                <td><a href="LabManual/TheGreatBeyond">Project #3</a>, a <a href="Schedule.html">Schedule</a> update, and all missing <a href="CodeExamples">code examples</a> to date are now available.</td>
            </tr>
            <tr>
                <td>Th 4/29</td>
                <td>A <a href="Schedule.html">Schedule</a> update and tonight's <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>W 4/28</td>
                <td>Yesterday's <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>Th 4/22</td>
                <td>Tonight's sockets-and-GUIs <a href="CodeExamples">code example</a> is now available.</td>
            </tr>
            <tr>
                <td>Tu 4/20</td>
                <td>Our <a href="CodeExamples">code example</a> from today is available.</td>
            </tr>
            <tr>
                <td>Th 4/15</td>
                <td>The <a href="CodeExamples">code example</a> from tonight's lecture is now available.</td>
            </tr>
            <tr>
                <td>W 4/14</td>
                <td><a href="LabManual/PicturesOfYou">Project #2</a> is now available, along with a <a href="Schedule.html">Schedule</a> estimate through Week 5.</td>
            </tr>
            <tr>
                <td>Th 4/8</td>
                <td>Tonight's <a href="CodeExamples">code example</a>, along with a preview of some things we'll be next week.</td>
            </tr>
            <tr>
                <td>W 4/7</td>
                <td>The <a href="CodeExamples">code example</a> from yesterday's lecture, along with a sneak preview of some of the things we'll do tomorrow, is now available.</td>
            </tr>
            <tr>
                <td>Th 4/1</td>
                <td>Today's <a href="CodeExamples">code example</a> is now available.</td>
            </tr>
            <tr>
                <td>M 3/29</td>
                <td>
                <p>Welcome!  A few things:</p>
                <ul>
                    <li>The first lecture will meet on Tuesday, March 30 and lab sections will begin meeting on Wednesday, March 31.  For more information about meeting times of labs, see the <a href="CourseReference.html">Course Reference</a>.  For information about lecture material and readings, see the <a href="Schedule.html">Schedule</a>.</li>
                    <li>I encourage you to spend some time reading through the material on this course web site.  Notice the set of links at the top of this (and every) page, leading you to the <a href="CourseReference.html">Course Reference</a>, the <a href="Schedule.html">Schedule</a>, and the <a href="LabManual">Lab Manual</a>, as well as a set of commented <a href="CodeExamples">Code Examples</a> that will be posted during the course of the quarter.</li>
                </ul>
                </td>
            </tr>
            </tbody></table>
            <br>
            </div>
            <div class="history">
            <hr>
            <p>This course web site has been validated against the XHTML 1.1 and CSS 2.0 standards.  To ensure that your own Web pages meet established Web standards, visit <a href="http://validator.w3.org/">validator.w3.org</a>.</p>
            <p>
            <img src="valid-xhtml11.gif" alt="Valid XHTML 1.1!" height="24" width="104">
            <img src="vcss-new.gif" alt="Valid CSS 2.0!" height="24" width="104">
            </p>
            </div>
            </body></html>
            '''
        html_content_2 = '''
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"><head>
            <meta http-equiv="content-type" content="text/html; charset=iso-8859-1">
            <link rel="stylesheet" href="course2.css" type="text/css">

            <title>Informatics 45 Spring 2010</title>
            </head>
            <body>
            <div class="navbar">
            <p>
            Informatics 45 Spring 2010 |
            <a href="index.html">News</a> |
            <a href="CourseReference.html">Course Reference</a> |
            <a href="Schedule.html">Schedule</a> |
            <a href="LabManual">Lab Manual</a> |
            <a href="CodeExamples">Code Examples</a> |
            <a href="http://www.ics.uci.edu/~thornton/">About alex</a>
            </p>
            <hr>
            </div>
            <div class="header">
            <p>Informatics 45 Spring 2010<br>
            Course News</p>
            </div>
            <div class="section">
            <hr>
            <p>Check back here every day or so.  I will generally post important course wide announcements here.  They will be listed in reverse-chronological order (i.e., newest items first).</p>

            <table class="normal">
            <tbody><tr class="top">
                <td>Date&nbsp;Added</td>
                <td>News Item</td>
            </tr>
            <tr>
                <td>Su 6/13</td>
                <td>The <a href="FinalGrades.html">final course grades</a> are now available.</td>
            </tr>
            <tr>
                <td>Tu 6/1</td>
                <td>The <a href="Schedule.html">Schedule</a> has been updated to reflect the topics to be covered for the remainder of the quarter.</td>
            </tr>
            <tr>
                <td>Th 5/27</td>
                <td>The ball animation and ball-and-paddle game <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>Su 5/23</td>
                <td><a href="LabManual/GamesWithoutFrontiers">Project #4</a> is now available.</td>
            </tr>
            <tr>
                <td>W 5/19</td>
                <td>The Othello game we wrote in lecture is now available as a commented <a href="CodeExamples">code example</a>.</td>
            </tr>
            <tr>
                <td>Th 5/13</td>
                <td>To accommodate a due date that many of you have in INF 43, I've postponed the <a href="LabManual/TheGreatBeyond">Project #3</a> due date a bit.  Because of the fourth project, I can't postpone it further than I have, but I hope that this at least provides some relief.</td>
            </tr>
            <tr>
                <td>M 5/10</td>
                <td><a href="LabManual/TheGreatBeyond">Project #3</a>, a <a href="Schedule.html">Schedule</a> update, and all missing <a href="CodeExamples">code examples</a> to date are now available.</td>
            </tr>
            <tr>
                <td>Th 4/29</td>
                <td>A <a href="Schedule.html">Schedule</a> update and tonight's <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>W 4/28</td>
                <td>Yesterday's <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>Th 4/22</td>
                <td>Tonight's sockets-and-GUIs <a href="CodeExamples">code example</a> is now available.</td>
            </tr>
            <tr>
                <td>Tu 4/20</td>
                <td>Our <a href="CodeExamples">code example</a> from today is available.</td>
            </tr>
            <tr>
                <td>Th 4/15</td>
                <td>The <a href="CodeExamples">code example</a> from tonight's lecture is now available.</td>
            </tr>
            <tr>
                <td>W 4/14</td>
                <td><a href="LabManual/PicturesOfYou">Project #2</a> is now available, along with a <a href="Schedule.html">Schedule</a> estimate through Week 5.</td>
            </tr>
            <tr>
                <td>Th 4/8</td>
                <td>Tonight's <a href="CodeExamples">code example</a>, along with a preview of some things we'll be next week.</td>
            </tr>
            <tr>
                <td>W 4/7</td>
                <td>The <a href="CodeExamples">code example</a> from yesterday's lecture, along with a sneak preview of some of the things we'll do tomorrow, is now available.</td>
            </tr>
            <tr>
                <td>Th 4/1</td>
                <td>Today's <a href="CodeExamples">code example</a> is now available.</td>
            </tr>
            <tr>
                <td>M 3/29</td>
                <td>
                <p>Welcome!  A few things:</p>
                <ul>
                    <li>The first lecture will meet on Tuesday, March 30 and lab sections will begin meeting on Wednesday, March 31.  For more information about meeting times of labs, see the <a href="CourseReference.html">Course Reference</a>.  For information about lecture material and readings, see the <a href="Schedule.html">Schedule</a>.</li>
                    <li>I encourage you to spend some time reading through the material on this course web site.  Notice the set of links at the top of this (and every) page, leading you to the <a href="CourseReference.html">Course Reference</a>, the <a href="Schedule.html">Schedule</a>, and the <a href="LabManual">Lab Manual</a>, as well as a set of commented <a href="CodeExamples">Code Examples</a> that will be posted during the course of the quarter.</li>
                </ul>
                </td>
            </tr>
            </tbody></table>
            <br>
            </div>
            <div class="history">
            <hr>
            <p>This course web site has been validated against the XHTML 1.1 and CSS 2.0 standards.  To ensure that your own Web pages meet established Web standards, visit <a href="http://validator.w3.org/">validator.w3.org</a>.</p>
            <p>
            <img src="valid-xhtml11.gif" alt="Valid XHTML 1.1!" height="24" width="104">
            <img src="vcss-new.gif" alt="Valid CSS 2.0!" height="24" width="104">
            </p>
            </div>
            </body></html>
            '''

        url_1 = "https://ics.uci.edu/page1"
        url_2 = "https://ics.uci.edu/notthesamepage"

        page1_resp = MockResponse(url_1, 200, html_content_1)
        page2_resp = MockResponse(url_2, 200, html_content_2)
        
        links_1 = scraper.scraper(url_1, page1_resp)
        links_2 = scraper.scraper(url_2, page2_resp)

        self.assertTrue(len(links_1) > 0)
        self.assertEqual(len(links_2), 0)
        self.assertEqual(links_2, [])

    def test_infinite_trap_pattern(self):
        url = "http://ics.uci.edu/a/b/c/d/e/f/g/h/i/j"
        self.assertFalse(scraper.is_valid(url))

    def test_avoid_query_string(self):
        url = "https://ics.uci.edu"
        url_query = "https://ics.uci.edu/?s=news"

        self.assertTrue(scraper.is_valid(url))
        self.assertFalse(scraper.is_valid(url_query))

    def test_avoid_archive_links (self):
        url_archive = "https://archive.ics.uci.edu/dataset/53/iris"

        self.assertFalse(scraper.is_valid(url_archive))

    def test_avoid_calendar_links (self):
        url_calendar = "http://calendar.ics.uci.edu/calendar.php"

        self.assertFalse(scraper.is_valid(url_calendar))

    def test_avoid_commit_links (self):
        url_commit = "http://gitlab.ics.uci.edu/curtic3/checkers_student/-/commit/120d8ceab82bfd7a92f94767ae51095c5e11b641"

        self.assertFalse(scraper.is_valid(url_commit))

    def test_avoid_readme_md_trap_detection(self): 
        url_readme_1 = "https://gitlab.ics.uci.edu/curtic3/Checkers_Student/-/blob/f179207851371a407b7a7bea832d6ee07baddd26/readme.md"
        url_readme_2 = "https://gitlab.ics.uci.edu/curtic3/Checkers_Student/-/blob/readme.md"

        self.assertFalse(scraper.is_valid(url_readme_1))
        self.assertFalse(scraper.is_valid(url_readme_2))

    def test_id_trap_detection(self): 
        trap_url_1 = "https://www.ics.uci.edu/path/dffe26132d98b7a7dc702b0ec5a4a76000d48373"
        trap_url_2 = "https://www.ics.uci.edu/path/18f79a635a0a2f6aa84c9f116856a253d6c257ba"
        trap_url_3 = "https://uci.zoom.us/meeting/register/tJIrduqsrTspGtaNnebaEUenSu_WF6Y9WGf"

        self.assertFalse(scraper.is_valid(trap_url_1))
        self.assertFalse(scraper.is_valid(trap_url_2))
        self.assertFalse(scraper.is_valid(trap_url_3))


    def test_extract_next_line_defragment(self):
        html_content_1 = '''
        <html>
            <body>
                <a href="https://ics.uci.edu/happening/news/">News</a>
                <a href="https://ics.uci.edu/happening/news#bottom">News</a>
                <a href="https://ics.uci.edu/happening/news/?filter%5Baffiliation_posts%5D=1988#top">News</a>
            </body>
        </html>
        '''
        url_1 = "https://ics.uci.edu/page1"
        page1_resp = MockResponse(url_1, 200, html_content_1)

        links = scraper.extract_next_links(url_1, page1_resp)
        expected_links = ['https://ics.uci.edu/happening/news', "https://ics.uci.edu/happening/news", "https://ics.uci.edu/happening/news"]

        self.assertEqual(links, expected_links)

    def test_extract_next_stripe_query(self):
        html_content_1 = '''
        <html>
            <body>
                <a href="https://ics.uci.edu/happening/news/">News</a>
                <a href="https://ics.uci.edu/happening/news/?filter%5Baffiliation_posts%5D=1988">News</a>
                <a href="https://ics.uci.edu/happening/news/?filter%5Baffiliation_posts%5D=1988#top">News</a>
            </body>
        </html>
        '''
        url_1 = "https://ics.uci.edu/page1"
        page1_resp = MockResponse(url_1, 200, html_content_1)

        links = scraper.extract_next_links(url_1, page1_resp)
        expected_links = ['https://ics.uci.edu/happening/news', "https://ics.uci.edu/happening/news", "https://ics.uci.edu/happening/news"]

        self.assertEqual(links, expected_links)

class TestSimHash(unittest.TestCase): 

    def test_compute_hash_value(self):
        input_val_1= 'a'
        input_val_2= 'a'
        input_val_3= 'A'
        input_val_4= '52'

        output_1 = simhash.compute_hash_value(input_val_1)
        output_2 = simhash.compute_hash_value(input_val_2)
        output_3 = simhash.compute_hash_value(input_val_3)
        output_4 = simhash.compute_hash_value(input_val_4)

        self.assertEqual(output_1, output_2)
        self.assertNotEqual(output_1, output_3)
        self.assertNotEqual(output_3, output_4)

    def test_compute_simhash(self):
       
        self.assertTrue(False)

    def test_compute_hash_distance(self):
        str_1 = """To accommodate a due date that many of you have in Informatics 43,
        I've postponed the Project #3 due date a bit. 
        Because of the fourth project, I can't postpone it further than I have, 
        but I hope that this at least provides some relief.""" 
        str_2 = """To accommodate a due date that many of you have in INF 43,
        i've postponed the Prj #3 due date a bit. 
        Because of the fourth project, i can't postpone it further than i have, 
        but i hope that this at least provides some relief."""
        str_3 = """The code example from yesterday's lecture, 
        along with a sneak preview of some of the things we'll do tomorrow, 
        is now available."""

        simhash_1 = simhash.compute_simhash(str_1)
        simhash_2 = simhash.compute_simhash(str_2)
        simhash_3 = simhash.compute_simhash(str_3)

        dist_1 = simhash.calculate_hash_distance(simhash_1, simhash_1)
        dist_2 = simhash.calculate_hash_distance(simhash_1, simhash_2)
        dist_3 = simhash.calculate_hash_distance(simhash_1, simhash_3)

        self.assertTrue(dist_1 == 0)
        self.assertTrue(dist_2 < simhash.THRESHOLD)
        self.assertTrue(dist_3 > simhash.THRESHOLD)

class TestSummaryStatistics(unittest.TestCase): 
    def test_unique_pages(self):
        self.assertTrue(False)

    def test_longest_page(self):

        html_content_1 = '''
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"><head>
            <meta http-equiv="content-type" content="text/html; charset=iso-8859-1">
            <link rel="stylesheet" href="course2.css" type="text/css">

            <title>Informatics 45 Spring 2010</title>
            </head>
            <body>
            <div class="navbar">
            <p>
            Informatics 45 Spring 2010 |
            <a href="index.html">News</a> |
            <a href="CourseReference.html">Course Reference</a> |
            <a href="Schedule.html">Schedule</a> |
            <a href="LabManual">Lab Manual</a> |
            <a href="CodeExamples">Code Examples</a> |
            <a href="http://www.ics.uci.edu/~thornton/">About Alex</a>
            </p>
            <hr>
            </div>
            <div class="header">
            <p>Informatics 45 Spring 2010<br>
            Course News</p>
            </div>
            <div class="section">
            <hr>
            <p>Check back here every day or so.  I will generally post important coursewide announcements here.  They will be listed in reverse-chronological order (i.e., newest items first).</p>

            <table class="normal">
            <tbody><tr class="top">
                <td>Date&nbsp;Added</td>
                <td>News Item</td>
            </tr>
            <tr>
                <td>Su 6/13</td>
                <td>The <a href="FinalGrades.html">final course grades</a> are now available.</td>
            </tr>
            <tr>
                <td>Tu 6/1</td>
                <td>The <a href="Schedule.html">Schedule</a> has been updated to reflect the topics to be covered for the remainder of the quarter.</td>
            </tr>
            <tr>
                <td>Th 5/27</td>
                <td>The ball animation and ball-and-paddle game <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>Su 5/23</td>
                <td><a href="LabManual/GamesWithoutFrontiers">Project #4</a> is now available.</td>
            </tr>
            <tr>
                <td>W 5/19</td>
                <td>The Othello game we wrote in lecture is now available as a commented <a href="CodeExamples">code example</a>.</td>
            </tr>
            <tr>
                <td>Th 5/13</td>
                <td>To accommodate a due date that many of you have in Informatics 43, I've postponed the <a href="LabManual/TheGreatBeyond">Project #3</a> due date a bit.  Because of the fourth project, I can't postpone it further than I have, but I hope that this at least provides some relief.</td>
            </tr>
            <tr>
                <td>M 5/10</td>
                <td><a href="LabManual/TheGreatBeyond">Project #3</a>, a <a href="Schedule.html">Schedule</a> update, and all missing <a href="CodeExamples">code examples</a> to date are now available.</td>
            </tr>
            <tr>
                <td>Th 4/29</td>
                <td>A <a href="Schedule.html">Schedule</a> update and tonight's <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>W 4/28</td>
                <td>Yesterday's <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>Th 4/22</td>
                <td>Tonight's sockets-and-GUIs <a href="CodeExamples">code example</a> is now available.</td>
            </tr>
            <tr>
                <td>Tu 4/20</td>
                <td>Our <a href="CodeExamples">code example</a> from today is available.</td>
            </tr>
            <tr>
                <td>Th 4/15</td>
                <td>The <a href="CodeExamples">code example</a> from tonight's lecture is now available.</td>
            </tr>
            <tr>
                <td>W 4/14</td>
                <td><a href="LabManual/PicturesOfYou">Project #2</a> is now available, along with a <a href="Schedule.html">Schedule</a> estimate through Week 5.</td>
            </tr>
            <tr>
                <td>Th 4/8</td>
                <td>Tonight's <a href="CodeExamples">code example</a>, along with a preview of some things we'll be next week.</td>
            </tr>
            <tr>
                <td>W 4/7</td>
                <td>The <a href="CodeExamples">code example</a> from yesterday's lecture, along with a sneak preview of some of the things we'll do tomorrow, is now available.</td>
            </tr>
            <tr>
                <td>Th 4/1</td>
                <td>Today's <a href="CodeExamples">code example</a> is now available.</td>
            </tr>
            <tr>
                <td>M 3/29</td>
                <td>
                <p>Welcome!  A few things:</p>
                <ul>
                    <li>The first lecture will meet on Tuesday, March 30 and lab sections will begin meeting on Wednesday, March 31.  For more information about meeting times of labs, see the <a href="CourseReference.html">Course Reference</a>.  For information about lecture material and readings, see the <a href="Schedule.html">Schedule</a>.</li>
                    <li>I encourage you to spend some time reading through the material on this course web site.  Notice the set of links at the top of this (and every) page, leading you to the <a href="CourseReference.html">Course Reference</a>, the <a href="Schedule.html">Schedule</a>, and the <a href="LabManual">Lab Manual</a>, as well as a set of commented <a href="CodeExamples">Code Examples</a> that will be posted during the course of the quarter.</li>
                </ul>
                </td>
            </tr>
            </tbody></table>
            <br>
            </div>
            <div class="history">
            <hr>
            <p>This course web site has been validated against the XHTML 1.1 and CSS 2.0 standards.  To ensure that your own Web pages meet established Web standards, visit <a href="http://validator.w3.org/">validator.w3.org</a>.</p>
            <p>
            <img src="valid-xhtml11.gif" alt="Valid XHTML 1.1!" height="24" width="104">
            <img src="vcss-new.gif" alt="Valid CSS 2.0!" height="24" width="104">
            </p>
            </div>
            </body></html>
            '''
        html_content_2 = '''
        <html>
            <body>
                <p> Hello World Hello </p>
                <a href="https://ics.uci.edu/page2">Page 2</a>
                <p> Hello Moon Bye Bye/* </p>
            </body>
        </html>
        '''
        
        url_1 = "https://ics.uci.edu/~thornton/inf45/"
        url_2 = "https://ics.uci.edu/page/1"
        
        responses = []
        responses.append(MockResponse(url_1, 200, html_content_1))
        responses.append(MockResponse(url_2, 200, html_content_2))

        summary.restart_summary_stats("summary_test.shelve" ,True)
        for resp in responses:
            soup = BeautifulSoup(resp.raw_response.content, 'html.parser')

            # Remove the text of CSS, JS, metadata, alter for JS, embeded websites
            for markup in soup.find_all(["style", "script", "meta", "noscript", "iframe"]):  
                markup.decompose()  # remove all markups stated above
            
            # soup contains only human-readable texts now to be compared near-duplicate
            text = soup.get_text(separator=" ", strip=True)
            page_tokens = simhash.tokenize(text)
            summary.update_page_lengths("summary_test.shelve", resp.url, page_tokens)

        longest_page = summary.get_longest_page("summary_test.shelve")
        expected_result = ("https://ics.uci.edu/~thornton/inf45/", 416)
        
        self.assertEqual(longest_page, expected_result)

    def test_common_words(self):
        html_content_1 = '''
            <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en"><head>
            <meta http-equiv="content-type" content="text/html; charset=iso-8859-1">
            <link rel="stylesheet" href="course2.css" type="text/css">

            <title>Informatics 45 Spring 2010</title>
            </head>
            <body>
            <div class="navbar">
            <p>
            Informatics 45 Spring 2010 |
            <a href="index.html">News</a> |
            <a href="CourseReference.html">Course Reference</a> |
            <a href="Schedule.html">Schedule</a> |
            <a href="LabManual">Lab Manual</a> |
            <a href="CodeExamples">Code Examples</a> |
            <a href="http://www.ics.uci.edu/~thornton/">About Alex</a>
            </p>
            <hr>
            </div>
            <div class="header">
            <p>Informatics 45 Spring 2010<br>
            Course News</p>
            </div>
            <div class="section">
            <hr>
            <p>Check back here every day or so.  I will generally post important coursewide announcements here.  They will be listed in reverse-chronological order (i.e., newest items first).</p>

            <table class="normal">
            <tbody><tr class="top">
                <td>Date&nbsp;Added</td>
                <td>News Item</td>
            </tr>
            <tr>
                <td>Su 6/13</td>
                <td>The <a href="FinalGrades.html">final course grades</a> are now available.</td>
            </tr>
            <tr>
                <td>Tu 6/1</td>
                <td>The <a href="Schedule.html">Schedule</a> has been updated to reflect the topics to be covered for the remainder of the quarter.</td>
            </tr>
            <tr>
                <td>Th 5/27</td>
                <td>The ball animation and ball-and-paddle game <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>Su 5/23</td>
                <td><a href="LabManual/GamesWithoutFrontiers">Project #4</a> is now available.</td>
            </tr>
            <tr>
                <td>W 5/19</td>
                <td>The Othello game we wrote in lecture is now available as a commented <a href="CodeExamples">code example</a>.</td>
            </tr>
            <tr>
                <td>Th 5/13</td>
                <td>To accommodate a due date that many of you have in Informatics 43, I've postponed the <a href="LabManual/TheGreatBeyond">Project #3</a> due date a bit.  Because of the fourth project, I can't postpone it further than I have, but I hope that this at least provides some relief.</td>
            </tr>
            <tr>
                <td>M 5/10</td>
                <td><a href="LabManual/TheGreatBeyond">Project #3</a>, a <a href="Schedule.html">Schedule</a> update, and all missing <a href="CodeExamples">code examples</a> to date are now available.</td>
            </tr>
            <tr>
                <td>Th 4/29</td>
                <td>A <a href="Schedule.html">Schedule</a> update and tonight's <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>W 4/28</td>
                <td>Yesterday's <a href="CodeExamples">code examples</a> are now available.</td>
            </tr>
            <tr>
                <td>Th 4/22</td>
                <td>Tonight's sockets-and-GUIs <a href="CodeExamples">code example</a> is now available.</td>
            </tr>
            <tr>
                <td>Tu 4/20</td>
                <td>Our <a href="CodeExamples">code example</a> from today is available.</td>
            </tr>
            <tr>
                <td>Th 4/15</td>
                <td>The <a href="CodeExamples">code example</a> from tonight's lecture is now available.</td>
            </tr>
            <tr>
                <td>W 4/14</td>
                <td><a href="LabManual/PicturesOfYou">Project #2</a> is now available, along with a <a href="Schedule.html">Schedule</a> estimate through Week 5.</td>
            </tr>
            <tr>
                <td>Th 4/8</td>
                <td>Tonight's <a href="CodeExamples">code example</a>, along with a preview of some things we'll be next week.</td>
            </tr>
            <tr>
                <td>W 4/7</td>
                <td>The <a href="CodeExamples">code example</a> from yesterday's lecture, along with a sneak preview of some of the things we'll do tomorrow, is now available.</td>
            </tr>
            <tr>
                <td>Th 4/1</td>
                <td>Today's <a href="CodeExamples">code example</a> is now available.</td>
            </tr>
            <tr>
                <td>M 3/29</td>
                <td>
                <p>Welcome!  A few things:</p>
                <ul>
                    <li>The first lecture will meet on Tuesday, March 30 and lab sections will begin meeting on Wednesday, March 31.  For more information about meeting times of labs, see the <a href="CourseReference.html">Course Reference</a>.  For information about lecture material and readings, see the <a href="Schedule.html">Schedule</a>.</li>
                    <li>I encourage you to spend some time reading through the material on this course web site.  Notice the set of links at the top of this (and every) page, leading you to the <a href="CourseReference.html">Course Reference</a>, the <a href="Schedule.html">Schedule</a>, and the <a href="LabManual">Lab Manual</a>, as well as a set of commented <a href="CodeExamples">Code Examples</a> that will be posted during the course of the quarter.</li>
                </ul>
                </td>
            </tr>
            </tbody></table>
            <br>
            </div>
            <div class="history">
            <hr>
            <p>This course web site has been validated against the XHTML 1.1 and CSS 2.0 standards.  To ensure that your own Web pages meet established Web standards, visit <a href="http://validator.w3.org/">validator.w3.org</a>.</p>
            <p>
            <img src="valid-xhtml11.gif" alt="Valid XHTML 1.1!" height="24" width="104">
            <img src="vcss-new.gif" alt="Valid CSS 2.0!" height="24" width="104">
            </p>
            </div>
            </body></html>
            '''
        html_content_2 = '''
        <html>
            <body>
                <p> Hello World Hello </p>
                <a href="https://ics.uci.edu/page2">Page 2</a>
                <p> Hello Moon Bye Bye/* </p>
            </body>
        </html>
        '''
        
        url_1 = "https://ics.uci.edu/~thornton/inf45/"
        url_2 = "https://ics.uci.edu/page/1"
        
        resp_1 = MockResponse(url_1, 200, html_content_1)
        resp_2 = MockResponse(url_2, 200, html_content_2)
        
        soup = BeautifulSoup(resp_2.raw_response.content, 'html.parser')

        # Remove the text of CSS, JS, metadata, alter for JS, embeded websites
        for markup in soup.find_all(["style", "script", "meta", "noscript", "iframe"]):  
            markup.decompose()  # remove all markups stated above
        
        # soup contains only human-readable texts now to be compared near-duplicate
        text = soup.get_text(separator=" ", strip=True)
        page_tokens = simhash.tokenize(text)

        summary.restart_summary_stats("summary_test.shelve" ,True)
        summary.update_token_frequency("summary_test.shelve", page_tokens)
        common_words = summary.get_common_words("summary_test.shelve", 2)

        expected_results = [("hello", 3), ("bye", 2)]

        self.assertEqual(common_words, expected_results) 
        
    def test_ics_subdomains(self):
        self.assertTrue(False)