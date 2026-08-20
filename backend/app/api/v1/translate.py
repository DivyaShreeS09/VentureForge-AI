from fastapi import APIRouter
from pydantic import BaseModel
from deep_translator import GoogleTranslator

router = APIRouter(prefix="/translate", tags=["translation"])


class TranslationRequest(BaseModel):
    text: str
    target_language: str


class TranslationResponse(BaseModel):
    translated_text: str


@router.post("", response_model=TranslationResponse)
async def translate(request: TranslationRequest):
    if not request.text.strip() or request.target_language == "en":
        return TranslationResponse(translated_text=request.text)

    translated = GoogleTranslator(
        source="auto",
        target=request.target_language,
    ).translate(request.text)

    return TranslationResponse(translated_text=translated)