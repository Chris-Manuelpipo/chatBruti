"""
Module de génération de réponses Chat-Bruti
Utilise Groq pour générer des réponses absurdes
"""
from groq import Groq
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class ChatBrutiGenerator:
    """Générateur de réponses Chat-Bruti avec Groq"""

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        system_prompt: str = "",
        temperature: float = 1.5,
        max_tokens: int = 200,
        top_p: float = 0.95
    ):
        if not api_key:
            raise ValueError("GROQ_API_KEY est requis")

        self.client = Groq(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p

        logger.info(f"Chat-Bruti Generator initialisé avec modèle: {model}")

    def generate_response(self, context: str, question: str) -> str:
        """
        Génère une réponse Chat-Bruti

        Args:
            context: Contexte récupéré par la recherche sémantique
            question: Question de l'utilisateur

        Returns:
            Réponse absurde et drôle
        """
        try:
            user_prompt = (
                f"Voici le contexte récupéré de la base de connaissances : {context} ; "
                f"la question de l'utilisateur : {question}\n"
                "Réponds de manière complètement absurde en détournant le contexte !"
            )

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p
            )

            answer = completion.choices[0].message.content
            logger.info(f"Réponse générée: {len(answer)} caractères")

            return answer

        except Exception as e:
            logger.error(f"Erreur lors de la génération: {e}")
            # Réponse de fallback en cas d'erreur
            return (
                "Oups ! Mon cerveau a planté plus vite qu'un Windows 95. "
                "Réessaye, ou pas, je m'en fiche un peu en vrai. Yeahh ! 🤪"
            )

    def test_connection(self) -> bool:
        """Teste la connexion à l'API Groq"""
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            logger.info("Connexion Groq OK")
            return True
        except Exception as e:
            logger.error(f"Erreur connexion Groq: {e}")
            return False