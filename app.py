"""Movied — Flask port of the original Express/EJS app.

This is the entry point (the Python equivalent of server.js).
Run it with:  python app.py

A triple-quoted string at the very top of a file like this one is called a
"docstring". It's just documentation — Python doesn't run it.
"""

# ---------------------------------------------------------------------------
# IMPORTS (like `require(...)` in Node)
# ---------------------------------------------------------------------------
# `import os` gives us access to environment variables via os.environ,
# which is Python's version of Node's `process.env`.
import os

# `from X import Y` pulls specific names out of a package, similar to
# `const { Y } = require("X")` in JavaScript.
from dotenv import load_dotenv  # same job as require("dotenv").config()
from flask import Flask, redirect, url_for  # Flask is Python's "Express"

# Read the .env file and put its values into os.environ.
# We do this BEFORE importing our own routes so they can see the variables.
load_dotenv()

# Our route files ("blueprints" are Flask's version of express.Router()).
# The `# noqa: E402` comment just tells code linters "yes, I know this import
# isn't at the very top of the file, it's on purpose".
from blueprints.movies import movies_bp  # noqa: E402
from blueprints.user import user_bp  # noqa: E402


# ---------------------------------------------------------------------------
# METHOD OVERRIDE MIDDLEWARE
# ---------------------------------------------------------------------------
# HTML forms can only send GET or POST. In the Node app, the `method-override`
# package let a form POST to "/movies/123?_method=DELETE" and Express treated
# it as a DELETE request. Flask doesn't ship with that, so we write our own.
#
# `class` defines a new type of object. This one wraps the Flask app: every
# request passes through __call__ first, where we can rewrite the method.
class MethodOverrideMiddleware:
    # A "set" — like a JS Set — of methods we allow forms to fake.
    ALLOWED = {"PUT", "DELETE", "PATCH"}

    # __init__ is the constructor (like `constructor()` in a JS class).
    # `self` is Python's `this`, and it must be listed as the first parameter.
    def __init__(self, app):
        self.app = app

    # __call__ lets an object be called like a function: middleware(environ, ...).
    # The web server calls this for every incoming request.
    # `environ` is a dictionary (like a JS object) describing the request.
    def __call__(self, environ, start_response):
        # .get("KEY") reads a dictionary value, returning None if it's missing
        # (instead of throwing an error like environ["KEY"] would).
        if environ.get("REQUEST_METHOD") == "POST":
            from urllib.parse import parse_qs

            # parse_qs turns "_method=DELETE&x=1" into {"_method": ["DELETE"], "x": ["1"]}
            qs = parse_qs(environ.get("QUERY_STRING", ""))
            # `(qs.get("_method") or [""])[0]` means: take the list of values,
            # or a list with an empty string if there were none, then grab the first.
            method = (qs.get("_method") or [""])[0].upper()
            if method in self.ALLOWED:
                # Pretend the browser actually sent PUT/DELETE.
                environ["REQUEST_METHOD"] = method
        # Hand the (possibly modified) request on to the real Flask app,
        # like calling next() in Express middleware.
        return self.app(environ, start_response)


# ---------------------------------------------------------------------------
# CREATE THE APP
# ---------------------------------------------------------------------------
# `def` defines a function (like `function createApp() {}` in JS).
# Wrapping setup in a function makes it easy for the tests to build a fresh app.
def create_app():
    # Like `const app = express()`.
    # __name__ tells Flask where this file lives so it can find the
    # templates/ and static/ folders next to it.
    # static_url_path="" serves static/style.css at "/style.css",
    # the same as express.static("public") did.
    app = Flask(__name__, static_folder="static", static_url_path="")

    # The secret key signs the session cookie so users can't tamper with it.
    # os.environ.get("SECRET", "fallback") = process.env.SECRET || "fallback"
    app.secret_key = os.environ.get("SECRET", "dev-secret-change-me")

    # Plug in our method-override middleware (app.use(methodOverride(...))).
    app.wsgi_app = MethodOverrideMiddleware(app.wsgi_app)

    # `@app.route("/")` is a "decorator". It registers the function below it
    # as the handler for "/" — the same as app.get("/", (req, res) => {...}).
    @app.route("/")
    def root():
        # url_for("movies.index") builds the URL of the `index` function in
        # the `movies` blueprint ("/movies/"), so we never hard-code paths.
        return redirect(url_for("movies.index"))

    # Mount the routers: app.use("/movies", MovieRouter), app.use("/user", UserRouter)
    app.register_blueprint(movies_bp, url_prefix="/movies")
    app.register_blueprint(user_bp, url_prefix="/user")
    return app


# Build the app at import time. Production servers like gunicorn look for
# this variable: `gunicorn app:app` means "in app.py, use the variable `app`".
app = create_app()

# This block only runs when you start the file directly (`python app.py`),
# not when another file imports it (like the tests do).
if __name__ == "__main__":
    # Environment variables are always strings, so convert PORT to an int.
    port = int(os.environ.get("PORT", 3000))
    # f"...{port}" is an f-string: Python's template literal (`...${port}`).
    print(f"Listening on port: {port}")
    # Start the development server (like app.listen(PORT)).
    # debug=True turns on auto-reload; we only enable it if FLASK_DEBUG=1.
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
