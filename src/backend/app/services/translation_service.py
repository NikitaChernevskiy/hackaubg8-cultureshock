"""Multilingual support — translates decision instructions.

Uses Azure OpenAI for translation when language != 'en'.
Falls back to English if translation fails.
"""

import json
import logging

from openai import AsyncAzureOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)

# Pre-built translations for the most critical instructions
# (works offline / when AI is unavailable)
_STATIC_TRANSLATIONS: dict[str, dict[str, str]] = {
    "bg": {
        "TAKE COVER NOW": "СКРИЙТЕ СЕ ВЕДНАГА",
        "STAY WHERE YOU ARE": "ОСТАНЕТЕ КЪДЕТО СТЕ",
        "PREPARE TO LEAVE": "ПОДГОТВЕТЕ СЕ ЗА ЗАМИНАВАНЕ",
        "NO IMMEDIATE THREAT": "НЯМА НЕПОСРЕДСТВЕНА ЗАПЛАХА",
        "STAY ALERT": "БЪДЕТЕ НАЩРЕК",
        "MOVE TO HIGH GROUND IMMEDIATELY": "ПРЕМЕСТЕТЕ СЕ НА ВИСОЧИНА ВЕДНАГА",
    },
    "tr": {
        "TAKE COVER NOW": "HEMEN SIPERIN",
        "STAY WHERE YOU ARE": "OLDUĞUNUZ YERDE KALIN",
        "PREPARE TO LEAVE": "AYRILMAYA HAZIRLANIN",
        "NO IMMEDIATE THREAT": "ACİL TEHDİT YOK",
        "STAY ALERT": "TETIKTE KALIN",
    },
    "de": {
        "TAKE COVER NOW": "SOFORT IN DECKUNG GEHEN",
        "STAY WHERE YOU ARE": "BLEIBEN SIE WO SIE SIND",
        "PREPARE TO LEAVE": "BEREITEN SIE SICH AUF DIE ABREISE VOR",
        "NO IMMEDIATE THREAT": "KEINE UNMITTELBARE GEFAHR",
        "STAY ALERT": "BLEIBEN SIE WACHSAM",
    },
    "fr": {
        "TAKE COVER NOW": "METTEZ-VOUS À L'ABRI IMMÉDIATEMENT",
        "STAY WHERE YOU ARE": "RESTEZ OÙ VOUS ÊTES",
        "PREPARE TO LEAVE": "PRÉPAREZ-VOUS À PARTIR",
        "NO IMMEDIATE THREAT": "PAS DE MENACE IMMÉDIATE",
        "STAY ALERT": "RESTEZ VIGILANT",
    },
    "es": {
        "TAKE COVER NOW": "BUSQUE REFUGIO AHORA",
        "STAY WHERE YOU ARE": "QUÉDESE DONDE ESTÁ",
        "PREPARE TO LEAVE": "PREPÁRESE PARA IRSE",
        "NO IMMEDIATE THREAT": "NO HAY AMENAZA INMEDIATA",
        "STAY ALERT": "MANTÉNGASE ALERTA",
    },
    "ja": {
        "TAKE COVER NOW": "今すぐ身を守れ",
        "STAY WHERE YOU ARE": "その場にとどまれ",
        "PREPARE TO LEAVE": "避難の準備をしてください",
        "NO IMMEDIATE THREAT": "差し迫った脅威なし",
        "STAY ALERT": "警戒を続けてください",
        "MOVE TO HIGH GROUND IMMEDIATELY": "直ちに高台へ避難してください",
    },
    "ko": {
        "TAKE COVER NOW": "지금 대피하세요",
        "STAY WHERE YOU ARE": "그 자리에 머무세요",
        "NO IMMEDIATE THREAT": "즉각적인 위협 없음",
    },
    "ar": {
        "TAKE COVER NOW": "احتمِ الآن",
        "STAY WHERE YOU ARE": "ابقَ مكانك",
        "PREPARE TO LEAVE": "استعد للمغادرة",
        "NO IMMEDIATE THREAT": "لا تهديد فوري",
    },
}

_LANGUAGE_NAMES = {
    "en": "English", "bg": "Bulgarian", "tr": "Turkish", "de": "German",
    "fr": "French", "es": "Spanish", "it": "Italian", "pt": "Portuguese",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "ar": "Arabic",
    "hi": "Hindi", "ru": "Russian", "uk": "Ukrainian", "pl": "Polish",
    "nl": "Dutch", "el": "Greek", "ro": "Romanian", "th": "Thai",
}


async def translate_instruction(
    instruction: str,
    fallback: str,
    language: str,
) -> tuple[str, str]:
    """Translate instruction + fallback to target language.

    Returns (translated_instruction, translated_fallback).
    Falls back to English on any failure.
    """
    if language == "en" or not language:
        return instruction, fallback

    # Try static translations first (instant, no API call)
    static = _STATIC_TRANSLATIONS.get(language, {})
    for key, translation in static.items():
        if instruction.upper().startswith(key):
            # Translate the prefix, keep the context in English
            rest = instruction[len(key):]
            translated_instr = translation + rest
            return translated_instr, fallback  # Fallback stays English for safety

    # Fall back to Azure OpenAI translation
    settings = get_settings()
    if settings.ai_provider == "mock" or not settings.azure_openai_endpoint:
        return instruction, fallback

    try:
        client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

        lang_name = _LANGUAGE_NAMES.get(language, language)
        response = await client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[
                {"role": "system", "content": (
                    f"Translate the following emergency instruction to {lang_name}. "
                    "Keep it short, urgent, and clear. Do NOT add explanations. "
                    "Respond with ONLY the translation in JSON: "
                    '{\"instruction\": \"...\", \"fallback\": \"...\"}'
                )},
                {"role": "user", "content": json.dumps({
                    "instruction": instruction, "fallback": fallback,
                })},
            ],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        return (
            parsed.get("instruction", instruction),
            parsed.get("fallback", fallback),
        )
    except Exception:
        logger.exception("Translation to %s failed, falling back to English", language)
        return instruction, fallback
