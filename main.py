from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from pydantic import BaseModel, Field
from typing import List, Union
import sqlite3
from rapidfuzz import fuzz

app = FastAPI()


@app.exception_handler(sqlite3.Error)
async def sqlite_exception_handler(_request: Request, exc: sqlite3.Error):
    return JSONResponse(status_code=500, content={"detail": f"Database error: {exc}"})


class Item(BaseModel):
    catalog: str = Field(alias="Katalog")
    quantity: Union[str, int] = Field(alias="Mnozstvi")
    item_number: int = Field(alias="CisloPolozky")

    class Config:
        allow_population_by_field_name = True


class InputData(BaseModel):
    items: List[Item] = Field(alias="polozky")

    class Config:
        allow_population_by_field_name = True


@app.post("/debug-vstup")
async def debug_input(request: Request):
    body = await request.json()
    print("DEBUG Retrieved input", body)
    return body


@app.post("/overit-hromadne")
def verify_codes_bulk(data: InputData):
    with sqlite3.connect("produkty_kody.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Katalog, AlternativKatalog1, AlternativKatalog2, AlternativKatalog3
            FROM produkty_kody
        """)
        records = cursor.fetchall()

    if not records:
        raise HTTPException(status_code=404, detail="Database has no records")

    norm_codes = {str(val).strip().upper(): str(val).strip()
                  for row in records for val in row if val}

    results = []
    for item in data.items:
        code_raw = item.catalog.strip()
        code_key = code_raw.upper()
        if code_key in norm_codes:
            best = norm_codes[code_key]
        else:
            scores = [(k, fuzz.ratio(code_key, k)) for k in norm_codes]
            if not scores:
                best = "nenalezeno"
            else:
                max_score = max(scores, key=lambda x: x[1])[1]
                candidates = [k for k, s in scores if s == max_score]
                if max_score < 80:
                    best = "nenalezeno"
                else:
                    if len(candidates) == 1:
                        best = norm_codes[candidates[0]]
                    else:
                        partial = max(candidates, key=lambda k: fuzz.partial_ratio(code_key, k))
                        best = norm_codes[partial]

        results.append({
            "Katalog": best,
            "Mnozstvi": item.quantity,
            "CisloPolozky": item.item_number
        })

    return {"polozky": results}


@app.post("/normalizovat-kody")
def normalize_codes(data: InputData):
    with sqlite3.connect("produkty_kody.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Katalog, AlternativKatalog1, AlternativKatalog2, AlternativKatalog3
            FROM produkty_kody
        """)
        records = cursor.fetchall()

    if not records:
        raise HTTPException(status_code=404, detail="Database is empty")

    results = []
    for item in data.items:
        code_raw = item.catalog.strip()
        found = "nenalezeno"
        for row in records:
            if any(code_raw == (alt.strip() if alt else "") for alt in row):
                found = row[0]
                break
        results.append({
            "Katalog": found,
            "Mnozstvi": item.quantity,
            "CisloPolozky": item.item_number
        })

    return {"polozky": results}


@app.post("/doplnit-nazvy")
def enrich_names(data: InputData):
    with sqlite3.connect("produkty_nazvy.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Katalog, Nazev FROM produkty_nazvy")
        rows = cursor.fetchall()
        name_map = {str(k).strip(): v for k, v in rows}

    results = []
    for item in data.items:
        code_raw = item.catalog.strip()
        name = name_map.get(code_raw, "not found")
        results.append({
            "Katalog": code_raw,
            "Nazev": name,
            "Mnozstvi": item.quantity,
            "CisloPolozky": item.item_number
        })

    return {"polozky": results}
