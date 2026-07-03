from typing import Dict, Any, Type
from .base import BaseSmartForm

class Planner:
    def plan_next_action(self, form_class: Type[BaseSmartForm], current_state: Dict[str, Any]) -> str:
        \"\"\"
        Analyzes the current form state and determines the next intent.
        Returns an Intent string, like 'ASK_GOAL' or 'SUBMIT_FORM'.
        \"\"\"
        fields_state = current_state.get("fields", {})
        
        pending_fields = []
        for field_name, field_info in form_class.model_fields.items():
            state = fields_state.get(field_name, {})
            if state.get("status") not in ("confirmed",):
                # Try to get priority from Pydantic field extra
                priority = 0
                if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
                    priority = field_info.json_schema_extra.get("priority", 0)
                pending_fields.append((field_name, priority))
        
        if not pending_fields:
            return "SUBMIT_FORM"
            
        # Sort by priority descending (highest priority first)
        pending_fields.sort(key=lambda x: x[1], reverse=True)
        next_field = pending_fields[0][0]
        
        # Determine if we are asking or confirming
        status = fields_state.get(next_field, {}).get("status", "missing")
        if status == "needs_confirmation":
            return f"CONFIRM_{next_field.upper()}"
        
        return f"ASK_{next_field.upper()}"
