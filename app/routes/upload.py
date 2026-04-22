import os
import uuid
import mimetypes
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
from PIL.ExifTags import TAGS
from app import db
from app.models.media import Media
from app.models.album import Album

upload = Blueprint('upload', __name__)


def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in current_app.config.get('ALLOWED_EXTENSIONS', set())


def get_media_type(mime_type):
    if mime_type and mime_type.startswith('image/'):
        return 'image'
    elif mime_type and mime_type.startswith('video/'):
        return 'video'
    return None


def generate_thumbnail(file_path, media_type, thumb_path):
    try:
        if media_type == 'image':
            with Image.open(file_path) as img:
                orig_size = img.size
                thumb_size = current_app.config.get('THUMBNAIL_SIZE', (300, 300))
                img.thumbnail(thumb_size)
                quality = current_app.config.get('THUMBNAIL_QUALITY', 85)
                img.save(thumb_path, 'JPEG', quality=quality)
                return True
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
    return False


def extract_metadata(file_path, media_type):
    metadata = {}
    taken_at = None
    try:
        if media_type == 'image':
            with Image.open(file_path) as img:
                metadata['width'] = img.width
                metadata['height'] = img.height

                exif_data = img._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        if tag == 'DateTimeOriginal':
                            try:
                                taken_at = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                            except:
                                pass
                        elif tag == 'DateTime':
                            if not taken_at:
                                try:
                                    taken_at = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                                except:
                                    pass
    except Exception as e:
        print(f"Error extracting metadata: {e}")
    metadata['taken_at'] = taken_at
    return metadata


@upload.route('/')
@login_required
def upload_page():
    return render_template('main/upload.html', show_public_albums=True)


def process_upload_for_album(album):
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'No file provided'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit('.', 1)[1].lower()
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    
    mime_type = file.mimetype or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
    media_type = get_media_type(mime_type)
    if not media_type:
        return jsonify({'error': 'Unsupported file type'}), 400
    
    folder_name = "".join(c for c in album.title if c.isalnum() or c in " -_").strip()[:30] or f"album_{album.id}"
    now = datetime.utcnow()
    date_path = f"{folder_name}/{media_type}s/{now.year}/{now.month:02d}/{now.day:02d}"
    abs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], date_path)
    os.makedirs(abs_dir, exist_ok=True)
    
    rel_path = f"{date_path}/{stored_filename}"
    abs_path = os.path.join(abs_dir, stored_filename)
    file.save(abs_path)
    
    file_size = os.path.getsize(abs_path)
    metadata = extract_metadata(abs_path, media_type)
    
    thumb_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_filename = f"{uuid.uuid4().hex}.jpg"
    thumb_path = os.path.join(thumb_dir, thumb_filename)
    thumb_rel_path = None
    
    if generate_thumbnail(abs_path, media_type, thumb_path):
        thumb_rel_path = f"thumbnails/{thumb_filename}"
    
    user_id = album.user_id
    
    media = Media(
        user_id=user_id,
        album_id=album.id,
        filename=original_filename,
        stored_filename=stored_filename,
        file_path=rel_path,
        file_size=file_size,
        mime_type=mime_type,
        media_type=media_type,
        thumbnail_path=thumb_rel_path,
        width=metadata.get('width'),
        height=metadata.get('height'),
        taken_at=metadata.get('taken_at')
    )
    
    db.session.add(media)
    db.session.commit()
    
    if media.album_id and media.thumbnail_path:
        album = Album.query.get(media.album_id)
        if album and not album.cover_media_id:
            album.cover_media_id = media.id
            db.session.commit()
    
    return jsonify({'success': True, 'media': media.to_dict()}), 201


