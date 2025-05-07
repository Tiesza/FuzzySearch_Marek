from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from rapidfuzz import fuzz

app = FastAPI()

# Definice vstupního modelu
class KodInput(BaseModel):
    overovanyKod: str

@app.post("/overit")
def overit_kod(data: KodInput):
    overovanyKod = data.overovanyKod

    # Připojení k databázi
    conn = sqlite3.connect("produkty.db")
    cursor = conn.cursor()
    cursor.execute("SELECT kod FROM produkty")
    vysledky_db = cursor.fetchall()
    conn.close()

    if not vysledky_db:
        raise HTTPException(status_code=404, detail="Databáze neobsahuje žádné kódy")

    # Získání kódů ze seznamu n-tic
    kody = [radek[0] for radek in vysledky_db]

    # Krok 1: fuzz.ratio
    vysledky = [(kod, fuzz.ratio(overovanyKod, kod)) for kod in kody]
    max_ratio = max(vysledky, key=lambda x: x[1])[1]
    kandidati = [kod for kod, score in vysledky if score == max_ratio]

    # Krok 2: pokud víc kandidátů, použij partial_ratio
    if len(kandidati) == 1:
        nejlepsi = kandidati[0]
    else:
        nejlepsi = max(kandidati, key=lambda k: fuzz.partial_ratio(overovanyKod, k))

    return {
        "vstup": overovanyKod,
        "nejlepsi_shoda": nejlepsi,
        "fuzz_ratio": fuzz.ratio(overovanyKod, nejlepsi),
        "partial_ratio": fuzz.partial_ratio(overovanyKod, nejlepsi)
    }
