"""User routes: signup, login, logout (the Python equivalent of controllers/user.js)."""

# bcrypt hashes passwords, same as bcryptjs in the Node app.
import bcrypt

# Flask helpers:
#   Blueprint        - a group of routes (express.Router())
#   redirect         - res.redirect(...)
#   render_template  - res.render(...) — fills in a Jinja template from templates/
#   request          - the incoming request (req); request.form is req.body
#   session          - the logged-in user's session (req.session)
#   url_for          - builds a URL from a route function's name
from flask import Blueprint, redirect, render_template, request, session, url_for

# The error pymongo raises when the unique username index is violated.
from pymongo.errors import DuplicateKeyError

# Our own db.py file.
import db

# Create the router. "user" is its name, used in url_for("user.login_form").
user_bp = Blueprint("user", __name__)


# `@user_bp.get("/signup")` = router.get("/signup", ...).
# Because the blueprint is mounted at /user, the full path is /user/signup.
@user_bp.get("/signup")
def signup_form():
    # Renders templates/user/signup.html (res.render("user/signup.ejs")).
    return render_template("user/signup.html")


@user_bp.post("/signup")
def signup():
    # request.form is the submitted form data (req.body in Express).
    # .get("username", "") returns "" if the field is missing; .strip() trims spaces.
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # `not username` is true for an empty string — Python treats "" as falsy, like JS.
    if not username or not password:
        # Returning a (body, status_code) pair sets the HTTP status, here 400 Bad Request.
        # Extra keyword arguments (error=...) become variables inside the template.
        return render_template("user/signup.html", error="Username and password are required."), 400

    # bcrypt works on bytes, not text, so .encode() turns the string into bytes,
    # and .decode() turns the resulting hash back into a string for storage.
    # gensalt(10) matches bcrypt.genSalt(10) from the Node version.
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

    try:
        # Save the new user (User.create(req.body)).
        db.users().insert_one({"username": username, "password": hashed})
    except DuplicateKeyError:
        # The username already exists in the database.
        return render_template("user/signup.html", error="That username is taken."), 400

    return redirect(url_for("user.login_form"))


@user_bp.get("/login")
def login_form():
    return render_template("user/login.html")


@user_bp.post("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    # find_one returns a dictionary for the matching user, or None if not found
    # (User.findOne({username})).
    user = db.users().find_one({"username": username})

    # Check the typed password against the stored hash (bcrypt.compare).
    # Hashes created by the old Node app ("$2a$...") verify fine here too.
    # `user["password"]` reads a key from the dictionary, like user.password in JS.
    if not user or not bcrypt.checkpw(password.encode(), user["password"].encode()):
        # 401 = Unauthorized. We use one vague message on purpose so attackers
        # can't tell whether the username or the password was wrong.
        return render_template("user/login.html", error="Invalid username or password."), 401

    # Remember who is logged in. Flask stores the session in a signed cookie
    # (req.session.username = username; req.session.loggedIn = true).
    session["username"] = username
    session["logged_in"] = True
    return redirect(url_for("movies.index"))


@user_bp.get("/logout")
def logout():
    # Wipe the session (req.session.destroy()).
    session.clear()
    return redirect(url_for("user.login_form"))
