import sys
import os
import json
import sqlite3
import re
import cssutils
import socket
import threading
import uuid
import time
from datetime import datetime
from PyQt6.QtCore import QUrl, Qt, QSize, QPoint, QTimer, pyqtSignal, QObject
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLineEdit, QProgressBar,
                           QTabWidget, QMenu, QMenuBar, QToolBar, QStatusBar,
                           QDialog, QLabel, QComboBox, QMessageBox, QListWidget,
                           QSystemTrayIcon, QScrollArea, QFrame, QSizePolicy,
                           QRadioButton, QCheckBox, QFormLayout)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QIcon, QAction, QPalette, QColor, QFont
from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineDownloadRequest

class DownloadManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloads")
        self.setGeometry(300, 300, 400, 300)
        
        layout = QVBoxLayout()
        self.download_list = QListWidget()
        layout.addWidget(self.download_list)
        self.setLayout(layout)
        
        self.downloads = {}
    
    def add_download(self, download):
        filename = download.downloadFileName()
        item = QListWidget.addItem(self.download_list, f"Downloading: {filename}")
        self.downloads[download] = item
        
        download.downloadProgress.connect(
            lambda received, total: self.update_progress(download, received, total))
        download.finished.connect(
            lambda: self.download_finished(download))
    
    def update_progress(self, download, received, total):
        if total > 0:
            progress = int((received / total) * 100)
            self.downloads[download].setText(
                f"Downloading: {download.downloadFileName()} - {progress}%")
    
    def download_finished(self, download):
        self.downloads[download].setText(
            f"Completed: {download.downloadFileName()}")

class BookmarkManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bookmarks")
        self.setGeometry(300, 300, 400, 300)
        
        layout = QVBoxLayout()
        self.bookmark_list = QListWidget()
        layout.addWidget(self.bookmark_list)
        
        self.load_bookmarks()
        self.setLayout(layout)
        
        # Double click to open bookmark
        self.bookmark_list.itemDoubleClicked.connect(self.open_bookmark)
    
    def load_bookmarks(self):
        try:
            with open('bookmarks.json', 'r') as f:
                self.bookmarks = json.load(f)
                for title, url in self.bookmarks.items():
                    self.bookmark_list.addItem(f"{title} - {url}")
        except FileNotFoundError:
            self.bookmarks = {}
    
    def save_bookmarks(self):
        with open('bookmarks.json', 'w') as f:
            json.dump(self.bookmarks, f)
    
    def add_bookmark(self, title, url):
        self.bookmarks[title] = url
        self.bookmark_list.addItem(f"{title} - {url}")
        self.save_bookmarks()
    
    def open_bookmark(self, item):
        url = item.text().split(' - ')[1]
        self.parent().current_tab().setUrl(QUrl(url))
        self.close()

class ThemeManager:
    def __init__(self):
        self.themes = self.load_default_themes()
        self.load_css_themes()
    
    def load_default_themes(self):
        return {
            'Light': {
                'background': '#FFFFFF',
                'foreground': '#000000',
                'accent': '#0078D7',
                'sub': '#808080'
            },
            'Dark': {
                'background': '#2D2D2D',
                'foreground': '#FFFFFF',
                'accent': '#0078D7',
                'sub': '#A0A0A0'
            },
            'Sepia': {
                'background': '#F4ECD8',
                'foreground': '#5B4636',
                'accent': '#8B4513',
                'sub': '#9B7B6B'
            },
            'Blue': {
                'background': '#E8F0FE',
                'foreground': '#202124',
                'accent': '#1A73E8',
                'sub': '#5F6368'
            },
            'Green': {
                'background': '#E6F4EA',
                'foreground': '#202124',
                'accent': '#0F9D58',
                'sub': '#5F6368'
            },
            'Purple': {
                'background': '#F3E5F5',
                'foreground': '#202124',
                'accent': '#9C27B0',
                'sub': '#5F6368'
            },
            'Red': {
                'background': '#FCE4EC',
                'foreground': '#202124',
                'accent': '#DB4437',
                'sub': '#5F6368'
            }
        }
    
    def load_css_themes(self):
        themes_dir = "themes"
        if not os.path.exists(themes_dir):
            return
        
        # Try to load themes from _list.json if it exists
        list_json_path = os.path.join(themes_dir, "_list.json")
        if os.path.exists(list_json_path):
            try:
                with open(list_json_path, 'r') as f:
                    themes_data = json.load(f)
                    
                    # If themes_data is a list of theme objects
                    if isinstance(themes_data, list):
                        for theme in themes_data:
                            if isinstance(theme, dict):
                                theme_name = theme.get('name', '')
                                if theme_name:
                                    # Check for different possible color keys
                                    bg_color = theme.get('bgColor', theme.get('bg', theme.get('background', '#FFFFFF')))
                                    text_color = theme.get('textColor', theme.get('fg', theme.get('foreground', '#000000')))
                                    main_color = theme.get('mainColor', theme.get('accent', '#0078D7'))
                                    sub_color = theme.get('subColor', theme.get('sub', '#808080'))
                                    
                                    self.themes[theme_name] = {
                                        'background': bg_color,
                                        'foreground': text_color,
                                        'accent': main_color,
                                        'sub': sub_color
                                    }
            except Exception as e:
                print(f"Error loading themes from _list.json: {e}")
        
        # Load individual CSS files
        for filename in os.listdir(themes_dir):
            if filename.endswith('.css') and filename != "_list.css":
                theme_name = os.path.splitext(filename)[0].replace('_', ' ').title()
                theme_path = os.path.join(themes_dir, filename)
                
                try:
                    with open(theme_path, 'r') as f:
                        css_content = f.read()
                        
                    # Parse CSS variables
                    root_vars = {}
                    for line in css_content.split('\n'):
                        if '--' in line:
                            var_match = re.match(r'\s*--([^:]+):\s*([^;]+);', line)
                            if var_match:
                                var_name, var_value = var_match.groups()
                                root_vars[var_name.strip()] = var_value.strip()
                    
                    # Map CSS variables to theme colors
                    theme_colors = {
                        'background': root_vars.get('bg-color', root_vars.get('bg', root_vars.get('background', '#FFFFFF'))),
                        'foreground': root_vars.get('text-color', root_vars.get('fg-color', root_vars.get('fg', root_vars.get('foreground', '#000000')))),
                        'accent': root_vars.get('main-color', root_vars.get('accent-color', root_vars.get('accent', '#0078D7'))),
                        'sub': root_vars.get('sub-color', root_vars.get('sub-alt-color', root_vars.get('sub', '#808080')))
                    }
                    
                    self.themes[theme_name] = theme_colors
                except Exception as e:
                    print(f"Error loading theme {filename}: {e}")
    
    def apply_theme(self, window, theme_name):
        theme = self.themes.get(theme_name)
        if not theme:
            return
        
        palette = QPalette()
        
        # Set main colors
        palette.setColor(QPalette.ColorRole.Window, QColor(theme['background']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(theme['foreground']))
        palette.setColor(QPalette.ColorRole.Base, QColor(theme['background']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme['sub']))
        palette.setColor(QPalette.ColorRole.Text, QColor(theme['foreground']))
        
        # Set button colors
        palette.setColor(QPalette.ColorRole.Button, QColor(theme['background']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme['foreground']))
        
        # Set highlight colors
        palette.setColor(QPalette.ColorRole.Highlight, QColor(theme['accent']))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme['background']))
        
        # Set link colors
        palette.setColor(QPalette.ColorRole.Link, QColor(theme['accent']))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(theme['sub']))
        
        window.setPalette(palette)
        
        # Apply theme to all child widgets
        for child in window.findChildren(QWidget):
            child.setPalette(palette)

