import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from flask import current_app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_unique_filename(filename):
    """Generate a unique filename to avoid conflicts"""
    if filename and allowed_file(filename):
        # Get file extension
        ext = filename.rsplit('.', 1)[1].lower()
        # Generate unique filename with timestamp and UUID
        unique_name = f"{uuid.uuid4().hex[:12]}_{filename.rsplit('.', 1)[0][:30]}"
        unique_name = secure_filename(unique_name)
        return f"{unique_name}.{ext}"
    return None


def save_uploaded_file(file, upload_folder):
    """
    Save an uploaded file to the upload folder
    
    Args:
        file: Flask file object from request.files
        upload_folder: Path to the upload folder
    
    Returns:
        str: Relative path to the uploaded file, or None if save failed
    """
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        return None
    
    # Generate unique filename
    filename = generate_unique_filename(file.filename)
    if not filename:
        return None
    
    # Ensure upload folder exists
    os.makedirs(upload_folder, exist_ok=True)
    
    # Save file
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    # Return relative path from static folder
    return f"uploads/{filename}"


def delete_file(file_path):
    """Delete a file if it exists"""
    try:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            return True
    except Exception:
        pass
    return False


def get_full_path(relative_path):
    """Get full filesystem path from relative static path"""
    if not relative_path:
        return None
    return os.path.join(current_app.static_folder, relative_path)