def process_upload_current_user():
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'No file provided'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit('.', 1)[1].lower()
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    
    mime_type = file.mimetype or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
    media_type = get_media_type(mime_type)
    if not media_type:
        return jsonify({'error': 'Unsupported file type'}), 400
    
    album_id = request.form.get('album_id', type=int)
    album = Album.query.get(album_id) if album_id else None
    
    can_upload = False
    if album:
        can_upload = album.user_id == current_user.id
        if not can_upload and album.can_view(current_user):
            can_upload = True
    
    final_album_id = album_id if can_upload else None
    
    folder_name = current_user.username
    if album and album.title:
        folder_name = "".join(c for c in album.title if c.isalnum() or c in " -_").strip()[:30] or f"album_{album.id}"
    
    now = datetime.utcnow()
    date_path = f"{folder_name}/{media_type}s/{now.year}/{now.month:02d}/{now.day:02d}"
    abs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], date_path)
    os.makedirs(abs_dir, exist_ok=True)
    
    rel_path = f"{date_path}/{stored_filename}"
    abs_path = os.path.join(abs_dir, stored_filename)
    file.save(abs_path)
    
    file_size = os.path.getsize(abs_path)
    metadata = extract_metadata(abs_path, media_type)
    
    thumb_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_filename = f"{uuid.uuid4().hex}.jpg"
    thumb_path = os.path.join(thumb_dir, thumb_filename)
    thumb_rel_path = None
    
    if generate_thumbnail(abs_path, media_type, thumb_path):
        thumb_rel_path = f"thumbnails/{thumb_filename}"
    
    media = Media(
        user_id=current_user.id,
        album_id=final_album_id,
        filename=original_filename,
        stored_filename=stored_filename,
        file_path=rel_path,
        file_size=file_size,
        mime_type=mime_type,
        media_type=media_type,
        thumbnail_path=thumb_rel_path,
        width=metadata.get('width'),
        height=metadata.get('height'),
        taken_at=metadata.get('taken_at')
    )
    
    db.session.add(media)
    db.session.commit()
    
    return jsonify({'success': True, 'media': media.to_dict()}), 201


@upload.route('/public/<share_token>', methods=['GET', 'POST'])
def public_upload(share_token):
    album = Album.query.filter_by(share_token=share_token).first_or_404()
    if not album.can_upload_anyone():
        return jsonify({'error': 'Cannot upload to this album'}), 403

    if request.method == 'GET':
        return render_template('main/upload.html', album=album, show_public_albums=True)

    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'error': 'No file provided'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400
    
    original_filename = secure_filename(file.filename)
    ext = original_filename.rsplit('.', 1)[1].lower()
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    
    mime_type = file.mimetype or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
    media_type = get_media_type(mime_type)
    if not media_type:
        return jsonify({'error': 'Unsupported file type'}), 400
    
    folder_name = "".join(c for c in album.title if c.isalnum() or c in " -_").strip()[:30] or f"album_{album.id}"
    now = datetime.utcnow()
    date_path = f"{folder_name}/{media_type}s/{now.year}/{now.month:02d}/{now.day:02d}"
    abs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], date_path)
    os.makedirs(abs_dir, exist_ok=True)
    
    rel_path = f"{date_path}/{stored_filename}"
    abs_path = os.path.join(abs_dir, stored_filename)
    file.save(abs_path)
    
    file_size = os.path.getsize(abs_path)
    metadata = extract_metadata(abs_path, media_type)
    
    thumb_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_filename = f"{uuid.uuid4().hex}.jpg"
    thumb_path = os.path.join(thumb_dir, thumb_filename)
    thumb_rel_path = None
    
    if generate_thumbnail(abs_path, media_type, thumb_path):
        thumb_rel_path = f"thumbnails/{thumb_filename}"
    
    user_id = album.user_id
    
    media = Media(
        user_id=user_id,
        album_id=album.id,
        filename=original_filename,
        stored_filename=stored_filename,
        file_path=rel_path,
        file_size=file_size,
        mime_type=mime_type,
        media_type=media_type,
        thumbnail_path=thumb_rel_path,
        width=metadata.get('width'),
        height=metadata.get('height'),
        taken_at=metadata.get('taken_at')
    )
    
    db.session.add(media)
    db.session.commit()
    
    if media.album_id and media.thumbnail_path:
        album = Album.query.get(media.album_id)
        if album and not album.cover_media_id:
            album.cover_media_id = media.id
            db.session.commit()
    
    return jsonify({'success': True, 'media': media.to_dict()}), 201


