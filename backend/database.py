import os
import sqlite3
from flask import g


DB_PATH = os.path.join(os.path.dirname(__file__), "gardencircle.db")


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db


def close_db(e=None):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()
        g._database = None


