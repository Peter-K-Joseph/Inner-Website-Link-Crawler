import logging
from modules.crawler import WebCrawler
from PyQt5.QtWidgets import QApplication

"""
This script initializes and runs a web crawler application using PyQt5 for the GUI.

Modules:
    logging: Provides logging capabilities.
    WebCrawler: Custom module for web crawling functionality.
    QApplication: PyQt5 module for creating the application.

Constants:
    no_workers (int): Number of worker threads for the web crawler.
    title (str): Title of the web crawler application.
    valid_pattern (list): List of valid patterns for URL matching.
    url (str): The URL to start crawling from.

Usage:
    Run this script directly to start the web crawler application.
"""

logging.basicConfig(filename='./logs/crawler.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
no_workers = 20
title = 'Site Crawler'
valid_pattern = ['https://www.vha.ca']
ignore_pattern = ['https://www.vha.ca/news/', 'https://www.vha.ca/tag/', 'https://www.vha.ca/blog/', 'https://www.vha.ca/\\d+/', 'https://www.vha.ca/recent-news', 'https://www.vha.ca/category', 'wpa-', '.xml', '/data:']

url = 'https://www.vha.ca/sitemap.xml'

if __name__ == '__main__':
    app = QApplication([])
    window = WebCrawler(no_workers, url, title=title, valid_patterns=valid_pattern, ignore_patterns=ignore_pattern)
    window.show()
    app.exec_()