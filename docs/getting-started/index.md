# Getting Started

This section walks you through setting up Sentinel Auth from scratch to a running instance with OAuth login.

## Prerequisites

### Docker (recommended)

| Tool | Version | Purpose |
|------|---------|---------|
| **Docker** & **Docker Compose** | latest | Runs the Sentinel container, PostgreSQL 16, and Redis 7 |
| **OpenSSL** | any | Generates RSA key pair for JWT signing |

### From Source (contributors)

All of the above, plus:

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.12+ | Runtime for the FastAPI service and SDK |
| **uv** | latest | Python package manager and workspace tool |
| **Node.js** | 18+ | Admin panel and demo frontend |

You will also need **OAuth credentials** from at least one identity provider (Google is the easiest to set up) to enable user authentication.

!!! note "Client app registration"
    Before any frontend can authenticate through Sentinel, you must register it as a **client app** with its redirect URI. The [Quickstart](quickstart.md) covers this step.

## What's Covered

- **[Installation](installation.md)** -- Pull the Docker image (or clone the repo for development), generate JWT keys, and start the full stack.
- **[Quickstart](quickstart.md)** -- Configure an OAuth provider, register client and service apps, and verify everything works end to end.
- **[Configuration](configuration.md)** -- Complete reference for every environment variable, organized by category.
