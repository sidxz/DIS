# Installation

This guide covers getting the Daikon Identity Service installed and its infrastructure running on your local machine.

## Quick Path

If you want to skip the manual steps, the Makefile handles everything:

```bash
git clone <repo-url> identity-service
cd identity-service
cp .env.example .env
make setup
```

`make setup` will generate RSA keys, install all dependencies (service + SDK + admin UI), and start PostgreSQL and Redis in Docker. Once it finishes, jump to the [Quickstart](quickstart.md).

---

## Step-by-Step

### 1. Clone the repository

```bash
git clone <repo-url> identity-service
cd identity-service
```

### 2. Install dependencies

The project uses a **uv workspace** with two members (`service/` and `sdk/`), managed from the root `pyproject.toml`. A single sync installs everything:

```bash
uv sync
```

This creates a virtual environment and installs both the FastAPI service and the `daikon-identity-sdk` package in editable mode.

### 3. Generate RSA keys for JWT signing

The service signs access tokens with RS256. Generate a 2048-bit RSA key pair into the `keys/` directory:

```bash
mkdir -p keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
```

!!! warning "Keep your private key safe"
    The `keys/` directory is gitignored. Never commit `private.pem` to version control. In production, inject the key via a secrets manager or mount it as a volume.

### 4. Create your `.env` file

```bash
cp .env.example .env
```

The defaults work for local development. You will configure OAuth credentials and the session secret in the [Quickstart](quickstart.md).

### 5. Start infrastructure

The service depends on **PostgreSQL 16** and **Redis 7**, both defined in `docker-compose.yml`. Start only what you need:

```bash
docker compose up -d identity-postgres identity-redis
```

Default ports:

| Service | Port |
|---------|------|
| PostgreSQL | `9001` |
| Redis | `9002` |

Wait for PostgreSQL to report healthy before proceeding:

```bash
docker compose ps
```

### 6. Database migrations

No manual migration step is required. The service runs Alembic migrations **automatically on startup**, so the schema is always up to date when the application boots.

---

## Verify the installation

At this point you should have:

- [x] Python dependencies installed (check with `uv run python -c "import identity_sdk"`)
- [x] RSA key pair in `keys/`
- [x] PostgreSQL and Redis running in Docker
- [x] A `.env` file based on `.env.example`

Next: [Quickstart](quickstart.md) -- configure an OAuth provider and start the service.
