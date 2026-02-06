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


class Person(BaseModel):  # Rinominato da Actor a Person
    id: int
    name: str
    character: str
    profile_path: Optional[str] = None


class PersonDetail(BaseModel):  # Rinominato da ActorDetail a PersonDetail
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
    director_id: Optional[int] = None
    trailer_key: Optional[str] = None
    cast: List[Person]  # Aggiornato riferimento

# --- API ---


# Aggiornato modello risposta
@app.get("/api/person/{person_id}", response_model=PersonDetail)
def get_person_details(person_id: int):
    url_it = f"{BASE_URL}/person/{person_id}?api_key={TMDB_API_KEY}&language=it-IT"
    response = requests.get(url_it)
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Persona non trovata")

    data = response.json()

    if not data.get("biography"):
        url_en = f"{BASE_URL}/person/{person_id}?api_key={TMDB_API_KEY}&language=en-US"
        data_en = requests.get(url_en).json()
        data["biography"] = data_en.get("biography")

    return data


@app.get("/api/movie/{movie_id}", response_model=MovieDetail)
def get_movie_details(movie_id: int):
    url_it = f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=it-IT&append_to_response=credits,videos"
    response = requests.get(url_it)
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Film non trovato")

    data = response.json()

    if not data.get("overview"):
        url_en = f"{BASE_URL}/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
        data_en = requests.get(url_en).json()
        data["overview"] = data_en.get("overview")

    director_data = next(
        (c for c in data["credits"]["crew"] if c["job"] == "Director"), None)
    director_name = director_data["name"] if director_data else "N/D"
    director_id = director_data["id"] if director_data else None

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
        "director": director_name,
        "director_id": director_id,
        "trailer_key": trailer,
        "cast": cast_list
    }


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
    # 1. Controllo formato: deve esserci l'ID e deve essere numerico
    if not id or not id.isdigit():
        return RedirectResponse(url="/", status_code=307)

    # 2. Controllo esistenza: verifichiamo se il film esiste su TMDB
    check_url = f"{BASE_URL}/movie/{id}?api_key={TMDB_API_KEY}"
    response = requests.get(check_url)

    if response.status_code != 200:
        # Se TMDB restituisce 404 (o altro errore), l'utente viene rispedito in Home
        return RedirectResponse(url="/", status_code=307)

    return FileResponse('detail.html')


@app.get("/person")
async def serve_person_page(id: Optional[str] = None):
    if not id or not id.isdigit():
        return RedirectResponse(url="/", status_code=307)

    check_url = f"{BASE_URL}/person/{id}?api_key={TMDB_API_KEY}"
    response = requests.get(check_url)
    if response.status_code != 200:
        return RedirectResponse(url="/", status_code=307)

    return FileResponse('person.html')
