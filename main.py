from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
from rapidfuzz import fuzz
import sqlite3

app = FastAPI()

# Načti všechna data z databáze jednou
def nacti_data():
    conn = sqlite3.connect("produkty.db")
    cursor = conn.cursor()
    cursor.execute("SELECT kod, nazev FROM produkty")
    data = cursor.fetchall()
    conn.close()
    return [(str(kod).strip(), str(nazev).strip()) for kod, nazev in data]

data_z_db = nacti_data()

# Najdi nejbližší odpovídající kód a název
def najdi_kod(kontrolovany_kod):
    kod_input = kontrolovany_kod.strip()

    for kod, nazev in data_z_db:
        if kod_input == kod:
            return kod, nazev

    for kod, nazev in data_z_db:
        if kod in kod_input:
            return kod, nazev

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

# 🔧 Uprav každou položku v rámci objektu
def zpracuj_objekt(objekt: Dict[str, Any]) -> Dict[str, Any]:
    nove_polozky = []

    for polozka in objekt.get("polozky", []):
        puvodni_kod = polozka.get("Katalog", "")
        novy_kod, nazev = najdi_kod(puvodni_kod)

        polozka["Katalog"] = novy_kod
        polozka["Nazev"] = nazev

        if "ObsahPolozky" in polozka and "Artikl" in polozka["ObsahPolozky"]:
            polozka["ObsahPolozky"]["Artikl"]["Katalog"] = novy_kod

        nove_polozky.append(polozka)

    objekt["polozky"] = nove_polozky
    return objekt

# 🔁 Endpoint pro pole objektů
@app.post("/kontrola")
async def hromadna_kontrola(data: List[Dict[str, Any]]):
    upravene = [zpracuj_objekt(obj) for obj in data]
    return upravene
