# 🎵 Spotify Playlist Generator

Personal Playlist Generator with Collaborative Editing

## Quick Start with Docker

### Prerequisites
- Docker & Docker Compose installed
- Spotify Developer Account (Client ID & Secret already in `.env.example`)

### Start the application

```bash
# 1. Clone environment variables
cp .env.example .env

# 2. Start all services
docker-compose up -d

# 3. Check services are running
docker-compose ps

# 4. View logs (optional)
docker-compose logs -f
```

### Access the application

- **Frontend:** http://localhost 🎵
- **Backend API:** http://localhost/api
- **Health Check:** http://localhost/api/health
- **Direct Backend:** http://localhost:8000 (if Nginx unavailable)

### Stop the application

```bash
docker-compose down

# Remove volumes (database)
docker-compose down -v
```

---

## Local Development (Without Docker)

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp ../.env.example .env

# Run server
python main.py
# Listens on http://localhost:8000
```

### Frontend

```bash
cd frontend

# Simple HTTP server
python -m http.server 8080
# Open http://localhost:8080 in browser
```

### Database

PostgreSQL must be running on `localhost:5432` with credentials from `.env`.

---

## API Endpoints

### Health Check
- `GET /api/health` - Server status and database connectivity

### Playlists
- `GET /api/playlists` - List all playlists
- `POST /api/playlists` - Create new playlist
- `GET /api/playlists/{id}` - Get specific playlist

### Test
- `GET /api/test-data` - Verify API is responding

---

## Database Schema

**users** - Application users
- id (UUID)
- email (unique)
- username (unique)
- password_hash
- created_at, updated_at

**playlists** - User playlists
- id (UUID)
- name
- description
- owner_id (FK users)
- snapshot_id (for collaborative editing)
- created_at, updated_at

**playlist_collaborators** - Join table for shared playlists
- playlist_id (FK)
- user_id (FK)

**playlist_tracks** - Tracks in playlists
- id (UUID)
- playlist_id (FK)
- spotify_track_id
- added_by_id (FK users)
- added_at

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── core/              # Interfaces, exceptions
│   │   ├── domain/            # Domain models
│   │   ├── use_cases/         # Business logic
│   │   ├── infrastructure/    # DB, Spotify client, cache
│   │   └── interfaces/        # HTTP routes, schemas
│   ├── main.py                # FastAPI app entry point
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── app.js             # Main app
│       ├── api.js             # API client
│       └── ui.js              # UI manager
├── docker-compose.yml
├── nginx.conf
├── .env                       # Local config (git-ignored)
├── .env.example               # Config template
└── .github/copilot-instructions.md
```

---

## Troubleshooting

### Database Connection Error
- Ensure `.env` has correct `DATABASE_URL`
- Check PostgreSQL container is running: `docker-compose ps`
- View logs: `docker-compose logs postgres`

### API Returns 502 Bad Gateway
- Backend container crashed. View logs: `docker-compose logs backend`
- Check database initialization: `docker-compose logs backend | grep -i init`

### Frontend shows "Checking..." indefinitely
- Backend might not be running. Visit http://localhost/api/health
- Check CORS settings in `backend/main.py`
- View browser console for errors (F12)

### Port already in use
- Change ports in `docker-compose.yml` and access via new port
- Or stop conflicting container: `docker-compose down`

---

## Development Workflow

See `.github/copilot-instructions.md` for detailed architecture and development guidelines.

### Next Phases (Not yet implemented)
1. User authentication (JWT, registration/login)
2. Spotify integration (OAuth PKCE, /recommendations API)
3. Audio features analysis and averaging
4. Collaborative editing (HTTP polling)
5. Caching layer (PostgreSQL-backed)
6. Error handling and logging
7. Comprehensive tests

---

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, Pydantic, python-jose
- **Frontend:** Vanilla JS (ES6+), HTML5, CSS3
- **Database:** PostgreSQL
- **Infrastructure:** Docker Compose, Nginx
- **External:** Spotify Web API

---

## License

Course project - Educational use only.
