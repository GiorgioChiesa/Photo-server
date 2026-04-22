# Photo Server

A self-hosted photo gallery web application with multi-user support, album sharing, and remote access via Cloudflare Tunnel.

## Features

- **Multi-user authentication** - Each user has their own private photo gallery
- **Album sharing** - Three visibility levels: Personal, Shared (specific users), Public (anyone)
- **Public upload** - Anyone can upload to public albums without logging in
- **Responsive gallery** - Works on phone, tablet, and desktop
- **Photo/video upload** - Upload from browser, automatic thumbnail generation
- **Multi-select** - Long-press to select multiple photos for bulk actions (move, delete, download)
- **Remote access** - Access from anywhere via Cloudflare Tunnel (free, unlimited)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start locally
python run.py

# Open http://localhost:5000
```

## First Run

1. Register your first account (becomes admin automatically)
2. Create albums in the gallery interface
3. Set album visibility: Personal, Shared, or Public

## Album Visibility

| Level | Who can see | Who can upload |
|-------|------------|----------------|
| Personal | Owner only | Owner only |
| Shared | Selected users | Selected users |
| Public | Anyone (no login) | Anyone (no login) |

## Remote Access

### With Cloudflare Tunnel (recommended)

```bash
# Install cloudflared
brew install cloudflared  # Mac
# or: curl -L https://github.com/cloudflare/cloudflare/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared

# Login to Cloudflare
cloudflared login

# Create tunnel
cloudflared tunnel create photos-server

# Set environment variable
export CLOUDFLARE_TUNNEL_TOKEN=your-token

# Run with tunnel
python run.py --tunnel
```

### Quick tunnel (no domain needed)

```bash
cloudflared tunnel --url http://localhost:5000
# Returns: https://random-name.trycloudflare.com
```

## URLs

| Route | Description |
|-------|-------------|
| `/` | Home - redirects to gallery or login |
| `/gallery` | Main photo gallery |
| `/upload` | Upload photos |
| `/public` | Public albums list (no login) |
| `/shared/<token>` | View shared album (no login) |
| `/upload/public/<token>` | Upload to public album (no login) |

## Environment Variables

```env
SECRET_KEY=your-secret-key-at-least-32-characters-long
DATABASE_URL=sqlite:///data/photos.db
UPLOAD_FOLDER=./uploads
FLASK_ENV=development
CLOUDFLARE_TUNNEL_TOKEN=
```

## Tech Stack

- **Web Framework**: Flask 3.0
- **Authentication**: Flask-Login + Flask-Bcrypt
- **Database**: SQLite
- **Image Processing**: Pillow
- **Remote Access**: Cloudflare Tunnel
- **Frontend**: Mobile-first HTML/CSS/JS

## Commands

```bash
# Development
python run.py

# With Cloudflare Tunnel
python run.py --tunnel

# Production
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

## Storage

Photos are stored in:
- `uploads/{album_name}/images/{year}/{month}/{day}/`
- `uploads/{album_name}/videos/{year}/{month}/{day}/`
- `uploads/thumbnails/`

For external storage (e.g., USB drive):
```bash
export UPLOAD_FOLDER=/Volumes/your-drive/photos
python run.py
```

## License

MIT