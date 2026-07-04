"""Foydalanuvchi matnidan forma maydonlarini ajratib olish.

Avvalgi versiya google.genai (Gemini) ga qattiq bog'langan edi — loyiha DO
stack'ida bu hech qachon ishlamasdi va suhbat bitta savolda aylanib qolardi.
Endi loyihaning umumiy provider qatlami (`ai.providers.get_chat_provider`)
ishlatiladi: Gemini ham, DigitalOcean (maverick/qwen) ham bir xil ishlaydi.
"""
import json
import logging
import re
from typing import Any, Dict, Type

from .base import BaseSmartForm

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_llm_json(text: str) -> Dict[str, Any]:
    """LLM javobidan JSON obyektini chidamli tarzda ajratadi.

    Kichik modellar ko'pincha ```json ... ``` fence yoki izoh matni bilan
    qaytaradi — birinchi {...} blokini topamiz.
    """
    if not text:
        return {}
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = _JSON_BLOCK_RE.search(cleaned)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


class BaseExtractor:
    def extract(
        self, text: str, form_class: Type[BaseSmartForm], current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Matndan maydonlarni ajratadi.

        Natija: {"goal": {"value": "travel", "status": "confirmed"}} ko'rinishida.
        status: "confirmed" (aniq) yoki "needs_confirmation" (taxminiy).
        """
        raise NotImplementedError


class LLMExtractor(BaseExtractor):
    """Provider-agnostik LLM extractor (DO yoki Gemini — settings hal qiladi)."""

    def __init__(self, provider=None):
        self._provider = provider

    @property
    def provider(self):
        if self._provider is None:
            from ai.providers import get_chat_provider

            self._provider = get_chat_provider()
        return self._provider

    def _build_prompt(self, text: str, target_fields: dict, fields_state: dict) -> str:
        lines = [
            "Sen qat'iy ma'lumot ajratuvchisan (data extractor).",
            "Foydalanuvchi xabaridan quyidagi maydonlarni ajrat va FAQAT JSON qaytar.",
            "",
            "Maydonlar:",
        ]
        for fname, finfo in target_fields.items():
            lines.append(f'- "{fname}": {finfo.description or fname}')
            pending = fields_state.get(fname, {})
            if pending.get("status") == "needs_confirmation" and pending.get("value"):
                lines.append(
                    f'  (Hozirgi taxminiy qiymat: "{pending["value"]}". '
                    f"Agar foydalanuvchi tasdiqlasa — ha, to'g'ri, xop, aynan — "
                    f"shu qiymatni needs_confirmation=false bilan qaytar; "
                    f"rad etsa yangi qiymatni yoki null qaytar.)"
                )
        lines += [
            "",
            "Javob formati — aynan shunday JSON, boshqa hech narsa yozma:",
            "{" + ", ".join(
                f'"{fname}": {{"extracted_value": "<qiymat yoki null>", "needs_confirmation": true/false}}'
                for fname in target_fields
            ) + "}",
            "Qoidalar: topilmagan maydon uchun extracted_value=null; qiymat aniq aytilgan bo'lsa "
            "needs_confirmation=false, taxmin bo'lsa true. Maydon tavsifidagi ruxsat etilgan "
            "qiymatlardan chetga chiqma.",
            "",
            f'Foydalanuvchi xabari: "{text}"',
        ]
        return "\n".join(lines)

    def extract(
        self, text: str, form_class: Type[BaseSmartForm], current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        fields_state = current_state.get("fields", {})
        target_fields = {
            fname: finfo
            for fname, finfo in form_class.model_fields.items()
            if fields_state.get(fname, {}).get("status") != "confirmed"
        }
        if not target_fields:
            return {}

        prompt = self._build_prompt(text, target_fields, fields_state)
        try:
            response = self.provider.generate(prompt=prompt)
            data = parse_llm_json(response.text)
        except Exception as exc:
            logger.warning("SmartForm LLMExtractor xatosi: %s", exc)
            return {}

        result: Dict[str, Any] = {}
        for fname in target_fields:
            ext = data.get(fname)
            if not isinstance(ext, dict):
                continue
            value = ext.get("extracted_value")
            if value in (None, "", "null", "None"):
                continue
            status = "needs_confirmation" if ext.get("needs_confirmation") else "confirmed"
            result[fname] = {"value": str(value), "status": status}
        return result
