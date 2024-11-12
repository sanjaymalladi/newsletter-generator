# -*- coding: utf-8 -*-
import feedparser
from bs4 import BeautifulSoup
import requests
from PIL import Image
from io import BytesIO
from mistralai import Mistral, UserMessage
import sys
import os
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# NewsletterGenerator class code here (copy everything from your class definition)

from flask import Flask, jsonify, send_file

app = Flask(__name__)

# Setup logging in the Flask app
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Instantiate the NewsletterGenerator class
RSS_URL = "https://rss-feed-aggrigator.onrender.com/rss"
API_KEY = os.getenv("MISTRAL_API_KEY")
OUTPUT_DIR = "newsletter_output"

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
