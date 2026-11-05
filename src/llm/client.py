"""Gemini LLM Client wrapper using the official google-genai SDK."""
from typing import Optional, Dict, Any, Tuple
from google import genai
from google.genai import types
from google.genai.errors import APIError
from src.utils.config import settings
from src.utils.logger import logger

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = (api_key or settings.GEMINI_API_KEY or "").strip()
        self.model_name = model_name or settings.GEMINI_MODEL
        self._client: Optional[genai.Client] = None
        self._is_live = False

        if self.api_key and not self.api_key.startswith("your_"):
            try:
                self._client = genai.Client(api_key=self.api_key)
                self._is_live = True
                logger.info(f"Gemini client initialized with model '{self.model_name}'.")
            except Exception as e:
                logger.warning(f"Could not initialize live Gemini client: {e}. Falling back to demo mock mode.")
                self._client = None
                self._is_live = False
        else:
            logger.info("No valid GEMINI_API_KEY configured. Running in high-fidelity Mock/Demo Mode.")

    @property
    def is_live(self) -> bool:
        """Indicates whether a verified live Gemini API connection is available."""
        return self._is_live and self._client is not None

    def test_connection(self) -> Tuple[bool, str]:
        """Tests live API key validity with a lightweight ping."""
        if not self.is_live:
            return False, "GEMINI_API_KEY is not configured or in placeholder state. Operating in Mock/Demo mode."

        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents="Ping. Respond with 'PONG' only.",
                config=types.GenerateContentConfig(max_output_tokens=10)
            )
            text = response.text.strip() if response.text else ""
            return True, f"Live Gemini API Connected: {text}"
        except APIError as api_err:
            return False, f"Gemini API Error: {api_err.message}"
        except Exception as e:
            return False, f"Connection Failed: {str(e)}"

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Generates text using live Gemini API or returns a failure signal if offline.
        """
        if not self.is_live:
            return {
                "success": False,
                "text": "",
                "is_mock": True,
                "error": "No live Gemini API key configured."
            }

        try:
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                system_instruction=system_instruction
            )
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            usage_metadata = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage_metadata = {
                    "prompt_token_count": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "candidates_token_count": getattr(response.usage_metadata, "candidates_token_count", 0),
                    "total_token_count": getattr(response.usage_metadata, "total_token_count", 0),
                }

            return {
                "success": True,
                "text": response.text or "",
                "is_mock": False,
                "model": self.model_name,
                "usage": usage_metadata
            }
        except APIError as api_err:
            logger.error(f"Gemini API error during generation: {api_err}")
            return {
                "success": False,
                "text": "",
                "is_mock": False,
                "error": f"Gemini API Error: {api_err.message}"
            }
        except Exception as err:
            logger.error(f"Unexpected error calling Gemini: {err}")
            return {
                "success": False,
                "text": "",
                "is_mock": False,
                "error": str(err)
            }
