from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Union
import sqlite3
from rapidfuzz import fuzz

app = FastAPI()

# Jedna položka (Mnozstvi může být string i int)
class Polozka(BaseModel):
    Katalog: str
    Mnozstvi: Union[str, int]
    CisloPolozky: int

# Model vstupu s klíčem "polozky"
class VstupData(BaseModel):
    polozky: List[Polozka]

# ✅ Debugovací endpoint
@app.post("/debug-vstup")
async def debug_vstup(request: Request):
    body = await request.json()
    print("DEBUG /debug-vstup – přijatý vstup:", body)
    return body

# ✅ Endpoint: fuzzy ověření
@app.post("/overit-hromadne")
def overit_kody_bulk(data: VstupData):
    try:
        with sqlite3.connect("produkty_kody.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Katalog, AlternativKatalog1, AlternativKatalog2, AlternativKatalog3
                FROM produkty_kody
            """)
            vysledky_db = cursor.fetchall()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Chyba při práci s databází: {str(e)}")

    if not vysledky_db:
        raise HTTPException(status_code=404, detail="Databáze neobsahuje žádné záznamy")

    # Mapa pro porovnání (normalizovaný kód => originální kód)
    kody_normalizovane = {}

    for radek in vysledky_db:
        for hodnota in radek:
            if hodnota:
                original = str(hodnota).strip()
                normalizovany = original.upper()
                kody_normalizovane[normalizovany] = original

    vysledne_polozky = []

    for polozka in data.polozky:
        zadany_kod = polozka.Katalog.strip()
        zadany_kod_norm = zadany_kod.upper()

        if zadany_kod_norm in kody_normalizovane:
            nejlepsi = kody_normalizovane[zadany_kod_norm]
        else:
            # Fuzzy matching nad normalizovanými kódy
            vysledky = [
                (kod_norm, fuzz.ratio(zadany_kod_norm, kod_norm))
                for kod_norm in kody_normalizovane
            ]

            if not vysledky:
                nejlepsi = "nenalezeno"
            else:
                max_ratio = max(vysledky, key=lambda x: x[1])[1]
                kandidati = [kod for kod, score in vysledky if score == max_ratio]

                if max_ratio < 80:
                    nejlepsi = "špatný kód"
                else:
                    if len(kandidati) == 1:
                        nejlepsi = kody_normalizovane[kandidati[0]]
                    else:
                        # Doplňkové rozhodnutí podle partial_ratio
                        nejlepsi = max(
                            kandidati,
                            key=lambda k: fuzz.partial_ratio(zadany_kod_norm, k)
                        )
                        nejlepsi = kody_normalizovane[nejlepsi]

        vysledne_polozky.append({
            "Katalog": nejlepsi,
            "Mnozstvi": polozka.Mnozstvi,
            "CisloPolozky": polozka.CisloPolozky
        })

    return {"polozky": vysledne_polozky}


# ✅ Endpoint: přesná shoda s hlavním kódem
@app.post("/normalizovat-kody")
def normalizovat_kody(data: VstupData):
    try:
        with sqlite3.connect("produkty_kody.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT Katalog, AlternativKatalog1, AlternativKatalog2, AlternativKatalog3
                FROM produkty_kody
            """)
            zaznamy = cursor.fetchall()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Chyba databáze: {str(e)}")

    if not zaznamy:
        raise HTTPException(status_code=404, detail="Databáze je prázdná")

    vysledne_polozky = []

    for polozka in data.polozky:
        zadany_kod = polozka.Katalog.strip()
        nalezeny_kod = "nenalezeno"

        for radek in zaznamy:
            if any(zadany_kod == (sl.strip() if sl else "") for sl in radek):
                nalezeny_kod = radek[0]
                break

        vysledne_polozky.append({
            "Katalog": nalezeny_kod,
            "Mnozstvi": polozka.Mnozstvi,
            "CisloPolozky": polozka.CisloPolozky
        })

    return {"polozky": vysledne_polozky}


# ✅ Endpoint: doplnění názvů podle katalogového čísla
@app.post("/doplnit-nazvy")
def doplnit_nazvy(data: VstupData):
    try:
        with sqlite3.connect("produkty_nazvy.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT Katalog, Nazev FROM produkty_nazvy")
            zaznamy = cursor.fetchall()
            katalog_na_nazev = {str(katalog).strip(): nazev for katalog, nazev in zaznamy}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Chyba při načítání názvů z databáze: {str(e)}")

    vysledne_polozky = []

    for polozka in data.polozky:
        zadany_kod = polozka.Katalog.strip()
        nazev = katalog_na_nazev.get(zadany_kod, "nenalezeno")

        vysledne_polozky.append({
            "Katalog": zadany_kod,
            "Nazev": nazev,
            "Mnozstvi": polozka.Mnozstvi,
            "CisloPolozky": polozka.CisloPolozky
        })

    return {"polozky": vysledne_polozky}

