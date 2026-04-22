import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, send_from_directory, jsonify, request, redirect, url_for, current_app, flash
from flask_login import login_required, current_user
from app import db
from app.models.media import Media
from app.models.album import Album

main = Blueprint('main', __name__)


@main.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.gallery'))
    return redirect(url_for('main.public_gallery'))


@main.route('/gallery')
def gallery():
    if not current_user.is_authenticated:
        return redirect(url_for('main.public_gallery'))

    user_albums = Album.query.filter_by(user_id=current_user.id).order_by(Album.created_at.desc()).all()
    public_albums = Album.query.filter_by(is_public=True).order_by(Album.created_at.desc()).all()

    return render_template('main/gallery.html',
                         albums=user_albums,
                         public_albums=public_albums)


@main.route('/public')
def public_gallery():
    public_albums = Album.query.filter_by(visibility=Album.VISIBILITY_PUBLIC).order_by(Album.created_at.desc()).all()

    return render_template('main/public_gallery.html',
                         public_albums=public_albums)


@main.route('/api/public-albums')
def api_public_albums():
    public_albums = Album.query.filter_by(visibility=Album.VISIBILITY_PUBLIC).order_by(Album.created_at.desc()).all()
    return jsonify({
        'public_albums': [a.to_dict(include_token=True) for a in public_albums]
    })


@main.route('/api/media')
@login_required
def api_media():
    media_type = request.args.get('type', None)
    album_id = request.args.get('album_id', None, type=int)

    query = Media.query.filter_by(user_id=current_user.id)

    if media_type:
        query = query.filter_by(media_type=media_type)
    if album_id:
        query = query.filter_by(album_id=album_id)

    all_media = query.all()

    now = datetime.utcnow()
    one_month_ago = now - timedelta(days=30)
    one_year_ago = now - timedelta(days=365)

    groups = {
        'last_month': {'title': 'Last Month', 'items': [], 'by_day': {}},
        'last_year': {'title': 'Last Year', 'items': [], 'by_month': {}},
        'older': {'title': 'Older', 'items': [], 'by_year': {}}
    }

    for media in all_media:
        taken = media.taken_at or media.uploaded_at

        if taken >= one_month_ago:
            day_key = taken.strftime('%Y-%m-%d')
            if day_key not in groups['last_month']['by_day']:
                groups['last_month']['by_day'][day_key] = {
                    'date': taken,
                    'items': [],
                    'label': taken.strftime('%A %d %B')
                }
            groups['last_month']['by_day'][day_key]['items'].append(media)
            groups['last_month']['items'].append(media)
        elif taken >= one_year_ago:
            month_key = taken.strftime('%Y-%m')
            if month_key not in groups['last_year']['by_month']:
                month_date = taken.replace(day=1)
                groups['last_year']['by_month'][month_key] = {
                    'date': month_date,
                    'items': [],
                    'label': taken.strftime('%B %Y')
                }
            groups['last_year']['by_month'][month_key]['items'].append(media)
            groups['last_year']['items'].append(media)
        else:
            year_key = taken.strftime('%Y')
            if year_key not in groups['older']['by_year']:
                year_date = taken.replace(month=1, day=1)
                groups['older']['by_year'][year_key] = {
                    'date': year_date,
                    'items': [],
                    'label': taken.strftime('%Y')
                }
            groups['older']['by_year'][year_key]['items'].append(media)
            groups['older']['items'].append(media)

    result = {}
    for key, group in groups.items():
        if group['items']:
            if key == 'last_month':
                sorted_days = sorted(group['by_day'].items(), key=lambda x: x[1]['date'], reverse=True)
                result[key] = {
                    'title': group['title'],
                    'period': 'day',
                    'sections': [
                        {'label': v['label'], 'items': [m.to_dict() for m in v['items']]}
                        for k, v in sorted_days
                    ]
                }
            elif key == 'last_year':
                sorted_months = sorted(group['by_month'].items(), key=lambda x: x[1]['date'], reverse=True)
                result[key] = {
                    'title': group['title'],
                    'period': 'month',
                    'sections': [
                        {'label': v['label'], 'items': [m.to_dict() for m in v['items']]}
                        for k, v in sorted_months
                    ]
                }
            else:
                sorted_years = sorted(group['by_year'].items(), key=lambda x: x[1]['date'], reverse=True)
                result[key] = {
                    'title': group['title'],
                    'period': 'year',
                    'sections': [
                        {'label': v['label'], 'items': [m.to_dict() for m in v['items']]}
                        for k, v in sorted_years
                    ]
                }

    return jsonify(result)


@main.route('/media/<int:media_id>')
@login_required
def media_viewer(media_id):
    media = Media.query.get_or_404(media_id)
    if media.user_id != current_user.id and not current_user.is_admin:
        return redirect(url_for('main.gallery'))
    return render_template('main/viewer.html', media=media)





@main.route('/media/<int:media_id>/thumbnail')
def serve_thumbnail(media_id):
    media = Media.query.get_or_404(media_id)
    from app.models.album import Album
    can_view = False
    if media.album_id:
        album = Album.query.get(media.album_id)
        if album and album.visibility == Album.VISIBILITY_PUBLIC:
            can_view = True
    if not can_view and media.user_id != current_user.id and not (current_user.is_authenticated and current_user.is_admin):
        return '', 403
    if not media.thumbnail_path:
        return '', 404
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, media.thumbnail_path)


