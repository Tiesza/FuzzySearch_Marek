from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from rapidfuzz import fuzz
import sqlite3

app = FastAPI()

def nacti_data():
    conn = sqlite3.connect("produkty.db")
    cursor = conn.cursor()
    cursor.execute("SELECT kod, nazev FROM produkty")
    data = cursor.fetchall()
    conn.close()
    return [(str(kod).strip(), str(nazev).strip()) for kod, nazev in data]

data_z_db = nacti_data()

def najdi_kod(kontrolovany_kod):
    kod_input = kontrolovany_kod.strip()

    # Přesná shoda
    for kod, nazev in data_z_db:
        if kod_input == kod:
            return kod, nazev

    # Substring shoda
    for kod, nazev in data_z_db:
        if kod in kod_input:
            return kod, nazev

    # Fuzzy shoda
    best_score = 0
    best_match = None
    for kod, nazev in data_z_db:
        score = fuzz.ratio(kod_input, kod)
        if score > best_score:
            best_score = score
            best_match = (kod, nazev)

    if best_score >= 87:
        return best_match
    else:
        return "nenalezeno", "nenalezeno"

@app.post("/kontrola")
async def kontrola_tovaru(data: Dict[str, Any]):
    polozky = data.get("polozky", [])
    nove_polozky = []

    for polozka in polozky:
        puvodni_kod = polozka.get("Katalog", "")
        novy_kod, nazev = najdi_kod(puvodni_kod)

        # Přepiš pole "Katalog" i v "ObsahPolozky > Artikl > Katalog"
        polozka["Katalog"] = novy_kod
        polozka["Nazev"] = nazev

        if "ObsahPolozky" in polozka and "Artikl" in polozka["ObsahPolozky"]:
            polozka["ObsahPolozky"]["Artikl"]["Katalog"] = novy_kod

        nove_polozky.append(polozka)

    return { "polozky": nove_polozky }
