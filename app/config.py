import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{BASE_DIR / "data" / "photos.db"}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload settings
    UPLOAD_FOLDER = str(BASE_DIR / 'uploads')
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # 2GB
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'avi', 'webm', 'mkv'}

    # Thumbnail sizes
    THUMBNAIL_SIZE = (300, 300)
    THUMBNAIL_QUALITY = 85

    # ngrok
    USE_NGROK = os.environ.get('USE_NGROK', 'false').lower() == 'true'
    NGROK_AUTH_TOKEN = os.environ.get('NGROK_AUTH_TOKEN', '')


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}