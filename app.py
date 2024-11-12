import feedparser
from bs4 import BeautifulSoup
import requests
from PIL import Image
from io import BytesIO
from mistralai import Mistral, UserMessage
import os
from pathlib import Path
import logging
from flask import Flask, jsonify, send_file

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NewsletterGenerator:
    def __init__(self, rss_url, api_key, output_dir="newsletter_output"):
        self.rss_url = rss_url
        self.client = Mistral(api_key=api_key)
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(exist_ok=True)
        self.image_dir = self.output_dir / "images"
        self.image_dir.mkdir(exist_ok=True)

    def fetch_rss_feed(self):
        """Fetch and parse the RSS feed."""
        try:
            logger.info("Fetching RSS feed...")
            feed = feedparser.parse(self.rss_url)
            logger.info(f"Feed parsed. Number of entries: {len(feed.entries)}")
            return feed
        except Exception as e:
            logger.error(f"Error fetching RSS feed: {e}")
            raise

    def generate_paragraph(self, title, description=""):
        """Get AI-generated paragraph using Mistral AI."""
        try:
            messages = [
                UserMessage(content=f"Write an engaging, detailed paragraph about the following article to make people want to read it: {title}. {description}")
            ]
            response = self.client.chat.complete(model="mistral-small", messages=messages)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating paragraph: {e}")
            return "Content unavailable."

    def scrape_image_from_article(self, article_url, title):
        """Scrape the first image from the article page."""
        try:
            response = requests.get(article_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            img_tag = soup.find('img')
            if img_tag and img_tag.get('src'):
                img_url = img_tag['src']
                if not img_url.startswith('http'):
                    img_url = requests.compat.urljoin(article_url, img_url)
                return self.download_image(img_url, title)
            else:
                logger.warning("No suitable image found on the article page.")
                return None
        except Exception as e:
            logger.error(f"Error scraping image from article: {e}")
            return None

    def download_image(self, url, title):
        """Download and save image from URL."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            safe_filename = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in title).strip()
            safe_filename = safe_filename[:50]
            image_path = self.image_dir / f"{safe_filename}.jpg"
            img = Image.open(BytesIO(response.content))
            img.save(image_path)
            return image_path
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None

    def generate_newsletter(self):
        """Generate the complete newsletter."""
        feed = self.fetch_rss_feed()
        newsletter_content = "# Today's Top News\n\n"
        processed_entries = 0
        for entry in feed.entries:
            title = entry.title or "Untitled"
            description = entry.get("description", "No description available.")
            logger.info(f"Processing entry: {title}")
            paragraph = self.generate_paragraph(title, description)
            if not paragraph:
                continue
            image_path = self.scrape_image_from_article(entry.link, title)
            newsletter_content += f"## {title}\n\n"
            if image_path:
                relative_path = os.path.relpath(image_path, self.output_dir)
                relative_path = relative_path.replace('\\', '/')
                newsletter_content += f"![{title}]({relative_path})\n\n"
            newsletter_content += f"{paragraph}\n\n"
            newsletter_content += f"[Read more]({entry.link})\n\n---\n\n"
            processed_entries += 1
            if processed_entries >= 5:
                break
        introduction = "Today's newsletter highlights the top 5 news stories that caught our attention. Each story comes with an in-depth, engaging overview and relevant visuals to give you a compelling look into recent developments."
        conclusion = "That's all for today's newsletter. We hope you found the information inspiring and insightful. Stay tuned for more updates tomorrow!"
        newsletter_content = f"{introduction}\n\n{newsletter_content}\n\n{conclusion}"
        return newsletter_content

    def save_newsletter(self, content):
        """Save the newsletter content to a file."""
        try:
            output_file = self.output_dir / "newsletter.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Newsletter saved successfully to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving newsletter: {e}")
            return False

# Flask app
app = Flask(__name__)

# Environment variables and setup
RSS_URL = "https://rss-feed-aggrigator.onrender.com/rss"
API_KEY = os.getenv("MISTRAL_API_KEY")
OUTPUT_DIR = "newsletter_output"

# Initialize the NewsletterGenerator
generator = NewsletterGenerator(RSS_URL, API_KEY, OUTPUT_DIR)

@app.route("/generate-newsletter", methods=["POST"])
def generate_newsletter():
    """Endpoint to generate the newsletter."""
    try:
        content = generator.generate_newsletter()
        saved = generator.save_newsletter(content)
        if saved:
            return jsonify({"message": "Newsletter generated successfully"}), 200
        else:
            return jsonify({"error": "Failed to save the newsletter"}), 500
    except Exception as e:
        logger.error(f"Error generating newsletter: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/download-newsletter", methods=["GET"])
def download_newsletter():
    """Endpoint to download the latest newsletter."""
    try:
        file_path = os.path.join(OUTPUT_DIR, "newsletter.md")
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "Newsletter not found"}), 404
    except Exception as e:
        logger.error(f"Error downloading newsletter: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
