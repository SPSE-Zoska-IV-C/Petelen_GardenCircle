from .database import get_db


def ensure_schema():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            bio TEXT DEFAULT '',
            profile_image TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER,
            author TEXT NOT NULL DEFAULT 'Anonym',
            content TEXT NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author_id INTEGER,
            author TEXT NOT NULL DEFAULT 'Anonym',
            text TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
            FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    
    # Best-effort migrations for existing DBs
    migrations = [
        ("ALTER TABLE posts ADD COLUMN image_path TEXT", None),
        ("ALTER TABLE posts ADD COLUMN author_id INTEGER", None),
        ("ALTER TABLE comments ADD COLUMN author_id INTEGER", None),
        ("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0", None)
    ]
    
    for migration_sql, _ in migrations:
        try:
            db.execute(migration_sql)
        except Exception:
            pass
    
    db.commit()