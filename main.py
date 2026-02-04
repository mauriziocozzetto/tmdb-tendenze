import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import List, Optional

load_dotenv()

app = FastAPI()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

# --- MODELLI ---


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


class ActorDetail(BaseModel):
    id: int
    name: str
    biography: Optional[str] = None
    birthday: Optional[str] = None
    place_of_birth: Optional[str] = None
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

# --- API ATTORI CON FALLBACK ---


@app.get("/api/actor/{actor_id}", response_model=ActorDetail)
def get_actor_details(actor_id: int):
    # 1. Chiamata in Italiano
    url_it = f"{BASE_URL}/person/{actor_id}?api_key={TMDB_API_KEY}&language=it-IT"
    response = requests.get(url_it)
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Attore non trovato")

    data = response.json()

    # 2. Se la biografia italiana è vuota, recupero quella inglese
    if not data.get("biography"):
        url_en = f"{BASE_URL}/person/{actor_id}?api_key={TMDB_API_KEY}&language=en-US"
        data_en = requests.get(url_en).json()
        data["biography"] = data_en.get("biography")

    return data

# --- API FILM CON FALLBACK ---


@app.get("/api/movie/{movie_id}", response_model=MovieDetail)
def get_movie_details(movie_id: int):
    # 1. Chiamata in Italiano
    url_it = f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=it-IT&append_to_response=credits,videos"
    response = requests.get(url_it)
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Film non trovato")

    data = response.json()

    # 2. Se la sinossi italiana è vuota, recupero quella inglese
    if not data.get("overview"):
        url_en = f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
        data_en = requests.get(url_en).json()
        data["overview"] = data_en.get("overview")

    # Estrazione dati per il frontend
    director = next((c["name"] for c in data["credits"]
                    ["crew"] if c["job"] == "Director"), "N/D")
    trailer = next((v["key"] for v in data["videos"]["results"]
                   if v["type"] == "Trailer" and v["site"] == "YouTube"), None)

    cast_list = []
    for a in data["credits"]["cast"][:6]:
        cast_list.append({
            "id": a["id"],
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

# --- RESTANTI ROTTE (TRENDING, SEARCH, SERVE HTML) ---


@app.get("/api/trending", response_model=List[MovieCard])
def get_trending():
    url = f"{BASE_URL}/trending/movie/week?api_key={TMDB_API_KEY}&language=it-IT"
    response = requests.get(url)
    return response.json()["results"]


@app.get("/api/search", response_model=List[MovieCard])
def search_movie(query: str):
    url = f"{BASE_URL}/search/movie?api_key={TMDB_API_KEY}&language=it-IT&query={query}"
    response = requests.get(url)
    return response.json()["results"]


@app.get("/")
async def serve_index():
    return FileResponse('index.html')


@app.get("/movie")
async def serve_detail(id: Optional[str] = None):
    if not id or not id.isdigit():
        return RedirectResponse(url="/", status_code=307)
    check_url = f"{BASE_URL}/movie/{id}?api_key={TMDB_API_KEY}"
    if requests.get(check_url).status_code != 200:
        return RedirectResponse(url="/", status_code=307)
    return FileResponse('detail.html')


@app.get("/actor")
async def serve_actor_page(id: Optional[str] = None):
    if not id or not id.isdigit():
        return RedirectResponse(url="/", status_code=307)
    check_url = f"{BASE_URL}/person/{id}?api_key={TMDB_API_KEY}"
    if requests.get(check_url).status_code != 200:
        return RedirectResponse(url="/", status_code=307)
    return FileResponse('actor.html')
