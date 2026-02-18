"""
Companion Agent Module – LLM Reasoning with Streaming.

Uses Google Gemini API for conversational AI with streaming token output.
Maintains conversation history for multi-turn dialogue. Designed for
extensibility — swap LLM provider or add tool use without changing the interface.

Usage:
    agent = CompanionAgent(config)
    
    # Streaming response (sentence-by-sentence)
    async for sentence in agent.generate_response("مساء الخير", fall_flag=False):
        tts.synthesize(sentence)
    
    # Or get full response
    text = await agent.generate_response_full("مساء الخير")
"""

import os
import asyncio
import logging
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

from .prompts import get_system_prompt

logger = logging.getLogger(__name__)


@dataclass 
class ConversationTurn:
    """A single turn in the conversation history, supporting multi-part messages."""
    role: str      
    content: str   
    parts: list = None 


class CompanionAgent:
    """Wanis AI companion powered by Google Gemini.
    
    Provides streaming LLM responses with sentence-level output
    for the TTS pipeline. Manages conversation history with a
    sliding window.
    
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
        self.model_name = config.get("model", "gemini-3-flash-preview")
        # User requested last 3 sentences/turns to keep track
        self.max_history = config.get("max_history_turns", 3)
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 512)
        self.language = config.get("language", "ar")
        
        self.history: list[ConversationTurn] = []
        
        # New: Use ContextManager for daily context
        from ..core.context_manager import context_manager
        self.context_manager = context_manager
        
        # New: Use MemoryManager for long-term memory
        from ..core.memory import MemoryManager
        profile_path = os.path.join(os.path.dirname(__file__), "../data/user_profile.json")
        self.memory_manager = MemoryManager(profile_path)
        
        self._base_prompt = get_system_prompt(self.language)
        self._client = None
    
    def initialize(self):
        """Initialize the Gemini client. Call once at startup.
        
        Requires GEMINI_API_KEY environment variable to be set.
        """
        from google import genai
        
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
        except:
            raise ValueError(
                "GEMINI_API_KEY environment variable must be set"
            )
        
        self._client = genai.Client(api_key=api_key)
        logger.info(f"Gemini client initialized with model: {self.model_name}")

    async def generate_response(
        self, 
        user_text: str, 
        fall_flag: bool = False,
        health_status: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response to user input, yielding sentences.
        
        Args:
            user_text: The user's transcribed speech.
            fall_flag: Safety signal. If True, triggers emergency protocol.
            health_status: Optional dictionary representing health status.
            
        Yields:
            Complete sentences from the agent's response.
        """
        if self._client is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        # 1. Build dynamic system prompt
        daily_context = self.context_manager.get_context_summary()
        # Memory retrieval is now agentic (via tool) to save quota.
        # We only inject static context by default.
        static_context = self.memory_manager.static.get_summary()
        
        current_system_prompt = (
            f"{self._base_prompt}\n\n"
            f"## Context of the Day:\n{daily_context}\n\n"
            f"## User Profile (Static):\n{static_context}\n"
        )
        
        if fall_flag:
            logger.critical("Fall detected! Switching to Emergency Protocol.")
            if self.language == "ar":
                emergency_instruction = "\n\nتنبيه: لقد سقط المستخدم! يجب عليك تفعيل بروتوكول الطوارئ فوراً. اسأل المستخدم هل هو بخير وتصرف بجدية."
            else:
                emergency_instruction = "\n\nALERT: USER HAS FALLEN! ACTIVATE EMERGENCY PROTOCOL IMMEDIATELY. Ask if they are okay and act seriously."
            
            current_system_prompt += emergency_instruction

        # 2. Add user turn to history (unless it's a bracketed system simulation message)
        if user_text:
            if not (user_text.startswith("[System:") and user_text.endswith("]")):
                self._add_to_history("user", user_text)
            else:
                logger.debug(f"Skipping history storage for system query: {user_text}")
        
        # 3. Build contents as a simple string for single-turn, or list for multi-turn
        contents = self._build_contents(health_status)
        
        # Import sentence splitter
        from ..utils.streaming import SentenceSplitter
        splitter = SentenceSplitter()
        
        full_response = ""
        
        # build mapping
        from .tools import TOOLS
        tool_map = {func.__name__: func for func in TOOLS}
        
        # Max turns for tool usage to prevent infinite loops
        max_tool_turns = 5
        current_turn_count = 0
        
        full_response_text = ""
        
        try:
            from google.genai import types as genai_types
            
            # Initial Loop (User Input -> Model)
            # We might need to loop if the model calls a tool
            
            while current_turn_count < max_tool_turns:
                current_turn_count += 1
                               # Implement Retry logic for the ENTIRE turn (creation + consumption)
                max_retries = 3
                retry_count = 0
                success = False
                
                while retry_count < max_retries:
                    try:
                        # Reset for this retry attempt
                        local_tool_calls = []
                        local_text_chunk = ""
                        local_turn_parts = []
                        
                        response_stream = self._client.models.generate_content_stream(
                            model=self.model_name,
                            contents=contents,
                            config={
                                "system_instruction": current_system_prompt,
                                "temperature": self.temperature,
                                "max_output_tokens": self.max_tokens,
                                "tools": TOOLS,
                                "automatic_function_calling": {"disable": True} 
                            }
                        )
                        
                        for chunk in response_stream:
                            # 1. Text Content
                            if chunk.text:
                                text = chunk.text
                                local_text_chunk += text
                                
                                # Yield sentences immediately
                                sentences = splitter.feed(text)
                                for sentence in sentences:
                                    # Only yield if not already yielded in a previous FAILED attempt of this turn
                                    # (Actually, in a full turn retry, it's safer to just yield and let UI handle, 
                                    # but we'll try to keep it clean)
                                    yield sentence
                                    
                            # 2. Function Calls
                            if chunk.candidates:
                                for cand in chunk.candidates:
                                    if cand.content and cand.content.parts:
                                        for part in cand.content.parts:
                                            # Deduplicate
                                            if part not in local_turn_parts:
                                                local_turn_parts.append(part)
                                                if part.function_call:
                                                    local_tool_calls.append(part.function_call)
                        
                        # If we reached here, the stream finished successfully
                        tool_calls = local_tool_calls
                        current_text_chunk = local_text_chunk
                        turn_parts = local_turn_parts
                        full_response_text += current_text_chunk
                        success = True
                        break

                    except Exception as e:
                        if "503" in str(e) or "UNAVAILABLE" in str(e):
                            retry_count += 1
                            wait_time = 2 ** retry_count
                            logger.warning(f"Gemini 503 during stream. Retrying {retry_count}/{max_retries} in {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                        raise e

                if not success:
                    raise RuntimeError("Failed to process Gemini turn after multiple retries.")
                
                # If no tool calls, we are done with this turn
                if not tool_calls:
                    break
                
                # Flush splitter BEFORE tool calls so user sees the "intro" text
                intro_remaining = splitter.flush()
                if intro_remaining:
                    yield intro_remaining

                # Persist model turn to history
                self._add_to_history("model", current_text_chunk or "[Function Call]", parts=turn_parts)
                contents.append(genai_types.Content(role="model", parts=turn_parts))
                
                # Execute Tools (Async)
                for tc in tool_calls:
                    func_name = tc.name
                    func_args = tc.args
                    
                    if func_name in tool_map:
                        logger.info(f"Executing tool: {func_name} with args: {func_args}")
                        try:
                            tool_result_data = await tool_map[func_name](**func_args)
                            if not isinstance(tool_result_data, dict):
                                tool_result_data = {"result": tool_result_data}
                        except Exception as tool_err:
                            logger.error(f"Tool execution failed: {tool_err}")
                            tool_result_data = {"error": str(tool_err)}
                    else:
                        tool_result_data = {"error": f"Tool {func_name} not found"}
                    
                    response_part = genai_types.Part(
                        function_response=genai_types.FunctionResponse(
                            name=func_name,
                            response=tool_result_data
                        )
                    )
                    
                    self._add_to_history("user", f"[Tool Result for {func_name}]", parts=[response_part])
                    contents.append(genai_types.Content(role="user", parts=[response_part]))
                
                # Loop continues...
                
            # Final step: If the last turn was a pure text response from model (no tool calls in that turn), 
            # we need to save it to history as well. 
            # If current_text_chunk exists and tool_calls is empty, it means the loop terminated on a text turn.
            if not tool_calls and current_text_chunk:
                self._add_to_history("model", current_text_chunk, parts=[genai_types.Part.from_text(text=current_text_chunk)])

            # Flush any remaining text from splitter
            remaining = splitter.flush()
            if remaining:
                yield remaining
                
        except Exception as e:
            import traceback
            print(f"\n{'='*60}")
            print(f"DEBUG: Gemini API Error: {type(e).__name__}: {e}")
            traceback.print_exc()
            print(f"{'='*60}\n")
            logger.error(f"Gemini API error: {e}")
            error_msg = "معلش، حصل مشكلة. ممكن تعيد تاني؟" if self.language == "ar" else "Sorry, something went wrong."
            full_response = error_msg
            yield error_msg
        
        # Add final assistant response (text only) to history for display 
        # But we actually want to store the MODEL contents we accumulated
        # History is now managed turn-by-turn during generate_response
        pass
    
    async def generate_response_full(self, user_text: str, **kwargs) -> str:
        """Generate a full (non-streaming) response."""
        sentences = []
        async for sentence in self.generate_response(user_text, **kwargs):
            sentences.append(sentence)
        return " ".join(sentences)
    
    def _build_contents(self, health_status: Optional[dict] = None):
        """Build the message list for the Gemini API using google.genai types."""
        from google.genai import types as genai_types
        
        contents = []
        agreement_words = ["تمام", "حاضر", "ماشي", "طيب", "أهو", "حطيت", "عملت", "ماشي يا بني"]
        
        for i, turn in enumerate(self.history):
            if turn.parts:
                # Use stored parts directly
                contents.append(genai_types.Content(role=turn.role, parts=turn.parts))
                continue

            # Fallback for simple text-based history items
            text = turn.content
            
            # Contextual Nudge for health vitals
            if i == len(self.history) - 1 and turn.role == "user":
                if any(word in text for word in agreement_words):
                    if len(self.history) >= 2:
                        prev_turn = self.history[-2]
                        if prev_turn.role == "model" and ("صباعك" in prev_turn.content or "الجهاز" in prev_turn.content):
                            text += "\n[System Instruction: User has agreed. You MUST now call `fetch_vitals` immediately.]"
            
            # Contextual Nudge for telegram (intermittent failure fix)
            if i == len(self.history) - 1 and turn.role == "user":
                 if "بلغ" in text or "قول" in text or "بعت" in text:
                     text += "\n[System Instruction: User asked to notify someone. Use `send_telegram_notification` now.]"

            if health_status and i == len(self.history) - 1 and turn.role == "user":
                text += f"\n[Health Status: {health_status}]"
            
            contents.append(
                genai_types.Content(
                    role=turn.role,
                    parts=[genai_types.Part.from_text(text=text)]
                )
            )
            
        return contents
    
    def _add_to_history(self, role: str, content: str, parts: list = None):
        """Add a turn to conversation history, maintaining window size."""
        self.history.append(ConversationTurn(role=role, content=content, parts=parts))
        
        # Trim history (keep last 10 entries = ~5 full turns)
        max_entries = 10
        if len(self.history) > max_entries:
            self.history = self.history[-max_entries:]
            
        # Optimization: Ensure the first entry is ALWAYS a 'user' turn for API compatibility
        if self.history and self.history[0].role == "model":
            self.history = self.history[1:]
    
    def clear_history(self):
        """Clear the conversation history."""
        self.history = []
        logger.info("Conversation history cleared")
    
    @property
    def is_initialized(self) -> bool:
        """Check if the agent is initialized."""
        return self._client is not None
