"""
Configuration centralisée pour Chat-Bruti
"""
import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# API Configuration
API_TITLE = "Chat-Bruti API"
API_VERSION = "1.0.0"
API_DESCRIPTION = "Chatbot absurde avec recherche sémantique NIRD"

# Scraping Configuration
NIRD_URL = "https://nird.forge.apps.education.fr/"
OUTPUT_FILE = "nird_chunks.json"
OUTPUT_DIR = str(DATA_DIR)
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Semantic Search Configuration
SIMILARITY_THRESHOLD = 0.12
MAX_CONTEXT_LENGTH = 600
BOOST_KEYWORDS = [
    "linux", "reconditionnement", "nird", "primtux", "tchap",
    "écologique", "libre", "inclusif", "durable", "obsolescence", "forge"
]

# Chat-Bruti Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
print("cle :",GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"
CHAT_TEMPERATURE = 1.5
CHAT_MAX_TOKENS = 200
CHAT_TOP_P = 0.95

# Prompt système Chat-Bruti
CHAT_BRUTI_SYSTEM_PROMPT = """
Tu es Chat-Bruti, un chatbot volontairement con.
Tu ne réponds jamais directement à la question.
Tu exagères, tu inventes, tu oublies.
Tu fais de l'humour.
Tu te prends pour un philosophe du dimanche.
Les figures de style et les jeux de mots sont tes meilleurs amis.
Ta réponse doit être courte, inutile, mais drôle.
Appuie-toi très vaguement sur le contexte ci-dessous, mais détourne-le complètement.
Utilise des mots comme waouh, yeahh, oups, dans tes réponses
"""

# Scraping au démarrage
AUTO_SCRAPE_ON_STARTUP = True
SCRAPE_INTERVAL_HOURS = 24  # Optionnel: pour mise à jour périodique