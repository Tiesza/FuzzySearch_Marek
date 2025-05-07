from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import sqlite3
from rapidfuzz import fuzz

app = FastAPI()

# Model jednotlivé položky
class Polozka(BaseModel):
    Katalog: str
    Mnozstvi: int
    CisloPolozky: int

# Model celého vstupu, alias pro __IMTAGGLENGTH__
class VstupData(BaseModel):
    array: List[Polozka]
    IMTAGGLENGTH: int = Field(..., alias="__IMTAGGLENGTH__")

    class Config:
        allow_population_by_field_name = True

@app.post("/overit-hromadne")
def overit_kody_bulk(data: VstupData):
    conn = None
    try:
        conn = sqlite3.connect("produkty.db")
        cursor = conn.cursor()
        cursor.execute("SELECT kod FROM produkty")
        vysledky_db = cursor.fetchall()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Chyba při připojení nebo čtení z databáze: {str(e)}")
    finally:
        if conn:
            conn.close()

    if not vysledky_db:
        raise HTTPException(status_code=404, detail="Databáze neobsahuje žádné kódy")

    # Vyčištění kódů z databáze
    kody = [radek[0] for radek in vysledky_db if radek[0]]

    vysledne_polozky = []

    for polozka in data.array:
        zadany_kod = polozka.Katalog

        # Fuzzy matching
        vysledky = [(kod, fuzz.ratio(zadany_kod, kod)) for kod in kody]
        if not vysledky:
            nejlepsi = "nenalezeno" # Nebo jiná vhodná hodnota, pokud nejsou žádné kódy v databázi
        else:
            max_ratio = max(vysledky, key=lambda x: x[1])[1]
            kandidati = [kod for kod, score in vysledky if score == max_ratio]

            # Podmínka: pokud shoda menší než 80 %, vrátit "špatný kód"
            if max_ratio < 80:
                nejlepsi = "špatný kód"
            else:
                if len(kandidati) == 1:
                    nejlepsi = kandidati[0]
                else:
                    # Zvažte jiné metriky nebo logiku pro výběr z více kandidátů
                    nejlepsi = max(kandidati, key=lambda k: fuzz.partial_ratio(zadany_kod, k))

        # Přidat do výstupu
        vysledne_polozky.append({
            "Katalog": nejlepsi,
            "Mnozstvi": polozka.Mnozstvi,
            "CisloPolozky": polozka.CisloPolozky
        })

    # Vrátit ve stejném formátu
    return {
        "array": vysledne_polozky,
        "__IMTAGGLENGTH__": data.IMTAGGLENGTH
    }
