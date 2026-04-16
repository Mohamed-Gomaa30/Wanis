"""
Sentence Buffer for Streaming LLM Output.

Accumulates streaming LLM tokens and yields complete sentences.
This bridges LLM (token stream) and TTS (needs complete sentences).

Supports Arabic and English sentence boundaries.
Handles abbreviations and special cases.

Usage:
    buffer = SentenceBuffer()
    for token in llm_stream:
        sentences = buffer.add(token)
        for sentence in sentences:
            await tts.synthesize(sentence)

    remaining = buffer.flush()
    if remaining:
        await tts.synthesize(remaining)
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SentenceBuffer:
    """
    Accumulates streaming text tokens and yields complete sentences.

    Detects sentence boundaries (. ! ? ؟) and handles:
    - Abbreviations (Dr., Mr., etc.)
    - Arabic punctuation (؟)
    - Decimal numbers (3.14)
    """

    # Common abbreviations that end with periods but aren't sentence endings
    ABBREVIATIONS = {
        # English
        "mr",
        "mrs",
        "ms",
        "dr",
        "prof",
        "sr",
        "jr",
        "st",
        "ave",
        "blvd",
        "rd",
        "jan",
        "feb",
        "mar",
        "apr",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
        "inc",
        "ltd",
        "corp",
        "co",
        "dept",
        "vs",
        "etc",
        "approx",
        "appt",
        "e.g",
        "i.e",
        "a.m",
        "p.m",
    }

    # Arabic sentence terminators
    ARABIC_SENTENCE_END = "؟"

    def __init__(self, min_length: Optional[int] = None):
        """
        Args:
            min_length: Minimum character count before yielding a sentence.
                       Prevents very short fragments.
        """
        if min_length is None:
            from wanis.utils.config import get_value

            min_length = get_value("sentence_buffer", "min_length", 10)

        self.buffer = ""
        self.min_length = min_length

    def add(self, token: str) -> list[str]:
        """
        Add a token to the buffer and return any complete sentences.

        Args:
            token: A text token from the LLM stream

        Returns:
            List of complete sentences (may be empty)
        """
        self.buffer += token
        return self._extract_sentences()

    def flush(self) -> Optional[str]:
        """
        Flush any remaining text in the buffer.

        Call when stream ends to get the final incomplete sentence.

        Returns:
            Remaining text or None if buffer is empty
        """
        remaining = self.buffer.strip()
        self.buffer = ""
        return remaining if remaining else None

    def _extract_sentences(self) -> list[str]:
        """Extract complete sentences from the buffer."""
        sentences = []

        while True:
            # Find potential sentence boundary
            # English: . ! ?
            # Arabic: ؟ (Arabic question mark)
            match = re.search(r'[.!?؟]["\s]', self.buffer)

            if not match:
                # Check for sentence-ending punctuation at end of buffer
                # (followed by nothing yet — wait for next token)
                break

            boundary_pos = match.start() + 1  # Include the punctuation
            candidate = self.buffer[:boundary_pos].strip()

            # Check if this is a real sentence boundary
            if self._is_sentence_boundary(candidate):
                if len(candidate) >= self.min_length:
                    sentences.append(candidate)
                    self.buffer = self.buffer[boundary_pos:].lstrip()
                else:
                    # Too short — keep accumulating
                    break
            else:
                # False positive (abbreviation, number) — skip past it
                # Move past this period and continue searching
                break

        return sentences

    def _is_sentence_boundary(self, text: str) -> bool:
        """Check if the text ending represents a real sentence boundary."""
        if not text:
            return False

        # Get the last word before the punctuation
        words = text.rstrip(".!?؟").rsplit(None, 1)
        if not words:
            return True

        last_word = words[-1].lower().rstrip(".")

        # Check against abbreviations
        if last_word in self.ABBREVIATIONS:
            return False

        # Check for decimal numbers (e.g., "3.14")
        if re.search(r"\d.$", text.rstrip()):
            return False

        return True

    def reset(self) -> None:
        """Clear the buffer."""
        self.buffer = ""

    def peek(self) -> str:
        """Look at current buffer without clearing."""
        return self.buffer

    def has_pending(self) -> bool:
        """Check if there's text in the buffer."""
        return len(self.buffer.strip()) > 0
