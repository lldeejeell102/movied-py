"""Movie routes (the Python equivalent of controllers/movie.js)."""
import os

# datetime gives us the current time for createdAt/updatedAt
# (Mongoose added those automatically with {timestamps: true}; here we do it by hand).
from datetime import datetime, timezone

# quote_plus makes text safe to put in a URL: "the matrix" -> "the+matrix".
from urllib.parse import quote_plus

# requests is the most popular Python library for making HTTP calls (like fetch).
import requests

# ObjectId is MongoDB's id type (the "_id" field). InvalidId is the error raised
# when a string isn't a valid id, e.g. /movies/not-a-real-id.
from bson import ObjectId
from bson.errors import InvalidId

# abort(404) stops the request and sends a "Not Found" page.
# jsonify(...) is res.json(...).
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for

import db

movies_bp = Blueprint("movies", __name__)


# ---------------------------------------------------------------------------
# MIDDLEWARE
# ---------------------------------------------------------------------------
# before_request runs before EVERY route in this blueprint, like router.use(...)
# in the Node version. If it returns something (a redirect), the route is skipped.
# If it returns nothing (None), Flask continues on to the route — like calling next().
@movies_bp.before_request
def require_login():
    if not session.get("logged_in"):
        return redirect(url_for("user.signup_form"))


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def _oid(movie_id):
    """Turn the id string from the URL into a MongoDB ObjectId, or send a 404."""
    try:
        return ObjectId(movie_id)
    # Catch either of two error types by putting them in parentheses.
    except (InvalidId, TypeError):
        abort(404)


def _to_int(value):
    """Convert text like "1975" to the number 1975; return None if it isn't a number."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

# SEED — wipes the movies collection and adds one sample movie.
@movies_bp.get("/seed")
def seed():
    # A list (JS array) containing one dictionary (JS object).
    start_movies = [
        {
            "Title": "Autobiography 1",
            "Year": 2024,
            "Released": "01 Jan 2024",
            "Actors": "Daniel Ji, Dan Ji",
            "Plot": "The main character, Daniel Ji, shows off his hot mess of a life",
            "Poster": "https://i.imgur.com/hXZxSmM.png",
            "username": "user1",
        }
    ]
    db.movies().delete_many({})  # Movie.deleteMany({})
    db.movies().insert_many(start_movies)  # Movie.create(startMovie)

    # This is a "list comprehension": a one-line loop that builds a new list.
    # It's like start_movies.map(m => ({...m, _id: String(m._id)})) in JS.
    # `**m` copies every key from m, like the `...m` spread in JS.
    # We convert _id to a string because ObjectId can't be turned into JSON directly.
    return jsonify([{**m, "_id": str(m["_id"])} for m in start_movies])


# INDEX — show the logged-in user's movies.
# Note: because the blueprint is mounted at /movies, "/" here means "/movies/".
@movies_bp.get("/")
def index():
    username = session.get("username")
    # find() returns a "cursor" (results that load lazily); list(...) reads them all
    # into a regular list so the template can loop over it. (Movie.find({username}))
    movies = list(db.movies().find({"username": username}))
    # Variables passed here are available in templates/movies/index.html.
    return render_template("movies/index.html", movies=movies, username=username)


# NEW — the search form for adding a movie.
@movies_bp.get("/add")
def new():
    return render_template("movies/new.html")


# CREATE — save a movie picked from the search results.
@movies_bp.post("/")
def create():
    # A short alias so we can write f.get(...) instead of request.form.get(...).
    f = request.form
    now = datetime.now(timezone.utc)
    db.movies().insert_one(
        {
            "Title": f.get("title"),
            "Year": _to_int(f.get("year")),
            "Released": f.get("released"),
            "Actors": f.get("actors"),
            "Plot": f.get("plot"),
            "Poster": f.get("poster"),
            "Watched": f.get("watched"),
            "username": session.get("username"),
            "createdAt": now,
            "updatedAt": now,
        }
    )
    return redirect(url_for("movies.index"))


# DELETE — "<movie_id>" in the path is a URL parameter, like ":id" in Express.
# Flask passes it into the function as an argument (req.params.id).
@movies_bp.delete("/<movie_id>")
def delete(movie_id):
    # Matching on username too means users can only delete their OWN movies.
    db.movies().delete_one({"_id": _oid(movie_id), "username": session.get("username")})
    # code=303 tells the browser to follow the redirect with a GET request.
    return redirect(url_for("movies.index"), code=303)


# UPDATE — change the watched date.
@movies_bp.put("/<movie_id>")
def update(movie_id):
    db.movies().update_one(
        # 1st argument: which document to update (the filter).
        {"_id": _oid(movie_id), "username": session.get("username")},
        # 2nd argument: what to change. "$set" updates only these fields.
        {"$set": {"Watched": request.form.get("newwatched"), "updatedAt": datetime.now(timezone.utc)}},
    )
    return redirect(url_for("movies.index"), code=303)


# SHOW / EDIT — the page for changing a movie's watched date.
@movies_bp.get("/<movie_id>")
def show(movie_id):
    movie = db.movies().find_one({"_id": _oid(movie_id), "username": session.get("username")})
    if movie is None:
        abort(404)
    return render_template("movies/edit.html", movie=movie)


# SEARCH — look the movie up on the OMDb API.
# URL_API in .env should look like "http://www.omdbapi.com/?apikey=XXXX".
@movies_bp.post("/results")
def results():
    title = request.form.get("title", "").strip()
    year = request.form.get("year", "").strip()

    # A title is required; without one, go back to the search form.
    if not title:
        return redirect(url_for("movies.new"))

    # Build the API URL, e.g. ".../?apikey=XXXX&t=the+matrix&y=1999".
    api_url = f"{os.environ.get('URL_API', '')}&t={quote_plus(title.lower())}"
    if year:
        # `+=` appends to the string, same as in JS.
        api_url += f"&y={quote_plus(year)}"

    try:
        # requests.get(...) waits for the response (no await needed — this code
        # is synchronous). .json() parses the body into a dictionary.
        # timeout=10 gives up after 10 seconds instead of hanging forever.
        data = requests.get(api_url, timeout=10).json()
    except (requests.RequestException, ValueError):
        # Network failure or a non-JSON reply: fake an OMDb-style "not found"
        # answer so the template shows a friendly message.
        data = {"Response": "False", "Error": "Could not reach the movie database."}

    return render_template("movies/results.html", data=data)
