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
    
    def __init__(self, user_id: str):
        api_key = os.environ.get("MEM0_API_KEY")
        self.user_id = user_id
        
        if api_key and not api_key.startswith("your_"):
            self.client = MemoryClient(api_key=api_key) 
            self.enabled = True
        else:
            logger.warning("Valid MEM0_API_KEY not found. Dynamic memory will be disabled.")
            self.client = None
            self.enabled = False

    async def delete_all(self):
        """Wipes ALL memories for the current user."""
        if not self.enabled: return
        try:
            self.client.delete_all(user_id=self.user_id)
            logger.info(f"Memory wiped for user: {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset Mem0 for {self.user_id}: {e}")
            return False

    async def delete_last(self):
        """Attempts to remove the most recent memory."""
        if not self.enabled: return
        try:
            mems = self.client.get_all(user_id=self.user_id)
            if isinstance(mems, dict) and 'results' in mems:
                mems = mems['results']
            
            if not mems: return False
                
            last_mem_id = mems[-1]['id']
            self.client.delete(last_mem_id)
            logger.info(f"Deleted last memory (ID: {last_mem_id}) for {self.user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete last memory: {e}")
            return False

    async def add_memory(self, text: str, metadata: Optional[Dict] = None):
        """Adds a text to the dynamic memory."""
        if not self.enabled: return
        
        try:
            self.client.add(text, user_id=self.user_id, metadata=metadata)
            logger.info(f"Added to dynamic memory for {self.user_id}: {text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to add to Mem0 Managed API: {e}")

    async def search_memories(self, query: str, limit: int = 5) -> str:
        """Searches for relevant memories based on query."""
        if not self.enabled: return ""
        
        try:
            logger.debug(f"Mem0: Searching for '{query}' as user '{self.user_id}'...")
            
            params = {
                "user_id": self.user_id,
                "limit": limit
            }
            results = self.client.search(query, version="v2", **params)
            
            if isinstance(results, dict) and 'results' in results:
                results = results['results']
            
            if not results: return ""
            
            mem_list = []
            for res in results:
                text = ""
                if isinstance(res, dict):
                    text = res.get('memory') or res.get('text') or res.get('content')
                elif isinstance(res, str):
                    text = res
                if text:
                    mem_list.append(f"- {text}")
            
            return "\n".join(mem_list)
        except Exception as e:
            logger.error(f"Failed to search Mem0: {e}")
            return ""

class MemoryManager:
    """Orchestrates both Static and Dynamic memory for the Agent."""
    
    def __init__(self, profile_path: str):
        self.static = StaticMemory(profile_path)
        
        # Extract user_id dynamically from profile (default to anonymous)
        # Using the full_name from JSON as requested by USER
        self.user_id = self.static.data.get("full_name", "anonymous").strip()
        
        self.dynamic = DynamicMemory(user_id=self.user_id)

    async def get_full_context(self, user_query: str = "") -> str:
        """Builds a combined prompt injection string."""
        static_prompt = f"### [Static Profile - Truths]\n{self.static.get_summary()}"
        
        dynamic_context = ""
        if user_query:
            dynamic_context = await self.dynamic.search_memories(user_query)
        
        if dynamic_context:
            return f"{static_prompt}\n\n### [Relevant Past Memories]\n{dynamic_context}"
        
        return static_prompt
