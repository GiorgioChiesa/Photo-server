# Photo Server - Google Photos Clone

Self-hosted photo gallery with multi-user support and remote access via Cloudflare Tunnel.

## Features

- **Multi-user authentication** - Each user has their own private photo gallery
- **Anonymous public albums** - Share albums publicly via URL (no login required)
- **Responsive gallery** - Works on phone, tablet, and laptop
- **Photo upload** - Upload from phone or laptop via browser
- **Video support** - Store and view videos
- **Thumbnail generation** - Automatic thumbnails for fast browsing
- **Remote access** - Access from anywhere via Cloudflare Tunnel (free, unlimited)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Start locally
python run.py

# Open http://localhost:5000 in browser
```

## First Run

1. The first user to register becomes admin
2. Create albums in the web interface
3. Mark albums as "public" to share via URL

## Remote Access (Cloudflare Tunnel)

### Option 1: With your own domain

```bash
# Install cloudflared
brew install cloudflared  # Mac
# or: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared

# Login to Cloudflare
cloudflared login

# Create tunnel
cloudflared tunnel create photos-server

# Configure DNS in Cloudflare dashboard

# Set environment variable
export CLOUDFLARE_TUNNEL_TOKEN=your-token

# Run with tunnel
python run.py --tunnel
```

### Option 2: Quick tunnel (no domain)

```bash
# Just run this command
cloudflared tunnel --url http://localhost:5000

# Gives you a URL like https://random-name.trycloudflare.com
```

## Anonymous Access

When you mark an album as "public":
- Generates unique URL like `https://yourdomain.com/shared/abc123`
- Anyone with the URL can view (no login required)
- Great for sharing family photos

## User Management

| User Type | Access |
|-----------|--------|
| Anonymous | Only public/shared albums |
| Registered User | Own private photos + public albums |
| Admin (first user) | All albums, can delete any file |

## API Endpoints

| Endpoint | Auth | Description |
|----------|-----|-------------|
| `/` | Redirect | Go to login or gallery |
| `/login` | No | Login form |
| `/register` | No | Registration form |
| `/gallery` | Yes | Main photo gallery |
| `/upload` | Yes | Upload photos |
| `/api/media` | Yes | List user's photos |
| `/api/albums` | Yes | List/create albums |
| `/shared/<token>` | No | View public album |

## Environment Variables

```
SECRET_KEY=your-secret-key-at-least-32-characters-long
DATABASE_URL=sqlite:///data/photos.db
UPLOAD_FOLDER=./uploads
FLASK_ENV=development
CLOUDFLARE_TUNNEL_TOKEN=
```

## Storage

Photos stored in:
- `uploads/originals/images/{year}/{month}/{day}/`
- `uploads/originals/videos/{year}/{month}/{day}/`
- `uploads/thumbnails/`

For external storage (e.g., USB drive on tablet):
```bash
# Mount drive and set UPLOAD_FOLDER
export UPLOAD_FOLDER=/Volumes/your-drive/photos
python run.py
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web Framework | Flask 3.0 |
| Auth | Flask-Login + Flask-Bcrypt |
| Database | SQLite |
| Images | Pillow |
| Remote Access | Cloudflare Tunnel |
| Frontend | Mobile-first HTML/CSS |

## Commands

```bash
# Development
python run.py

# With Cloudflare Tunnel
python run.py --tunnel

# With ngrok (alternative)
python run.py --ngrok

# Production (using gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```