@upload.route('/', methods=['POST'])
@login_required
def upload_file():
    return process_upload_current_user()

    album_id = request.form.get('album_id', type=int)

    album = None
    if album_id:
        album = Album.query.get(album_id)

    can_upload = False
    if album:
        can_upload = album.user_id == current_user.id
        if not can_upload and album.can_view(current_user):
            can_upload = True

    final_album_id = album_id if can_upload else None

    folder_name = current_user.username
    if album and album.title:
        folder_name = "".join(c for c in album.title if c.isalnum() or c in " -_").strip()[:30]
        if not folder_name:
            folder_name = f"album_{album.id}"

    now = datetime.utcnow()
    date_path = f"{folder_name}/{media_type}s/{now.year}/{now.month:02d}/{now.day:02d}"
    abs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], date_path)
    os.makedirs(abs_dir, exist_ok=True)

    rel_path = f"{date_path}/{stored_filename}"
    abs_path = os.path.join(abs_dir, stored_filename)
    file.save(abs_path)

    file_size = os.path.getsize(abs_path)
    metadata = extract_metadata(abs_path, media_type)
    taken_at = metadata.get('taken_at')

    thumb_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_filename = f"{uuid.uuid4().hex}.jpg"
    thumb_path = os.path.join(thumb_dir, thumb_filename)
    thumb_rel_path = None

    if generate_thumbnail(abs_path, media_type, thumb_path):
        thumb_rel_path = f"thumbnails/{thumb_filename}"

    media = Media(
        user_id=current_user.id,
        album_id=final_album_id,
        filename=original_filename,
        stored_filename=stored_filename,
        file_path=rel_path,
        file_size=file_size,
        mime_type=mime_type,
        media_type=media_type,
        thumbnail_path=thumb_rel_path,
        width=metadata.get('width'),
        height=metadata.get('height'),
        taken_at=taken_at
    )

    db.session.add(media)
    db.session.commit()

    if media.album_id and media.thumbnail_path:
        album = Album.query.get(media.album_id)
        if album and not album.cover_media_id:
            album.cover_media_id = media.id
            db.session.commit()

    return jsonify({
        'success': True,
        'media': media.to_dict()
    }), 201


@upload.route('/multiple', methods=['POST'])
@login_required
def upload_multiple():
    files = request.files.getlist('files')
    if not files or (len(files) == 1 and files[0].filename == ''):
        return jsonify({'error': 'No files provided'}), 400

    album_id = request.form.get('album_id', type=int)

    uploaded = []
    errors = []
    first_media = None

    for file in files:
        try:
            if file.filename == '' or not allowed_file(file.filename):
                errors.append({'filename': file.filename, 'error': 'File type not allowed'})
                continue

            original_filename = secure_filename(file.filename)
            ext = original_filename.rsplit('.', 1)[1].lower()
            stored_filename = f"{uuid.uuid4().hex}.{ext}"

            mime_type = file.mimetype or mimetypes.guess_type(original_filename)[0] or 'application/octet-stream'
            media_type = get_media_type(mime_type)

            if not media_type:
                errors.append({'filename': file.filename, 'error': 'Unsupported file type'})
                continue

            now = datetime.utcnow()
            date_path = f"{current_user.id}/originals/{media_type}s/{now.year}/{now.month:02d}/{now.day:02d}"
            abs_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], date_path)
            os.makedirs(abs_dir, exist_ok=True)

            rel_path = f"{date_path}/{stored_filename}"
            abs_path = os.path.join(abs_dir, stored_filename)
            file.save(abs_path)

            file_size = os.path.getsize(abs_path)
            metadata = extract_metadata(abs_path, media_type)
            taken_at = metadata.get('taken_at')

            thumb_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], f"{current_user.id}/thumbnails")
            os.makedirs(thumb_dir, exist_ok=True)
            thumb_filename = f"{uuid.uuid4().hex}.jpg"
            thumb_path = os.path.join(thumb_dir, thumb_filename)
            thumb_rel_path = None

            if generate_thumbnail(abs_path, media_type, thumb_path):
                thumb_rel_path = f"{current_user.id}/thumbnails/{thumb_filename}"

            media = Media(
                user_id=current_user.id,
                album_id=album_id,
                filename=original_filename,
                stored_filename=stored_filename,
                file_path=rel_path,
                file_size=file_size,
                mime_type=mime_type,
                media_type=media_type,
                thumbnail_path=thumb_rel_path,
                width=metadata.get('width'),
                height=metadata.get('height'),
                taken_at=taken_at
            )

            db.session.add(media)
            uploaded.append(media.filename)
            
            if first_media is None and media.thumbnail_path:
                first_media = media

        except Exception as e:
            errors.append({'filename': file.filename, 'error': str(e)})

    db.session.commit()
    
    if first_media and album_id:
        album = Album.query.get(album_id)
        if album and not album.cover_media_id:
            album.cover_media_id = first_media.id
            db.session.commit()

    return jsonify({
        'success': True,
        'uploaded': uploaded,
        'errors': errors
    })