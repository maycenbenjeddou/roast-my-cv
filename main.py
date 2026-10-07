import io
import os
import re
from functools import lru_cache

import groq
import pdfplumber
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

from prompts import LEVELS, SYSTEM_PROMPT, user_prompt

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PAGES = 4
# Real CVs come in well under this; it caps what a junk upload costs in tokens.
MAX_CHARS = 12_000

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\+?\d[\d .-]{7,}\d")
# PHONE also matches "2023-2025", which the roast needs to see.
YEAR_RANGE = re.compile(r"(19|20)\d\d ?- ?(19|20)\d\d")

app = FastAPI(title="Roast my CV")


class Roast(BaseModel):
    roast: str
    conseils: list[str]
    note: int = Field(ge=0, le=10)
    verdict: str


# Built lazily: AsyncGroq() raises without a key, and the app should still
# start and serve the page with a readable error instead.
@lru_cache
def client() -> groq.AsyncGroq:
    return groq.AsyncGroq()


def extract_text(pdf_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            # The default tolerance (3) glues words together on tightly kerned
            # CVs ("Étudianteeninformatique"), and the model then roasts the typos.
            pages = [p.extract_text(x_tolerance=1.5) or "" for p in pdf.pages[:MAX_PAGES]]
    except Exception:  # pdfminer can throw just about anything on a malformed file
        raise HTTPException(400, "El PDF mouch sa7i7, ma najamtech n7ellou.")
    return "\n".join(pages).strip()


def redact(text: str) -> str:
    # The roast doesn't need contact details, so they never leave the server.
    text = EMAIL.sub("[email]", text)
    return PHONE.sub(lambda m: m[0] if YEAR_RANGE.fullmatch(m[0]) else "[tel]", text)


@app.post("/api/roast", response_model=Roast)
async def roast(cv: UploadFile = File(...), level: str = Form("normal")):
    if level not in LEVELS:
        raise HTTPException(400, "Niveau inconnu.")
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(500, "GROQ_API_KEY na9sa fil fichier .env.")

    data = await cv.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(413, "El PDF kbir barcha (5 Mo max).")
    if not data.startswith(b"%PDF"):
        raise HTTPException(400, "Ab3ath PDF ya m3allem, mouch 7aja o5ra.")

    text = extract_text(data)
    if len(text) < 80:
        raise HTTPException(
            422, "Ma najamtech na9ra el CV. Ykoun scanné ? Jarreb PDF fih texte."
        )

    try:
        completion = await client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt(redact(text)[:MAX_CHARS], level)},
            ],
            temperature=0.9,
            response_format={"type": "json_object"},
        )
    except groq.RateLimitError:
        raise HTTPException(429, "Si Lamine ta3eb, barcha CV fi d9i9a. Arja3 ba3d chwaya.")
    except groq.APIError as e:
        raise HTTPException(502, f"Mochkla m3a Groq : {e.message}")

    try:
        return Roast.model_validate_json(completion.choices[0].message.content)
    except ValidationError:
        raise HTTPException(502, "El IA jebet jweb mouch mfahhem. 3awed jarreb.")


# Mounted last so it doesn't shadow /api routes.
app.mount("/", StaticFiles(directory="static", html=True), name="static")
