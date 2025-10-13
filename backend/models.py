from .database import get_db


def ensure_schema():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author TEXT NOT NULL DEFAULT 'Anonym',
            content TEXT NOT NULL,
            image_path TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            author TEXT NOT NULL DEFAULT 'Anonym',
            text TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
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
    try:
        db.execute("ALTER TABLE posts ADD COLUMN image_path TEXT")
    except Exception:
        pass
    db.commit()


