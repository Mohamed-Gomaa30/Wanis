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
import logging
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

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
        # User requested last 3 sentences/turns to keep track
        self.max_history = config.get("max_history_turns", 3)
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 512)
        self.language = config.get("language", "ar")
        
        self.history: list[ConversationTurn] = []
        
        # New: Use ContextManager for daily context
        from ..core.context_manager import context_manager
        self.context_manager = context_manager
        
        # Build initial system prompt with context
        base_prompt = get_system_prompt(self.language)
        daily_context = self.context_manager.get_context_summary()
        
        self.system_prompt = f"{base_prompt}\n\n## Context of the Day:\n{daily_context}\n"
        self._client = None
    
    def initialize(self):
        """Initialize the Gemini client. Call once at startup.
        
        Requires GEMINI_API_KEY environment variable to be set.
        """
        from google import genai
        
        # api_key = os.environ.get("GEMINI_API_KEY")
        api_key = "AIzaSyBk2D9ugVHoYL3qf9IcDMXJ4QR_eI6Ocp4"
        if not api_key:
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
        
        # 1. Handle Fall Detection (Priority 0)
        current_system_prompt = self.system_prompt
        
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
        
        # Import tools and build mapping
        from .tools import TOOLS
        tool_map = {func.__name__: func for func in TOOLS}
        
        # Max turns for tool usage to prevent infinite loops
        max_tool_turns = 3
        current_turn_count = 0
        
        full_response_text = ""
        
        try:
            from google.genai import types as genai_types
            
            # Initial Loop (User Input -> Model)
            # We might need to loop if the model calls a tool
            
            while current_turn_count < max_tool_turns:
                current_turn_count += 1
                
                # Stream content
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
                
                # Collect chunks for this turn
                tool_calls = []
                current_text_chunk = ""
                
                print(f"DEBUG: Starting generation loop turn {current_turn_count}")
                
                for chunk in response_stream:
                    # 1. Text Content
                    if chunk.text:
                        text = chunk.text
                        current_text_chunk += text
                        full_response_text += text
                        
                        # Yield sentences immediately
                        sentences = splitter.feed(text)
                        for sentence in sentences:
                            yield sentence
                            
                    # 2. Function Calls
                    # Check candidates for function calls
                    if chunk.candidates:
                        for cand in chunk.candidates:
                            if cand.content and cand.content.parts:
                                for part in cand.content.parts:
                                    if part.function_call:
                                        print(f"DEBUG: Found function call: {part.function_call.name} with args: {part.function_call.args}")
                                        tool_calls.append(part.function_call)
                
                # If no tool calls, we are done with this turn
                if not tool_calls:
                    print("DEBUG: No tool calls in this turn. Finishing.")
                    break
                
                # If tool calls, execute them and continue loop
                # First, add the model's call to history/contents
                # We need to reconstruct the model's message exactly as it appeared
                
                # Note: chunk.text might be partial, but function_call parts are usually complete in the last chunk
                # or accumulated. The SDK handles aggregation of function calls in `candidates[0]`.
                
                # We need to construct the previous turn (Model Output)
                model_parts = []
                if current_text_chunk:
                    model_parts.append(genai_types.Part.from_text(text=current_text_chunk))
                
                for tc in tool_calls:
                    model_parts.append(genai_types.Part(function_call=tc))
                
                contents.append(genai_types.Content(role="model", parts=model_parts))
                
                # Execute Tools (Async)
                for tc in tool_calls:
                    func_name = tc.name
                    func_args = tc.args
                    
                    if func_name in tool_map:
                        logger.info(f"Executing tool: {func_name} with args: {func_args}")
                        try:
                            # Execute the async function
                            tool_result_data = await tool_map[func_name](**func_args)
                            print(f"DEBUG: Tool result for {func_name}: {tool_result_data}")
                            
                            # Ensure result is a dictionary (for Google GenAI SDK compatibility)
                            if not isinstance(tool_result_data, dict):
                                tool_result_data = {"result": tool_result_data}
                            
                        except Exception as tool_err:
                            logger.error(f"Tool execution failed: {tool_err}")
                            tool_result_data = {"error": str(tool_err)}
                    else:
                        tool_result_data = {"error": f"Tool {func_name} not found"}
                    
                    # Create Function Response Part
                    # The SDK expects a specific format:
                    # Part(function_response=FunctionResponse(name=..., response=...))
                    
                    response_part = genai_types.Part(
                        function_response=genai_types.FunctionResponse(
                            name=func_name,
                            response=tool_result_data
                        )
                    )
                    
                    # Append result to contents (User role for tool response)
                    contents.append(genai_types.Content(role="user", parts=[response_part]))
                
                # Loop continues to send tool outputs back to model
                
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
        
        # Add assistant response to history
        if full_response_text:
            self._add_to_history("assistant", full_response_text)
        elif full_response: # Fallback for error_msg
            self._add_to_history("assistant", full_response)
    
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
            text = turn.content
            
            # Contextual Nudge: If this is the latest user message and it contains agreement,
            # remind the model that it MUST call the tool now if the previous assistant message asked for vitals.
            if i == len(self.history) - 1 and turn.role == "user":
                # Check for agreement
                if any(word in text for word in agreement_words):
                    # Check if previous assistant message asked to put finger
                    if len(self.history) >= 2:
                        prev_assistant = self.history[-2]
                        if prev_assistant.role == "assistant" and ("صباعك" in prev_assistant.content or "الجهاز" in prev_assistant.content):
                            text += "\n[System Instruction: User has agreed/complied. You MUST now call `fetch_vitals` immediately.]"

            # Inject explicit health status if provided
            if health_status and i == len(self.history) - 1 and turn.role == "user":
                health_str = f"\n[System Note: Health Status: {health_status}]"
                text += health_str
            
            role = "user" if turn.role == "user" else "model"
            contents.append(
                genai_types.Content(
                    role=role,
                    parts=[genai_types.Part.from_text(text=text)]
                )
            )
            
        return contents
    
    def _add_to_history(self, role: str, content: str):
        """Add a turn to conversation history, maintaining window size."""
        self.history.append(ConversationTurn(role=role, content=content))
        
        # Trim history to max turns (each turn = 1 entry)
        # max_history is number of turns (e.g., 3). 
        # But usually we want pairs. The user requirement "last 3 sentence" 
        # is vague. Interpreting as "last 3 user inputs + responses".
        max_entries = self.max_history * 2 
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
