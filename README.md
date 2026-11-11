# MOVIED (Python)

A Python/Flask port of [Movied](https://github.com/lldeejeell102/movied), originally built with Express + EJS.
Users create an account and track which movies they've watched, looked up by title via the OMDb API.

## Stack mapping

| Original (Node)                  | Python port                         |
| -------------------------------- | ----------------------------------- |
| express                          | Flask                               |
| ejs views                        | Jinja2 templates (`templates/`)     |
| mongoose                         | pymongo (`db.py`)                   |
| bcryptjs                         | bcrypt (existing hashes still work) |
| express-session + connect-mongo  | Flask signed-cookie session         |
| method-override                  | `MethodOverrideMiddleware` in `app.py` |
| dotenv                           | python-dotenv                       |
| morgan                           | Flask/werkzeug request logging      |

It uses the same MongoDB collections (`users`, `movies`) and the same env vars, so it can run against your existing database.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in values (or copy the .env from the Node project)
python app.py
```

Production: `gunicorn app:app`

To try it without a real MongoDB, set `USE_MONGOMOCK=1` (needs `pip install -r requirements-dev.txt`); data is in-memory only.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Route Map

| Route Name   | Endpoint          | Method | Description |
| ------------ | ----------------- | ------ | ----------- |
| Movie Index  | /movies           | GET    | Renders all movies by user |
| Movie New    | /movies/add       | GET    | Search form for adding a movie |
| Movie Search | /movies/results   | POST   | Looks the movie up on OMDb |
| Movie Create | /movies           | POST   | Adds movie to user's list |
| Movie Edit   | /movies/:id       | GET    | Page to change the watched date |
| Movie Update | /movies/:id       | PUT    | Updates the watched date |
| Movie Delete | /movies/:id       | DELETE | Deletes a movie from the user's list |
| Signup       | /user/signup      | GET/POST | Create an account |
| Login        | /user/login       | GET/POST | Log in |
| Logout       | /user/logout      | GET    | Log out |

## Differences from the original

- Bad logins/duplicate signups show an error on the form instead of a plain "There was an error" page.
- Searching with a year but no title redirects back to the search form (the original request hung).
- A "not found" OMDb result shows a message instead of an empty card.
- Update/delete/show only touch movies owned by the logged-in user.
