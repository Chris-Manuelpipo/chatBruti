"""
Module de recherche sémantique pour Chat-Bruti
Basé sur la similarité cosinus
"""
import re
import math
from collections import Counter
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SemanticSearch:
    """Moteur de recherche sémantique léger"""

    def __init__(self, chunks: List[Dict], boost_keywords: List[str] = None):
        self.chunks = chunks
        self.boost_keywords = boost_keywords or []
        self.vectors = []
        self.stopwords = {
            "le", "la", "les", "de", "du", "des", "un", "une", "et", "ou", "à", "au", "aux",
            "en", "dans", "sur", "pour", "par", "avec", "sans", "sous", "chez", "ce", "cette",
            "ces", "son", "sa", "ses", "mon", "ma", "mes", "ton", "ta", "tes", "je", "tu",
            "il", "elle", "nous", "vous", "ils", "elles", "qui", "que", "quoi", "dont", "où",
            "quand", "comment", "mais", "est", "sont", "pas", "plus", "très"
        }
        self._index_chunks()

    def _clean_and_vectorize(self, text: str) -> Counter:
        """Nettoie et vectorise un texte"""
        text = text.lower()
        words = re.findall(r'\w+', text)
        words = [w for w in words if w not in self.stopwords and len(w) > 2]
        return Counter(words)

    def _cosine_similarity(self, vec1: Counter, vec2: Counter) -> float:
        """Calcule la similarité cosinus entre deux vecteurs"""
        common = set(vec1) & set(vec2)
        if not common:
            return 0.0

        numerator = sum(vec1[w] * vec2[w] for w in common)
        denominator = (
            math.sqrt(sum(v * v for v in vec1.values())) *
            math.sqrt(sum(v * v for v in vec2.values()))
        )

        return numerator / denominator if denominator != 0 else 0.0

    def _index_chunks(self):
        """Pré-calcule les vecteurs de tous les chunks"""
        logger.info(f"Indexation de {len(self.chunks)} chunks...")
        self.vectors = [self._clean_and_vectorize(chunk["text"]) for chunk in self.chunks]
        logger.info("Indexation terminée")

    def search(
        self,
        query: str,
        threshold: float = 0.12,
        max_context_length: int = 600
    ) -> Optional[Dict]:
        """
        Recherche le meilleur chunk correspondant à la requête

        Args:
            query: Question de l'utilisateur
            threshold: Seuil minimum de similarité
            max_context_length: Longueur max du contexte retourné

        Returns:
            Dict avec contexte, score, chunk_id, source, etc.
        """
        if not query.strip():
            return None

        query_vector = self._clean_and_vectorize(query)
        best_score = 0.0
        best_chunk = None
        best_index = -1

        query_lower = query.lower()

        for i, chunk_vector in enumerate(self.vectors):
            score = self._cosine_similarity(query_vector, chunk_vector)

            # Bonus pour mots-clés stratégiques
            for keyword in self.boost_keywords:
                if keyword in query_lower:
                    score += 0.18

            if score > best_score:
                best_score = score
                best_chunk = self.chunks[i]
                best_index = i

        # Retour du résultat
        if best_score > threshold and best_chunk:
            context = best_chunk["text"].strip()

            # Troncature si nécessaire
            if len(context) > max_context_length:
                context = context[:max_context_length].rsplit(' ', 1)[0] + "..."

            return {
                "context": context,
                "confidence": round(best_score, 3),
                "chunk_id": best_chunk.get("chunk_id", best_index),
                "source_url": best_chunk.get("source_url", ""),
                "source_title": best_chunk.get("source_title", ""),
                "found": True
            }
        else:
            # Contexte par défaut si rien trouvé
            return {
                "context": (
                    "La démarche NIRD promeut un numérique Inclusif, Responsable et Durable "
                    "dans les établissements scolaires via Linux, le reconditionnement et "
                    "les logiciels libres."
                ),
                "confidence": 0.0,
                "chunk_id": -1,
                "source_url": "https://nird.forge.apps.education.fr/",
                "source_title": "Accueil NIRD",
                "found": False
            }

    def get_stats(self) -> Dict:
        """Retourne des statistiques sur l'index"""
        return {
            "total_chunks": len(self.chunks),
            "total_vectors": len(self.vectors),
            "boost_keywords": self.boost_keywords,
            "stopwords_count": len(self.stopwords)
        }