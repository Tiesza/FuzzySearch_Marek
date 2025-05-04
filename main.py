from fastapi import FastAPI
from pydantic import BaseModel
from rapidfuzz import fuzz
import sqlite3

app = FastAPI()

class KodInput(BaseModel):
    overenyKod: str

def fuzzy_find(kod_input):
    conn = sqlite3.connect("produkty.db")
    cursor = conn.cursor()
    cursor.execute("SELECT kod, nazev FROM produkty")
    vsechny = cursor.fetchall()
    conn.close()

    best_score = 0
    best_match = None

    for kod, nazev in vsechny:
        score = fuzz.token_sort_ratio(kod_input, str(kod))
        if score > best_score:
            best_score = score
            best_match = (kod, nazev)

    if best_score >= 80:
        return {"Katalog": best_match[0], "Nazev": best_match[1]}
    else:
        return {"Katalog": "nenalezeno", "Nazev": "nenalezeno"}

@app.post("/lookup")
async def lookup(data: KodInput):
    vysledek = fuzzy_find(data.overenyKod)
    return {
        "overenyKod": data.overenyKod,
        **vysledek
    }
