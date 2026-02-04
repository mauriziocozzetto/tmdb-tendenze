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
    id: int
    name: str
    character: str
    profile_path: Optional[str] = None

# 1. Aggiungi il modello Pydantic per i dettagli dell'attore


class ActorDetail(BaseModel):
    id: int
    name: str
    biography: Optional[str] = None
    birthday: Optional[str] = None
    place_of_birth: Optional[str] = None
    profile_path: Optional[str] = None

# 2. Crea la rotta API per l'attore


@app.get("/api/actor/{actor_id}", response_model=ActorDetail)
def get_actor_details(actor_id: int):
    url = f"{BASE_URL}/person/{actor_id}?api_key={TMDB_API_KEY}&language=it-IT"
    response = requests.get(url)
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Attore non trovato")
    return response.json()

# 3. Crea la rotta per servire l'HTML (con protezione)

@app.get("/actor")
async def serve_actor_page(id: Optional[str] = None):
    # 1. Se l'ID manca o non è un numero (es. ?id=abc), reindirizza subito alla home
    if not id or not id.isdigit():
        return RedirectResponse(url="/", status_code=307)

    # 2. Controllo rapido su TMDB per vedere se l'ID persona esiste davvero
    try:
        check_url = f"{BASE_URL}/person/{id}?api_key={TMDB_API_KEY}"
        res = requests.get(check_url)

        # Se TMDB risponde con un errore (es. 404), l'ID non è valido: torna alla home
        if res.status_code != 200:
            return RedirectResponse(url="/", status_code=307)

    except Exception:
        # In caso di errori di rete, per sicurezza torna alla home
        return RedirectResponse(url="/", status_code=307)

    # 3. Solo se l'ID è valido e l'attore esiste, serviamo il file HTML
    return FileResponse('actor.html')


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

    # Mappiamo i primi 6 attori includendo l'ID
    cast_list = []
    for a in data["credits"]["cast"][:6]:
        cast_list.append({
            "id": a["id"],  # <--- Recuperiamo l'ID da TMDB
            "name": a["name"],
            "character": a["character"],
            "profile_path": a["profile_path"]
        })

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
        "cast": cast_list
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
