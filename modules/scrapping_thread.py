import os
import requests
from bs4 import BeautifulSoup
import logging
import re
from urllib.parse import urlparse, urljoin
from PyQt5.QtCore import QThread, pyqtSignal
from concurrent.futures import ThreadPoolExecutor
import threading
import pandas as pd

class ScrapingThread(QThread):
    """
    A QThread subclass to handle web scraping in a separate thread.
    Signals:
        update_status (str): Signal to update status messages.
        update_progress (int, int): Signal to update progress (visited, unvisited).
        update_thread_status (int, str): Signal to update individual thread status.
        update_results (set, set): Signal to update results.
        update_save_execution (pd.DataFrame): Signal to update save execution.
    Args:
        initial_sitemap_url (str): The initial sitemap URL to start scraping from.
        thread_status_labels (list): List of thread status labels.
        no_workers (int): Number of worker threads to use.
        pattern (list, optional): List of regex patterns to filter URLs. Defaults to [].
    Methods:
        run():
            Override the run method to perform the scraping.
        save_exec_result():
            Save the execution results to a CSV file.
        save_results():
            Save the results to a text file.
        reset_counts():
            Reset the counts and update thread status labels.
        process_sitemaps(initial_sitemap_url):
            Process the initial sitemap sequentially.
        parse_xml(xml_content):
            Parse sitemap XML content to extract URLs.
        parse_from_links():
            Crawl links in the sitemap using multiple threads.
        parse_links_worker(url, thread_id):
            Worker function to parse links.
        is_a_valid_http_link(url):
            Check if a URL is a valid HTTP link.
        fetch_links(url):
            Fetch and parse links from the given URL.
        is_url_content(url):
            Check if a URL points to valid content.
        clean_url(url):
            Remove hash parameters from a URL.
    """
    update_status = pyqtSignal(str)  # Signal to update status
    update_progress = pyqtSignal(int, int)  # Signal to update progress (visited, unvisited)
    update_thread_status = pyqtSignal(int, str)  # Signal to update individual thread status
    update_results = pyqtSignal(set, set)  # Signal to update results
    update_save_execution = pyqtSignal(pd.DataFrame)  # Signal to update save execution

    def __init__(self, initial_sitemap_url, thread_status_labels, no_workers, pattern = []):
        super().__init__()
        self.no_workers = no_workers
        self.initial_sitemap_url = initial_sitemap_url
        self.visited_links = set()
        self.unvisited_links = set()
        self.save_execution = pd.DataFrame(columns=['Links', 'Source'])
        self.lock = threading.Lock()
        self.pattern = pattern
        self.thread_status_labels = thread_status_labels  # List of thread status labels
        self.HEADERS = {
            'User-Agent': (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/58.0.3029.110 Safari/537.36"
            ),
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': "*/*",
            'Connection': 'keep-alive',
        }

    def run(self):
        """Override the run method to perform the scraping."""
        self.update_status.emit("Starting sitemap parsing...")
        self.process_sitemaps(self.initial_sitemap_url)
        
        self.update_status.emit("Resetting counts...")
        self.reset_counts()

        self.update_status.emit("Crawling links...")
        self.parse_from_links()
        self.update_status.emit("Crawling complete!")
        self.save_exec_result()
        self.update_status.emit("Execution saved to execution.csv")
        self.save_results()
        self.update_status.emit("Results saved to results.txt")
    
    def save_exec_result(self):
        location = os.getcwd()
        self.save_execution.to_csv(f"{location}/logs/execution.csv", index=False)
        self.update_status.emit("Execution saved to execution.csv")
        
    def save_results(self):
        """Save the results to a file."""
        combined = self.visited_links.union(self.unvisited_links)
        combined = list(dict.fromkeys(combined))
        location = os.getcwd()
        with open(f"{location}/results/results.txt", 'w') as f:
            for link in combined:
                f.write(f"{link}\n")
        self.update_status.emit("Results saved to results.txt")
    
    def reset_counts(self):
        self.unvisited_links = self.visited_links
        for label in self.thread_status_labels:
            label.setText("Starting: Thread Ready")
            
        self.visited_links = set()
        self.update_progress.emit(0, len(self.unvisited_links))

    def process_sitemaps(self, initial_sitemap_url):
        """Process the initial sitemap sequentially."""
        self.unvisited_links.add(initial_sitemap_url)
        while self.unvisited_links:
            url = self.unvisited_links.pop()
            if url in self.visited_links:
                continue
            self.visited_links.add(url)

            if 'sitemap.xml' in url:
                logging.info(f"Processing sitemap: {url}")
                self.update_status.emit(f"Parsing sitemap: {url}")
                try:
                    response = requests.get(url, headers=self.HEADERS)
                    response.raise_for_status()
                    new_links = self.parse_xml(response.text)
                    for link in new_links:
                        if link not in self.visited_links:
                            self.unvisited_links.add(link)
                except requests.RequestException as e:
                    logging.error(f"Failed to fetch sitemap {url}: {e}")
                    
    def parse_xml(self, xml_content):
        """Parse sitemap XML content to extract URLs."""
        # Basic XML parsing to find URL entries.
        links = []
        urls = re.findall(r'<loc>(.*?)</loc>', xml_content)
        return urls

    def parse_from_links(self):
        """Crawl links in the sitemap using multiple threads."""
        thread_counter = 0
        with ThreadPoolExecutor(max_workers=self.no_workers) as executor:
            while self.unvisited_links:
                url = self.unvisited_links.pop()
                thread_id = thread_counter % self.no_workers  # Round-robin approach
                self.update_thread_status.emit(thread_id, f"Parsing {url}")
                executor.submit(self.parse_links_worker, url, thread_id)  # Submit task to thread pool
                thread_counter += 1
                self.update_progress.emit(len(self.visited_links), len(self.unvisited_links))
                self.update_results.emit(self.visited_links, self.unvisited_links)

    def parse_links_worker(self, url, thread_id):
        """Worker function to parse links."""
        with self.lock:
            if url in self.visited_links:
                return
            self.visited_links.add(url)

        domain = urlparse(url).netloc
        if self.pattern and not any(re.search(p, domain) for p in self.pattern):
            logging.info(f"Skipping {url} as it is not a valid link")
            self.update_thread_status.emit(thread_id, f"Skipping {url}")  # Update thread status when skipping
            self.unvisited_links.discard(url)
            return

        logging.info(f"Visiting {url}")
        self.update_thread_status.emit(thread_id, f"Visiting {url}")  # Update thread status when visiting
        found_links = self.fetch_links(url)

        with self.lock:
            for link in found_links:
                if link not in self.visited_links and link not in self.unvisited_links and self.is_a_valid_http_link(link):
                    self.unvisited_links.add(link)
                    self.save_execution.loc[len(self.save_execution)] = [link, url]

        self.update_progress.emit(len(self.visited_links), len(self.unvisited_links))
        self.update_save_execution.emit(self.save_execution)
        self.update_thread_status.emit(thread_id, f"Finished {url}")  # Update thread status when done
        
    def is_a_valid_http_link(self, url):
        if url.startswith("mailto:") or url.startswith("tel:"):
            return False
        return url.startswith("http://") or url.startswith("https://")

    def fetch_links(self, url):
        """Fetch and parse links from the given URL."""
        links = []
        try:
            response = requests.get(url, headers=self.HEADERS)
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]
        except requests.RequestException as e:
            logging.error(f"Error fetching {url}: {e}")
        return links
    
    def parse_xml(self, xml_text):
        """Parse XML and extract links from <loc> tags."""
        soup = BeautifulSoup(xml_text, 'lxml-xml')
        links = []
        loc_tags = soup.find_all('loc')
        for loc_tag in loc_tags:
            link = loc_tag.text.strip()
            if self.is_url_content(link):
                link = self.clean_url(link)
                links.append(link)
        return links

    def is_url_content(self, url):
        """Check if a URL points to valid content."""
        invalid_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.ppt', '.pptx', '.xls', '.xlsx')
        invalid_keywords = ('wp-content', 'wp-json', 'wp-login', 'wp-admin', 'wp-includes')

        if url.endswith(invalid_extensions):
            return False
        if any(keyword in url for keyword in invalid_keywords):
            return False
        return True

    def clean_url(self, url):
        """Remove hash parameters from a URL."""
        return url.split('#')[0]