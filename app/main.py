"""
API principale Chat-Bruti
Orchestre le scraping, la recherche sémantique et la génération de réponses
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime
from pathlib import Path

from app.config import (
    API_TITLE, API_VERSION, API_DESCRIPTION,
    NIRD_URL, OUTPUT_FILE, OUTPUT_DIR, CHUNK_SIZE, CHUNK_OVERLAP,
    SIMILARITY_THRESHOLD, MAX_CONTEXT_LENGTH, BOOST_KEYWORDS,
    GROQ_API_KEY, GROQ_MODEL, CHAT_TEMPERATURE, CHAT_MAX_TOKENS,
    CHAT_TOP_P, CHAT_BRUTI_SYSTEM_PROMPT, AUTO_SCRAPE_ON_STARTUP
)
from app.modules.scraper import WebScraper, TextChunker, JSONExporter
from app.modules.semantic_search import SemanticSearch
# from app.modules.chat_generator import ChatBrutiGenerator  # On n'utilise plus la classe
from groq import Groq  # Import direct comme dans votre code original

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialisation FastAPI
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
)

from fastapi.middleware.cors import CORSMiddleware

origins = [
    "*",  # ou ton domaine précis pour plus de sécurité
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# Variables globales
semantic_search: Optional[SemanticSearch] = None
groq_client: Optional[Groq] = None  # Client Groq direct
scraper = WebScraper()
chunker = TextChunker(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
exporter = JSONExporter(output_dir=OUTPUT_DIR)


# ============================================
# Modèles Pydantic
# ============================================

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    question: str
    response: str
    context: str
    confidence: float
    source_url: str
    source_title: str
    timestamp: str

class ScrapeResponse(BaseModel):
    success: bool
    message: str
    total_chunks: int
    total_tokens: int
    output_file: str


# ============================================
# Fonctions utilitaires
# ============================================

def load_or_scrape_data():
    """Charge les données existantes ou lance un scraping"""
    global semantic_search

    data_file = Path(OUTPUT_DIR) / OUTPUT_FILE

    if data_file.exists():
        logger.info(f"Chargement des données depuis {data_file}")
        try:
            data = exporter.load(OUTPUT_FILE)
            chunks = data.get("chunks", [])
            if chunks:
                semantic_search = SemanticSearch(chunks, BOOST_KEYWORDS)
                logger.info(f"✅ {len(chunks)} chunks chargés et indexés")
                return True
        except Exception as e:
            logger.error(f"Erreur chargement: {e}")

    # Si pas de données ou erreur, on scrape
    if AUTO_SCRAPE_ON_STARTUP:
        logger.info("🔄 Scraping initial en cours...")
        return perform_scraping()

    return False


def perform_scraping() -> bool:
    """Effectue le scraping et l'indexation"""
    global semantic_search

    try:
        # Scraping
        logger.info(f"Scraping de {NIRD_URL}")
        documents = scraper.scrape_multiple_urls([NIRD_URL])

        if not documents:
            logger.error("Aucun document scrapé")
            return False

        # Chunking
        chunks = chunker.chunk_documents(documents)
        logger.info(f"Découpage en {len(chunks)} chunks")

        # Export
        exporter.export(chunks, OUTPUT_FILE)

        # Indexation
        semantic_search = SemanticSearch(chunks, BOOST_KEYWORDS)
        logger.info("✅ Scraping et indexation terminés")

        return True

    except Exception as e:
        logger.error(f"Erreur lors du scraping: {e}")
        return False


def initialize_chat_generator():
    """Initialise le client Groq (méthode simple qui fonctionne)"""
    global groq_client

    try:
        # Nettoyer la clé API
        api_key = GROQ_API_KEY.strip().strip('"').strip("'")
        
        if not api_key:
            logger.error("GROQ_API_KEY vide")
            return False
        
        # Initialisation simple comme dans votre code original
        groq_client = Groq(api_key=api_key)
        logger.info("✅ Client Groq initialisé")
        return True
    except Exception as e:
        logger.error(f"Erreur initialisation Groq: {e}")
        return False


# ============================================
# Événements de démarrage
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage de l'API"""
    logger.info("🚀 Démarrage de Chat-Bruti API...")

    # 1. Charger/scraper les données
    if not load_or_scrape_data():
        logger.warning("⚠️ Aucune donnée disponible au démarrage")

    # 2. Initialiser le générateur
    if not initialize_chat_generator():
        logger.warning("⚠️ Générateur non initialisé (vérifier GROQ_API_KEY)")

    logger.info("✅ Chat-Bruti API prête !")


