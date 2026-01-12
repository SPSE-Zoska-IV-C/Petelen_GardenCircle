from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def admin_required(f):
    """Decorator to require admin status for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash("Musíš byť prihlásený", "error")
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash("Nemáš oprávnenie na prístup k tejto stránke", "error")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

