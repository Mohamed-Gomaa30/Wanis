"""
Companion Agent Module – LLM Reasoning with Streaming.

Uses Google Gemini API for conversational AI with streaming token output.
Maintains conversation history for multi-turn dialogue. Designed for
extensibility — swap LLM provider or add tool use without changing the interface.

Usage:
    agent = CompanionAgent(config)
    
    # Streaming response (sentence-by-sentence)
    async for sentence in agent.generate_response("مساء الخير"):
        tts.synthesize(sentence)
    
    # Or get full response
    text = await agent.generate_response_full("مساء الخير")
"""

import os
import logging
from typing import AsyncGenerator
from dataclasses import dataclass, field

from .prompts import get_system_prompt

logger = logging.getLogger(__name__)


@dataclass 
class ConversationTurn:
    """A single turn in the conversation history."""
    role: str       # "user" or "assistant"
    content: str


class CompanionAgent:
    """Wanis AI companion powered by Google Gemini.
    
    Provides streaming LLM responses with sentence-level output
    for the TTS pipeline. Manages conversation history with a
    sliding window.
    
    The agent is designed to be provider-agnostic at the interface level.
    To switch from Gemini to another provider, only the internal
    _call_llm_stream method needs to change.
    
    Attributes:
        config: Agent configuration dict.
        history: List of conversation turns.
        system_prompt: The agent's persona prompt.
    """

    def __init__(self, config: dict):
        """Initialize the companion agent.
        
        Args:
            config: Agent configuration dict with keys:
                - model: Model name (e.g., 'gemini-2.0-flash')
                - max_history_turns: Max conversation turns to keep
                - temperature: LLM temperature
                - max_tokens: Max response tokens
                - language: Response language ('ar' or 'en')
        """
        self.config = config
        self.model_name = config.get("model", "gemini-2.0-flash")
        self.max_history = config.get("max_history_turns", 10)
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 512)
        self.language = config.get("language", "ar")
        
        self.history: list[ConversationTurn] = []
        self.system_prompt = get_system_prompt(self.language)
        self._client = None
    
    def initialize(self):
        """Initialize the Gemini client. Call once at startup.
        
        Requires GEMINI_API_KEY environment variable to be set.
        """
        from google import genai
        
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY or GOOGLE_API_KEY environment variable must be set"
            )
        
        self._client = genai.Client(api_key=api_key)
        logger.info(f"Gemini client initialized with model: {self.model_name}")

    async def generate_response(self, user_text: str) -> AsyncGenerator[str, None]:
        """Generate a streaming response to user input, yielding sentences.
        
        Sends user text to Gemini, streams back tokens, and yields
        complete sentences as they're formed. Each yielded sentence
        is ready for TTS synthesis.
        
        Args:
            user_text: The user's transcribed speech.
            
        Yields:
            Complete sentences from the agent's response.
        """
        if self._client is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        # Add user turn to history
        self._add_to_history("user", user_text)
        
        # Build the conversation messages
        contents = self._build_contents()
        
        # Import sentence splitter
        from ..utils.streaming import SentenceSplitter
        splitter = SentenceSplitter()
        
        full_response = ""
        
        try:
            # Stream tokens from Gemini
            response = self._client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config={
                    "temperature": self.temperature,
                    "max_output_tokens": self.max_tokens,
                    "system_instruction": self.system_prompt,
                }
            )
            
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    
                    # Split into sentences
                    sentences = splitter.feed(chunk.text)
                    for sentence in sentences:
                        yield sentence
            
            # Flush any remaining text
            remaining = splitter.flush()
            if remaining:
                yield remaining
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            error_msg = "معلش، حصل مشكلة. ممكن تعيد تاني؟" if self.language == "ar" else "Sorry, something went wrong."
            full_response = error_msg
            yield error_msg
        
        # Add assistant response to history
        self._add_to_history("assistant", full_response)
    
    async def generate_response_full(self, user_text: str) -> str:
        """Generate a full (non-streaming) response.
        
        Convenience method that collects all sentences into a single string.
        
        Args:
            user_text: The user's transcribed speech.
            
        Returns:
            Complete response text.
        """
        sentences = []
        async for sentence in self.generate_response(user_text):
            sentences.append(sentence)
        return " ".join(sentences)
    
    def _build_contents(self) -> list[dict]:
        """Build the message list for the Gemini API.
        
        Constructs the conversation history in the format expected
        by the Gemini SDK.
        
        Returns:
            List of content dicts with 'role' and 'parts'.
        """
        contents = []
        for turn in self.history:
            contents.append({
                "role": "user" if turn.role == "user" else "model",
                "parts": [{"text": turn.content}],
            })
        return contents
    
    def _add_to_history(self, role: str, content: str):
        """Add a turn to conversation history, maintaining window size.
        
        Args:
            role: 'user' or 'assistant'.
            content: The text content of the turn.
        """
        self.history.append(ConversationTurn(role=role, content=content))
        
        # Trim history to max turns (each turn = 1 entry)
        max_entries = self.max_history * 2  # user + assistant pairs
        if len(self.history) > max_entries:
            self.history = self.history[-max_entries:]
    
    def clear_history(self):
        """Clear the conversation history."""
        self.history = []
        logger.info("Conversation history cleared")
    
    @property
    def is_initialized(self) -> bool:
        """Check if the agent is initialized."""
        return self._client is not None