@main.route('/media/<int:media_id>/file')
def serve_media_file(media_id):
    media = Media.query.get_or_404(media_id)
    from app.models.album import Album
    can_view = False
    if media.album_id:
        album = Album.query.get(media.album_id)
        if album and album.visibility == Album.VISIBILITY_PUBLIC:
            can_view = True
    if not can_view and media.user_id != current_user.id and not (current_user.is_authenticated and current_user.is_admin):
        return '', 403
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(upload_folder, media.file_path, as_attachment=(request.args.get('download') == 'true'))


@main.route('/media/<int:media_id>/download')
@login_required
def download_media(media_id):
    media = Media.query.get_or_404(media_id)
    if media.user_id != current_user.id and not current_user.is_admin:
        return '', 403
    upload_folder = current_app.config['UPLOAD_FOLDER']
    return send_from_directory(
        upload_folder,
        media.file_path,
        as_attachment=True,
        download_name=media.filename
    )


@main.route('/media/<int:media_id>', methods=['DELETE', 'PUT'])
@login_required
def manage_media(media_id):
    media = Media.query.get_or_404(media_id)
    if media.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Permission denied'}), 403

    if request.method == 'PUT':
        data = request.get_json() or {}
        new_album_id = data.get('album_id')

        if new_album_id is not None:
            if new_album_id == 0:
                media.album_id = None
            else:
                album = Album.query.get(new_album_id)
                if album and album.user_id == media.user_id:
                    media.album_id = new_album_id
                else:
                    return jsonify({'error': 'Album not found or not owned by you'}), 400

            db.session.commit()
            return jsonify({'success': True, 'album_id': media.album_id})

    upload_folder = current_app.config['UPLOAD_FOLDER']
    try:
        if media.file_path:
            os.remove(os.path.join(upload_folder, media.file_path))
        if media.thumbnail_path:
            os.remove(os.path.join(upload_folder, media.thumbnail_path))
    except FileNotFoundError:
        pass

    db.session.delete(media)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Media deleted'})


@main.route('/api/albums', methods=['GET', 'POST'])
@login_required
def api_albums():
    if request.method == 'POST':
        data = request.get_json() or {}
        title = data.get('title', '').strip()
        is_public = data.get('is_public', False)

        if not title:
            return jsonify({'error': 'Title is required'}), 400

        album = Album(
            user_id=current_user.id,
            title=title,
            is_public=is_public
        )
        if is_public:
            album.generate_share_token()

        db.session.add(album)
        db.session.commit()

        return jsonify({'album': album.to_dict(include_token=True, include_shared=True)}), 201

    user_albums = Album.query.filter_by(user_id=current_user.id).order_by(Album.created_at.desc()).all()
    shared_albums = Album.query.filter(
        Album.shared_with.contains(str(current_user.id))
    ).order_by(Album.created_at.desc()).all()
    public_albums = Album.query.filter_by(is_public=True).order_by(Album.created_at.desc()).all()

    return jsonify({
        'my_albums': [a.to_dict(include_token=True, include_shared=True) for a in user_albums],
        'shared_with_me': [a.to_dict(include_token=True) for a in shared_albums],
        'public_albums': [a.to_dict() for a in public_albums]
    })


@main.route('/api/albums/<int:album_id>', methods=['PUT', 'DELETE'])
@login_required
def api_album(album_id):
    album = Album.query.get_or_404(album_id)

    if album.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Permission denied'}), 403

    if request.method == 'PUT':
        data = request.get_json() or {}
        if 'title' in data:
            album.title = data['title'].strip()
        if 'description' in data:
            album.description = data['description']
        if 'visibility' in data:
            album.set_visibility(data['visibility'])
        elif 'is_public' in data:
            album.is_public = data['is_public']
            if album.is_public:
                album.visibility = Album.VISIBILITY_PUBLIC
            if data['is_public'] and not album.share_token:
                album.generate_share_token()
        if 'shared_with' in data:
            album.set_shared_with(data['shared_with'])

        db.session.commit()
        return jsonify({'album': album.to_dict(include_token=True, include_shared=True)})

    db.session.delete(album)
    db.session.commit()
    return jsonify({'success': True})


@main.route('/api/users')
@login_required
def api_users():
    from app.models.user import User
    users = User.query.order_by(User.username).all()
    return jsonify({
        'users': [{'id': u.id, 'username': u.username} for u in users]
    })


@main.route('/shared/<share_token>')
def shared_album(share_token):
    album = Album.query.filter_by(share_token=share_token).first_or_404()
    if not album.can_view(current_user):
        from flask import abort
        abort(404)

    media = Media.query.filter_by(album_id=album.id).order_by(Media.taken_at.desc(), Media.uploaded_at.desc()).all()
    media_data = [m.to_dict() for m in media]

    return render_template('main/shared.html', album=album, media=media_data)


@main.route('/api/shared/<share_token>')
def api_shared_album(share_token):
    album = Album.query.filter_by(share_token=share_token).first_or_404()
    if not album.can_view(current_user):
        from flask import abort
        abort(404)

    media = Media.query.filter_by(album_id=album.id).order_by(Media.taken_at.desc(), Media.uploaded_at.desc()).all()

    return jsonify({
        'album': album.to_dict(),
        'media': [m.to_dict() for m in media]
    })


from flask import current_app