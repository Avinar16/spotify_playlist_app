# 🎵 Spotify Playlist Generator

Приложение для создания и совместного редактирования плейлистов Spotify на основе анализа музыкальных предпочтений.

## Что делает

- **Генерация плейлистов:** Анализирует топ-треки пользователей, усредняет аудиофичи (valence, energy, danceability, acousticness) и запрашивает рекомендации через Spotify Web API
- **Ручное добавление:** Поиск и добавление треков вручную
- **Совместное редактирование:** Несколько пользователей могут редактировать плейлист (только владелец и приглашенные)
- **Синхронизация в реальном времени:** HTTP polling для отслеживания изменений

## Технологический стек

**Backend:** Python 3.11+, FastAPI, SQLAlchemy, Pydantic v2, HTTPX  
**Frontend:** Vanilla JS (ES6+), HTML5, CSS3  
**База данных:** PostgreSQL  
**Инфраструктура:** Docker Compose, Nginx  
**API:** Spotify Web API (PKCE flow)

## Запуск

```bash
docker-compose up -d
# http://localhost
```

## Структура

- `backend/app/` — Clean Architecture (core, domain, use_cases, infrastructure, interfaces)
- `frontend/js/` — Модули (auth, api, ui, app)
- `.env.example` — Пример переменных окружения
