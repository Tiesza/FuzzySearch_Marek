from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List
import sqlite3
from rapidfuzz import fuzz

app = FastAPI()

# Jedna položka
class Polozka(BaseModel):
    Katalog: str
    Mnozstvi: int
    CisloPolozky: int

# Model vstupu s klíčem "Polozky"
class VstupData(BaseModel):
    Polozky: List[Polozka]

# ✅ Debugovací endpoint pro ladění vstupu
@app.post("/debug-vstup")
async def debug_vstup(request: Request):
    body = await request.json()
    print("DEBUG /debug-vstup – přijatý vstup:", body)
    return body

# ✅ Hlavní endpoint pro ověření kódů
@app.post("/overit-hromadne")
def overit_kody_bulk(data: VstupData):
    conn = None
    try:
        conn = sqlite3.connect("produkty.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Katalog, AlternativKatalog1, AlternativKatalog2, AlternativKatalog3
            FROM produkty
        """)
        vysledky_db = cursor.fetchall()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Chyba při připojení nebo čtení z databáze: {str(e)}")
    finally:
        if conn:
            conn.close()

    if not vysledky_db:
        raise HTTPException(status_code=404, detail="Databáze neobsahuje žádné záznamy")

    # Vytvoření množiny všech dostupných kódů (unikátní hodnoty, žádné None)
    kody = set()
    for radek in vysledky_db:
        for hodnota in radek:
            if hodnota:
                kody.add(str(hodnota).strip())

    kody = list(kody)

    vysledne_polozky = []

    for polozka in data.Polozky:
        zadany_kod = polozka.Katalog.strip()

        vysledky = [(kod, fuzz.ratio(zadany_kod, kod)) for kod in kody]

        if not vysledky:
            nejlepsi = "nenalezeno"
        else:
            max_ratio = max(vysledky, key=lambda x: x[1])[1]
            kandidati = [kod for kod, score in vysledky if score == max_ratio]

            if max_ratio < 80:
                nejlepsi = "špatný kód"
            else:
                if len(kandidati) == 1:
                    nejlepsi = kandidati[0]
                else:
                    nejlepsi = max(kandidati, key=lambda k: fuzz.partial_ratio(zadany_kod, k))

        vysledne_polozky.append({
            "Katalog": nejlepsi,
            "Mnozstvi": polozka.Mnozstvi,
            "CisloPolozky": polozka.CisloPolozky
        })

    vysledek = {
        "Polozky": vysledne_polozky
    }

    print("DEBUG /overit-hromadne – výstup:", vysledek)

    return vysledek
