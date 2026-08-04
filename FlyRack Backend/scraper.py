import time
import json
import logging
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, HttpUrl, Field

# --- CONFIGURATION & PROFESSIONALISM ---
BASE_URL = "https://quotes.toscrape.com/"  # Standard practice site
USER_AGENT = "MyWorkshopRAGBot/1.0 (+http://yourdomain.com/contact; student-project)"
REQUEST_DELAY = 1.0  # Politeness delay (in seconds) between requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# --- 1. RESPECT LAYER (Robots.txt & Rate Limits) ---
class PolitenessManager:
    def __init__(self, base_url: str, user_agent: str, delay: float = 1.0):
        self.base_url = base_url
        self.user_agent = user_agent
        self.delay = delay
        self.last_request_time = 0
        self.rp = RobotFileParser()
        
        # Load robots.txt
        robots_url = urljoin(self.base_url, "/robots.txt")
        self.rp.set_url(robots_url)
        try:
            self.rp.read()
            logging.info(f"Loaded robots.txt from {robots_url}")
        except Exception as e:
            logging.warning(f"Could not read robots.txt ({e}). Defaulting to cautious crawling.")

    def can_fetch(self, url: str) -> bool:
        """Check if robots.txt allows fetching this URL."""
        return self.rp.can_fetch(self.user_agent, url)

    def wait(self):
        """Enforce rate limiting between HTTP requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request_time = time.time()


# --- 5. DATA STRUCTURE LAYER (Pydantic Schema) ---
class ScrapedItem(BaseModel):
    quote: str
    author: str
    tags: list[str]
    source_url: str


# --- MAIN PIPELINE CLASS ---
class RespectfulScraper:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.politeness = PolitenessManager(base_url, USER_AGENT, delay=REQUEST_DELAY)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    # --- 2. FETCH LAYER ---
    def fetch_page(self, url: str) -> str | None:
        if not self.politeness.can_fetch(url):
            logging.warning(f"BLOCKED by robots.txt: {url}")
            return None

        self.politeness.wait()
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            logging.info(f"Successfully fetched (HTTP {response.status_code}): {url}")
            return response.text
        except requests.RequestException as e:
            logging.error(f"Failed to fetch {url}: {e}")
            return None

    # --- 3 & 4. PARSE, EXTRACT & CLEAN LAYER ---
    def parse_and_extract(self, html_content: str, current_url: str) -> tuple[list[ScrapedItem], list[str]]:
        soup = BeautifulSoup(html_content, "html.parser")
        items: list[ScrapedItem] = []
        next_urls: list[str] = []

        # Extract items from page
        quote_elements = soup.select(".quote")
        for q in quote_elements:
            # Extract raw fields
            text_raw = q.select_one(".text").get_text(strip=True) if q.select_one(".text") else ""
            author_raw = q.select_one(".author").get_text(strip=True) if q.select_one(".author") else ""
            tags_raw = [t.get_text(strip=True) for t in q.select(".tag")]

            # Clean fields (strip quotes, whitespace normalization)
            cleaned_quote = text_raw.strip("“ ”\"'")
            cleaned_author = author_raw.strip()

            item = ScrapedItem(
                quote=cleaned_quote,
                author=cleaned_author,
                tags=tags_raw,
                source_url=current_url
            )
            items.append(item)

        # Pagination: Discover next page link
        next_button = soup.select_one("li.next > a")
        if next_button and next_button.get("href"):
            next_url = urljoin(current_url, next_button["href"])
            next_urls.append(next_url)

        return items, next_urls

    # --- RUNNER ---
    def run(self, start_url: str, max_pages: int = 5) -> list[dict]:
        to_visit = [start_url]
        visited = set()
        all_records = []

        while to_visit and len(visited) < max_pages:
            url = to_visit.pop(0)
            if url in visited:
                continue

            visited.add(url)
            html = self.fetch_page(url)
            if not html:
                continue

            records, next_pages = self.parse_and_extract(html, url)
            all_records.extend([r.model_dump() for r in records])

            for next_page in next_pages:
                if next_page not in visited:
                    to_visit.append(next_page)

        return all_records


# --- EXECUTION & EXPORT ---
if __name__ == "__main__":
    scraper = RespectfulScraper(BASE_URL)
    results = scraper.run(BASE_URL, max_pages=3)

    # Save structured dataset for next week's RAG pipeline
    output_filename = "rag_corpus.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Scraping Complete! Saved {len(results)} structured records to '{output_filename}'.")