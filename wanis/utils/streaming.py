from typing import List
import re


class SentenceSplitter:
    """
    Splits streaming text into complete sentences.

    Useful for streaming TTS where we want to start synthesizing
    as soon as a complete sentence is available.
    """

    ARABIC_TERMINATORS = "۔؟۔!"
    ENGLISH_TERMINATORS = ".?!"
    ALL_TERMINATORS = ARABIC_TERMINATORS + ENGLISH_TERMINATORS

    def __init__(self):
        self._buffer = ""

    def feed(self, text: str) -> List[str]:
        """
        Feed text into the splitter and return any complete sentences.

        Args:
            text: New text chunk to process

        Returns:
            List of complete sentences found in the buffer
        """
        if not text:
            return []

        self._buffer += text
        sentences = []

        # Find sentence boundaries
        while True:
            # Find the earliest sentence terminator
            earliest_pos = -1
            for terminator in self.ALL_TERMINATORS:
                pos = self._buffer.find(terminator)
                if pos != -1 and (earliest_pos == -1 or pos < earliest_pos):
                    earliest_pos = pos

            if earliest_pos == -1:
                break

            # Extract sentence including the terminator
            sentence = self._buffer[: earliest_pos + 1].strip()
            if sentence:
                sentences.append(sentence)

            # Remove processed sentence from buffer
            self._buffer = self._buffer[earliest_pos + 1 :].strip()

        return sentences

    def flush(self) -> str:
        """
        Return any remaining text in the buffer.

        Returns:
            Any remaining incomplete sentence, or empty string
        """
        remaining = self._buffer.strip()
        self._buffer = ""
        return remaining

    def reset(self) -> None:
        """Clear the buffer and start fresh."""
        self._buffer = ""
