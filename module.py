# api_nird.py
# API FastAPI – Recherche sémantique intelligente dans la base NIRD
# Lance avec : uvicorn api_nird:app --reload

import json
import re
import math
from collections import Counter
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict

# ================================================
# 1. Chargement de la base NIRD
# ================================================



with open('larousse_tokens.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

chunks = data["chunks"]

# ================================================
# 2. Moteur sémantique léger (cosine similarity)
# ================================================
def nettoyer_et_vectoriser(texte: str) -> Counter:
    texte = texte.lower()
    mots = re.findall(r'\w+', texte)
    stopwords = {
        "le","la","les","de","du","des","un","une","et","ou","à","au","aux","en","dans",
        "sur","pour","par","avec","sans","sous","chez","ce","cette","ces","son","sa","ses",
        "mon","ma","mes","ton","ta","tes","je","tu","il","elle","nous","vous","ils","elles",
        "qui","que","quoi","dont","où","quand","comment","mais","est","sont","pas","plus","très"
    }
    mots = [m for m in mots if m not in stopwords and len(m) > 2]
    return Counter(mots)

def cosine_similarity(vec1: Counter, vec2: Counter) -> float:
    communs = set(vec1) & set(vec2)
    if not communs:
        return 0.0
    num = sum(vec1[w] * vec2[w] for w in communs)
    den = math.sqrt(sum(v*v for v in vec1.values())) * math.sqrt(sum(v*v for v in vec2.values()))
    return num / den if den != 0 else 0.0

# Pré-calcul des vecteurs (super rapide au démarrage)
print("Indexation sémantique des chunks NIRD...")
vecteurs_chunks = [nettoyer_et_vectoriser(c["text"]) for c in chunks]
print(f"{len(chunks)} chunks indexés – API prête !\n")

# ================================================
# 3. FastAPI
# ================================================
app = FastAPI(
    title="NIRD Semantic Search API",
    description="Recherche intelligente dans la démarche NIRD – retourne le meilleur contexte",
    version="1.0.0"
)

class QuestionRequest(BaseModel):
    question: str

class ReponseNIRD(BaseModel):
    question: str
    contexte: str
    confiance: float
    chunk_id: int
    source_url: str
    source_title: str
    timestamp: str

# ================================================
# 4. Route principale
# ================================================
@app.post("/nird", response_model=ReponseNIRD)
def chercher_dans_nird(payload: QuestionRequest):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question vide")

    vec_q = nettoyer_et_vectoriser(question)

    meilleur_score = 0.0
    meilleur_chunk = None

    mots_forts = ["linux","reconditionnement","nird","primtux","tchap","écologique","libre","inclusif","durable","obsolescence","forge"]

    for i, vec_chunk in enumerate(vecteurs_chunks):
        score = cosine_similarity(vec_q, vec_chunk)
        # Bonus si sujet stratégique
        for mot in mots_forts:
            if mot in question.lower():
                score += 0.18
        if score > meilleur_score:
            meilleur_score = score
            meilleur_chunk = chunks[i]

    # Réponse finale
    if meilleur_score > 0.12:
        texte = meilleur_chunk["text"].strip()
        if len(texte) > 600:
            texte = texte[:600].rsplit(' ', 1)[0] + "..."
        return ReponseNIRD(
            question=question,
            contexte=texte,
            confiance=round(meilleur_score, 3),
            chunk_id=meilleur_chunk["chunk_id"],
            source_url=meilleur_chunk["source_url"],
            source_title=meilleur_chunk["source_title"],
            timestamp=datetime.now().isoformat()
        )
    else:
        return ReponseNIRD(
            question=question,
            contexte="La démarche NIRD promeut un numérique Inclusif, Responsable et Durable dans les établissements scolaires via Linux, le reconditionnement et les logiciels libres.",
            confiance=0.0,
            chunk_id=-1,
            source_url="https://nird.forge.apps.education.fr/",
            source_title="Accueil",
            timestamp=datetime.now().isoformat()
        )

# Page d'accueil sympa
@app.get("/")
def accueil():
    return {
        "message": "NIRD Semantic Search API est en ligne !",
        "utilisation": "POST /nird avec { \"question\": \"votre question\" }",
        "exemple": "curl -X POST http://127.0.0.1:8000/nird -H \"Content-Type: application/json\" -d \"{\\\"question\\\": \\\"comment faire du reconditionnement ?\\\"}\""
    }

