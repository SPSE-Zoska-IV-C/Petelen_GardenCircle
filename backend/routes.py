from flask import render_template, request, redirect, url_for, jsonify, session, send_from_directory, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from datetime import datetime
import os

from .database import get_db
from .user import User
from .file_utils import save_uploaded_file, allowed_file, generate_unique_filename
from .news_fetcher import fetch_guardian_environment

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

login_manager = LoginManager()
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


def register_routes(app):
    login_manager.init_app(app)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # Configure file upload settings
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
    app.config['UPLOAD_FOLDER'] = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads"))
    
    upload_dir = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_dir, exist_ok=True)

    # Authentication Routes
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('posts_page'))
        
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            
            if not username or not password:
                return render_template("login.html", error="Prosím vyplň všetky polia")
            
            user = User.get_by_username(username)
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('posts_page'))
            else:
                return render_template("login.html", error="Nesprávne prihlasovacie údaje")
        
        return render_template("login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('posts_page'))
        
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            
            if not username or not email or not password:
                return render_template("register.html", error="Prosím vyplň všetky polia")
            
            if password != confirm_password:
                return render_template("register.html", error="Heslá sa nezhodujú")
            
            if len(password) < 6:
                return render_template("register.html", error="Heslo musí mať najmenej 6 znakov")
            
            if User.get_by_username(username):
                return render_template("register.html", error="Používateľské meno už existuje")
            
            if User.get_by_email(email):
                return render_template("register.html", error="Email už je registrovaný")
            
            user_id = User.create(username, email, password)
            if user_id:
                user = User.get_by_id(user_id)
                login_user(user)
                return redirect(url_for('posts_page'))
            else:
                return render_template("register.html", error="Registrácia zlyhala")
        
        return render_template("register.html")

    @app.route("/logout")
    def logout():
        logout_user()
        return redirect(url_for('login'))

    # Profile Routes
    @app.route("/user/<username>")
    @login_required
    def user_profile(username):
        user = User.get_by_username(username)
        if not user:
            return render_template("404.html"), 404
        
        db = get_db()
        # Get posts with same structure as posts page
        rows = db.execute(
            "SELECT id, author_id, author, content, created_at, image_path FROM posts WHERE author_id = ? ORDER BY created_at DESC",
            (user.id,)
        ).fetchall()
        
        if not rows:
            posts = []
        else:
            # Bulk fetch all like counts and comment counts
            post_ids = [r[0] for r in rows]
            placeholders = ','.join('?' * len(post_ids))
            
            # Get all like counts in one query
            like_counts = db.execute(
                f"SELECT post_id, COUNT(*) as count FROM likes WHERE post_id IN ({placeholders}) GROUP BY post_id",
                post_ids
            ).fetchall()
            like_counts_dict = {row[0]: row[1] for row in like_counts}
            
            # Get all comment counts in one query
            comment_counts = db.execute(
                f"SELECT post_id, COUNT(*) as count FROM comments WHERE post_id IN ({placeholders}) GROUP BY post_id",
                post_ids
            ).fetchall()
            comment_counts_dict = {row[0]: row[1] for row in comment_counts}
            
            # Get all liked posts for current user in one query
            liked_posts = set()
            if current_user.is_authenticated:
                liked_rows = db.execute(
                    f"SELECT post_id FROM likes WHERE post_id IN ({placeholders}) AND user_id = ?",
                    post_ids + [current_user.id]
                ).fetchall()
                liked_posts = {row[0] for row in liked_rows}
            
            # Format posts with all data
            posts = []
            for r in rows:
                post_id = r[0]
                posts.append({
                    "id": post_id,
                    "author_id": r[1],
                    "author": r[2],
                    "content": r[3],
                    "created_at": r[4],
                    "image_path": r[5],
                    "like_count": like_counts_dict.get(post_id, 0),
                    "liked": post_id in liked_posts,
                    "comment_count": comment_counts_dict.get(post_id, 0)
                })
        
        followers = db.execute("SELECT COUNT(1) FROM follows WHERE followed_id=?", (user.id,)).fetchone()[0]
        following = db.execute("SELECT COUNT(1) FROM follows WHERE follower_id=?", (user.id,)).fetchone()[0]
        is_following = False
        if current_user.is_authenticated and current_user.id != user.id:
            is_following = db.execute("SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?", (current_user.id, user.id)).fetchone() is not None
        return render_template("profile.html", user=user, posts=posts, followers=followers, following=following, is_following=is_following)

    @app.route("/edit-profile", methods=["GET", "POST"])
    @login_required
    def edit_profile():
        if request.method == "POST":
            bio = request.form.get("bio", "").strip()
            profile_image_url = request.form.get("profile_image", "").strip()
            
            current_user.update_bio(bio)
            
            # Handle file upload for profile picture
            if 'profile_image_file' in request.files:
                file = request.files['profile_image_file']
                if file and file.filename != '':
                    profile_image_path = save_uploaded_file(file, upload_dir)
                    if profile_image_path:
                        current_user.update_profile_image(profile_image_path)
                elif profile_image_url:
                    # Use URL if no file uploaded but URL provided
                    current_user.update_profile_image(profile_image_url)
            elif profile_image_url:
                current_user.update_profile_image(profile_image_url)
            
            flash("Profil bol aktualizovaný", "success")
            return redirect(url_for('user_profile', username=current_user.username))
        
        return render_template("edit_profile.html")

    # Home redirects to login if not authenticated
    @app.route("/")
    def home():
        if current_user.is_authenticated:
            return render_template("home.html")
        return redirect(url_for('login'))

    # Settings page
    @app.route('/settings')
    @login_required
    def settings():
        return render_template('settings.html')

    @app.route("/posts", methods=["GET"])
    @login_required
    def posts_page():
        db = get_db()
        # Optimized query with pagination (limit 20 posts)
        limit = 20
        rows = db.execute(
            "SELECT id, author_id, author, content, created_at, image_path FROM posts ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        
        if not rows:
            return render_template("posts.html", posts=[])
        
        # Bulk fetch all like counts and comment counts in 2 queries instead of N queries
        post_ids = [r[0] for r in rows]
        placeholders = ','.join('?' * len(post_ids))

        # Fetch author avatars for all authors in this page
        author_ids = [r[1] for r in rows if r[1] is not None]
        author_map = {}
        if author_ids:
            author_placeholders = ','.join('?' * len(author_ids))
            author_rows = db.execute(
                f"SELECT id, profile_image FROM users WHERE id IN ({author_placeholders})",
                author_ids
            ).fetchall()
            author_map = {row[0]: row[1] for row in author_rows}
        
        # Get all like counts in one query
        like_counts = db.execute(
            f"SELECT post_id, COUNT(*) as count FROM likes WHERE post_id IN ({placeholders}) GROUP BY post_id",
            post_ids
        ).fetchall()
        like_counts_dict = {row[0]: row[1] for row in like_counts}
        
        # Get all comment counts in one query
        comment_counts = db.execute(
            f"SELECT post_id, COUNT(*) as count FROM comments WHERE post_id IN ({placeholders}) GROUP BY post_id",
            post_ids
        ).fetchall()
        comment_counts_dict = {row[0]: row[1] for row in comment_counts}
        
        # Get all liked posts for current user in one query
        liked_posts = set()
        if current_user.is_authenticated:
            liked_rows = db.execute(
                f"SELECT post_id FROM likes WHERE post_id IN ({placeholders}) AND user_id = ?",
                post_ids + [current_user.id]
            ).fetchall()
            liked_posts = {row[0] for row in liked_rows}
        
        posts = []
        for r in rows:
            posts.append({
                "id": r[0],
                "author_id": r[1],
                "author": r[2],
                "author_image": author_map.get(r[1]),
                "content": r[3],
                "created_at": r[4],
                "image_path": r[5],
                "like_count": like_counts_dict.get(r[0], 0),
                "liked": r[0] in liked_posts,
                "comment_count": comment_counts_dict.get(r[0], 0),
            })
        return render_template("posts.html", posts=posts)

    @app.route("/api/posts", methods=["GET", "POST"])
    @login_required
    def posts():
        db = get_db()
        if request.method == "POST":
            data = request.get_json(silent=True) or request.form
            content = (data.get("content") or "").strip()
            if not content.strip():
                return jsonify({"error": "Content required"}), 400
            
            # Handle file upload
            image_path = None
            if 'file' in request.files:
                file = request.files['file']
                if file and file.filename != '':
                    image_path = save_uploaded_file(file, upload_dir)
            
            cur = db.execute(
                "INSERT INTO posts(author_id, author, content, image_path) VALUES(?, ?, ?, ?)",
                (current_user.id, current_user.username, content, image_path)
            )
            db.commit()
            if request.content_type and "application/json" in request.content_type:
                return jsonify({
                    "id": cur.lastrowid, "author": current_user.username, "content": content, "image_path": image_path,
                    "like_count": 0, "liked": False, "comment_count": 0, "created_at": None
                }), 201
            return redirect(url_for('posts_page'))
        else:
            # Optimized: limit results and use bulk queries
            limit = 30
            rows = db.execute(
                "SELECT id, author_id, author, content, created_at, image_path FROM posts ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
            
            if not rows:
                return jsonify([])
            
            # Bulk fetch counts
            post_ids = [r[0] for r in rows]
            placeholders = ','.join('?' * len(post_ids))

            # Fetch author avatars
            author_ids = [r[1] for r in rows if r[1] is not None]
            author_map = {}
            if author_ids:
                author_placeholders = ','.join('?' * len(author_ids))
                author_rows = db.execute(
                    f"SELECT id, profile_image FROM users WHERE id IN ({author_placeholders})",
                    author_ids
                ).fetchall()
                author_map = {row[0]: row[1] for row in author_rows}
            
            like_counts = db.execute(
                f"SELECT post_id, COUNT(*) as count FROM likes WHERE post_id IN ({placeholders}) GROUP BY post_id",
                post_ids
            ).fetchall()
            like_counts_dict = {row[0]: row[1] for row in like_counts}
            
            comment_counts = db.execute(
                f"SELECT post_id, COUNT(*) as count FROM comments WHERE post_id IN ({placeholders}) GROUP BY post_id",
                post_ids
            ).fetchall()
            comment_counts_dict = {row[0]: row[1] for row in comment_counts}
            
            liked_posts = set()
            if current_user.is_authenticated:
                liked_rows = db.execute(
                    f"SELECT post_id FROM likes WHERE post_id IN ({placeholders}) AND user_id = ?",
                    post_ids + [current_user.id]
                ).fetchall()
                liked_posts = {row[0] for row in liked_rows}
            
            data = []
            for r in rows:
                data.append({
                    "id": r[0],
                    "author_id": r[1],
                    "author": r[2],
                    "author_image": author_map.get(r[1]),
                    "content": r[3],
                    "created_at": r[4],
                    "image_path": r[5],
                    "like_count": like_counts_dict.get(r[0], 0),
                    "liked": r[0] in liked_posts,
                    "comment_count": comment_counts_dict.get(r[0], 0)
                })
            return jsonify(data)

    @app.route("/posts/<int:post_id>")
    @login_required
    def post_detail(post_id: int):
        db = get_db()
        pc = db.execute("SELECT id, author_id, author, content, created_at, image_path FROM posts WHERE id=?", (post_id,)).fetchone()
        if not pc:
            return render_template("404.html"), 404
        like_count = db.execute("SELECT COUNT(1) FROM likes WHERE post_id=?", (post_id,)).fetchone()[0]
        liked = db.execute("SELECT 1 FROM likes WHERE post_id=? AND user_id=?", (post_id, current_user.id)).fetchone() is not None
        comments = db.execute(
            "SELECT id, author_id, author, text, created_at FROM comments WHERE post_id=? ORDER BY created_at ASC",
            (post_id,),
        ).fetchall()
        comment_author_ids = [r[1] for r in comments if r[1] is not None]
        comment_author_map = {}
        if comment_author_ids:
            ca_placeholders = ','.join('?' * len(comment_author_ids))
            comment_author_rows = db.execute(
                f"SELECT id, profile_image FROM users WHERE id IN ({ca_placeholders})",
                comment_author_ids
            ).fetchall()
            comment_author_map = {row[0]: row[1] for row in comment_author_rows}

        comments_fmt = [
            {
                "id": r[0],
                "author_id": r[1],
                "author": r[2],
                "author_image": comment_author_map.get(r[1]),
                "text": r[3],
                "created_at": r[4]
            } for r in comments
        ]
        post_author_image = None
        if pc[1]:
            post_author_image = comment_author_map.get(pc[1])
            if post_author_image is None:
                row = db.execute("SELECT profile_image FROM users WHERE id=?", (pc[1],)).fetchone()
                post_author_image = row[0] if row else None

        post = {
            "id": pc[0],
            "author_id": pc[1],
            "author": pc[2],
            "author_image": post_author_image,
            "content": pc[3],
            "created_at": pc[4],
            "image_path": pc[5],
            "like_count": like_count,
            "liked": liked
        }
        return render_template("post.html", post=post, comments=comments_fmt)

    @app.route("/api/posts/<int:post_id>/comments", methods=["GET", "POST"])
    @login_required
    def add_comment(post_id: int):
        db = get_db()
        if request.method == "GET":
            rows = db.execute(
                "SELECT id, author_id, author, text, created_at FROM comments WHERE post_id=? ORDER BY created_at ASC",
                (post_id,),
            ).fetchall()
            author_ids = [r[1] for r in rows if r[1] is not None]
            author_map = {}
            if author_ids:
                a_placeholders = ','.join('?' * len(author_ids))
                a_rows = db.execute(
                    f"SELECT id, profile_image FROM users WHERE id IN ({a_placeholders})",
                    author_ids
                ).fetchall()
                author_map = {row[0]: row[1] for row in a_rows}
            return jsonify([
                {"id": r[0], "author_id": r[1], "author": r[2], "author_image": author_map.get(r[1]), "text": r[3], "created_at": r[4]} for r in rows
            ])
        data = request.get_json(silent=True) or request.form
        text = (data.get("text") or "").strip()
        if not text.strip():
            return jsonify({"error": "Text required"}), 400
        cur = db.execute(
            "INSERT INTO comments(post_id, author_id, author, text) VALUES(?, ?, ?, ?)",
            (post_id, current_user.id, current_user.username, text)
        )
        db.commit()
        if request.content_type and "application/json" in request.content_type:
            return jsonify({"id": cur.lastrowid, "author": current_user.username, "author_id": current_user.id, "author_image": current_user.profile_image, "text": text}), 201
        return redirect(url_for('post_detail', post_id=post_id))

    @app.route("/api/posts/<int:post_id>/answer", methods=["POST"])
    @login_required
    def auto_answer_post(post_id: int):
        """Generate a concise AI helper reply for a post (ephemeral; not saved)."""
        db = get_db()
        post = db.execute(
            "SELECT id, author, content FROM posts WHERE id=?",
            (post_id,)
        ).fetchone()
        if not post:
            return jsonify({"error": "Príspevok sa nenašiel."}), 404

        api_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
        if not api_key:
            return jsonify({"error": "AI nie je nastavená. Skontroluj API kľúč."}), 500
        if not GEMINI_AVAILABLE:
            return jsonify({"error": "Chýba balíček google-generativeai."}), 500

        genai.configure(api_key=api_key)
        model_names = [
            'gemini-2.5-flash',
            'gemini-2.5-pro-preview-05-06',
            'gemini-2.5-flash-preview-05-20',
            'gemini-2.5-pro-preview-03-25',
            'gemini-pro',
        ]

        payload = request.get_json(silent=True) or {}
        answer_length = (payload.get("length") or "short").lower()
        if answer_length not in ("short", "long"):
            answer_length = "short"

        if answer_length == "short":
            instructions = "Odpovedaj maximálne v 2 krátkych vetách."
            max_chars = 400
        else:
            instructions = "Môžeš použiť 4–5 viet s praktickými tipmi."
            max_chars = 900

        system_prompt = f"""You are GardenCircle Guide, a Slovak nature mentor.
        {instructions}
        Ostaň vecný, priateľský, pripomeň bezpečnosť alebo legálne zásady, ak je to vhodné.
        Ak zadanie nie je jasné, ponúkni všeobecný tip a vyzvi používateľa, aby spresnil otázku.
        Text príspevku:
        {{post_content}}
        Vytvor odpoveď."""

        full_prompt = system_prompt.format(post_content=post["content"])
        response = None
        last_error = None
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(full_prompt)
                break
            except Exception as e:
                last_error = str(e)
                continue

        if response is None or not getattr(response, "text", "").strip():
            return jsonify({"error": f"AI odpoveď sa nepodarila: {last_error or 'neznáma chyba'}"}), 500

        reply = response.text.strip()
        reply = reply[:max_chars]

        # Return reply only to the requesting user; do NOT persist to DB.
        return jsonify({
            "author": "GardenCircle Guide",
            "text": reply
        })

    @app.route("/api/posts/<int:post_id>", methods=["DELETE"])
    @login_required
    def delete_post(post_id: int):
        db = get_db()
        # Check if user owns the post
        post = db.execute("SELECT author_id FROM posts WHERE id=?", (post_id,)).fetchone()
        if post and post[0] == current_user.id:
            db.execute("DELETE FROM posts WHERE id=?", (post_id,))
            db.commit()
        return ("", 204)

    @app.route("/like/<int:post_id>", methods=["POST"])
    @login_required
    def toggle_like(post_id: int):
        db = get_db()
        exists = db.execute("SELECT 1 FROM posts WHERE id=?", (post_id,)).fetchone()
        if not exists:
            return jsonify({"error": "Not found"}), 404
        liked = db.execute("SELECT 1 FROM likes WHERE post_id=? AND user_id=?", (post_id, current_user.id)).fetchone() is not None
        if liked:
            db.execute("DELETE FROM likes WHERE post_id=? AND user_id=?", (post_id, current_user.id))
            db.commit()
            liked = False
        else:
            try:
                db.execute("INSERT OR IGNORE INTO likes(user_id, post_id) VALUES(?, ?)", (current_user.id, post_id))
                db.commit()
                liked = True
            except Exception:
                pass
        count = db.execute("SELECT COUNT(1) FROM likes WHERE post_id=?", (post_id,)).fetchone()[0]
        return jsonify({"liked": liked, "count": count})

    @app.route("/follow/<username>", methods=["POST"])
    @login_required
    def follow_user(username):
        target = User.get_by_username(username)
        if not target or target.id == current_user.id:
            return jsonify({"error": "Invalid user"}), 400
        db = get_db()
        db.execute("INSERT OR IGNORE INTO follows(follower_id, followed_id) VALUES(?, ?)", (current_user.id, target.id))
        db.commit()
        followers = db.execute("SELECT COUNT(1) FROM follows WHERE followed_id=?", (target.id,)).fetchone()[0]
        following = db.execute("SELECT COUNT(1) FROM follows WHERE follower_id=?", (current_user.id,)).fetchone()[0]
        return jsonify({"following": True, "followers": followers, "following_count": following})

    @app.route("/unfollow/<username>", methods=["POST"])
    @login_required
    def unfollow_user(username):
        target = User.get_by_username(username)
        if not target or target.id == current_user.id:
            return jsonify({"error": "Invalid user"}), 400
        db = get_db()
        db.execute("DELETE FROM follows WHERE follower_id=? AND followed_id=?", (current_user.id, target.id))
        db.commit()
        followers = db.execute("SELECT COUNT(1) FROM follows WHERE followed_id=?", (target.id,)).fetchone()[0]
        following = db.execute("SELECT COUNT(1) FROM follows WHERE follower_id=?", (current_user.id,)).fetchone()[0]
        return jsonify({"following": False, "followers": followers, "following_count": following})

    @app.route("/articles")
    @login_required
    def articles():
        db = get_db()
        rows = db.execute("SELECT id, title, content, image_path, created_at FROM articles ORDER BY created_at DESC").fetchall()
        items = [{"id":r[0],"title":r[1],"content":r[2],"image_path":r[3],"created_at":r[4]} for r in rows]
        return render_template("articles.html", items=items)

    @app.route("/articles/<int:article_id>")
    @login_required
    def article_detail(article_id: int):
        db = get_db()
        row = db.execute("SELECT id, title, content, image_path, created_at FROM articles WHERE id=?", (article_id,)).fetchone()
        if not row:
            return render_template("404.html"), 404
        article = {"id": row[0], "title": row[1], "content": row[2], "image_path": row[3], "created_at": row[4]}
        return render_template("article_detail.html", article=article)

    @app.route("/news")
    @login_required
    def news():
        error_message = None
        try:
            bypass_cache = request.args.get("refresh") in ("1", "true", "yes")
            articles = fetch_guardian_environment(limit=12, bypass_cache=bypass_cache)
        except Exception:
            articles = []
            error_message = "Couldn't load news at the moment. Please try again later."

        return render_template("news.html", articles=articles, error_message=error_message)

    @app.route("/about")
    @login_required
    def about():
        return render_template("about.html")

    @app.route("/contact")
    @login_required
    def contact():
        return render_template("contact.html")

    @app.route("/chatbot")
    @login_required
    def chatbot_placeholder():
        return render_template("chatbot.html")

    @app.route("/api/chatbot", methods=["POST"])
    @login_required
    def api_chatbot():
        """Handle chatbot requests using Google AI Studio (Gemini API)"""
        try:
            data = request.get_json()
            message = data.get("message", "").strip()
            
            if not message:
                return jsonify({"error": "Message is required"}), 400
            
            # Get API key from environment variable
            api_key = os.getenv("GOOGLE_AI_STUDIO_API_KEY")
            
            if not api_key:
                return jsonify({
                    "error": "Google AI Studio API key not configured. Please set GOOGLE_AI_STUDIO_API_KEY environment variable."
                }), 500
            
            if not GEMINI_AVAILABLE:
                return jsonify({
                    "error": "Google Generative AI library not installed. Please run: pip install google-generativeai"
                }), 500
            
            # Configure Gemini API
            genai.configure(api_key=api_key)
            
            # Try different model names - use available gemini-2.5 models
            # Try models in order of preference (stable versions first, then preview)
            model_names = [
                'gemini-2.5-flash',  # Stable flash version (fastest)
                'gemini-2.5-pro-preview-05-06',  # Latest pro preview
                'gemini-2.5-flash-preview-05-20',  # Latest flash preview
                'gemini-2.5-pro-preview-03-25',  # Older pro preview
                'gemini-pro',  # Fallback to original (may not work)
            ]
            
            model = None
            last_error = None
            
            # Create a system prompt for nature/outdoor assistance
            system_prompt = """You are GardenCircle Guide, a friendly AI expert on všetko zo sveta prírody.
            Rozprávaj sa po slovensky a pokrývaj:
            - rastliny a záhradu
            - huby a ich bezpečný zber
            - zvieratá, stopovanie, voľne žijúcu zver
            - počasie, klímu, ekológiu a environmentálne témy
            - turistiku, kempovanie, udržateľné pobyty v prírode a ochranu životného prostredia.
            Buď povzbudivý, poskytuj praktické tipy, zdôrazni bezpečnosť, legislatívu a etiku.
            Ak si nie si istý, daj všeobecné odporúčania alebo bezpečnostné rady a navrhni príbuznú prírodnú tému.
            Odmietni len otázky úplne mimo prírody alebo nebezpečné/ilegálne požiadavky; aj vtedy odpovedz zdvorilo a ponúkni súvisiacu prírodnú oblasť.
            Vždy podporuj udržateľné a legálne správanie."""
            
            # Combine system prompt with user message
            full_prompt = f"{system_prompt}\n\nUser question: {message}\n\nAssistant:"
            
            # Try each model until one works
            response = None
            for model_name in model_names:
                try:
                    model = genai.GenerativeModel(model_name)
                    # Try to generate response
                    response = model.generate_content(full_prompt)
                    break  # Success, exit loop
                except Exception as e:
                    last_error = str(e)
                    response = None
                    continue  # Try next model
            
            if response is None:
                # If all models failed, try to list available models for debugging
                try:
                    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model_list = ', '.join(available_models[:5]) if available_models else "žiadne"
                    return jsonify({
                        "error": f"Žiadny z modelov nefunguje. Dostupné modely: {model_list}. Posledná chyba: {last_error}. Skúste aktualizovať: pip install --upgrade google-generativeai"
                    }), 500
                except Exception as list_error:
                    return jsonify({
                        "error": f"Nepodarilo sa nájsť fungujúci model. Posledná chyba: {last_error}. Skúste aktualizovať google-generativeai: pip install --upgrade google-generativeai"
                    }), 500
            
            reply = response.text if response.text else "Prepáč, nepodarilo sa mi vygenerovať odpoveď."
            
            # Save messages to database
            db = get_db()
            try:
                # Save user message
                db.execute(
                    "INSERT INTO chat_messages (user_id, role, message) VALUES (?, ?, ?)",
                    (current_user.id, 'user', message)
                )
                # Save bot reply
                db.execute(
                    "INSERT INTO chat_messages (user_id, role, message) VALUES (?, ?, ?)",
                    (current_user.id, 'bot', reply)
                )
                db.commit()
            except Exception as db_error:
                # Log error but don't fail the request
                print(f"Error saving chat message: {db_error}")
            
            return jsonify({"reply": reply})
            
        except Exception as e:
            return jsonify({"error": f"Chyba pri komunikácii s AI: {str(e)}"}), 500

    @app.route("/api/chatbot/history", methods=["GET"])
    @login_required
    def api_chatbot_history():
        """Get chat history for the current user"""
        try:
            db = get_db()
            messages = db.execute(
                "SELECT role, message, created_at FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC",
                (current_user.id,)
            ).fetchall()
            
            history = [
                {
                    "role": msg[0],
                    "message": msg[1],
                    "created_at": msg[2]
                }
                for msg in messages
            ]
            
            return jsonify({"history": history})
        except Exception as e:
            return jsonify({"error": f"Chyba pri načítaní histórie: {str(e)}"}), 500

    @app.route("/api/chatbot/clear", methods=["POST"])
    @login_required
    def api_chatbot_clear():
        """Clear chat history for the current user"""
        try:
            db = get_db()
            db.execute(
                "DELETE FROM chat_messages WHERE user_id = ?",
                (current_user.id,)
            )
            db.commit()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": f"Chyba pri vymazaní histórie: {str(e)}"}), 500

    # Admin auth (unchanged)
    @app.route('/admin/login', methods=['GET','POST'])
    def admin_login():
        if request.method == 'POST':
            pw = (request.form.get('password') or '').strip()
            if pw == 'admin':
                session['is_admin'] = True
                return redirect(url_for('admin_panel'))
            return render_template('admin_login.html', error='Nesprávne heslo')
        return render_template('admin_login.html')

    @app.route('/admin/logout')
    def admin_logout():
        session.pop('is_admin', None)
        return redirect(url_for('home'))

    @app.route('/admin')
    def admin_panel():
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        db = get_db()
        rows = db.execute(
            "SELECT id, author, content, created_at FROM posts ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        user_rows = db.execute(
            """
            SELECT id, username, email, bio, profile_image, created_at, COALESCE(is_admin, 0) as is_admin
            FROM users
            ORDER BY created_at DESC
            LIMIT 50
            """
        ).fetchall()
        recent_posts = [
            {"id": r[0], "author": r[1], "content": r[2], "created_at": r[3]}
            for r in rows
        ]
        users = [
            {
                "id": u["id"],
                "username": u["username"],
                "email": u["email"],
                "bio": u["bio"],
                "profile_image": u["profile_image"],
                "created_at": u["created_at"],
                "is_admin": bool(u["is_admin"]),
            }
            for u in user_rows
        ]
        return render_template('admin_panel.html', recent_posts=recent_posts, users=users)

    @app.route('/admin/upload', methods=['POST'])
    def admin_upload():
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        f = request.files.get('image')
        if not f:
            return redirect(url_for('admin_panel'))
        fname = f.filename
        path = os.path.join(upload_dir, fname)
        f.save(path)
        return jsonify({"path": f"/static/uploads/{fname}"})

    @app.route('/admin/articles', methods=['POST'])
    def admin_add_article():
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        title = (request.form.get('title') or '').strip()
        content = (request.form.get('content') or '').strip()
        external_image = (request.form.get('external_image_url') or '').strip()
        image_file = request.files.get('image_file')
        image_path = external_image or None
        if image_file and image_file.filename:
            uploaded = save_uploaded_file(image_file, upload_dir)
            if uploaded:
                image_path = uploaded
        if not title or not content:
            return redirect(url_for('admin_panel'))
        db = get_db()
        db.execute("INSERT INTO articles(title, content, image_path) VALUES(?,?,?)", (title, content, image_path))
        db.commit()
        return redirect(url_for('articles'))

    @app.route('/admin/delete-post', methods=['POST'])
    def admin_delete_post():
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        post_id = request.form.get('post_id')
        try:
            post_id = int(post_id)
        except (TypeError, ValueError):
            return redirect(url_for('admin_panel'))
        db = get_db()
        db.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
        db.execute("DELETE FROM likes WHERE post_id=?", (post_id,))
        db.execute("DELETE FROM posts WHERE id=?", (post_id,))
        db.commit()
        return redirect(url_for('admin_panel'))

    @app.route('/admin/delete-user', methods=['POST'])
    def admin_delete_user():
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        user_id = request.form.get('user_id')
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return redirect(url_for('admin_panel'))

        db = get_db()
        user = db.execute(
            "SELECT id, COALESCE(is_admin, 0) as is_admin FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

        # Prevent deleting missing or admin accounts
        if not user or user["is_admin"]:
            return redirect(url_for('admin_panel'))

        # Clean up related content before removing the user entry
        db.execute("DELETE FROM comments WHERE author_id=?", (user_id,))
        db.execute("DELETE FROM posts WHERE author_id=?", (user_id,))
        db.execute("DELETE FROM follows WHERE follower_id=? OR followed_id=?", (user_id, user_id))
        db.execute("DELETE FROM likes WHERE user_id=?", (user_id,))
        db.execute("DELETE FROM chat_messages WHERE user_id=?", (user_id,))
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()
        return redirect(url_for('admin_panel'))

    @app.route('/admin/news', methods=['POST'])
    def admin_add_news():
        # Manual news creation is disabled; live news are fetched from NewsAPI
        return render_template('404.html'), 404

    @app.route('/admin/post-image', methods=['POST'])
    def admin_add_post_image():
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        post_id = request.form.get('post_id')
        image_path = request.form.get('image_path')
        if not post_id or not image_path:
            return redirect(url_for('admin_panel'))
        db = get_db()
        db.execute("UPDATE posts SET image_path=? WHERE id=?", (image_path, post_id))
        db.commit()
        return redirect(url_for('posts_page'))
