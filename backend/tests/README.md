"""README for running tests"""

# Running Tests

## Install test dependencies

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio aiosqlite
```

## Run all tests

```bash
pytest
```

## Run specific test file

```bash
pytest tests/test_auth.py
```

## Run specific test

```bash
pytest tests/test_auth.py::test_register_user_success
```

## Run with verbose output

```bash
pytest -v
```

## Run with coverage report

```bash
pip install pytest-cov
pytest --cov=app --cov-report=html
```

## Run only unit tests

```bash
pytest -m unit
```

## Run only integration tests

```bash
pytest -m integration
```

## Test markers available

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Tests requiring database
- `@pytest.mark.slow` - Slow tests

## Test structure

```
backend/
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_auth.py          # Auth use case tests
│   ├── test_playlists.py     # Playlist use case tests
│   ├── test_lastfm_client.py # Last.fm client tests
│   └── test_bridge_artists.py # Bridge artists tests
├── pytest.ini                 # Pytest configuration
└── requirements.txt           # Dependencies
```

## Notes

- Tests use in-memory SQLite database for speed
- API clients are mocked to avoid external dependencies
- All tests are async-compatible
- Add `pytest-asyncio` to run async tests
