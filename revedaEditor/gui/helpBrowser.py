import re
from pathlib import Path

import PySide6.QtWebEngineWidgets  # noqa: F401
import markdown
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import (QDesktopServices, QAction, QIcon)
from PySide6.QtPrintSupport import (QPrinter, QPrintDialog)
from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget,
                               QTextBrowser, QDialog, QPushButton, QLabel, )


# from revedaEditor.gui.startThread import startThread

class MarkdownViewer(QTextBrowser):
    def __init__(self, basePath="docs"):
        super().__init__()
        self.basePath = Path(basePath)
        self.currentFile = None

        # Enable link clicking
        self.setOpenLinks(False)  # We'll handle links ourselves
        self.anchorClicked.connect(self.handleLinkClick)

        # Load initial file
        self.loadMarkdownFile("index.md")

    def loadMarkdownFile(self, filename):
        """Load a markdown file and render it"""
        try:
            filePath = self.basePath / filename
            filePath = filePath.resolve()  # Resolve to absolute path

            if not filePath.exists():
                self.setHtml(f"<h1>Error</h1><p>File not found: {filename}</p>")
                return

            with open(filePath, "r", encoding="utf-8") as f:
                text = f.read()

            # Convert markdown to HTML
            html = markdown.markdown(text, extensions=[
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code',
                'markdown.extensions.codehilite',
                'markdown.extensions.toc'
            ])

            # Process images to use absolute file paths
            html = self.processImages(html, filePath.parent)

            # Add styling and set base URL for relative links
            styledHtml = self.addStyling(html)

            # Set the HTML content
            self.setHtml(styledHtml)

            # Update current file reference
            self.currentFile = filePath

        except Exception as e:
            self.setHtml(f"<h1>Error</h1><p>Could not load file: {str(e)}</p>")

    def processImages(self, html, baseDir):
        """Process image tags to use absolute file paths"""

        def replaceImageSrc(match):
            imgTag = match.group(0)
            srcMatch = re.search(r'src=["\']([^"\']+)["\']', imgTag)

            if srcMatch:
                src = srcMatch.group(1)

                # Skip if already absolute URL or file path
                if src.startswith(('http://', 'https://', 'file://', '/')):
                    return imgTag

                # Convert relative path to absolute file path
                absPath = baseDir / src
                if absPath.exists():
                    fileUrl = QUrl.fromLocalFile(str(absPath)).toString()
                    return imgTag.replace(srcMatch.group(0), f'src="{fileUrl}"')
                else:
                    print(f"Warning: Image not found: {absPath}")

            return imgTag

        # Replace all img tags
        return re.sub(r'<img[^>]*>', replaceImageSrc, html)

    def handleLinkClick(self, url):
        """Handle clicking on links in the markdown"""
        urlString = url.toString()

        # Check if it's a markdown file link
        if urlString.endswith('.md') or urlString.endswith('.markdown'):
            # Handle relative paths
            if not urlString.startswith('http'):
                # Calculate the full path
                if self.currentFile:
                    # Resolve relative to current file's directory
                    linkPath = (self.currentFile.parent / urlString).resolve()

                    # Check if the target file exists
                    if linkPath.exists() and linkPath.is_relative_to(self.basePath):
                        # Load the new markdown file
                        relativePath = linkPath.relative_to(self.basePath)
                        self.loadMarkdownFile(str(relativePath))
                        return

                # If relative path resolution failed, try from base path
                baseLinkPath = self.basePath / urlString
                if baseLinkPath.exists():
                    self.loadMarkdownFile(urlString)
                    return

        # For external links or non-markdown files, open in default browser
        if urlString.startswith('http'):
            QDesktopServices.openUrl(url)
        else:
            print(f"Could not resolve link: {urlString}")

    def addStyling(self, htmlContent):
        """Add CSS styling to the HTML"""
        return f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    font-size: 12pt;
                    line-height: 1.6;
                    color: #333;
                    max-width: none;
                    margin: 20px;
                    background-color: white;
                }}
                h1, h2, h3, h4, h5, h6 {{
                    color: #2c3e50;
                    margin-top: 12px;
                    margin-bottom: 8px;
                }}
                h1 {{ 
                    border-bottom: 2px solid #eaecef; 
                    padding-bottom: 8px; 
                    font-size: 18pt;
                }}
                h2 {{ 
                    border-bottom: 1px solid #eaecef; 
                    padding-bottom: 6px; 
                    font-size: 14pt;
                }}
                h3 {{ 
                    font-size: 13pt;
                }}
                code {{
                    background-color: #f6f8fa;
                    border-radius: 3px;
                    padding: 2px 4px;
                    font-family: 'Courier New', Consolas, monospace;
                    font-size: 85%;
                    color: #d73a49;
                }}
                pre {{
                    background-color: #f6f8fa;
                    border-radius: 6px;
                    padding: 16px;
                    overflow: auto;
                    line-height: 1.45;
                    border: 1px solid #e1e4e8;
                }}
                pre code {{
                    background-color: transparent;
                    padding: 0;
                    color: #333;
                }}
                blockquote {{
                    border-left: 4px solid #dfe2e5;
                    padding: 0 16px;
                    color: #6a737d;
                    margin: 8px 0;
                    font-style: italic;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 8px 0;
                }}
                th, td {{
                    border: 1px solid #dfe2e5;
                    padding: 8px 12px;
                    text-align: left;
                }}
                th {{
                    background-color: #f6f8fa;
                    font-weight: bold;
                }}
                a {{
                    color: #0366d6;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                    color: #0256cc;
                }}
                ul, ol {{
                    padding-left: 24px;
                    margin: 8px 0;
                }}
                li {{
                    margin: 4px 0;
                }}
                hr {{
                    border: none;
                    border-top: 1px solid #eaecef;
                    margin: 24px 0;
                }}
                p {{
                    margin: 8px 0;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                    margin: 4px 0;
                }}
                figure {{
                    margin: 4px 0;
                }}
                figcaption {{
                    margin: 2px 0;
                }}
            </style>
        </head>
        <body>
            {htmlContent}
        </body>
        </html>
        """


class helpBrowser(QMainWindow):
    def __init__(self, _parent):
        super().__init__(parent=_parent)
        self.appMainW = _parent
        self.setWindowTitle("Revolution EDA Documentation Viewer")
        self.setGeometry(100, 100, 1000, 700)

        # Navigation history
        self.history = []
        self.historyIndex = -1

        # Create toolbar
        toolbar = self.addToolBar("Navigation")

        # Home button
        homeAction = QAction(QIcon(":/icons/home.png"), "Home", self)
        homeAction.triggered.connect(self.goHome)
        toolbar.addAction(homeAction)

        # Back button
        self.backAction = QAction(QIcon(":/icons/arrow-180.png"), "Back", self)
        self.backAction.triggered.connect(self.goBack)
        self.backAction.setEnabled(False)
        toolbar.addAction(self.backAction)
        self.backAction.setToolTip('Go back')

        # Forward button
        self.forwardAtion = QAction(QIcon(":/icons/arrow.png"), "Forward", self)
        self.forwardAtion.triggered.connect(self.goForward)
        self.forwardAtion.setEnabled(False)
        toolbar.addAction(self.forwardAtion)

        toolbar.addSeparator()

        # Print button
        printAction = QAction(QIcon(":/icons/printer--arrow.png"), "Print", self)
        printAction.triggered.connect(self.printDocument)
        toolbar.addAction(printAction)

        # Create central widget
        centralW = QWidget()
        self.setCentralWidget(centralW)
        layout = QVBoxLayout(centralW)

        # Create markdown viewer
        self.markdownViewer = MarkdownViewer("docs")
        self.markdownViewer.anchorClicked.connect(self.handleNavigation)
        layout.addWidget(self.markdownViewer)

        # Add initial page to history
        self.addToHistory("index.md")

    def addToHistory(self, filename):
        """Add a page to navigation history"""
        # Remove forward history if we're not at the end
        if self.historyIndex < len(self.history) - 1:
            self.history = self.history[:self.historyIndex + 1]

        self.history.append(filename)
        self.historyIndex = len(self.history) - 1
        self.updateNavigationButtons()

    def updateNavigationButtons(self):
        """Update the enabled state of navigation buttons"""
        self.backAction.setEnabled(self.historyIndex > 0)
        self.forwardAtion.setEnabled(self.historyIndex < len(self.history) - 1)

    def goHome(self):
        """Navigate to home page"""
        self.markdownViewer.loadMarkdownFile("index.md")
        self.addToHistory("index.md")

    def goBack(self):
        """Navigate back in history"""
        if self.historyIndex > 0:
            self.historyIndex -= 1
            filename = self.history[self.historyIndex]
            self.markdownViewer.loadMarkdownFile(filename)
            self.updateNavigationButtons()

    def goForward(self):
        """Navigate forward in history"""
        if self.historyIndex < len(self.history) - 1:
            self.historyIndex += 1
            filename = self.history[self.historyIndex]
            self.markdownViewer.loadMarkdownFile(filename)
            self.updateNavigationButtons()

    def handleNavigation(self, url):
        """Handle navigation and update history"""
        urlString = url.toString()
        if urlString.endswith('.md') or urlString.endswith('.markdown'):
            self.addToHistory(urlString)
        self.markdownViewer.handleLinkClick(url)

    def printDocument(self):
        """Print the current document"""
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec() == QPrintDialog.Accepted:
            self.markdownViewer.print_(printer)


class aboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("About Revolution EDA")
        self.setGeometry(100, 100, 400, 200)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setMinimumWidth(300)

        layout = QVBoxLayout()

        # Add information about your application using rich text
        aboutLabel = QLabel(
            "<h2>Revolution EDA</h2>"
            "<p><strong>Version:</strong> 0.8.8</p>"
            "<p><strong>Copyright: Revolution Semiconductor</strong> © 2026</p>"
            "<p><strong>License:</strong> Mozilla Public License 2.0 amended with Commons Clause</p>"
            "<p><strong> Website:</strong> <a href='https://reveda.eu'>Revolution EDA</a></p>"
            "<p><strong> GitHub:</strong> "
            "<a href='https://github.com/eskiyerli/revolution-eda'>Revolution "
            "EDA GitHub Repository</a></p>"
        )
        aboutLabel.setOpenExternalLinks(True)  # Allow clickable links
        layout.addWidget(aboutLabel)
        layout.addSpacing(20)

        # Add a "Close" button
        closeButton = QPushButton("Close")
        closeButton.clicked.connect(self.accept)
        layout.addWidget(closeButton)

        self.setLayout(layout)
