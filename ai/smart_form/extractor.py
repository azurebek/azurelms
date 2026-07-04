import json
from typing import Dict, Any, Type
from django.conf import settings
from .base import BaseSmartForm

class BaseExtractor:
    def extract(self, text: str, form_class: Type[BaseSmartForm], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract fields from raw text.
        Returns a dict of extracted fields with their status.
        Example: {\"goal\": {\"value\": \"travel\", \"status\": \"needs_confirmation\"}}
        """
        raise NotImplementedError

class LLMExtractor(BaseExtractor):
    def extract(self, text: str, form_class: Type[BaseSmartForm], current_state: Dict[str, Any]) -> Dict[str, Any]:
        from google import genai
        from google.genai import types

        target_fields = {}
        fields_state = current_state.get("fields", {})
        
        for field_name, field_info in form_class.model_fields.items():
            field_state = fields_state.get(field_name, {})
            if field_state.get("status") not in ("confirmed",):
                target_fields[field_name] = field_info

        if not target_fields:
            return {}

        properties = {}
        for fname, finfo in target_fields.items():
            properties[fname] = types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "extracted_value": types.Schema(type=types.Type.STRING, description=f"Extract this field if present: {finfo.description or fname}. Use null if not found."),
                    "needs_confirmation": types.Schema(type=types.Type.BOOLEAN, description="True if the extracted value is uncertain or inferred."),
                }
            )
        
        schema = types.Schema(
            type=types.Type.OBJECT,
            properties=properties,
        )

        # Assuming GEMINI_API_KEY is defined in django settings, or fallback to default client environment variables
        api_key = getattr(settings, 'GEMINI_API_KEY', None)
        client = genai.Client(api_key=api_key) if api_key else genai.Client()
        
        prompt = (
            f"You are a strict data extractor. Extract the following fields from the user's text:\n"
            f"Fields to look for: {', '.join(target_fields.keys())}\n\n"
            f"User Text: '{text}'"
        )
        
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.0
                ),
            )
            data = json.loads(response.text)
            
            result = {}
            for fname, ext_data in data.items():
                if ext_data and ext_data.get("extracted_value") is not None:
                    status = "needs_confirmation" if ext_data.get("needs_confirmation") else "confirmed"
                    result[fname] = {
                        "value": ext_data["extracted_value"],
                        "status": status
                    }
            return result
        except Exception as e:
            print(f"LLMExtractor error: {e}")
            return {}
