import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional

# Carica le variabili dal file .env
load_dotenv()

app = FastAPI()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

# --- MODELLI PYDANTIC (Indispensabili per il frontend) ---


class MovieCard(BaseModel):
    id: int
    title: str
    poster_path: Optional[str] = None
    release_date: Optional[str] = ""
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

# --- ROTTE API ---


@app.get("/api/trending", response_model=List[MovieCard])
def get_trending():
    # URL nel formato richiesto
    url = f"{BASE_URL}/trending/movie/week?api_key={TMDB_API_KEY}&language=it-IT"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Errore TMDB")

    data = response.json()
    return data["results"]


@app.get("/api/search", response_model=List[MovieCard])
def search_movie(query: str):
    # URL nel formato richiesto (aggiungendo il parametro query)
    url = f"{BASE_URL}/search/movie?api_key={TMDB_API_KEY}&language=it-IT&query={query}"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Errore TMDB")

    data = response.json()
    return data["results"]


@app.get("/api/movie/{movie_id}", response_model=MovieDetail)
def get_movie_details(movie_id: int):
    # URL nel formato richiesto con append_to_response per cast e video
    url = f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=it-IT&append_to_response=credits,videos"
    response = requests.get(url)

    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Film non trovato")

    data = response.json()

    # Estrazione dati semplificata per il frontend
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

# --- ROTTE FRONTEND (Con protezione URL manipolate) ---


@app.get("/")
async def serve_index():
    return FileResponse('index.html')


@app.get("/movie")
async def serve_detail(id: Optional[str] = None):
    # Se l'ID è manipolato (es: ?id=abc), il server reindirizza subito alla home
    if not id or not id.isdigit():
        return RedirectResponse(url="/")

    # Verifica rapida se l'ID esiste su TMDB
    check_url = f"{BASE_URL}/movie/{id}?api_key={TMDB_API_KEY}"
    if requests.get(check_url).status_code != 200:
        return RedirectResponse(url="/")

    return FileResponse('detail.html')
