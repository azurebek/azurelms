from typing import Dict, Any, List
from .registry import get_form_class
from .extractor import BaseExtractor, LLMExtractor
from .planner import Planner
from messenger.models import SmartFormSession, ChatRoom

class SmartFormEngine:
    def __init__(self, session: SmartFormSession):
        self.session = session
        self.form_class = get_form_class(session.schema_name)
        # MVP: We only use the LLMExtractor for now.
        self.extractors: List[BaseExtractor] = [LLMExtractor()]
        self.planner = Planner()
        
    def process_user_message(self, text: str) -> str:
        """
        Process a user message, update state, and return the next intent.
        """
        # 0. Birinchi xabardan boshlab sessiya "collecting" holatiga o'tadi
        if self.session.status == SmartFormSession.STATUS_CREATED:
            self.session.status = SmartFormSession.STATUS_COLLECTING
            self.session.save(update_fields=["status"])

        # 1. Extraction
        extracted_data = {}
        for extractor in self.extractors:
            data = extractor.extract(text, self.form_class, self.session.state)
            if data:
                extracted_data.update(data)
            
        # 2. Update state if fields were extracted
        if extracted_data:
            if "fields" not in self.session.state:
                self.session.state["fields"] = {}
                
            for fname, fdata in extracted_data.items():
                self.session.state["fields"][fname] = fdata
                
            self.session.save(update_fields=["state"])
        
        # 3. Validation & Normalization (To be added in V2)
        
        # 4. Plan next action
        intent = self.planner.plan_next_action(self.form_class, self.session.state)
        
        # 5. Handle submission if ready
        if intent == "SUBMIT_FORM":
            self.session.status = SmartFormSession.STATUS_SUBMITTING
            self.session.save(update_fields=["status"])
            
            # Extract only confirmed values
            form_data = {}
            for k, v in self.session.state.get("fields", {}).items():
                if v.get("status") == "confirmed":
                    form_data[k] = v.get("value")
                    
            try:
                form_instance = self.form_class(**form_data)
                # In 1:1 AI chat rooms, the student is the first (or only) participant
                user = self.session.chat_room.participants.first()
                result = form_instance.submit(user=user)
                self.session.status = SmartFormSession.STATUS_COMPLETED
                self.session.save(update_fields=["status"])
                # We return a specific signal format that the SmartFormSkill can interpret
                return f"SUBMIT_SUCCESS|{result}"
            except Exception as e:
                self.session.status = SmartFormSession.STATUS_FAILED
                self.session.save(update_fields=["status"])
                return f"SUBMIT_ERROR|{str(e)}"
                
        return intent
