from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import requests
from dotenv import load_dotenv

# Carica le variabili dal file .env
load_dotenv()

app = FastAPI()

# Recupera la chiave dalle variabili di sistema
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

# --- MODELLI PER IL FRONTEND ---


class MovieCard(BaseModel):
    id: int
    title: str
    poster_path: Optional[str] = None
    release_date: Optional[str] = ""  # Default stringa vuota se manca
    vote_average: float


class Actor(BaseModel):
    name: str
    character: str
    profile_path: Optional[str] = None


class MovieDetail(BaseModel):
    id: int
    title: str
    overview: str
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    release_date: str
    genres: List[str]
    runtime: Optional[int] = None
    vote_average: float
    director: str
    trailer_key: Optional[str] = None
    cast: List[Actor]

# --- LOGICA DI SUPPORTO ---


def call_tmdb(endpoint: str, params: dict = {}):
    p = {"api_key": TMDB_API_KEY, "language": "it-IT"}
    p.update(params)
    response = requests.get(f"{BASE_URL}{endpoint}", params=p)
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, detail="Errore TMDB")
    return response.json()

# --- ROTTE API FILTRATE ---


@app.get("/api/trending", response_model=List[MovieCard])
def get_trending():
    data = call_tmdb("/trending/movie/week")
    # Pulizia preventiva per evitare errori di validazione Pydantic
    results = []
    for m in data.get("results", []):
        results.append({
            "id": m.get("id"),
            "title": m.get("title"),
            "poster_path": m.get("poster_path"),
            "release_date": m.get("release_date") or "",  # Gestisce null
            "vote_average": m.get("vote_average", 0)
        })
    return results


@app.get("/api/search", response_model=List[MovieCard])
def search_movie(query: str):
    data = call_tmdb("/search/movie", {"query": query})
    results = []
    for m in data.get("results", []):
        results.append({
            "id": m.get("id"),
            "title": m.get("title"),
            "poster_path": m.get("poster_path"),
            "release_date": m.get("release_date") or "",
            "vote_average": m.get("vote_average", 0)
        })
    return results


@app.get("/api/movie/{movie_id}", response_model=MovieDetail)
def get_movie_details(movie_id: int):
    data = call_tmdb(f"/movie/{movie_id}",
                     {"append_to_response": "credits,videos"})

    director = next((c["name"] for c in data["credits"]
                    ["crew"] if c["job"] == "Director"), "N/D")
    trailer = next((v["key"] for v in data["videos"]["results"]
                   if v["type"] == "Trailer" and v["site"] == "YouTube"), None)

    return {
        "id": data["id"],
        "title": data["title"],
        "overview": data["overview"],
        "poster_path": data["poster_path"],
        "backdrop_path": data["backdrop_path"],
        "release_date": data.get("release_date", ""),
        "genres": [g["name"] for g in data["genres"]],
        "runtime": data.get("runtime"),
        "vote_average": data.get("vote_average", 0),
        "director": director,
        "trailer_key": trailer,
        "cast": data["credits"]["cast"][:6]
    }

# --- ROTTE FRONTEND ---


@app.get("/")
async def serve_index(): return FileResponse('index.html')


@app.get("/movie")
async def serve_detail(id: str = None):
    # 1. Se l'ID manca o non è un numero, reindirizziamo ISTANTANEAMENTE alla home
    if not id or not id.isdigit():
        return RedirectResponse(url="/", status_code=307)

    # 2. Verifichiamo se il film esiste davvero su TMDB prima di servire l'HTML
    try:
        # Usiamo una chiamata rapida solo per testare l'esistenza
        call_tmdb(f"/movie/{id}")
    except HTTPException:
        # Se TMDB dà errore (es. 404), reindirizziamo alla home
        return RedirectResponse(url="/", status_code=307)

    # 3. Solo se tutto è corretto, serviamo il file HTML
    return FileResponse('detail.html')