class BrowserTab(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Use a blank page instead of Google
        self.setUrl(QUrl('about:blank'))
        
        # Enable developer tools
        self.page().setDevToolsPage(self.page())

class SearchTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.browser = parent
        self.setup_ui()
        
        # List of websites to search
        self.websites = [
            {
                'url': 'https://www.python.org',
                'title': 'Python Programming Language',
                'description': 'The official home of the Python Programming Language'
            },
            {
                'url': 'https://www.wikipedia.org',
                'title': 'Wikipedia - The Free Encyclopedia',
                'description': 'The free encyclopedia that anyone can edit'
            },
            {
                'url': 'https://www.github.com',
                'title': 'GitHub: Where the world builds software',
                'description': 'GitHub is where over 100 million developers shape the future of software'
            },
            {
                'url': 'https://www.stackoverflow.com',
                'title': 'Stack Overflow - Where Developers Learn & Share',
                'description': 'Stack Overflow is the largest, most trusted online community for developers'
            },
            {
                'url': 'https://www.reddit.com',
                'title': 'Reddit - Dive into anything',
                'description': 'Reddit is home to thousands of communities, endless conversation, and authentic human connection'
            },
            {
                'url': 'https://www.youtube.com',
                'title': 'YouTube',
                'description': 'Enjoy the videos and music you love, upload original content, and share it all with friends, family, and the world'
            },
            {
                'url': 'https://www.geekparadize.fr',
                'title': 'GeekParadize - Le paradis des Geeks',
                'description': 'Toute l\'actualité Geek, High-Tech, et Gaming'
            },
            {
                'url': 'https://www.amazon.com',
                'title': 'Amazon.com: Online Shopping',
                'description': 'Online shopping from the earth\'s biggest selection'
            },
            {
                'url': 'https://www.netflix.com',
                'title': 'Netflix - Watch TV Shows & Movies',
                'description': 'Watch Netflix movies & TV shows online or stream right to your smart TV'
            },
            {
                'url': 'https://www.spotify.com',
                'title': 'Spotify - Music for Everyone',
                'description': 'Spotify is a digital music service that gives you access to millions of songs'
            },
        ]
        
        # Show all websites initially
        self.show_all_websites()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Search header
        header_widget = QWidget()
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 30)
        
        # Logo
        logo_label = QLabel('Visual Engine')
        logo_font = QFont()
        logo_font.setPointSize(40)
        logo_font.setBold(True)
        logo_label.setFont(logo_font)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("color: #4285F4; margin-bottom: 30px;") # Google blue color
        header_layout.addWidget(logo_label)
        
        # Search box container
        search_container = QWidget()
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)

        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText('Search the web...')
        self.search_box.setMinimumHeight(60)
        self.search_box.setFixedWidth(1200)  # Set fixed width for the search box
        self.search_box.setStyleSheet("""
            QLineEdit {
                border: 1px solid #dfe1e5;
                border-radius: 30px;
                padding: 10px 20px;
                font-size: 18px;
                background-color: rgba(255, 255, 255, 0.1);
            }
            QLineEdit:focus {
                border: 2px solid #4285F4;
                outline: none;
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.search_box.returnPressed.connect(self.perform_search)
        search_layout.addWidget(self.search_box)
        
        # Send button for search
        send_btn = QPushButton()
        send_btn.setIcon(QIcon('svg/send.svg'))
        send_btn.setIconSize(QSize(24, 24))
        send_btn.setFixedSize(40, 40)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        send_btn.clicked.connect(self.perform_search)  # Connect to perform_search
        search_layout.addWidget(send_btn)
        
        search_container.setLayout(search_layout)
        header_layout.addWidget(search_container)
        
        header_widget.setLayout(header_layout)
        layout.addWidget(header_widget)
        
        # Results area
        scroll = QScrollArea()
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(255, 255, 255, 0.1);
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout()
        self.results_layout.setContentsMargins(20, 20, 20, 20)
        self.results_layout.setSpacing(15)
        self.results_widget.setLayout(self.results_layout)
        
        scroll.setWidget(self.results_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # Set initial focus to search box
        self.search_box.setFocus()
    
    def show_all_websites(self):
        # Clear previous results
        for i in reversed(range(self.results_layout.count())): 
            self.results_layout.itemAt(i).widget().setParent(None)
        
        # Create a grid for popular websites
        grid_widget = QWidget()
        grid_layout = QHBoxLayout()
        grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid_layout.setSpacing(30)
        
        # Add the first 8 websites as icons in a grid
        sites_per_row = 4
        row_count = (min(len(self.websites), 8) + sites_per_row - 1) // sites_per_row
        
        for row in range(row_count):
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            row_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row_layout.setSpacing(40)
            
            for col in range(sites_per_row):
                idx = row * sites_per_row + col
                if idx >= min(len(self.websites), 8):
                    break
                    
                site = self.websites[idx]
                site_widget = QWidget()
                site_layout = QVBoxLayout()
                site_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                # Site icon/button
                site_btn = QPushButton()
                site_btn.setFixedSize(100, 100)
                site_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #{hash(site['url']) % 0xFFFFFF:06x};
                        color: white;
                        border-radius: 50px;
                        font-size: 32px;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        border: 3px solid #4285F4;
                    }}
                """)
                site_btn.setText(site['title'][0].upper())
                site_btn.clicked.connect(lambda checked, url=site['url']: self.open_url(url))
                
                # Site name
                site_name = QLabel(site['title'].split(' ')[0])
                site_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
                site_name.setStyleSheet("font-size: 14px; margin-top: 8px;")
                
                site_layout.addWidget(site_btn)
                site_layout.addWidget(site_name)
                site_widget.setLayout(site_layout)
                
                row_layout.addWidget(site_widget)
            
            row_widget.setLayout(row_layout)
            self.results_layout.addWidget(row_widget)
        
        # Add a separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("margin-top: 30px; margin-bottom: 30px;")
        self.results_layout.addWidget(separator)
        
        # Add all websites in a more compact list format
        all_sites_label = QLabel("All Sites")
        all_sites_font = QFont()
        all_sites_font.setPointSize(18)
        all_sites_font.setBold(True)
        all_sites_label.setFont(all_sites_font)
        all_sites_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        all_sites_label.setStyleSheet("color: #5f6368; margin-bottom: 20px;")
        self.results_layout.addWidget(all_sites_label)
        
        # Create a grid for all websites
        sites_grid = QWidget()
        sites_grid_layout = QVBoxLayout()
        
        # Display all websites in a two-column grid
        for i in range(0, len(self.websites), 2):
            row_widget = QWidget()
            row_layout = QHBoxLayout()
            
            # First column
            self.add_compact_result(row_layout, self.websites[i])
            
            # Second column (if available)
            if i + 1 < len(self.websites):
                self.add_compact_result(row_layout, self.websites[i + 1])
            
            row_widget.setLayout(row_layout)
            sites_grid_layout.addWidget(row_widget)
        
        sites_grid.setLayout(sites_grid_layout)
        self.results_layout.addWidget(sites_grid)
    
    def add_compact_result(self, layout, site):
        # Create result container
        result_widget = QFrame()
        result_widget.setFrameStyle(QFrame.Shape.StyledPanel)
        result_widget.setStyleSheet("""
            QFrame {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.05);
                padding: 10px;
                margin: 5px;
            }
            QFrame:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        
        result_layout = QVBoxLayout()
        
        # Title (clickable)
        title_label = QLabel(f'<a href="{site["url"]}" style="text-decoration: none; color: #1a73e8;">{site["title"]}</a>')
        title_label.setTextFormat(Qt.TextFormat.RichText)
        title_label.setOpenExternalLinks(False)  # Handle clicks ourselves
        title_label.linkActivated.connect(self.open_url)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        result_layout.addWidget(title_label)
        
        # URL
        url_label = QLabel(f'<span style="color: #006621;">{site["url"]}</span>')
        url_label.setTextFormat(Qt.TextFormat.RichText)
        result_layout.addWidget(url_label)
        
        # Description
        desc_label = QLabel(site["description"])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("margin-top: 5px;")
        result_layout.addWidget(desc_label)
        
        result_widget.setLayout(result_layout)
        layout.addWidget(result_widget)
    
    def add_result(self, title, url, description):
        # Create result container
        result_widget = QFrame()
        result_widget.setFrameStyle(QFrame.Shape.NoFrame)
        result_layout = QVBoxLayout()
        
        # Title (clickable)
        title_label = QLabel(f'<a href="{url}" style="text-decoration: none; color: #1a0dab;">{title}</a>')
        title_label.setTextFormat(Qt.TextFormat.RichText)
        title_label.setOpenExternalLinks(False)  # Handle clicks ourselves
        title_label.linkActivated.connect(self.open_url)
        title_font = QFont()
        title_font.setPointSize(18)
        title_label.setFont(title_font)
        result_layout.addWidget(title_label)
        
        # URL
        url_label = QLabel(f'<span style="color: #006621;">{url}</span>')
        url_label.setTextFormat(Qt.TextFormat.RichText)
        result_layout.addWidget(url_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        result_layout.addWidget(desc_label)
        
        result_widget.setLayout(result_layout)
        self.results_layout.addWidget(result_widget)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.results_layout.addWidget(separator)
    
    def open_url(self, url):
        # Open URL in the browser
        if self.browser:
            self.browser.navigate_to_url_external(url)
    
    def perform_search(self):
        # Clear previous results
        for i in reversed(range(self.results_layout.count())): 
            self.results_layout.itemAt(i).widget().setParent(None)
        
        query = self.search_box.text().strip().lower()
        if not query:
            self.show_all_websites()
            return
        
        # Add search header
        search_header = QLabel(f'Search results for "{query}"')
        search_header.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 15px;")
        self.results_layout.addWidget(search_header)
        
        # Search through websites
        results = []
        for site in self.websites:
            if (query in site['title'].lower() or 
                query in site['url'].lower() or 
                query in site['description'].lower()):
                results.append(site)
        
        if not results:
            no_results = QLabel('No results found')
            no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_results.setStyleSheet("font-size: 18px; margin: 40px 0;")
            self.results_layout.addWidget(no_results)
            
            # Add suggestions
            suggestions = QLabel('Try searching for:')
            suggestions.setStyleSheet("font-size: 16px; margin-top: 20px;")
            self.results_layout.addWidget(suggestions)
            
            # Add some suggested searches
            suggested_terms = ["python", "programming", "web", "technology", "news"]
            suggestions_layout = QHBoxLayout()
            
            for term in suggested_terms:
                suggestion_btn = QPushButton(term)
                suggestion_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(66, 133, 244, 0.1);
                        color: #4285F4;
                        border: 1px solid #4285F4;
                        border-radius: 15px;
                        padding: 5px 15px;
                        font-size: 14px;
                    }
                    QPushButton:hover {
                        background-color: rgba(66, 133, 244, 0.2);
                    }
                """)
                suggestion_btn.clicked.connect(lambda checked, t=term: self.search_for_term(t))
                suggestions_layout.addWidget(suggestion_btn)
            
            suggestions_container = QWidget()
            suggestions_container.setLayout(suggestions_layout)
            self.results_layout.addWidget(suggestions_container)
            
            return
        
        # Display results count
        results_count = QLabel(f"Found {len(results)} results")
        results_count.setStyleSheet("color: #5f6368; margin-bottom: 20px;")
        self.results_layout.addWidget(results_count)
        
        # Create a grid for search results
        results_grid = QWidget()
        results_grid_layout = QVBoxLayout()
        results_grid_layout.setSpacing(15)
        
        # Display results in a grid
        for site in results:
            result_widget = QFrame()
            result_widget.setFrameStyle(QFrame.Shape.StyledPanel)
            result_widget.setStyleSheet("""
                QFrame {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    background-color: rgba(255, 255, 255, 0.05);
                    padding: 15px;
                    margin: 5px 0;
                }
                QFrame:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-color: #4285F4;
                }
            """)
            
            result_layout = QVBoxLayout()
            
            # Title with highlighted query
            title = site['title']
            highlighted_title = title.replace(query, f'<span style="background-color: rgba(66, 133, 244, 0.2);">{query}</span>') if query in title.lower() else title
            
            title_label = QLabel(f'<a href="{site["url"]}" style="text-decoration: none; color: #1a73e8;">{highlighted_title}</a>')
            title_label.setTextFormat(Qt.TextFormat.RichText)
            title_label.setOpenExternalLinks(False)  # Handle clicks ourselves
            title_label.linkActivated.connect(self.open_url)
            title_font = QFont()
            title_font.setPointSize(16)
            title_font.setBold(True)
            title_label.setFont(title_font)
            result_layout.addWidget(title_label)
            
            # URL with highlighted query
            url = site['url']
            highlighted_url = url.replace(query, f'<span style="background-color: rgba(66, 133, 244, 0.2);">{query}</span>') if query in url.lower() else url
            
            url_label = QLabel(f'<span style="color: #006621;">{highlighted_url}</span>')
            url_label.setTextFormat(Qt.TextFormat.RichText)
            result_layout.addWidget(url_label)
            
            # Description with highlighted query
            description = site['description']
            highlighted_desc = description.replace(query, f'<span style="background-color: rgba(66, 133, 244, 0.2);">{query}</span>') if query in description.lower() else description
            
            desc_label = QLabel(highlighted_desc)
            desc_label.setWordWrap(True)
            desc_label.setTextFormat(Qt.TextFormat.RichText)
            desc_label.setStyleSheet("margin-top: 8px;")
            result_layout.addWidget(desc_label)
            
            # Visit button
            visit_btn = QPushButton("Visit Site")
            visit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4285F4;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 15px;
                    font-size: 14px;
                    max-width: 100px;
                    margin-top: 10px;
                }
                QPushButton:hover {
                    background-color: #3367D6;
                }
            """)
            visit_btn.clicked.connect(lambda checked, url=site['url']: self.open_url(url))
            
            button_container = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.addWidget(visit_btn)
            button_layout.addStretch()
            button_container.setLayout(button_layout)
            
            result_layout.addWidget(button_container)
            
            result_widget.setLayout(result_layout)
            results_grid_layout.addWidget(result_widget)
        
        results_grid.setLayout(results_grid_layout)
        self.results_layout.addWidget(results_grid)
    
    def search_for_term(self, term):
        self.search_box.setText(term)
        self.perform_search()

    def filter_by_hosting(self, hosting_type):
        # Clear previous results
        for i in reversed(range(self.results_layout.count())): 
            self.results_layout.itemAt(i).widget().setParent(None)
        
        # Add header
        header = QLabel(f"{hosting_type.capitalize()} Hosted Services")
        header.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.results_layout.addWidget(header)
        
        # Filter websites based on hosting type
        filtered_sites = []
        
        if hosting_type == "server":
            # Filter for server-hosted sites (example criteria)
            filtered_sites = [site for site in self.websites if 
                             "github" in site["url"].lower() or 
                             "python" in site["url"].lower() or
                             "stackoverflow" in site["url"].lower()]
        else:  # cloud
            # Filter for cloud-hosted sites (example criteria)
            filtered_sites = [site for site in self.websites if 
                             "youtube" in site["url"].lower() or 
                             "netflix" in site["url"].lower() or
                             "spotify" in site["url"].lower() or
                             "amazon" in site["url"].lower()]
        
        if not filtered_sites:
            no_results = QLabel(f'No {hosting_type}-hosted services found')
            no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_results.setStyleSheet("font-size: 18px; margin: 40px 0;")
            self.results_layout.addWidget(no_results)
            return
        
        # Display results count
        results_count = QLabel(f"Found {len(filtered_sites)} {hosting_type}-hosted services")
        results_count.setStyleSheet("color: #5f6368; margin-bottom: 20px;")
        self.results_layout.addWidget(results_count)
        
        # Display results in a grid
        results_grid = QWidget()
        results_grid_layout = QVBoxLayout()
        results_grid_layout.setSpacing(15)
        
        for site in filtered_sites:
            result_widget = QFrame()
            result_widget.setFrameStyle(QFrame.Shape.StyledPanel)
            result_widget.setStyleSheet("""
                QFrame {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    background-color: rgba(255, 255, 255, 0.05);
                    padding: 15px;
                    margin: 5px 0;
                }
                QFrame:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-color: #4285F4;
                }
            """)
            
            result_layout = QVBoxLayout()
            
            # Add hosting badge
            badge_color = "#5865F2" if hosting_type == "server" else "#EB459E"
            badge_icon = "svg/server.svg" if hosting_type == "server" else "svg/cloud.svg"
            
            badge_container = QWidget()
            badge_layout = QHBoxLayout()
            badge_layout.setContentsMargins(0, 0, 0, 0)
            badge_layout.setSpacing(5)
            
            icon_label = QLabel()
            icon = QIcon(badge_icon)
            pixmap = icon.pixmap(QSize(16, 16))
            icon_label.setPixmap(pixmap)
            badge_layout.addWidget(icon_label)
            
            text_label = QLabel(f'{hosting_type.capitalize()}')
            text_label.setStyleSheet(f"color: white; font-weight: bold;")
            badge_layout.addWidget(text_label)
            
            badge_container.setLayout(badge_layout)
            badge_container.setStyleSheet(f"background-color: {badge_color}; border-radius: 10px; padding: 3px 8px;")
            
            result_layout.addWidget(badge_container)
            
            # Title
            title_label = QLabel(f'<a href="{site["url"]}" style="text-decoration: none; color: #1a73e8;">{site["title"]}</a>')
            title_label.setTextFormat(Qt.TextFormat.RichText)
            title_label.setOpenExternalLinks(False)
            title_label.linkActivated.connect(self.open_url)
            title_font = QFont()
            title_font.setPointSize(16)
            title_font.setBold(True)
            title_label.setFont(title_font)
            result_layout.addWidget(title_label)
            
            # URL
            url_label = QLabel(f'<span style="color: #006621;">{site["url"]}</span>')
            url_label.setTextFormat(Qt.TextFormat.RichText)
            result_layout.addWidget(url_label)
            
            # Description
            desc_label = QLabel(site["description"])
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("margin-top: 8px;")
            result_layout.addWidget(desc_label)
            
            # Visit button
            visit_btn = QPushButton("Visit Site")
            visit_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {badge_color};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 5px 15px;
                    font-size: 14px;
                    max-width: 100px;
                    margin-top: 10px;
                }}
                QPushButton:hover {{
                    background-color: {'#4752C4' if hosting_type == "server" else '#C13584'};
                }}
            """)
            visit_btn.clicked.connect(lambda checked, url=site['url']: self.open_url(url))
            
            button_container = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.addWidget(visit_btn)
            button_layout.addStretch()
            button_container.setLayout(button_layout)
            
            result_layout.addWidget(button_container)
            
            result_widget.setLayout(result_layout)
            results_grid_layout.addWidget(result_widget)
        
        results_grid.setLayout(results_grid_layout)
        self.results_layout.addWidget(results_grid)

