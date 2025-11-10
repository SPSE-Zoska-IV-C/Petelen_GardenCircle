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

        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            UNIQUE(user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            followed_id INTEGER NOT NULL,
            UNIQUE(follower_id, followed_id),
            FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (followed_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'bot')),
            message TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        
        -- Performance indexes
        CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);
        CREATE INDEX IF NOT EXISTS idx_likes_post_id ON likes(post_id);
        CREATE INDEX IF NOT EXISTS idx_likes_user_id ON likes(user_id);
        CREATE INDEX IF NOT EXISTS idx_likes_user_post ON likes(user_id, post_id);
        CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
        CREATE INDEX IF NOT EXISTS idx_comments_author_id ON comments(author_id);
        CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower_id);
        CREATE INDEX IF NOT EXISTS idx_follows_followed ON follows(followed_id);
        CREATE INDEX IF NOT EXISTS idx_chat_messages_user_id ON chat_messages(user_id);
        CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at DESC);
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
    
    # Cleanup legacy/invalid data (best-effort)
    try:
        db.executescript(
            """
            DELETE FROM likes WHERE user_id IS NULL OR user_id = 0;
            DELETE FROM follows WHERE follower_id IS NULL OR followed_id IS NULL;
            DELETE FROM comments WHERE author_id IS NULL OR author_id = 0;
            DELETE FROM posts WHERE author_id IS NULL OR author_id = 0;
            VACUUM;
            """
        )
    except Exception:
        pass

    db.commit()