# ============================================
# Routes
# ============================================

@app.get("/")
async def root():
    """Page d'accueil"""
    return {
        "message": "Bienvenue sur Chat-Bruti API 🤪",
        "version": API_VERSION,
        "description": "Le chatbot le plus absurde du web",
        "endpoints": {
            "POST /chat": "Pose une question à Chat-Bruti (tout-en-un)",
            "POST /scrape": "Force un nouveau scraping",
            "POST /search": "Recherche sémantique seule (debug)",
            "GET /stats": "Statistiques sur les données",
            "GET /health": "Statut de l'API",
            "GET /docs": "Documentation interactive"
        }
    }


@app.get("/health")
async def health():
    """Vérifie l'état de l'API"""
    return {
        "status": "healthy",
        "semantic_search_ready": semantic_search is not None,
        "groq_client_ready": groq_client is not None,
        "data_indexed": semantic_search.get_stats() if semantic_search else None
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Route principale: recherche sémantique + génération de réponse

    Flow complet:
    1. Recherche le meilleur contexte
    2. Génère une réponse absurde avec Groq
    3. Retourne tout ça
    """
    try:
        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question vide")

        # 1. Vérifications
        if not semantic_search:
            raise HTTPException(
                status_code=503,
                detail="Service de recherche non disponible. Lancez /scrape d'abord."
            )

        if not groq_client:
            raise HTTPException(
                status_code=503,
                detail="Client Groq non disponible. Vérifiez GROQ_API_KEY."
            )

        # 2. Recherche sémantique
        search_result = semantic_search.search(
            query=question,
            threshold=SIMILARITY_THRESHOLD,
            max_context_length=MAX_CONTEXT_LENGTH
        )

        context = search_result["context"]
        confidence = search_result["confidence"]

        # 3. Génération de réponse avec Groq (méthode simple)
        user_prompt = (
            f"Voici le contexte récupéré de la base de connaissances : {context} ; "
            f"la question de l'utilisateur : {question}\n"
            "Réponds de manière complètement absurde en détournant le contexte !"
        )
        
        completion = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": CHAT_BRUTI_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=CHAT_TEMPERATURE,
            max_tokens=CHAT_MAX_TOKENS,
            top_p=CHAT_TOP_P
        )
        
        response = completion.choices[0].message.content

        # 4. Retour complet
        return ChatResponse(
            question=question,
            response=response,
            context=context,
            confidence=confidence,
            source_url=search_result["source_url"],
            source_title=search_result["source_title"],
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape():
    """Force un nouveau scraping du site NIRD"""
    try:
        success = perform_scraping()

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Échec du scraping"
            )

        stats = semantic_search.get_stats() if semantic_search else {}

        return ScrapeResponse(
            success=True,
            message="Scraping terminé avec succès",
            total_chunks=stats.get("total_chunks", 0),
            total_tokens=0,  # Vous pouvez ajouter ce calcul si besoin
            output_file=str(Path(OUTPUT_DIR) / OUTPUT_FILE)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /scrape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search_only(request: ChatRequest):
    """
    Recherche sémantique seule (pour debug)
    """
    try:
        if not semantic_search:
            raise HTTPException(
                status_code=503,
                detail="Service de recherche non disponible"
            )

        question = request.question.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Question vide")

        result = semantic_search.search(
            query=question,
            threshold=SIMILARITY_THRESHOLD,
            max_context_length=MAX_CONTEXT_LENGTH
        )

        return JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Statistiques sur les données indexées"""
    try:
        if not semantic_search:
            raise HTTPException(
                status_code=404,
                detail="Aucune donnée indexée"
            )

        data_file = Path(OUTPUT_DIR) / OUTPUT_FILE
        data = exporter.load(OUTPUT_FILE)

        return {
            "data_file": str(data_file),
            "metadata": data.get("metadata", {}),
            "search_stats": semantic_search.get_stats(),
            "config": {
                "nird_url": NIRD_URL,
                "chunk_size": CHUNK_SIZE,
                "similarity_threshold": SIMILARITY_THRESHOLD
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur dans /stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)