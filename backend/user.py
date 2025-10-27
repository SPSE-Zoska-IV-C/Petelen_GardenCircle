from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import sqlite3
from .database import get_db


class User(UserMixin):
    def __init__(self, id, username, email, password_hash, bio="", profile_image=None, created_at=None, is_admin=False):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.bio = bio
        self.profile_image = profile_image
        self.created_at = created_at
        self.is_admin = bool(is_admin)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @staticmethod
    def get_by_id(user_id):
        db = get_db()
        row = db.execute(
            "SELECT id, username, email, password_hash, bio, profile_image, created_at, COALESCE(is_admin, 0) as is_admin FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if row:
            return User(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])
        return None
    
    @staticmethod
    def get_by_username(username):
        db = get_db()
        row = db.execute(
            "SELECT id, username, email, password_hash, bio, profile_image, created_at, COALESCE(is_admin, 0) as is_admin FROM users WHERE username = ?",
            (username,)
        ).fetchone()
        if row:
            return User(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])
        return None
    
    @staticmethod
    def get_by_email(email):
        db = get_db()
        row = db.execute(
            "SELECT id, username, email, password_hash, bio, profile_image, created_at, COALESCE(is_admin, 0) as is_admin FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        if row:
            return User(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7])
        return None
    
    @staticmethod
    def create(username, email, password, is_admin=False):
        db = get_db()
        password_hash = generate_password_hash(password)
        try:
            cursor = db.execute(
                "INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                (username, email, password_hash, int(is_admin))
            )
            db.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def update_bio(self, bio):
        db = get_db()
        db.execute(
            "UPDATE users SET bio = ? WHERE id = ?",
            (bio, self.id)
        )
        db.commit()
        self.bio = bio
    
    def update_profile_image(self, image_path):
        db = get_db()
        db.execute(
            "UPDATE users SET profile_image = ? WHERE id = ?",
            (image_path, self.id)
        )
        db.commit()
        self.profile_image = image_path
    
    @staticmethod
    def get_user_posts(username):
        db = get_db()
        user = User.get_by_username(username)
        if not user:
            return []
        rows = db.execute(
            "SELECT id, author_id, author, content, image_path, created_at FROM posts WHERE author_id = ? ORDER BY created_at DESC",
            (user.id,)
        ).fetchall()
        return [{"id": r[0], "author_id": r[1], "author": r[2], "content": r[3], "image_path": r[4], "created_at": r[5]} for r in rows]
