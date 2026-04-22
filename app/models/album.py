import json
import secrets
from datetime import datetime
from app import db


class Album(db.Model):
    __tablename__ = 'albums'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    visibility = db.Column(db.String(20), default='personal')  # personal, shared, public
    is_public = db.Column(db.Boolean, default=False)
    share_token = db.Column(db.String(32), unique=True)
    shared_with = db.Column(db.Text, default='[]')
    cover_media_id = db.Column(db.Integer, db.ForeignKey('media.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('albums', lazy='dynamic'), foreign_keys=[user_id])

    VISIBILITY_PERSONAL = 'personal'
    VISIBILITY_SHARED = 'shared'
    VISIBILITY_PUBLIC = 'public'

    def generate_share_token(self):
        if not self.share_token:
            self.share_token = secrets.token_urlsafe(16)
            self.visibility = self.VISIBILITY_PUBLIC
            self.is_public = True
        return self.share_token

    def get_share_url(self, base_url):
        if not self.share_token:
            self.generate_share_token()
        return f"{base_url.rstrip('/')}/shared/{self.share_token}"

    def get_shared_with_list(self):
        if not self.shared_with:
            return []
        try:
            return json.loads(self.shared_with)
        except:
            return []

    def set_shared_with(self, user_ids):
        self.shared_with = json.dumps(user_ids)

    def set_visibility(self, visibility):
        self.visibility = visibility
        if visibility == self.VISIBILITY_PUBLIC:
            self.is_public = True
            if not self.share_token:
                self.generate_share_token()
        elif visibility == self.VISIBILITY_SHARED:
            self.is_public = False
        else:  # personal
            self.is_public = False

    @property
    def can_upload(self):
        return True

    def can_view(self, user):
        if self.visibility == self.VISIBILITY_PUBLIC:
            return True
        if not user or not user.is_authenticated:
            return False
        if self.user_id == user.id:
            return True
        if self.visibility == self.VISIBILITY_SHARED:
            shared_with = self.get_shared_with_list()
            return user.id in shared_with
        return False

    def can_upload_anyone(self):
        return self.visibility == self.VISIBILITY_PUBLIC

    def to_dict(self, include_token=False, include_shared=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'visibility': self.visibility,
            'is_public': self.is_public,
            'share_token': self.share_token,
            'cover_url': f'/media/{self.cover_media_id}/thumbnail' if self.cover_media_id else None,
            'media_count': self.media_items.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_shared:
            data['shared_with'] = self.get_shared_with_list()
        if not include_token:
            data.pop('share_token', None)
        return data

    def __repr__(self):
        return f'<Album {self.id}: {self.title}>'