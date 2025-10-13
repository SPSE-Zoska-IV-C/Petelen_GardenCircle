# backend/main.py
from flask import Flask
from .database import close_db
from .models import ensure_schema

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
    # Initialize DB schema inside app context
    with app.app_context():
        ensure_schema()
    return app


if __name__ == "__main__":
    create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
