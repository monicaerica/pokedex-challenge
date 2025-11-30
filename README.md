# Pokedex API

A RESTful API that provides Pokémon information with fun translations, built with FastAPI and clean architecture principles.

## Overview

This microservice fetches Pokémon data from the [PokéAPI](https://pokeapi.co/) and applies creative translations using the [FunTranslations API](https://funtranslations.com/api/).

## Features

### Endpoint 1: Basic Pokémon Information
### GET /pokemon/{name}

Returns standard Pokémon information including name, description, habitat, and legendary status.

**Example:**
```bash
curl http://localhost:8000/pokemon/mewtwo
```

**Response:**
```json
{
  "name": "mewtwo",
  "description": "It was created by a scientist after years of horrific gene splicing and DNA engineering experiments.",
  "habitat": "rare",
  "is_legendary": true
}
```

### Endpoint 2: Translated Pokémon Information
### GET /pokemon/{name}/translated

Returns Pokémon information with a fun translation applied based on these rules:
- **Yoda translation**: If the Pokémon is legendary OR lives in a cave habitat
- **Shakespeare translation**: For all other Pokémon

**Example:**
```bash
curl http://localhost:8000/pokemon/mewtwo/translated
```

**Response:**
```json
{
  "name": "mewtwo",
  "description": "Created by a scientist after years of horrific gene splicing and dna engineering experiments, it was.",
  "habitat": "rare",
  "is_legendary": true
}
```

## Requirements

- Python 3.11 or higher
- Poetry (for dependency management)
- Docker (for Redis and testcontainers tests)

## Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/monicaerica/pokedex-challenge.git
cd pokedex-challenge
```

### 2. Install Poetry (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 3. Install dependencies
```bash
poetry install
```

## Running the Application
### Option 1: Using Poetry (Recommended for Development)

#### Start Redis
```bash
# Start Redis using Docker Compose
docker-compose up -d redis
```

#### Run the Application
```bash
# Run with Poetry
poetry run uvicorn app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

#### Stop Redis
```bash
docker-compose down
```

### Option 2: Using Docker Compose (Full Stack)

```bash
# Start both Redis and the application
docker-compose up

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop all services
docker-compose down
```

The API will be available at http://localhost:8000

### Services
- **app**: FastAPI application (port 8000)
- **redis**: Redis cache (port 6379)

## Testing

### Run All Tests
```bash
poetry run pytest -v
```

### Unit Tests
```bash
poetry run pytest tests/unit/ -v
```

### Integration Tests

#### E2E Tests (FakeRedis)
Fast tests using FakeRedis mock:
```bash
poetry run pytest tests/integration/test_e2e_api.py -v
```

#### Testcontainers Tests (Real Redis)
Integration tests with real Redis container:
```bash
poetry run pytest tests/integration/test_with_testcontainers.py -v
```

## What Testcontainers Tests Verify

1. **Real Redis Integration**: Uses an actual Redis container instead of mocks
2. **Caching Behavior**: Verifies that data is properly cached and retrieved
3. **Container Lifecycle**: Tests container startup, connection, and cleanup
4. **Production-like Environment**: Tests run against real infrastructure

**Requirements:**
- Docker must be running
- testcontainers package (included in dev dependencies)

### Test Coverage
```bash
poetry run pytest --cov=app --cov-report=html
```

## Architecture

```
app/
├── main.py              # FastAPI application and endpoints
├── models.py            # Pydantic response models
├── dependencies.py      # Dependency injection setup
├── clients/
│   ├── pokeapi_client.py       # PokeAPI integration with caching
│   └── translation_client.py   # Translation API with caching
└── services/
    └── pokemon_service.py      # Business logic

tests/
├── unit/                # Unit tests with mocks
└── integration/         # Integration tests
    ├── test_e2e_api.py           # E2E tests with FakeRedis
    └── test_with_testcontainers.py  # Tests with real Redis container
```

## Architecture & Design Decisions

### Layered Architecture
- **Clients Layer**: Handles external API communication with error handling and caching
- **Service Layer**: Contains business logic (translation rules, data transformation)
- **API Layer**: FastAPI routes with dependency injection

### Caching Strategy
Both external API clients implements Redis caching for improved performance:
- Minimize external API calls and avoid rate limits
- Improve response times for repeated requests
- Only cache successful responses (errors trigger retries)

### Error Handling
- **404 errors**: Pokémon not found
- **503 errors**: External API failures (network issues, rate limits, server errors)
- Clear error messages propagated to API consumers

## What I Would Do Differently for Production

### 1. API Key Management & Rate Limits
- **Current**: Using free tier of FunTranslations API (60 requests/day) and PokéAPI (no authentication required)
- **Production**:  Subscribe to [FunTranslations Premium API](https://funtranslations.com/api/) for higher rate limits and guaranteed availability, get an API key, and store it in my environment variables

### 2. Security
- **Current**: No authentication or authorization. All endpoints are publicly accessible.
- **Production**:
  - Implement authentication using **OAuth2 and JSON Web Tokens (JWT)**, leveraging FastAPI's built-in security features.
  - All critical endpoints (e.g., `/pokemon/{name}`) will be protected by a Bearer Token requirement.
  - A secure, long-lived **JWT Secret Key** will be stored as an **environment variable** in the production environment (e.g., `JWT_SECRET`) for signing and verifying tokens.
  - **Authorization** should be implemented to check that the authenticated user has the necessary role or permissions to access the resource (e.g., paid vs. free tier users).
  - Implement rate limiting per authenticated user