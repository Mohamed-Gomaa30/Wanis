import json
import os
import logging
from typing import Dict, Any, List, Optional
from mem0 import MemoryClient

logger = logging.getLogger(__name__)

class StaticMemory:
    """Manages immutable/slow-changing user information from local storage."""
    
    def __init__(self, profile_path: str):
        self.profile_path = profile_path
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Loads the user profile from JSON."""
        try:
            if os.path.exists(self.profile_path):
                with open(self.profile_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                logger.info("Static profile loaded successfully.")
            else:
                logger.warning(f"Profile path {self.profile_path} does not exist.")
        except Exception as e:
            logger.error(f"Failed to load static profile: {e}")

    def get_summary(self) -> str:
        """Returns a string representation of the static profile for the prompt."""
        if not self.data:
            return "No profile data available."
            
        meds = ", ".join([f"{m['name']} ({m['time']})" for m in self.data.get('medications', [])])
        diseases = ", ".join(self.data.get('chronic_diseases', []))
        
        summary = (
            f"User Profile: {self.data.get('full_name', 'Unknown')}, Age: {self.data.get('age', 'N/A')}.\n"
            f"Chronic Diseases: {diseases}.\n"
            f"Medications: {meds}.\n"
            f"Doctor: {self.data.get('doctor', {}).get('name', 'N/A')}.\n"
            f"Preferences: {self.data.get('preferences', {})}"
        )
        return summary

class DynamicMemory:
    """Manages evolving user data through Mem0 Cloud API."""
    
    def __init__(self, user_id: str = "alhajj_ismail"):
        api_key = os.environ.get("MEM0_API_KEY")
        self.user_id = user_id
        
        if api_key and not api_key.startswith("your_"):
            self.client = MemoryClient(api_key=api_key) 
            self.enabled = True
        else:
            logger.warning("Valid MEM0_API_KEY not found. Dynamic memory will be disabled.")
            self.client = None
            self.enabled = False

    async def add_memory(self, text: str, metadata: Optional[Dict] = None):
        """Adds a text to the dynamic memory."""
        if not self.enabled: return
        
        try:
            self.client.add(text, user_id=self.user_id, metadata=metadata)
            logger.info(f"Added to dynamic memory: {text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to add to Mem0 Managed API: {e}")

    async def search_memories(self, query: str, limit: int = 5) -> str:
        """Searches for relevant memories based on query."""
        if not self.enabled: return ""
        
        try:
            # Managed API (v2) requires specific filters format.
            filters = {
                "OR": [
                    {"user_id": self.user_id}
                ]
            }
            results = self.client.search(query, version="v2", filters=filters, limit=limit)
            
            # In Mem0 v2, results is a dict containing a 'results' list
            if isinstance(results, dict) and 'results' in results:
                results = results['results']
                
            if not results: return ""
            
            # Handle results which could be a list of dictionaries or a list of strings
            mem_list = []
            for res in results:
                if isinstance(res, dict):
                    m_text = res.get('memory') or res.get('text')
                    if m_text:
                        mem_list.append(f"- {m_text}")
                elif isinstance(res, str):
                    mem_list.append(f"- {res}")
            
            return "\n".join(mem_list)
        except Exception as e:
            logger.error(f"Failed to search Mem0 Managed API: {e}")
            return ""

class MemoryManager:
    """Orchestrates both Static and Dynamic memory for the Agent."""
    
    def __init__(self, profile_path: str, user_id: str = "alhajj_ismail"):
        self.static = StaticMemory(profile_path)
        self.dynamic = DynamicMemory(user_id)

    async def get_full_context(self, user_query: str = "") -> str:
        """Builds a combined prompt injection string."""
        static_prompt = f"### [Static Profile - Truths]\n{self.static.get_summary()}"
        
        dynamic_context = ""
        if user_query:
            dynamic_context = await self.dynamic.search_memories(user_query)
        
        if dynamic_context:
            return f"{static_prompt}\n\n### [Relevant Past Memories]\n{dynamic_context}"
        
        return static_prompt
