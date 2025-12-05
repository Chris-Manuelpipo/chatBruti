"""
Module de scraping pour Chat-Bruti
Adapté du module NIRD original
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import tiktoken
import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class WebScraper:
    """Scraper de contenu web"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def scrape_url(self, url: str) -> Dict:
        """Scrape une URL et retourne le contenu structuré"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extraction du titre
            title = soup.find('title')
            title = title.get_text().strip() if title else url

            # Nettoyage du HTML
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()

            # Extraction du texte
            text = soup.get_text(separator='\n', strip=True)
            text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())

            logger.info(f"Scraping réussi: {url} - {len(text)} caractères")

            return {
                'url': url,
                'title': title,
                'text': text,
                'scraped_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Erreur scraping {url}: {e}")
            return None

    def scrape_multiple_urls(self, urls: List[str]) -> List[Dict]:
        """Scrape plusieurs URLs"""
        documents = []
        for url in urls:
            doc = self.scrape_url(url)
            if doc:
                documents.append(doc)
        return documents


class TextChunker:
    """Découpe le texte en chunks avec comptage de tokens"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except:
            self.encoding = None
            logger.warning("Tiktoken non disponible, utilisation d'une approximation")

    def count_tokens(self, text: str) -> int:
        """Compte les tokens dans un texte"""
        if self.encoding:
            return len(self.encoding.encode(text))
        else:
            # Approximation: 1 token ≈ 4 caractères
            return len(text) // 4

    def chunk_text(self, text: str, source_url: str, source_title: str) -> List[Dict]:
        """Découpe un texte en chunks"""
        if not text:
            return []

        chunks = []
        paragraphs = text.split('\n\n')
        current_chunk = ""
        chunk_id = 0

        for para in paragraphs:
            if not para.strip():
                continue

            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append({
                        'chunk_id': chunk_id,
                        'text': current_chunk.strip(),
                        'token_count': self.count_tokens(current_chunk),
                        'source_url': source_url,
                        'source_title': source_title
                    })
                    chunk_id += 1

                # Overlap
                current_chunk = para + "\n\n"

        # Dernier chunk
        if current_chunk:
            chunks.append({
                'chunk_id': chunk_id,
                'text': current_chunk.strip(),
                'token_count': self.count_tokens(current_chunk),
                'source_url': source_url,
                'source_title': source_title
            })

        return chunks

    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """Découpe plusieurs documents en chunks"""
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_text(doc['text'], doc['url'], doc['title'])
            all_chunks.extend(chunks)
        return all_chunks


class JSONExporter:
    """Exporte les chunks en JSON"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, chunks: List[Dict], filename: str) -> str:
        """Exporte les chunks en JSON"""
        output_path = self.output_dir / filename

        data = {
            'metadata': {
                'total_chunks': len(chunks),
                'total_tokens': sum(c.get('token_count', 0) for c in chunks),
                'export_date': datetime.now().isoformat()
            },
            'chunks': chunks
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Export réussi: {output_path}")
        return str(output_path)

    def load(self, filename: str) -> Dict:
        """Charge les données depuis JSON"""
        file_path = self.output_dir / filename
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)