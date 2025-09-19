from typing import List, Dict, Any
from services.openai_client import OpenAIClient
from observability.logger import setup_logger
import json

logger = setup_logger()


class ConversationMemory:
    """Manages conversation context with compression and summarization."""
    
    def __init__(self, max_turns: int = 8):
        self.max_turns = max_turns
        self.conversation_history: List[Dict[str, Any]] = []
        self.compressed_memo: str = ""
        self.openai_client = OpenAIClient()
    
    def add_turn(self, user_input: str, assistant_response: str, metadata: Dict[str, Any] = None):
        """Add a conversation turn to memory."""
        turn = {
            "user": user_input,
            "assistant": assistant_response,
            "metadata": metadata or {},
            "timestamp": metadata.get("timestamp") if metadata else None
        }
        
        self.conversation_history.append(turn)
        
        # Compress if we exceed max turns
        if len(self.conversation_history) > self.max_turns:
            self._compress_history()
    
    def _compress_history(self):
        """Compress older conversation history into a memo."""
        try:
            # Take the oldest turns for compression
            turns_to_compress = self.conversation_history[:-self.max_turns//2]
            
            # Format for compression
            history_text = ""
            for turn in turns_to_compress:
                history_text += f"User: {turn['user']}\n"
                history_text += f"Assistant: {turn['assistant']}\n\n"
            
            # Compress using OpenAI
            new_memo = self.openai_client.compress_context(history_text)
            
            # Update memo and remove compressed turns
            if self.compressed_memo:
                self.compressed_memo += f"\n\nAdditional context: {new_memo}"
            else:
                self.compressed_memo = new_memo
            
            # Keep only recent turns
            self.conversation_history = self.conversation_history[-self.max_turns//2:]
            
            logger.info("Compressed conversation history", 
                       compressed_turns=len(turns_to_compress),
                       remaining_turns=len(self.conversation_history))
            
        except Exception as e:
            logger.error("Failed to compress conversation history", error=str(e))
    
    def get_context(self) -> str:
        """Get the current conversation context."""
        context = ""
        
        # Add compressed memo if available
        if self.compressed_memo:
            context += f"Previous conversation summary: {self.compressed_memo}\n\n"
        
        # Add recent conversation history
        if self.conversation_history:
            context += "Recent conversation:\n"
            for turn in self.conversation_history[-3:]:  # Last 3 turns
                context += f"User: {turn['user']}\n"
                context += f"Assistant: {turn['assistant']}\n\n"
        
        return context.strip()
    
    def clear(self):
        """Clear all conversation memory."""
        self.conversation_history = []
        self.compressed_memo = ""
        logger.info("Cleared conversation memory")
    
    def get_preferences(self) -> Dict[str, Any]:
        """Extract user preferences from conversation history."""
        preferences = {}
        
        # Look through conversation for preference indicators
        for turn in self.conversation_history:
            user_input = turn['user'].lower()
            
            # Budget preferences
            if 'budget' in user_input or 'cheap' in user_input or 'expensive' in user_input:
                if 'cheap' in user_input or 'budget' in user_input:
                    preferences['budget_preference'] = 'budget-friendly'
                elif 'expensive' in user_input or 'luxury' in user_input:
                    preferences['budget_preference'] = 'luxury'
            
            # Activity preferences
            if any(word in user_input for word in ['museum', 'culture', 'history']):
                preferences.setdefault('activity_types', []).append('cultural')
            if any(word in user_input for word in ['beach', 'water', 'swim']):
                preferences.setdefault('activity_types', []).append('beach')
            if any(word in user_input for word in ['adventure', 'hiking', 'outdoor']):
                preferences.setdefault('activity_types', []).append('adventure')
            if any(word in user_input for word in ['food', 'restaurant', 'dining']):
                preferences.setdefault('activity_types', []).append('dining')
        
        return preferences
