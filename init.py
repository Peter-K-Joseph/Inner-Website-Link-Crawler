import logging
from modules.crawler import WebCrawler
from PyQt5.QtWidgets import QApplication

logging.basicConfig(filename='./logs/crawler.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
no_workers = 5

if __name__ == '__main__':
    app = QApplication([])
    window = WebCrawler(no_workers, '', title='VHA Crawler', pattern=['vha'])
    window.show()
    app.exec_()