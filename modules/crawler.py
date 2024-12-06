import logging
import os
from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton
from modules.scrapping_thread import ScrapingThread
import pandas as pd

class WebCrawler(QWidget):
    def __init__(self, no_workers, sitemap_url, title = 'Untitled Crawler', pattern = []):
        super().__init__()

        self.visited_links = set()
        self.no_workers = no_workers
        self.unvisited_links = set()
        self.title = title
        self.action_started = False
        self.save_execution = pd.DataFrame(columns=['Links', 'Source'])
        self.pattern = pattern
        if sitemap_url:
            self.initial_sitemap_url = sitemap_url
        else:
            raise ValueError("Sitemap URL is required")

        # Define HEADERS as instance attribute
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

        self.init_ui()

    def init_ui(self):
        """Initialize the UI components."""
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, 400, 400)
        self.setFixedSize(800, 400)

        # Create labels
        self.visited_links_label = QLabel(f"Visited Links: 0")
        self.unvisited_links_label = QLabel(f"Unvisited Links: 0")
        
        # Display number of threads
        self.unique_link = QLabel(f"Unique Links: 0")
        
        # Create labels for each thread status
        self.thread_status = [QLabel(f"Thread {i+1}: Idle") for i in range(self.no_workers)]

        # Create a label to display current status (sitemap parsing, crawling, etc.)
        self.status_label = QLabel("Status: Waiting to start...")

        # Create a grid layout to arrange the widgets
        grid_layout = QGridLayout()
        grid_layout.addWidget(self.visited_links_label, 0, 0)
        grid_layout.addWidget(self.unvisited_links_label, 0, 1)
        grid_layout.addWidget(self.unique_link, 0, 2)

        # Place thread status labels below the above row
        for i, label in enumerate(self.thread_status):
            grid_layout.addWidget(label, i + 1, 0, 1, 3)

        # Place status label at the bottom
        grid_layout.addWidget(self.status_label, len(self.thread_status) + 1, 0, 1, 3)

        # Create start button to initiate the crawler process
        self.start_button = QPushButton('Start Crawling')
        self.start_button.clicked.connect(self.start_crawling)
        grid_layout.addWidget(self.start_button, len(self.thread_status) + 2, 0, 1, 3)

        self.save_button = QPushButton('Save Results')
        self.save_button.clicked.connect(self.save_results)
        grid_layout.addWidget(self.save_button, len(self.thread_status) + 3, 0, 1, 3)

        self.save_complete_button = QPushButton('Export Execution to File')
        self.save_complete_button.clicked.connect(self.save_exec_result)
        grid_layout.addWidget(self.save_complete_button, len(self.thread_status) + 4, 0, 1, 3)

        # Set the layout for the main window
        self.setLayout(grid_layout)
        
    def save_exec_result(self):
        location = os.getcwd()
        self.save_execution.to_csv(f"{location}/logs/execution.csv", index=False)
        self.status_label.setText("Status: Execution saved")
        
    def save_results(self):
        """Save the results to a file."""
        combined = self.visited_links.union(self.unvisited_links)
        combined = list(dict.fromkeys(combined))
        location = os.getcwd()
        with open(f"{location}/results/results.txt", 'w') as f:
            for link in combined:
                f.write(f"{link}\n")
        self.status_label.setText("Status: Results saved to results.txt")
        self.update()

    def start_crawling(self):
        """Start the crawling process."""
        if self.action_started:
            return
        self.status_label.setText("Status: Starting sitemap parsing...")
        self.update_display_info()
        self.action_started = True
        logging.info("Starting sitemap parsing")

        # Start the scraping process in the worker thread
        self.scraping_thread = ScrapingThread(self.initial_sitemap_url, self.thread_status, self.no_workers, self.pattern)
        self.scraping_thread.update_status.connect(self.update_status)
        self.scraping_thread.update_progress.connect(self.update_progress)
        self.scraping_thread.update_thread_status.connect(self.update_thread_status)
        self.scraping_thread.update_results.connect(self.update_local_results)
        self.scraping_thread.update_save_execution.connect(self.update_save_execution)
        self.scraping_thread.start()
        
    def update_save_execution(self, save_execution):
        """Update the save execution with the latest crawling information."""
        self.save_execution = save_execution

    def update_status(self, status):
        """Update the status label in the UI."""
        self.status_label.setText(f"Status: {status}")

    def update_progress(self, visited, unvisited):
        """Update the progress (visited/unvisited links) in the UI."""
        self.visited_links_label.setText(f"Visited Links: {visited}")
        self.unvisited_links_label.setText(f"Unvisited Links: {unvisited}")
        combined = self.visited_links.union(self.unvisited_links)
        combined = list(dict.fromkeys(combined))
        self.unique_link.setText(f"Unique Links: {len(combined)}")
        percent = (visited/(unvisited+visited))*100
        percent = round(percent, 2)
        now = pd.Timestamp.now()
        now = now.strftime("%d-%m-%Y %H:%M:%S")
        self.status_label.setText(f"Status: Crawling links {percent}% completed as of {now} ({visited}/{unvisited+visited})")
        self.update()
        
    def update_local_results(self, visited_links, unvisited_links):
        """Update the local results with the latest crawling information."""
        self.visited_links = visited_links
        self.unvisited_links = unvisited_links

    def update_display_info(self):
        """Update the UI with the latest crawling information."""
        self.visited_links_label.setText(f"Visited Links: {len(self.visited_links)}")
        self.unvisited_links_label.setText(f"Unvisited Links: {len(self.unvisited_links)}")
        self.update()

    def update_thread_status(self, thread_index, status):
        """Update the individual thread status on the UI."""
        self.thread_status[thread_index].setText(f"Thread {thread_index + 1}: {status}")
        self.update()