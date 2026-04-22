from datetime import datetime
from app import db


class Media(db.Model):
    __tablename__ = 'media'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'), nullable=True)

    filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.BigInteger)
    mime_type = db.Column(db.String(100), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)

    thumbnail_path = db.Column(db.String(500))
    thumbnail_small_path = db.Column(db.String(500))

    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    duration = db.Column(db.Integer)
    taken_at = db.Column(db.DateTime)

    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    album = db.relationship('Album', backref=db.backref('media_items', lazy='dynamic'), foreign_keys=[album_id])
    user = db.relationship('User', backref=db.backref('media_items', lazy='dynamic'))

    def to_dict(self, include_owner=False):
        taken = self.taken_at or self.uploaded_at
        data = {
            'id': self.id,
            'filename': self.filename,
            'mime_type': self.mime_type,
            'media_type': self.media_type,
            'width': self.width,
            'height': self.height,
            'duration': self.duration,
            'taken_at': taken.isoformat() if taken else None,
            'thumbnail_url': f'/media/{self.id}/thumbnail' if self.thumbnail_path else None,
            'url': f'/media/{self.id}',
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None
        }
        if include_owner:
            data['user_id'] = self.user_id
            data['username'] = self.owner.username if self.owner else None
        return data

    @property
    def owner(self):
        from app.models.user import User
        return User.query.get(self.user_id)

    def __repr__(self):
        return f'<Media {self.id}: {self.filename}>'