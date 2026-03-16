# backend/main.py
from flask import Flask
from dotenv import load_dotenv
import os
from .database import close_db
from .models import ensure_schema

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder="../static", template_folder="../templates")


@app.route("/")
def root():
    from .routes import render_template
    return render_template("home.html")


def create_app():
    # Defer imports to avoid circulars during setup
    from .routes import register_routes
    register_routes(app)
    app.teardown_appcontext(close_db)

    # Performance defaults (safe, behavior-preserving)
    # - gzip/br compression for text responses (templates, css, js, json)
    # - modest caching for static files in non-debug mode
    try:
        from flask_compress import Compress
        app.config.setdefault("COMPRESS_MIMETYPES", [
            "text/html",
            "text/css",
            "application/javascript",
            "text/javascript",
            "application/json",
            "image/svg+xml",
        ])
        app.config.setdefault("COMPRESS_LEVEL", 6)
        app.config.setdefault("COMPRESS_MIN_SIZE", 512)
        Compress(app)
    except Exception:
        # Compression is optional; app should still run without it.
        pass

    app.config.setdefault("SEND_FILE_MAX_AGE_DEFAULT", 0 if app.debug else 3600)

    @app.after_request
    def _add_cache_headers(resp):
        try:
            # Only touch static responses; keep dynamic pages uncached by default.
            if (resp.direct_passthrough is False) and (resp.mimetype or "").startswith("text/"):
                pass
            path = (getattr(resp, "request", None) and getattr(resp.request, "path", "")) or ""
        except Exception:
            path = ""

        # Flask doesn't attach request to response, use global request safely.
        try:
            from flask import request as _req
            path = _req.path
        except Exception:
            path = path or ""

        if path.startswith("/static/"):
            # Static assets: allow browser caching but keep it modest since filenames aren't hashed.
            resp.headers.setdefault("Cache-Control", "public, max-age=3600")
        return resp

    # Initialize DB schema inside app context
    with app.app_context():
        ensure_schema()
    return app


if __name__ == "__main__":
    create_app()
    debug = os.environ.get("FLASK_DEBUG", "").strip() in ("1", "true", "yes", "on")
    app.run(host="127.0.0.1", port=5000, debug=debug)
