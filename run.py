#!/usr/bin/env python3
"""
Photo Server - Run Script

Usage:
    python run.py                    # Local only
    python run.py --tunnel           # With Cloudflare Tunnel
    python run.py --ngrok             # With ngrok (alternative)

Environment Variables:
    FLASK_ENV=development
    SECRET_KEY=your-secret-key
    DATABASE_URL=sqlite:///data/photos.db
    UPLOAD_FOLDER=/path/to/uploads
    CLOUDFLARE_TUNNEL_TOKEN=your-token
"""

import os
import sys
import argparse
import signal
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


def check_dependencies():
    """Check if required packages are installed."""
    required = ['flask', 'flask_sqlalchemy', 'flask_login', 'flask_bcrypt']
    missing = []

    for package in required:
        try:
            __import__(package.lower().replace('-', '_'))
        except ImportError:
            missing.append(package)

    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.info(f"Install with: pip install {' '.join(missing)}")
        return False
    return True


def create_directories(app):
    """Create necessary directories."""
    upload_folder = app.config.get('UPLOAD_FOLDER')
    if upload_folder:
        for subdir in ['originals/images', 'originals/videos', 'thumbnails']:
            path = Path(upload_folder) / subdir
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created: {path}")

    db_path = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_path.startswith('sqlite://'):
        db_file = db_path.replace('sqlite://', '')
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)


def start_flask_app(env='development', port=5000):
    """Start the Flask application."""
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / '.env')

    if not check_dependencies():
        sys.exit(1)

    os.environ.setdefault('FLASK_APP', 'run.py')

    from app import create_app

    config_name = env if env in ['development', 'production'] else 'default'
    app = create_app(config_name)

    create_directories(app)

    logger.info(f"Starting Flask server in {config_name} mode")
    logger.info(f"Server running on http://localhost:{port}")

    return app, port


def start_cloudflare_tunnel():
    """Start Cloudflare Tunnel (requires cloudflared installed)."""
    tunnel_token = os.environ.get('CLOUDFLARE_TUNNEL_TOKEN')

    if not tunnel_token:
        logger.error("CLOUDFLARE_TUNNEL_TOKEN environment variable not set")
        logger.info("""
To use Cloudflare Tunnel:

1. Install cloudflared:
   Mac: brew install cloudflared
   Linux: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared

2. Create a tunnel:
   cloudflared tunnel create photos-server

3. Set the environment variable:
   export CLOUDFLARE_TUNNEL_TOKEN=your-token

Or use the quick tunnel (no domain required):
   cloudflared tunnel --url http://localhost:5000
""")
        return None, None

    try:
        import subprocess

        logger.info("Starting Cloudflare Tunnel...")

        process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--no-autoupdate', 'run', '--token', tunnel_token],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        logger.info("Cloudflare Tunnel started")
        logger.info("Your server will be accessible via your Cloudflare domain")

        return process, None

    except FileNotFoundError:
        logger.error("cloudflared not found. Install from https://github.com/cloudflare/cloudflared")
        return None, None
    except Exception as e:
        logger.error(f"Failed to start Cloudflare Tunnel: {e}")
        return None, None


def start_ngrok_tunnel(port):
    """Start ngrok tunnel (requires pyngrok)."""
    try:
        from pyngrok import ngrok

        auth_token = os.environ.get('NGROK_AUTH_TOKEN')

        if auth_token:
            ngrok.set_auth_token(auth_token)

        tunnel = ngrok.connect(port, 'http')
        public_url = tunnel.public_url

        logger.info(f"ngrok tunnel started")
        logger.info(f"Public URL: {public_url}")

        return tunnel, public_url

    except ImportError:
        logger.error("pyngrok not installed. Install with: pip install pyngrok")
        return None, None
    except Exception as e:
        logger.error(f"Failed to start ngrok: {e}")
        return None, None


def main():
    parser = argparse.ArgumentParser(description='Photo Server')
    parser.add_argument('--env', choices=['development', 'production'],
                       default='development', help='Environment')
    parser.add_argument('--port', type=int, default=8080, help='Port to run on')
    parser.add_argument('--tunnel', action='store_true',
                       help='Start with Cloudflare Tunnel')
    parser.add_argument('--ngrok', action='store_true',
                       help='Start with ngrok tunnel')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')

    args = parser.parse_args()

    app, port = start_flask_app(args.env, args.port)

    tunnel_process = None
    tunnel_url = None

    if args.tunnel:
        tunnel_process = start_cloudflare_tunnel()[0]

    if args.ngrok:
        tunnel, tunnel_url = start_ngrok_tunnel(port)

    if args.host:
        try:
            app.run(host=args.host, port=port, debug=(args.env == 'development'))
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            if tunnel_process:
                tunnel_process.terminate()

            import atexit
            try:
                from pyngrok import ngrok
                ngrok.kill()
            except:
                pass


if __name__ == '__main__':
    main()