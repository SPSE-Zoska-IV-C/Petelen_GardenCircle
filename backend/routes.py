from flask import render_template, request, redirect, url_for, jsonify, session, send_from_directory, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import os

from .database import get_db
from .user import User
from .file_utils import save_uploaded_file, allowed_file, generate_unique_filename

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
        
        posts = User.get_user_posts(username)
        return render_template("profile.html", user=user, posts=posts)

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

    @app.route("/posts", methods=["GET"])
    @login_required
    def posts_page():
        db = get_db()
        cur = db.execute("SELECT id, author_id, author, content, created_at, image_path FROM posts ORDER BY created_at DESC")
        posts = [
            {"id": r[0], "author_id": r[1], "author": r[2], "content": r[3], "created_at": r[4], "image_path": r[5]}
            for r in cur.fetchall()
        ]
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
                return jsonify({"id": cur.lastrowid, "author": current_user.username, "content": content, "image_path": image_path}), 201
            return redirect(url_for('posts_page'))
        else:
            cur = db.execute("SELECT id, author_id, author, content, created_at, image_path FROM posts ORDER BY created_at DESC")
            data = [
                {"id": r[0], "author_id": r[1], "author": r[2], "content": r[3], "created_at": r[4], "image_path": r[5]}
                for r in cur.fetchall()
            ]
            return jsonify(data)

    @app.route("/posts/<int:post_id>")
    @login_required
    def post_detail(post_id: int):
        db = get_db()
        pc = db.execute("SELECT id, author_id, author, content, created_at, image_path FROM posts WHERE id=?", (post_id,)).fetchone()
        if not pc:
            return render_template("404.html"), 404
        comments = db.execute(
            "SELECT id, author_id, author, text, created_at FROM comments WHERE post_id=? ORDER BY created_at ASC",
            (post_id,),
        ).fetchall()
        comments_fmt = [
            {"id": r[0], "author_id": r[1], "author": r[2], "text": r[3], "created_at": r[4]} for r in comments
        ]
        post = {"id": pc[0], "author_id": pc[1], "author": pc[2], "content": pc[3], "created_at": pc[4], "image_path": pc[5]}
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
            return jsonify([
                {"id": r[0], "author_id": r[1], "author": r[2], "text": r[3], "created_at": r[4]} for r in rows
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
            return jsonify({"id": cur.lastrowid, "author": current_user.username, "text": text}), 201
        return redirect(url_for('post_detail', post_id=post_id))

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

    @app.route("/articles")
    @login_required
    def articles():
        db = get_db()
        rows = db.execute("SELECT id, title, content, image_path, created_at FROM articles ORDER BY created_at DESC").fetchall()
        items = [{"id":r[0],"title":r[1],"content":r[2],"image_path":r[3],"created_at":r[4]} for r in rows]
        return render_template("articles.html", items=items)

    @app.route("/news")
    @login_required
    def news():
        db = get_db()
        rows = db.execute("SELECT id, title, content, image_path, created_at FROM news ORDER BY created_at DESC").fetchall()
        items = [{"id":r[0],"title":r[1],"content":r[2],"image_path":r[3],"created_at":r[4]} for r in rows]
        return render_template("news.html", items=items)

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

    @app.route("/api/chatbot", methods=["GET"])
    @login_required
    def api_chatbot_placeholder():
        return jsonify({"reply": "Coming soon"})

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
        return render_template('admin_panel.html')

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
        title = request.form.get('title','').strip()
        content = request.form.get('content','').strip()
        image_path = request.form.get('image_path')
        if not title or not content:
            return redirect(url_for('admin_panel'))
        db = get_db()
        db.execute("INSERT INTO articles(title, content, image_path) VALUES(?,?,?)", (title, content, image_path))
        db.commit()
        return redirect(url_for('articles'))

    @app.route('/admin/news', methods=['POST'])
    def admin_add_news():
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        title = request.form.get('title','').strip()
        content = request.form.get('content','').strip()
        image_path = request.form.get('image_path')
        if not title or not content:
            return redirect(url_for('admin_panel'))
        db = get_db()
        db.execute("INSERT INTO news(title, content, image_path) VALUES(?,?,?)", (title, content, image_path))
        db.commit()
        return redirect(url_for('news'))

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