class P2PNetworkManager(QObject):
    message_received = pyqtSignal(str, str, str)  # username, message, timestamp
    peer_connected = pyqtSignal(str)  # username
    peer_disconnected = pyqtSignal(str)  # username
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.peers = {}  # {username: (ip, port)}
        self.username = f"User_{uuid.uuid4().hex[:8]}"  # Generate random username
        self.listening_socket = None
        self.is_listening = False
        self.listener_thread = None
        self.port = 55555  # Default port
        
    def start_listening(self):
        """Start listening for incoming connections"""
        if self.is_listening:
            return True
            
        try:
            # Try a different port if the default one is in use
            for port in range(self.port, self.port + 10):
                try:
                    self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.listening_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.listening_socket.bind(('0.0.0.0', port))  # Bind to all interfaces
                    self.listening_socket.listen(5)
                    self.port = port
                    self.is_listening = True
                    
                    # Start listener thread
                    self.listener_thread = threading.Thread(target=self._listen_for_connections)
                    self.listener_thread.daemon = True
                    self.listener_thread.start()
                    
                    print(f"P2P listening on port {port}")
                    return True
                except socket.error as e:
                    print(f"Could not bind to port {port}: {e}")
                    if self.listening_socket:
                        self.listening_socket.close()
                    continue
                    
            # If we get here, we couldn't bind to any port
            print("Failed to bind to any port in range")
            return False
        except Exception as e:
            print(f"Error starting P2P listener: {e}")
            return False
    
    def stop_listening(self):
        """Stop listening for connections"""
        self.is_listening = False
        if self.listening_socket:
            try:
                self.listening_socket.close()
            except:
                pass
    
    def _listen_for_connections(self):
        """Thread function to listen for incoming connections"""
        while self.is_listening:
            try:
                client_socket, address = self.listening_socket.accept()
                client_handler = threading.Thread(
                    target=self._handle_client_connection,
                    args=(client_socket, address)
                )
                client_handler.daemon = True
                client_handler.start()
            except Exception as e:
                print(f"Error accepting connection: {e}")
                # Socket closed or error occurred
                break
    
    def _handle_client_connection(self, client_socket, address):
        """Handle incoming client connection"""
        try:
            # Receive initial message with username
            data = client_socket.recv(1024).decode('utf-8')
            if data:
                parts = data.split(':', 1)
                if len(parts) == 2:
                    username, message = parts
                    
                    # Add peer to list if not already there
                    if username not in self.peers:
                        self.peers[username] = (address[0], self.port)
                        self.peer_connected.emit(username)
                    
                    # Process message
                    if message:
                        timestamp = datetime.now().strftime("%H:%M")
                        self.message_received.emit(username, message, timestamp)
                    
                    # Send acknowledgment
                    client_socket.send(f"{self.username}:ACK".encode('utf-8'))
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()
    
    def connect_to_peer(self, ip_address, port=None):
        """Connect to a peer at the given IP address"""
        if port is None:
            port = self.port
            
        try:
            # Create socket and connect
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(5)  # 5 second timeout
            peer_socket.connect((ip_address, port))
            
            # Send initial message with our username
            peer_socket.send(f"{self.username}:HELLO".encode('utf-8'))
            
            # Wait for response
            response = peer_socket.recv(1024).decode('utf-8')
            parts = response.split(':', 1)
            if len(parts) == 2:
                peer_username, _ = parts
                
                # Add peer to list
                self.peers[peer_username] = (ip_address, port)
                self.peer_connected.emit(peer_username)
                
                return True
        except Exception as e:
            print(f"Error connecting to peer: {e}")
            return False
        finally:
            peer_socket.close()
    
    def send_message_to_peer(self, username, message):
        """Send a message to a specific peer"""
        if username not in self.peers:
            return False
            
        ip, port = self.peers[username]
        try:
            # Create socket and connect
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(5)  # 5 second timeout
            peer_socket.connect((ip, port))
            
            # Send message
            peer_socket.send(f"{self.username}:{message}".encode('utf-8'))
            
            # Wait for acknowledgment
            peer_socket.recv(1024)
            return True
        except Exception as e:
            print(f"Error sending message to peer: {e}")
            # Remove peer if we can't connect
            del self.peers[username]
            self.peer_disconnected.emit(username)
            return False
        finally:
            peer_socket.close()
    
    def broadcast_message(self, message):
        """Send a message to all connected peers"""
        for username in list(self.peers.keys()):
            self.send_message_to_peer(username, message)
    
    def set_username(self, username):
        """Set the user's username"""
        self.username = username

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Advanced Python Web Browser')
        self.setGeometry(100, 100, 1280, 800)
        
        # Initialize managers
        self.download_manager = DownloadManager(self)
        self.bookmark_manager = BookmarkManager(self)
        self.theme_manager = ThemeManager()
        
        # Setup UI
        self.setup_ui()
        
        # Initialize history database
        self.setup_history_db()
        
        # Apply default theme
        self.theme_manager.apply_theme(self, 'Light')
        
        # Show the window
        self.show()
    
    def setup_ui(self):
        # Create central widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create toolbar
        self.create_toolbar()
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        layout.addWidget(self.tabs)
        
        # Add initial search tab instead of browser tab
        self.add_search_tab()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Setup system tray
        self.setup_system_tray()
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_tab_action = QAction('New Tab', self)
        new_tab_action.setShortcut('Ctrl+T')
        new_tab_action.triggered.connect(self.add_new_tab)
        file_menu.addAction(new_tab_action)
        
        new_search_tab_action = QAction('New Search Tab', self)
        new_search_tab_action.setShortcut('Ctrl+E')
        new_search_tab_action.triggered.connect(self.add_search_tab)
        file_menu.addAction(new_search_tab_action)
        
        close_tab_action = QAction('Close Tab', self)
        close_tab_action.setShortcut('Ctrl+W')
        close_tab_action.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))
        file_menu.addAction(close_tab_action)
        
        # Bookmarks menu
        bookmarks_menu = menubar.addMenu('Bookmarks')
        
        add_bookmark_action = QAction('Add Bookmark', self)
        add_bookmark_action.setShortcut('Ctrl+D')
        add_bookmark_action.triggered.connect(self.add_current_bookmark)
        bookmarks_menu.addAction(add_bookmark_action)
        
        show_bookmarks_action = QAction('Show Bookmarks', self)
        show_bookmarks_action.setShortcut('Ctrl+B')
        show_bookmarks_action.triggered.connect(self.bookmark_manager.show)
        bookmarks_menu.addAction(show_bookmarks_action)
        
        # History menu
        history_menu = menubar.addMenu('History')
        
        show_history_action = QAction('Show History', self)
        show_history_action.setShortcut('Ctrl+H')
        show_history_action.triggered.connect(self.show_history)
        history_menu.addAction(show_history_action)
        
        clear_history_action = QAction('Clear History', self)
        clear_history_action.triggered.connect(self.clear_history)
        history_menu.addAction(clear_history_action)
        
        # Theme menu with categories
        theme_menu = menubar.addMenu('Theme')
        
        # Group themes by first letter
        theme_groups = {}
        for theme_name in sorted(self.theme_manager.themes.keys()):
            first_letter = theme_name[0].upper()
            if first_letter not in theme_groups:
                theme_groups[first_letter] = []
            theme_groups[first_letter].append(theme_name)
        
        # Create submenus for each group
        for letter in sorted(theme_groups.keys()):
            letter_menu = theme_menu.addMenu(f'{letter}...')
            for theme_name in sorted(theme_groups[letter]):
                theme_action = QAction(theme_name, self)
                theme_action.triggered.connect(
                    lambda checked, tn=theme_name: self.theme_manager.apply_theme(self, tn))
                letter_menu.addAction(theme_action)
        
        # Add theme preview dialog option
        theme_menu.addSeparator()
        preview_action = QAction('Theme Preview', self)
        preview_action.triggered.connect(self.show_theme_preview)
        theme_menu.addAction(preview_action)
    
    def create_toolbar(self):
        nav_toolbar = QToolBar()
        self.addToolBar(nav_toolbar)
        
        # Navigation buttons
        back_btn = QPushButton()
        back_btn.setIcon(QIcon('svg/arrow-left.svg'))
        back_btn.setToolTip("Back")
        back_btn.clicked.connect(self.navigate_back)
        nav_toolbar.addWidget(back_btn)
        
        forward_btn = QPushButton()
        forward_btn.setIcon(QIcon('svg/arrow-right.svg'))
        forward_btn.setToolTip("Forward")
        forward_btn.clicked.connect(self.navigate_forward)
        nav_toolbar.addWidget(forward_btn)
        
        reload_btn = QPushButton()
        reload_btn.setIcon(QIcon('svg/rotate-cw.svg'))
        reload_btn.setToolTip("Reload")
        reload_btn.clicked.connect(self.reload_page)
        nav_toolbar.addWidget(reload_btn)
        
        home_btn = QPushButton()
        home_btn.setIcon(QIcon('svg/home.svg'))
        home_btn.setToolTip("Home")
        home_btn.clicked.connect(self.navigate_home)
        nav_toolbar.addWidget(home_btn)
        
        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        self.url_bar.setMinimumWidth(1200)  # Make the URL bar bigger
        self.url_bar.setStyleSheet("""
            QLineEdit {
                border: 1px solid #dfe1e5;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #4285F4;
            }
        """)
        nav_toolbar.addWidget(self.url_bar)
        
        # Send button for URL bar
        send_btn = QPushButton()
        send_btn.setIcon(QIcon('svg/send.svg'))
        send_btn.setIconSize(QSize(24, 24))
        send_btn.setFixedSize(40, 40)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        send_btn.clicked.connect(self.navigate_to_url)
        nav_toolbar.addWidget(send_btn)
        
        # Discord button next to URL bar
        discord_btn = QPushButton()
        discord_btn.setIcon(QIcon('svg/Discord--Streamline-Iconoir.svg'))
        discord_btn.setIconSize(QSize(24, 24))
        discord_btn.setFixedSize(40, 40)
        discord_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        discord_btn.clicked.connect(self.show_hosting_options)
        nav_toolbar.addWidget(discord_btn)
        
        # Add spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        nav_toolbar.addWidget(spacer)
        
        # Additional buttons
        download_btn = QPushButton()
        download_btn.setIcon(QIcon('svg/download.svg'))
        download_btn.setToolTip("Downloads")
        download_btn.clicked.connect(self.download_manager.show)
        nav_toolbar.addWidget(download_btn)
        
        bookmark_btn = QPushButton()
        bookmark_btn.setIcon(QIcon('svg/paperclip.svg'))
        bookmark_btn.setToolTip("Bookmarks")
        bookmark_btn.clicked.connect(self.bookmark_manager.show)
        nav_toolbar.addWidget(bookmark_btn)
        
        settings_btn = QPushButton()
        settings_btn.setIcon(QIcon('svg/sliders.svg'))
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self.show_settings)
        nav_toolbar.addWidget(settings_btn)
        
        user_btn = QPushButton()
        user_btn.setIcon(QIcon('svg/user.svg'))
        user_btn.setToolTip("User Profile")
        user_btn.clicked.connect(self.show_user_profile)
        nav_toolbar.addWidget(user_btn)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(10)
        self.progress_bar.hide()
        nav_toolbar.addWidget(self.progress_bar)
    
    def setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        
        # Try to load SVG icon, use fallback if file doesn't exist
        icon_path = 'svg/globe.svg'
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Create a simple fallback icon using a blank QIcon
            self.tray_icon.setIcon(QIcon())
        
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
    
    def setup_history_db(self):
        self.conn = sqlite3.connect('browser_history.db')
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS history
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             title TEXT,
             url TEXT,
             timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)
        ''')
        self.conn.commit()
    
    def add_new_tab(self):
        tab = BrowserTab(self)
        index = self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentIndex(index)
        
        tab.titleChanged.connect(
            lambda title: self.update_tab_title(index, title))
        tab.urlChanged.connect(self.update_url)
        tab.loadProgress.connect(self.update_progress)
        tab.loadFinished.connect(lambda: self.add_to_history(tab.title(), tab.url().toString()))
        
        # Setup download handling
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self.handle_download)
    
    def current_tab(self):
        return self.tabs.currentWidget()
    
    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            # If it's the last tab, replace it with a search tab instead of Google
            if isinstance(self.current_tab(), BrowserTab):
                self.tabs.removeTab(0)
                self.add_search_tab()
            else:
                # If it's already a search tab, just refresh it
                self.current_tab().show_all_websites()
    
    def update_tab_title(self, index, title):
        if title:
            self.tabs.setTabText(index, title[:15] + '...' if len(title) > 15 else title)
        else:
            self.tabs.setTabText(index, 'New Tab')
    
    def update_url(self, url):
        self.url_bar.setText(url.toString())
    
    def update_progress(self, progress):
        if progress < 100:
            self.progress_bar.show()
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.hide()
    
    def navigate_to_url(self):
        url = self.url_bar.text()
        
        # Check if it's a search URL
        if url.startswith("mysearch://"):
            # If we're not already on a search tab, switch to one
            if not isinstance(self.current_tab(), SearchTab):
                self.add_search_tab()
            return
            
        # For regular URLs
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # If we're on a search tab, switch to a browser tab
        if isinstance(self.current_tab(), SearchTab):
            self.add_new_tab()
            
        # Now navigate to the URL
        self.current_tab().setUrl(QUrl(url))
    
    def navigate_home(self):
        # Check if current tab is a browser tab
        if isinstance(self.current_tab(), BrowserTab):
            # Close the current tab and open a search tab
            current_index = self.tabs.currentIndex()
            self.tabs.removeTab(current_index)
            self.add_search_tab()
        else:
            # Already on a search tab, just refresh it
            self.current_tab().show_all_websites()
    
    def add_current_bookmark(self):
        url = self.current_tab().url().toString()
        title = self.current_tab().title()
        self.bookmark_manager.add_bookmark(title, url)
        QMessageBox.information(self, "Bookmark Added", 
                              f"Bookmark added:\n{title}")
    
    def handle_download(self, download):
        self.download_manager.add_download(download)
        download.accept()
        self.download_manager.show()
    
    def add_to_history(self, title, url):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO history (title, url)
            VALUES (?, ?)
        ''', (title, url))
        self.conn.commit()
    
    def show_history(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Browser History")
        dialog.setGeometry(300, 300, 600, 400)
        
        layout = QVBoxLayout()
        history_list = QListWidget()
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT title, url, timestamp
            FROM history
            ORDER BY timestamp DESC
            LIMIT 100
        ''')
        
        for title, url, timestamp in cursor.fetchall():
            history_list.addItem(f"{title} - {url}\n{timestamp}")
        
        layout.addWidget(history_list)
        dialog.setLayout(layout)
        
        # Double click to open URL from history
        history_list.itemDoubleClicked.connect(
            lambda item: self.current_tab().setUrl(
                QUrl(item.text().split(' - ')[1].split('\n')[0])))
        
        dialog.exec()
    
    def clear_history(self):
        reply = QMessageBox.question(
            self, "Clear History",
            "Are you sure you want to clear all browsing history?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM history')
            self.conn.commit()
            QMessageBox.information(self, "History Cleared", 
                                  "Your browsing history has been cleared.")
    
    def closeEvent(self, event):
        self.conn.close()
        event.accept()

    def show_theme_preview(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Theme Preview")
        dialog.setGeometry(200, 200, 900, 700)
        
        layout = QVBoxLayout()
        
        # Search and filter section
        filter_widget = QWidget()
        filter_layout = QHBoxLayout()
        
        # Search box
        search_label = QLabel("Search:")
        filter_layout.addWidget(search_label)
        
        search_box = QLineEdit()
        search_box.setPlaceholderText("Search themes...")
        filter_layout.addWidget(search_box)
        
        # Category filter
        category_label = QLabel("Category:")
        filter_layout.addWidget(category_label)
        
        category_combo = QComboBox()
        category_combo.addItem("All")
        
        # Extract categories from theme names
        categories = set()
        for theme_name in self.theme_manager.themes.keys():
            # Try to extract category from theme name (before first space or underscore)
            parts = re.split(r'[ _]', theme_name, 1)
            if len(parts) > 1:
                categories.add(parts[0].capitalize())
        
        # Add categories to combo box
        for category in sorted(categories):
            category_combo.addItem(category)
        
        filter_layout.addWidget(category_combo)
        
        filter_widget.setLayout(filter_layout)
        layout.addWidget(filter_widget)
        
        # Themes grid in a scrollable area
        scroll = QScrollArea()
        container = QWidget()
        grid_layout = QVBoxLayout()
        
        # Create preview widgets for each theme
        theme_widgets = []
        
        # Group themes by first letter for easier navigation
        theme_groups = {}
        for theme_name in sorted(self.theme_manager.themes.keys()):
            first_letter = theme_name[0].upper()
            if first_letter not in theme_groups:
                theme_groups[first_letter] = []
            theme_groups[first_letter].append(theme_name)
        
        # Create section for each letter group
        for letter in sorted(theme_groups.keys()):
            # Letter header
            letter_label = QLabel(f"--- {letter} ---")
            letter_label.setStyleSheet("font-weight: bold; font-size: 16px; margin-top: 10px;")
            letter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid_layout.addWidget(letter_label)
            
            # Add themes for this letter
            for theme_name in theme_groups[letter]:
                theme_colors = self.theme_manager.themes[theme_name]
                
                preview = QWidget()
                preview.setObjectName(f"theme_{theme_name.lower().replace(' ', '_')}")
                preview_layout = QHBoxLayout()
                
                # Color preview
                color_preview = QWidget()
                color_preview.setFixedSize(40, 40)
                color_preview.setAutoFillBackground(True)
                
                # Apply theme background color to preview
                palette = QPalette()
                palette.setColor(QPalette.ColorRole.Window, QColor(theme_colors['background']))
                color_preview.setPalette(palette)
                preview_layout.addWidget(color_preview)

                # Theme name
                name_label = QLabel(theme_name)
                preview_layout.addWidget(name_label)
                preview_layout.addStretch()
                
                # Apply button
                apply_button = QPushButton("Apply")
                apply_button.clicked.connect(
                    lambda checked, tn=theme_name: [
                        self.theme_manager.apply_theme(self, tn),
                        dialog.accept()
                    ])
                
                preview_layout.addWidget(apply_button)
                
                preview.setLayout(preview_layout)
                grid_layout.addWidget(preview)
                
                # Store for filtering
                category = theme_name.split(' ')[0] if ' ' in theme_name else ""
                theme_widgets.append((preview, theme_name, category))
        
        # Add search and category filtering functionality
        def filter_themes():
            search_text = search_box.text().lower()
            selected_category = category_combo.currentText()
            
            for widget, theme_name, category in theme_widgets:
                # Check if theme matches search text
                text_match = search_text in theme_name.lower()
                
                # Check if theme matches selected category
                category_match = (selected_category == "All" or 
                                 (selected_category != "All" and theme_name.lower().startswith(selected_category.lower())))
                
                # Show widget only if both conditions are met
                widget.setVisible(text_match and category_match)
        
        search_box.textChanged.connect(filter_themes)
        category_combo.currentTextChanged.connect(filter_themes)
        
        container.setLayout(grid_layout)
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        dialog.setLayout(layout)
        dialog.exec()

    def add_search_tab(self):
        tab = SearchTab(self)
        index = self.tabs.addTab(tab, "Search")
        self.tabs.setCurrentIndex(index)
    
    def navigate_to_url_external(self, url):
        # First check if we need to create a new tab
        if not isinstance(self.current_tab(), BrowserTab):
            self.add_new_tab()
        
        # Then navigate to the URL
        self.current_tab().setUrl(QUrl(url))
    
    def show_hosting_options(self):
        try:
            # Create a basic dialog window
            dialog = QDialog(self)
            dialog.setWindowTitle("Hosting Options")
            dialog.setGeometry(300, 300, 400, 200)
            
            layout = QVBoxLayout()
            
            # Title
            title_label = QLabel("Choose Hosting Type")
            title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 20px;")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(title_label)
            
            # Hosting options
            options_layout = QHBoxLayout()
            
            # Server hosted option
            server_btn = QPushButton("Server Hosted")
            server_btn.setIcon(QIcon('svg/server.svg'))
            server_btn.setMinimumHeight(60)
            server_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5865F2;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4752C4;
                }
            """)
            server_btn.clicked.connect(lambda: [self.show_lobby_selection("server"), dialog.accept()])
            options_layout.addWidget(server_btn)
            
            # Local hosted option
            local_btn = QPushButton("Local Hosted")
            local_btn.setIcon(QIcon('svg/cloud.svg'))
            local_btn.setMinimumHeight(60)
            local_btn.setStyleSheet("""
                QPushButton {
                    background-color: #EB459E;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 10px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #C13584;
                }
            """)
            local_btn.clicked.connect(lambda: [self.show_lobby_selection("local"), dialog.accept()])
            options_layout.addWidget(local_btn)
            
            layout.addLayout(options_layout)
            
            dialog.setLayout(layout)
            dialog.exec()
        except Exception as e:
            import traceback
            error_message = f"Error showing hosting options: {str(e)}\n\n{traceback.format_exc()}"
            print(error_message)
            
            # Show error dialog
            error_dialog = QMessageBox(self)
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Error")
            error_dialog.setText("An error occurred while showing hosting options:")
            error_dialog.setDetailedText(error_message)
            error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            error_dialog.exec()
    
    def show_lobby_selection(self, hosting_type):
        try:
            # First show a lobby selection dialog
            lobby_dialog = QDialog(self)
            lobby_dialog.setWindowTitle("Choose a Lobby")
            lobby_dialog.setGeometry(300, 300, 400, 300)
            lobby_dialog.setStyleSheet("""
                QDialog {
                    background-color: #17212B;
                }
                QLabel {
                    color: #FFFFFF;
                }
                QPushButton {
                    border: none;
                    border-radius: 5px;
                    padding: 10px;
                    color: white;
                    font-size: 14px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #2B5278;
                }
            """)
            
            lobby_layout = QVBoxLayout()
            
            # Title
            title_label = QLabel("Choose a Lobby Chat")
            title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 20px; color: #FFFFFF;")
            title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lobby_layout.addWidget(title_label)
            
            # Lobby options
            lobbies = [
                {"name": "General Chat", "color": "#4285F4", "icon": "svg/send.svg"},
                {"name": "Tech Support", "color": "#0F9D58", "icon": "svg/send.svg"},
                {"name": "Gaming", "color": "#EA4335", "icon": "svg/send.svg"},
                {"name": "Music", "color": "#FBBC05", "icon": "svg/send.svg"}
            ]
            
            for lobby in lobbies:
                lobby_btn = QPushButton(f"  {lobby['name']}")
                lobby_btn.setIcon(QIcon(lobby['icon']))
                lobby_btn.setMinimumHeight(50)
                lobby_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {lobby['color']};
                        color: white;
                        border-radius: 8px;
                        padding: 10px;
                        font-size: 16px;
                        font-weight: bold;
                        margin-bottom: 10px;
                    }}
                    QPushButton:hover {{
                        background-color: {lobby['color']}CC;
                    }}
                """)
                lobby_btn.clicked.connect(lambda checked, l=lobby['name'], h=hosting_type: 
                                         [self.show_chat_window(l, h), lobby_dialog.accept()])
                lobby_layout.addWidget(lobby_btn)
            
            lobby_dialog.setLayout(lobby_layout)
            lobby_dialog.exec()
        except Exception as e:
            import traceback
            error_message = f"Error showing lobby selection: {str(e)}\n\n{traceback.format_exc()}"
            print(error_message)
            
            # Show error dialog
            error_dialog = QMessageBox(self)
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Error")
            error_dialog.setText("An error occurred while showing lobby selection:")
            error_dialog.setDetailedText(error_message)
            error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            error_dialog.exec()
    
    def show_chat_window(self, lobby_name, hosting_type):
        # Create a Telegram-like dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"P2P Chat - {lobby_name}")
        dialog.setGeometry(300, 300, 800, 600)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #17212B;
            }
            QLabel {
                color: #FFFFFF;
            }
            QPushButton {
                border: none;
                border-radius: 5px;
                padding: 10px;
                color: white;
                font-size: 14px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #2B5278;
            }
        """)
        
        # Initialize P2P network manager if not already done
        if not hasattr(self, 'p2p_manager'):
            self.p2p_manager = P2PNetworkManager(self)
        
        layout = QVBoxLayout()
        
        # Connection status bar
        connection_bar = QWidget()
        connection_layout = QHBoxLayout()
        connection_layout.setContentsMargins(5, 5, 5, 5)
        
        # Status indicator
        status_indicator = QLabel("●")
        status_indicator.setStyleSheet("color: #4CAF50; font-size: 16px;")
        connection_layout.addWidget(status_indicator)
        
        # Status text
        status_text = QLabel(f"P2P Mode - {self.p2p_manager.username}")
        status_text.setStyleSheet("color: #FFFFFF; font-size: 12px;")
        connection_layout.addWidget(status_text)
        
        # User count
        user_count = QLabel("1 user online")
        user_count.setStyleSheet("color: #A0A0A0; font-size: 12px;")
        user_count.setAlignment(Qt.AlignmentFlag.AlignRight)
        connection_layout.addWidget(user_count)
        
        connection_bar.setLayout(connection_layout)
        connection_bar.setStyleSheet("background-color: #0E1621; border-radius: 5px;")
        layout.addWidget(connection_bar)
        
        # P2P connection panel
        p2p_panel = QWidget()
        p2p_layout = QHBoxLayout()
        
        # IP input
        ip_input = QLineEdit()
        ip_input.setPlaceholderText("Enter peer IP address...")
        ip_input.setStyleSheet("""
            QLineEdit {
                background-color: #253340;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
                border: none;
            }
        """)
        p2p_layout.addWidget(ip_input)
        
        # Connect button
        connect_btn = QPushButton("Connect")
        connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B5278;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                font-size: 14px;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #3A6A9E;
            }
        """)
        p2p_layout.addWidget(connect_btn)
        
        # Username input
        username_input = QLineEdit()
        username_input.setPlaceholderText("Change username...")
        username_input.setText(self.p2p_manager.username)
        username_input.setStyleSheet("""
            QLineEdit {
                background-color: #253340;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
                font-size: 14px;
                border: none;
                max-width: 200px;
            }
        """)
        p2p_layout.addWidget(username_input)
        
        # Set username button
        set_username_btn = QPushButton("Set")
        set_username_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B5278;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
                font-size: 14px;
                text-align: center;
                max-width: 50px;
            }
            QPushButton:hover {
                background-color: #3A6A9E;
            }
        """)
        p2p_layout.addWidget(set_username_btn)
        
        p2p_panel.setLayout(p2p_layout)
        layout.addWidget(p2p_panel)
        
        # Telegram-like chat interface
        chat_area = QScrollArea()
        chat_area.setWidgetResizable(True)
        chat_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #17212B;
            }
            QScrollBar:vertical {
                border: none;
                background: #17212B;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #2B5278;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)
        
        chat_widget = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.setSpacing(15)
        
        # System welcome message
        system_msg = QLabel(f"Welcome to the P2P {lobby_name} chat room! Connect directly with other users to discuss {hosting_type} hosting.")
        system_msg.setStyleSheet("""
            background-color: #2B5278;
            color: #FFFFFF;
            border-radius: 10px;
            padding: 10px;
            margin: 5px 50px;
        """)
        system_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chat_layout.addWidget(system_msg)
        
        # IP address info message
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except:
            local_ip = "127.0.0.1"
            
        ip_info_msg = QLabel(f"Your IP address: {local_ip} - Share this with others so they can connect to you")
        ip_info_msg.setStyleSheet("""
            background-color: #0F9D58;
            color: #FFFFFF;
            border-radius: 10px;
            padding: 10px;
            margin: 5px 50px;
        """)
        ip_info_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chat_layout.addWidget(ip_info_msg)
        
        # Main chat interface with user list
        chat_container = QWidget()
        chat_container_layout = QHBoxLayout()
        
        # Chat messages area
        messages_container = QWidget()
        messages_layout = QVBoxLayout()
        messages_layout.setContentsMargins(0, 0, 0, 0)
        messages_layout.setSpacing(15)
        
        # User list (right sidebar)
        users_list = QWidget()
        users_list.setFixedWidth(150)
        users_list.setStyleSheet("background-color: #0E1621;")
        users_layout = QVBoxLayout()
        
        # Online users header
        online_label = QLabel("Online Users")
        online_label.setStyleSheet("color: #FFFFFF; font-weight: bold; margin-bottom: 10px;")
        users_layout.addWidget(online_label)
        
        # Add current user (You)
        your_item = QWidget()
        your_item_layout = QHBoxLayout()
        your_item_layout.setContentsMargins(0, 5, 0, 5)
        
        # User status indicator
        your_status = QLabel("●")
        your_status.setStyleSheet("color: #4CAF50; font-size: 12px;")
        your_item_layout.addWidget(your_status)
        
        # Username
        your_label = QLabel(self.p2p_manager.username + " (You)")
        your_label.setStyleSheet("color: #FFFFFF; font-weight: bold;")
        your_item_layout.addWidget(your_label)
        
        your_item_layout.addStretch()
        your_item.setLayout(your_item_layout)
        users_layout.addWidget(your_item)
        
        # Function to add system message
        def add_system_message(text):
            system_container = QWidget()
            system_layout = QHBoxLayout()
            
            system_text = QLabel(text)
            system_text.setStyleSheet("""
                color: #A0A0A0;
                font-style: italic;
                font-size: 12px;
            """)
            system_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            system_layout.addWidget(system_text)
            
            system_container.setLayout(system_layout)
            messages_layout.insertWidget(messages_layout.count() - 1, system_container)
            
            # Scroll to the bottom
            QTimer.singleShot(100, lambda: chat_area.verticalScrollBar().setValue(
                chat_area.verticalScrollBar().maximum()))
        
        # Function to add peer message
        def add_peer_message(peer_username, message_text, timestamp):
            # Create peer message
            msg_container = QWidget()
            msg_layout = QHBoxLayout()
            msg_layout.setContentsMargins(5, 0, 5, 0)
            
            # User avatar
            avatar = QPushButton(peer_username[0])
            avatar.setFixedSize(40, 40)
            
            # Generate consistent color for user
            import hashlib
            hash_object = hashlib.md5(peer_username.encode())
            hex_dig = hash_object.hexdigest()
            color = f"#{hex_dig[:6]}"
            
            avatar.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border-radius: 20px;
                    font-size: 16px;
                    font-weight: bold;
                }}
            """)
            msg_layout.addWidget(avatar)
            
            # Message content
            content = QWidget()
            content_layout = QVBoxLayout()
            
            # Username
            username_label = QLabel(peer_username)
            username_label.setStyleSheet(f"color: {color}; font-weight: bold;")
            content_layout.addWidget(username_label)
            
            # Message text
            text_label = QLabel(message_text)
            text_label.setWordWrap(True)
            text_label.setStyleSheet("color: #FFFFFF;")
            content_layout.addWidget(text_label)
            
            # Timestamp
            timestamp_label = QLabel(timestamp)
            timestamp_label.setStyleSheet("color: #A0A0A0; font-size: 10px;")
            content_layout.addWidget(timestamp_label)
            
            content.setLayout(content_layout)
            msg_layout.addWidget(content)
            msg_layout.addStretch()
            
            msg_container.setLayout(msg_layout)
            messages_layout.insertWidget(messages_layout.count() - 1, msg_container)
            
            # Scroll to the bottom to show new message
            QTimer.singleShot(100, lambda: chat_area.verticalScrollBar().setValue(
                chat_area.verticalScrollBar().maximum()))
        
        # Function to update username in UI
        def update_username_ui():
            your_label.setText(self.p2p_manager.username + " (You)")
            status_text.setText(f"P2P Mode - {self.p2p_manager.username}")
        
        # Function to set username
        def set_username():
            new_username = username_input.text().strip()
            if new_username:
                self.p2p_manager.set_username(new_username)
                update_username_ui()
                add_system_message("You changed your username to " + new_username)
        
        # Connect set username button
        set_username_btn.clicked.connect(set_username)
        
        # Dictionary to keep track of peer widgets
        peer_widgets = {}
        
        # Function to add peer to UI
        def add_peer_to_ui(username):
            if username in peer_widgets:
                return
            
            # Check if the layout is still valid
            try:
                # Create peer item widget
                peer_item = QWidget()
                peer_item_layout = QHBoxLayout()
                peer_item_layout.setContentsMargins(0, 5, 0, 5)
                
                # User status indicator
                peer_status = QLabel("●")
                peer_status.setStyleSheet("color: #4CAF50; font-size: 12px;")
                peer_item_layout.addWidget(peer_status)
                
                # Username
                peer_label = QLabel(username)
                peer_label.setStyleSheet("color: #FFFFFF;")
                peer_item_layout.addWidget(peer_label)
                
                peer_item_layout.addStretch()
                peer_item.setLayout(peer_item_layout)
                
                # Use QTimer.singleShot to add the widget to the layout in the main thread
                # This helps avoid issues with the layout being deleted
                def safe_add_widget():
                    try:
                        users_layout.addWidget(peer_item)
                        # Store widget reference
                        peer_widgets[username] = peer_item
                        # Update user count
                        user_count.setText(f"{len(peer_widgets) + 1} users online")
                    except RuntimeError:
                        print(f"Failed to add peer {username} to UI: layout has been deleted")
                
                QTimer.singleShot(0, safe_add_widget)
            except Exception as e:
                print(f"Error adding peer {username} to UI: {str(e)}")
        
        # Function to remove peer from UI
        def remove_peer_from_ui(username):
            if username in peer_widgets:
                try:
                    peer_widgets[username].setParent(None)
                    del peer_widgets[username]
                    
                    # Update user count
                    user_count.setText(f"{len(peer_widgets) + 1} users online")
                except RuntimeError:
                    print(f"Failed to remove peer {username} from UI: widget has been deleted")
                except Exception as e:
                    print(f"Error removing peer {username} from UI: {str(e)}")
        
        # Connect to peer function
        def connect_to_peer():
            ip = ip_input.text().strip()
            if ip:
                add_system_message(f"Connecting to {ip}...")
                
                # Try to connect in a separate thread to avoid UI freezing
                def connect_thread():
                    success = self.p2p_manager.connect_to_peer(ip)
                    if success:
                        # Update UI from main thread
                        QTimer.singleShot(0, lambda: add_system_message(f"Connected to peer at {ip}"))
                    else:
                        QTimer.singleShot(0, lambda: add_system_message(f"Failed to connect to {ip}"))
                
                threading.Thread(target=connect_thread).start()
                ip_input.clear()
        
        # Connect button
        connect_btn.clicked.connect(connect_to_peer)
        
        # Connect signals for peer management
        self.p2p_manager.message_received.connect(lambda username, msg: add_peer_message(username, msg))
        self.p2p_manager.peer_connected.connect(lambda username: QTimer.singleShot(0, lambda: add_peer_to_ui(username)))
        self.p2p_manager.peer_connected.connect(lambda username: add_system_message(f"{username} has joined the chat"))
        self.p2p_manager.peer_disconnected.connect(lambda username: QTimer.singleShot(0, lambda: remove_peer_from_ui(username)))
        self.p2p_manager.peer_disconnected.connect(lambda username: add_system_message(f"{username} has left the chat"))
        
        # Start listening for connections
        if not self.p2p_manager.start_listening():
            QMessageBox.warning(self, "Network Error", 
                              "Could not start P2P networking. Chat will be in offline mode.")
        
        users_layout.addStretch()
        users_list.setLayout(users_layout)
        
        # Add spacer to push content to the top
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        messages_layout.addWidget(spacer)
        
        messages_container.setLayout(messages_layout)
        
        # Add messages and users to the panel
        chat_container_layout.addWidget(messages_container)
        chat_container_layout.addWidget(users_list)
        chat_container.setLayout(chat_container_layout)
        
        chat_layout.addWidget(chat_container)
        
        chat_widget.setLayout(chat_layout)
        chat_area.setWidget(chat_widget)
        layout.addWidget(chat_area)
        
        # Message input area
        input_container = QWidget()
        input_layout = QHBoxLayout()
        
        # Add attachment button
        attach_btn = QPushButton()
        attach_btn.setIcon(QIcon('svg/paperclip.svg'))
        attach_btn.setIconSize(QSize(20, 20))
        attach_btn.setFixedSize(40, 40)
        attach_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #253340;
            }
        """)
        input_layout.addWidget(attach_btn)
        
        message_input = QLineEdit()
        message_input.setPlaceholderText("Type a message...")
        message_input.setStyleSheet("""
            QLineEdit {
                background-color: #253340;
                color: white;
                border-radius: 18px;
                padding: 10px 15px;
                font-size: 14px;
                border: none;
            }
        """)
        message_input.setMinimumHeight(40)
        input_layout.addWidget(message_input)
        
        # Add emoji button
        emoji_btn = QPushButton()
        emoji_btn.setIcon(QIcon('svg/smile.svg'))
        emoji_btn.setIconSize(QSize(20, 20))
        emoji_btn.setFixedSize(40, 40)
        emoji_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #253340;
            }
        """)
        input_layout.addWidget(emoji_btn)
        
        send_msg_btn = QPushButton()
        send_msg_btn.setIcon(QIcon('svg/send.svg'))
        send_msg_btn.setIconSize(QSize(20, 20))
        send_msg_btn.setFixedSize(40, 40)
        send_msg_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B5278;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #3A6A9E;
            }
        """)
        
        # Function to add user message to chat
        def add_user_message():
            text = message_input.text().strip()
            if not text:
                return
                
            # Create user message
            msg_container = QWidget()
            msg_layout = QHBoxLayout()
            msg_layout.setContentsMargins(5, 0, 5, 0)
            
            # User avatar
            avatar = QPushButton(self.p2p_manager.username[0])
            avatar.setFixedSize(40, 40)
            avatar.setStyleSheet("""
                QPushButton {
                    background-color: #2B5278;
                    color: white;
                    border-radius: 20px;
                    font-size: 16px;
                    font-weight: bold;
                }
            """)
            msg_layout.addWidget(avatar)
            
            # Message content
            content = QWidget()
            content_layout = QVBoxLayout()
            
            # Username
            username = QLabel(self.p2p_manager.username + " (You)")
            username.setStyleSheet("color: #2B5278; font-weight: bold;")
            content_layout.addWidget(username)
            
            # Message text
            text_label = QLabel(text)
            text_label.setWordWrap(True)
            text_label.setStyleSheet("color: #FFFFFF;")
            content_layout.addWidget(text_label)
            
            # Timestamp
            current_time = datetime.now().strftime("%H:%M")
            timestamp = QLabel(current_time)
            timestamp.setStyleSheet("color: #A0A0A0; font-size: 10px;")
            content_layout.addWidget(timestamp)
            
            content.setLayout(content_layout)
            msg_layout.addWidget(content)
            msg_layout.addStretch()
            
            msg_container.setLayout(msg_layout)
            messages_layout.insertWidget(messages_layout.count() - 1, msg_container)
            
            # Broadcast message to all peers
            self.p2p_manager.broadcast_message(text)
            
            # Clear input
            message_input.clear()
            
            # Update status
            status_text.setText(f"P2P Mode - {self.p2p_manager.username}")
            
            # Scroll to the bottom to show new message
            QTimer.singleShot(100, lambda: chat_area.verticalScrollBar().setValue(
                chat_area.verticalScrollBar().maximum()))
        
        # Connect send button and Enter key
        send_msg_btn.clicked.connect(add_user_message)
        message_input.returnPressed.connect(add_user_message)
        
        input_layout.addWidget(send_msg_btn)
        
        input_container.setLayout(input_layout)
        layout.addWidget(input_container)
        
        # Clean up when dialog closes
        def on_dialog_closed():
            # We don't stop the P2P manager as it might be used in other chat windows
            pass
            
        dialog.finished.connect(on_dialog_closed)
        
        dialog.setLayout(layout)
        dialog.exec()

    def navigate_back(self):
        """Navigate back in the current tab's history"""
        if isinstance(self.current_tab(), BrowserTab):
            self.current_tab().back()
    
    def navigate_forward(self):
        """Navigate forward in the current tab's history"""
        if isinstance(self.current_tab(), BrowserTab):
            self.current_tab().forward()
    
    def reload_page(self):
        """Reload the current tab"""
        if isinstance(self.current_tab(), BrowserTab):
            self.current_tab().reload()
        elif isinstance(self.current_tab(), SearchTab):
            self.current_tab().show_all_websites()

    def tab_changed(self, index):
        """Handle tab change events"""
        current = self.tabs.widget(index)
        
        # Update URL bar based on tab type
        if isinstance(current, BrowserTab):
            self.url_bar.setText(current.url().toString())
        elif isinstance(current, SearchTab):
            self.url_bar.setText("mysearch://home")

    def show_settings(self):
        """Show browser settings dialog"""
        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("Browser Settings")
        settings_dialog.setGeometry(300, 300, 600, 500)
        
        layout = QVBoxLayout()
        
        # Create tabs for different settings categories
        settings_tabs = QTabWidget()
        
        # General settings tab
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        
        # Homepage setting
        homepage_group = QWidget()
        homepage_layout = QHBoxLayout()
        homepage_layout.setContentsMargins(0, 0, 0, 0)
        
        homepage_label = QLabel("Homepage:")
        homepage_layout.addWidget(homepage_label)
        
        homepage_input = QLineEdit("mysearch://home")
        homepage_layout.addWidget(homepage_input)
        
        homepage_group.setLayout(homepage_layout)
        general_layout.addWidget(homepage_group)
        
        # Default search engine
        search_group = QWidget()
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        search_label = QLabel("Default Search Engine:")
        search_layout.addWidget(search_label)
        
        search_combo = QComboBox()
        search_combo.addItems(["Visual Engine", "Google", "Bing", "DuckDuckGo", "Yahoo"])
        search_layout.addWidget(search_combo)
        
        search_group.setLayout(search_layout)
        general_layout.addWidget(search_group)
        
        # Download location
        download_group = QWidget()
        download_layout = QHBoxLayout()
        download_layout.setContentsMargins(0, 0, 0, 0)
        
        download_label = QLabel("Download Location:")
        download_layout.addWidget(download_label)
        
        download_input = QLineEdit(os.path.expanduser("~/Downloads"))
        download_layout.addWidget(download_input)
        
        download_btn = QPushButton("Browse...")
        download_layout.addWidget(download_btn)
        
        download_group.setLayout(download_layout)
        general_layout.addWidget(download_group)
        
        # Startup behavior
        startup_group = QWidget()
        startup_layout = QVBoxLayout()
        startup_layout.setContentsMargins(0, 10, 0, 0)
        
        startup_label = QLabel("On Startup:")
        startup_layout.addWidget(startup_label)
        
        startup_option1 = QRadioButton("Open the homepage")
        startup_option1.setChecked(True)
        startup_layout.addWidget(startup_option1)
        
        startup_option2 = QRadioButton("Open the new tab page")
        startup_layout.addWidget(startup_option2)
        
        startup_option3 = QRadioButton("Continue where I left off")
        startup_layout.addWidget(startup_option3)
        
        startup_group.setLayout(startup_layout)
        general_layout.addWidget(startup_group)
        
        general_layout.addStretch()
        general_tab.setLayout(general_layout)
        
        # Privacy settings tab
        privacy_tab = QWidget()
        privacy_layout = QVBoxLayout()
        
        # Cookies settings
        cookies_group = QWidget()
        cookies_layout = QVBoxLayout()
        cookies_layout.setContentsMargins(0, 0, 0, 0)
        
        cookies_label = QLabel("Cookies:")
        cookies_layout.addWidget(cookies_label)
        
        cookies_option1 = QRadioButton("Allow all cookies")
        cookies_option1.setChecked(True)
        cookies_layout.addWidget(cookies_option1)
        
        cookies_option2 = QRadioButton("Block third-party cookies")
        cookies_layout.addWidget(cookies_option2)
        
        cookies_option3 = QRadioButton("Block all cookies")
        cookies_layout.addWidget(cookies_option3)
        
        cookies_group.setLayout(cookies_layout)
        privacy_layout.addWidget(cookies_group)
        
        # History settings
        history_group = QWidget()
        history_layout = QVBoxLayout()
        history_layout.setContentsMargins(0, 10, 0, 0)
        
        history_label = QLabel("Browsing History:")
        history_layout.addWidget(history_label)
        
        history_option1 = QRadioButton("Keep history")
        history_option1.setChecked(True)
        history_layout.addWidget(history_option1)
        
        history_option2 = QRadioButton("Clear history when browser closes")
        history_layout.addWidget(history_option2)
        
        clear_history_btn = QPushButton("Clear Browsing History...")
        clear_history_btn.clicked.connect(self.clear_history)
        history_layout.addWidget(clear_history_btn)
        
        history_group.setLayout(history_layout)
        privacy_layout.addWidget(history_group)
        
        # Do Not Track
        dnt_checkbox = QCheckBox("Send 'Do Not Track' request with browsing traffic")
        privacy_layout.addWidget(dnt_checkbox)
        
        privacy_layout.addStretch()
        privacy_tab.setLayout(privacy_layout)
        
        # Appearance settings tab
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout()
        
        # Theme settings
        theme_group = QWidget()
        theme_layout = QVBoxLayout()
        theme_layout.setContentsMargins(0, 0, 0, 0)
        
        theme_label = QLabel("Theme:")
        theme_layout.addWidget(theme_label)
        
        theme_combo = QComboBox()
        theme_combo.addItems(sorted(self.theme_manager.themes.keys()))
        theme_combo.setCurrentText("Light")  # Default theme
        theme_combo.currentTextChanged.connect(
            lambda theme_name: self.theme_manager.apply_theme(self, theme_name))
        theme_layout.addWidget(theme_combo)
        
        preview_theme_btn = QPushButton("Preview Themes...")
        preview_theme_btn.clicked.connect(self.show_theme_preview)
        theme_layout.addWidget(preview_theme_btn)
        
        theme_group.setLayout(theme_layout)
        appearance_layout.addWidget(theme_group)
        
        # Font settings
        font_group = QWidget()
        font_layout = QHBoxLayout()
        font_layout.setContentsMargins(0, 10, 0, 0)
        
        font_label = QLabel("Default Font Size:")
        font_layout.addWidget(font_label)
        
        font_size_combo = QComboBox()
        font_size_combo.addItems(["Small (12px)", "Medium (16px)", "Large (20px)", "Very Large (24px)"])
        font_size_combo.setCurrentIndex(1)  # Medium by default
        font_layout.addWidget(font_size_combo)
        
        font_group.setLayout(font_layout)
        appearance_layout.addWidget(font_group)
        
        appearance_layout.addStretch()
        appearance_tab.setLayout(appearance_layout)
        
        # Advanced settings tab
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout()
        
        # JavaScript settings
        js_group = QWidget()
        js_layout = QVBoxLayout()
        js_layout.setContentsMargins(0, 0, 0, 0)
        
        js_label = QLabel("JavaScript:")
        js_layout.addWidget(js_label)
        
        js_option1 = QRadioButton("Allow all sites to run JavaScript (recommended)")
        js_option1.setChecked(True)
        js_layout.addWidget(js_option1)
        
        js_option2 = QRadioButton("Block JavaScript from running on sites")
        js_layout.addWidget(js_option2)
        
        js_group.setLayout(js_layout)
        advanced_layout.addWidget(js_group)
        
        # P2P settings
        p2p_group = QWidget()
        p2p_layout = QVBoxLayout()
        p2p_layout.setContentsMargins(0, 10, 0, 0)
        
        p2p_label = QLabel("P2P Chat Settings:")
        p2p_layout.addWidget(p2p_label)
        
        p2p_port_layout = QHBoxLayout()
        p2p_port_label = QLabel("Default Port:")
        p2p_port_layout.addWidget(p2p_port_label)
        
        p2p_port_input = QLineEdit("55555")
        p2p_port_layout.addWidget(p2p_port_input)
        
        p2p_port_widget = QWidget()
        p2p_port_widget.setLayout(p2p_port_layout)
        p2p_layout.addWidget(p2p_port_widget)
        
        p2p_username_layout = QHBoxLayout()
        p2p_username_label = QLabel("Default Username:")
        p2p_username_layout.addWidget(p2p_username_label)
        
        p2p_username_input = QLineEdit()
        if hasattr(self, 'p2p_manager'):
            p2p_username_input.setText(self.p2p_manager.username)
        else:
            p2p_username_input.setText(f"User_{uuid.uuid4().hex[:8]}")
        p2p_username_layout.addWidget(p2p_username_input)
        
        p2p_username_widget = QWidget()
        p2p_username_widget.setLayout(p2p_username_layout)
        p2p_layout.addWidget(p2p_username_widget)
        
        p2p_group.setLayout(p2p_layout)
        advanced_layout.addWidget(p2p_group)
        
        # Developer tools
        dev_checkbox = QCheckBox("Enable Developer Tools")
        dev_checkbox.setChecked(True)
        advanced_layout.addWidget(dev_checkbox)
        
        advanced_layout.addStretch()
        advanced_tab.setLayout(advanced_layout)
        
        # Add all tabs to the settings tab widget
        settings_tabs.addTab(general_tab, "General")
        settings_tabs.addTab(privacy_tab, "Privacy")
        settings_tabs.addTab(appearance_tab, "Appearance")
        settings_tabs.addTab(advanced_tab, "Advanced")
        
        layout.addWidget(settings_tabs)
        
        # Add buttons at the bottom
        button_layout = QHBoxLayout()
        
        reset_btn = QPushButton("Reset to Default")
        button_layout.addWidget(reset_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(settings_dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(settings_dialog.accept)
        button_layout.addWidget(save_btn)
        
        button_container = QWidget()
        button_container.setLayout(button_layout)
        layout.addWidget(button_container)
        
        settings_dialog.setLayout(layout)
        settings_dialog.exec()
    
    def show_user_profile(self):
        """Show user profile dialog"""
        profile_dialog = QDialog(self)
        profile_dialog.setWindowTitle("User Profile")
        profile_dialog.setGeometry(300, 300, 500, 600)
        
        layout = QVBoxLayout()
        
        # Profile header with avatar
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        
        # Avatar (placeholder)
        avatar_label = QLabel()
        avatar_label.setFixedSize(100, 100)
        avatar_label.setStyleSheet("""
            background-color: #2B5278;
            color: white;
            border-radius: 50px;
            font-size: 36px;
            font-weight: bold;
        """)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setText("U")  # Default first letter
        header_layout.addWidget(avatar_label)
        
        # User info
        user_info = QWidget()
        user_layout = QVBoxLayout()
        
        username_label = QLabel("Username")
        username_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        user_layout.addWidget(username_label)
        
        email_label = QLabel("user@example.com")
        email_label.setStyleSheet("color: #666;")
        user_layout.addWidget(email_label)
        
        edit_profile_btn = QPushButton("Edit Profile")
        edit_profile_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B5278;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #3A6A9E;
            }
        """)
        user_layout.addWidget(edit_profile_btn)
        
        user_info.setLayout(user_layout)
        header_layout.addWidget(user_info)
        
        header_widget.setLayout(header_layout)
        layout.addWidget(header_widget)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Profile details form
        form_widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)
        
        # Personal Information section
        personal_label = QLabel("Personal Information")
        personal_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px;")
        form_layout.addRow(personal_label)
        
        # Full Name
        name_input = QLineEdit("User Name")
        form_layout.addRow("Full Name:", name_input)
        
        # Email
        email_input = QLineEdit("user@example.com")
        form_layout.addRow("Email:", email_input)
        
        # Date of Birth
        dob_input = QLineEdit("01/01/1990")
        form_layout.addRow("Date of Birth:", dob_input)
        
        # Location
        location_input = QLineEdit("City, Country")
        form_layout.addRow("Location:", location_input)
        
        # Account Information section
        account_label = QLabel("Account Information")
        account_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        form_layout.addRow(account_label)
        
        # Username
        username_input = QLineEdit("username")
        form_layout.addRow("Username:", username_input)
        
        # Password
        password_btn = QPushButton("Change Password")
        form_layout.addRow("Password:", password_btn)
        
        # Account created
        created_label = QLabel("January 1, 2023")
        form_layout.addRow("Account Created:", created_label)
        
        # Preferences section
        preferences_label = QLabel("Preferences")
        preferences_label.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 20px;")
        form_layout.addRow(preferences_label)
        
        # Default theme
        theme_combo = QComboBox()
        theme_combo.addItems(sorted(self.theme_manager.themes.keys()))
        theme_combo.setCurrentText("Light")  # Default theme
        form_layout.addRow("Default Theme:", theme_combo)
        
        # Language
        language_combo = QComboBox()
        language_combo.addItems(["English", "Spanish", "French", "German", "Chinese", "Japanese"])
        form_layout.addRow("Language:", language_combo)
        
        # Notifications
        notifications_check = QCheckBox("Enable browser notifications")
        notifications_check.setChecked(True)
        form_layout.addRow("Notifications:", notifications_check)
        
        form_widget.setLayout(form_layout)
        layout.addWidget(form_widget)
        
        # Buttons at the bottom
        button_layout = QHBoxLayout()
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(profile_dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B5278;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #3A6A9E;
            }
        """)
        save_btn.clicked.connect(profile_dialog.accept)
        button_layout.addWidget(save_btn)
        
        button_container = QWidget()
        button_container.setLayout(button_layout)
        layout.addWidget(button_container)
        
        profile_dialog.setLayout(layout)
        profile_dialog.exec()

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        browser = Browser()
        sys.exit(app.exec())
    except Exception as e:
        import traceback
        error_message = f"Error: {str(e)}\n\n{traceback.format_exc()}"
        print(error_message)
        
        # Try to show error dialog
        try:
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Browser Error")
            error_dialog.setText("An error occurred while starting the browser:")
            error_dialog.setDetailedText(error_message)
            error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
            error_dialog.exec()
        except:
            # If we can't show a dialog, at least keep the console open
            input("Press Enter to exit...")