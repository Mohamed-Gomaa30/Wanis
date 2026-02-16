
import datetime
from typing import Dict, Any, List

class ContextManager:
    """Manages 'Context of the Day' and system-wide state for the agent."""
    
    def __init__(self):
        self.daily_context: Dict[str, Any] = {
            "date": datetime.date.today().strftime("%A, %B %d, %Y"),
            "location": "Cairo, Egypt",
            "medication_schedule": [
                {"time": "08:00 AM", "pill": "Blood Pressure (Amlodipine)", "taken": True},
                {"time": "02:00 PM", "pill": "Vitamin D", "taken": False},
                {"time": "09:00 PM", "pill": "Cholesterol (Atorvastatin)", "taken": False}
            ],
            "weather": "Sunny, 25°C",
            "doctor_name": "Dr. Ahmed Fawzy"
        }
        self.health_history: List[Dict[str, Any]] = []

    def get_context_summary(self) -> str:
        """Returns a string summary of the today's context for the prompt."""
        meds = ", ".join([f"{m['pill']} at {m['time']} ({'Taken' if m['taken'] else 'Pending'})" 
                         for m in self.daily_context['medication_schedule']])
        
        summary = (
            f"Today is {self.daily_context['date']}. "
            f"Location: {self.daily_context['location']}. "
            f"Weather: {self.daily_context['weather']}. "
            f"Doctor: {self.daily_context['doctor_name']}. "
            f"Medication Schedule: {meds}."
        )
        return summary

    def add_health_event(self, event_type: str, data: Dict[str, Any]):
        """Records a health-related event (e.g., Vitals check, Fall)."""
        event = {
            "timestamp": datetime.datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        self.health_history.append(event)
        # Keep only last 10 events for context
        if len(self.health_history) > 10:
            self.health_history.pop(0)

# Global instance
context_manager = ContextManager()
