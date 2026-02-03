#!/usr/bin/env python3
"""
Fetch and parse Medium article content.
Used as a backup when n8n's built-in HTTP node has issues with Medium.
"""

import sys
import json
import re
from urllib.request import urlopen, Request
from html.parser import HTMLParser


class ArticleParser(HTMLParser):
    """Parse article content from Medium HTML."""

    def __init__(self):
        super().__init__()
        self.in_article = False
        self.in_paragraph = False
        self.paragraphs = []
        self.current_text = ""

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "article":
            self.in_article = True
        elif tag == "p" and self.in_article:
            self.in_paragraph = True
            self.current_text = ""

    def handle_endtag(self, tag):
        if tag == "article":
            self.in_article = False
        elif tag == "p" and self.in_paragraph:
            self.in_paragraph = False
            text = self.current_text.strip()
            if text and len(text) > 20:
                self.paragraphs.append(text)

    def handle_data(self, data):
        if self.in_paragraph:
            self.current_text += data


def fetch_article(url: str) -> dict:
    """Fetch and parse a Medium article."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=30) as response:
            html = response.read().decode("utf-8")
    except Exception as e:
        return {"error": str(e), "success": False}

    # Extract title
    title_match = re.search(r"<title>([^<]+)</title>", html)
    title = title_match.group(1) if title_match else "Untitled"
    title = title.split("|")[0].strip()

    # Parse content
    parser = ArticleParser()
    parser.feed(html)

    content = "\n\n".join(parser.paragraphs)
    word_count = len(content.split())

    return {
        "success": True,
        "title": title,
        "content": content,
        "word_count": word_count,
        "url": url,
    }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "URL required", "success": False}))
        sys.exit(1)

    url = sys.argv[1]
    result = fetch_article(url)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
