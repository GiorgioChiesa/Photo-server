import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app(config_name='default'):
    from app.config import config

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'originals', 'images'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'originals', 'videos'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails'), exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))

    from app.routes.main import main as main_bp
    from app.routes.auth import auth as auth_bp
    from app.routes.upload import upload as upload_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp, url_prefix='/upload')

    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200

    with app.app_context():
        db.create_all()

    return app