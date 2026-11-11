"""MongoDB connection (the Python equivalent of models/connection.js + the models).

Uses the same DATABASE_URL as the Node app, so existing users and movies carry over.
Collection names match the ones Mongoose created automatically: "users" and "movies".

Note: unlike Mongoose, pymongo has no "schemas". A document is just a Python
dictionary, e.g. {"Title": "Jaws", "Year": 1975, "username": "dan"}.
"""
import os

# MongoClient is pymongo's connection object (like mongoose.connect()).
from pymongo import MongoClient

# Module-level variables. They start as None (Python's `null`) and get filled
# in the first time someone asks for the database. A leading underscore is a
# convention meaning "private — only used inside this file".
_client = None
_db = None


def get_db():
    """Return the database, connecting the first time it's needed."""
    # `global` lets this function reassign the module-level variables above.
    # Without it, `_db = ...` would create a new local variable instead.
    global _client, _db

    # `is None` is the Python way to check for null.
    if _db is None:
        url = os.environ.get("DATABASE_URL", "mongodb://localhost:27017/movied")

        if os.environ.get("USE_MONGOMOCK") == "1":
            # mongomock is a fake, in-memory MongoDB used for tests and for
            # trying the app without a real database. Data vanishes on restart.
            import mongomock

            _client = mongomock.MongoClient()
        else:
            _client = MongoClient(url)

        # try/except is Python's try/catch.
        try:
            # Use the database name from the URL (".../movied" -> "movied").
            _db = _client.get_default_database()
        except Exception:
            # If the URL had no database name, fall back to "movied".
            _db = _client["movied"]

        # Make usernames unique, like `unique: true` in the Mongoose User schema.
        # (Does nothing if the index already exists.)
        _db.users.create_index("username", unique=True)
        print("Connected to Mongo")
    return _db


# Small helper functions so other files can write db.movies().find(...)
# instead of db.get_db().movies.find(...). These play the role of the
# Movie and User models from the Node app.
def movies():
    return get_db().movies


def users():
    return get_db().users
