# Docker Deployment

The identity service ships with a `docker-compose.yml` that runs the full stack: PostgreSQL 16, Redis 7, and the FastAPI service.

## Services

The Compose file defines three services:

| Service | Image | Host Port | Container Port | Purpose |
|---------|-------|-----------|----------------|---------|
| `identity-postgres` | `postgres:16-alpine` | 9001 | 5432 | Primary datastore |
| `identity-redis` | `redis:7-alpine` | 9002 | 6379 | Token denylist, rate limiting |
| `identity-service` | Built from `./service` | 9003 | 9003 | The identity API |

## docker-compose.yml Explained

```yaml
services:
  identity-postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: identity
      POSTGRES_USER: identity
      POSTGRES_PASSWORD: identity_dev
    ports:
      - "9001:5432"
    volumes:
      - identity_pg_data:/var/lib/postgresql/data
    networks:
      - daikon-identity-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U identity"]
      interval: 5s
      timeout: 5s
      retries: 5

  identity-redis:
    image: redis:7-alpine
    ports:
      - "9002:6379"
    networks:
      - daikon-identity-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  identity-service:
    build: ./service
    ports:
      - "9003:9003"
    env_file:
      - .env
    depends_on:
      identity-postgres:
        condition: service_healthy
      identity-redis:
        condition: service_healthy
    networks:
      - daikon-identity-network

volumes:
  identity_pg_data:

networks:
  daikon-identity-network:
    driver: bridge
```

### Key details

- **Health checks**: Both PostgreSQL and Redis have health checks. The identity service waits for both to be healthy before starting (`depends_on` with `condition: service_healthy`).
- **Data persistence**: PostgreSQL data is stored in the `identity_pg_data` Docker volume, so it survives container restarts.
- **Environment**: The service reads its configuration from a `.env` file in the project root. See [Environment Variables](environment.md) for the full list.
- **Networking**: All services communicate over the `daikon-identity-network` bridge network. Other Daikon services can join this network to reach the identity service by container name.

## Commands

### Start the full stack

```bash
docker compose up -d
```

This builds the service image (if needed) and starts all three containers in the background.

### Start only infrastructure (for local dev)

If you want to run the FastAPI service directly on your host (e.g., with `make start` for hot reload), start only the database and cache:

```bash
docker compose up -d identity-postgres identity-redis
```

### View logs

```bash
docker compose logs -f identity-service
```

### Stop everything

```bash
docker compose down
```

This stops and removes containers but preserves the database volume.

### Stop and wipe all data

```bash
docker compose down -v
```

!!! danger "Data loss"
    The `-v` flag removes the `identity_pg_data` volume, permanently deleting all database contents. Only use this when you want a completely fresh start.

## Cross-Service Networking

If you are running other Daikon services (e.g., docu-store) that need to communicate with the identity service, they can join the `daikon-identity-network`:

```yaml
# In another service's docker-compose.yml
services:
  my-service:
    networks:
      - daikon-identity-network

networks:
  daikon-identity-network:
    external: true
```

The identity service will then be reachable at `http://identity-service:9003` from within the Docker network.

## Rebuilding

After code changes, rebuild the service image:

```bash
docker compose build identity-service
docker compose up -d identity-service
```

Or combine both steps:

```bash
docker compose up -d --build identity-service
```
