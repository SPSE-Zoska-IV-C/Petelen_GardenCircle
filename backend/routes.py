from flask import render_template, request, redirect, url_for, jsonify, session, send_from_directory
import os

from .database import get_db


def register_routes(app):
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")
    upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads"))
    os.makedirs(upload_dir, exist_ok=True)

    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/posts", methods=["GET"])
    def posts_page():
        db = get_db()
        cur = db.execute("SELECT id, author, content, created_at FROM posts ORDER BY created_at DESC")
        posts = [
            {"id": r[0], "author": r[1], "content": r[2], "created_at": r[3]}
            for r in cur.fetchall()
        ]
        return render_template("posts.html", posts=posts)

    # API endpoints for posts
    @app.route("/api/posts", methods=["GET", "POST"])
    def posts():
        db = get_db()
        if request.method == "POST":
            data = request.get_json(silent=True) or request.form
            author = (data.get("author") or "Anonym").strip()
            content = (data.get("content") or "").strip()
            if not content.strip():
                return jsonify({"error": "Content required"}), 400
            cur = db.execute(
                "INSERT INTO posts(author, content) VALUES(?, ?)", (author, content)
            )
            db.commit()
            if request.content_type and "application/json" in request.content_type:
                return jsonify({"id": cur.lastrowid, "author": author, "content": content}), 201
            return redirect(url_for('posts_page'))
        else:
            cur = db.execute("SELECT id, author, content, created_at FROM posts ORDER BY created_at DESC")
            data = [
                {"id": r[0], "author": r[1], "content": r[2], "created_at": r[3]}
                for r in cur.fetchall()
            ]
            return jsonify(data)

    @app.route("/posts/<int:post_id>")
    def post_detail(post_id: int):
        db = get_db()
        pc = db.execute("SELECT id, author, content, created_at FROM posts WHERE id=?", (post_id,)).fetchone()
        if not pc:
            return render_template("404.html"), 404
        comments = db.execute(
            "SELECT id, author, text, created_at FROM comments WHERE post_id=? ORDER BY created_at ASC",
            (post_id,),
        ).fetchall()
        comments_fmt = [
            {"id": r[0], "author": r[1], "text": r[2], "created_at": r[3]} for r in comments
        ]
        post = {"id": pc[0], "author": pc[1], "content": pc[2], "created_at": pc[3]}
        return render_template("post.html", post=post, comments=comments_fmt)

    @app.route("/api/posts/<int:post_id>/comments", methods=["GET", "POST"])
    def add_comment(post_id: int):
        db = get_db()
        if request.method == "GET":
            rows = db.execute(
                "SELECT id, author, text, created_at FROM comments WHERE post_id=? ORDER BY created_at ASC",
                (post_id,),
            ).fetchall()
            return jsonify([
                {"id": r[0], "author": r[1], "text": r[2], "created_at": r[3]} for r in rows
            ])
        data = request.get_json(silent=True) or request.form
        author = (data.get("author") or "Anonym").strip()
        text = (data.get("text") or "").strip()
        if not text.strip():
            return jsonify({"error": "Text required"}), 400
        cur = db.execute(
            "INSERT INTO comments(post_id, author, text) VALUES(?, ?, ?)", (post_id, author, text)
        )
        db.commit()
        if request.content_type and "application/json" in request.content_type:
            return jsonify({"id": cur.lastrowid, "author": author, "text": text}), 201
        return redirect(url_for('post_detail', post_id=post_id))

    @app.route("/api/posts/<int:post_id>", methods=["DELETE"]) 
    def delete_post(post_id: int):
        db = get_db()
        db.execute("DELETE FROM posts WHERE id=?", (post_id,))
        db.commit()
        return ("", 204)

    @app.route("/articles")
    def articles():
        db = get_db()
        rows = db.execute("SELECT id, title, content, image_path, created_at FROM articles ORDER BY created_at DESC").fetchall()
        items = [{"id":r[0],"title":r[1],"content":r[2],"image_path":r[3],"created_at":r[4]} for r in rows]
        return render_template("articles.html", items=items)

    @app.route("/news")
    def news():
        db = get_db()
        rows = db.execute("SELECT id, title, content, image_path, created_at FROM news ORDER BY created_at DESC").fetchall()
        items = [{"id":r[0],"title":r[1],"content":r[2],"image_path":r[3],"created_at":r[4]} for r in rows]
        return render_template("news.html", items=items)

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/contact")
    def contact():
        return render_template("contact.html")

    @app.route("/chatbot")
    def chatbot_placeholder():
        return render_template("chatbot.html")

    @app.route("/api/chatbot", methods=["GET"])  # placeholder JSON endpoint
    def api_chatbot_placeholder():
        return jsonify({"reply": "Coming soon"})

    # Admin auth
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

