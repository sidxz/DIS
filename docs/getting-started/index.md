# Getting Started

This section walks you through setting up the Daikon Identity Service from a fresh clone to a running instance with OAuth login.

## Prerequisites

Before you begin, make sure you have the following installed:

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.12+ | Runtime for the FastAPI service and SDK |
| **uv** | latest | Python package manager and workspace tool |
| **Docker** & **Docker Compose** | latest | Runs PostgreSQL 16 and Redis 7 |
| **OpenSSL** | any | Generates RSA key pair for JWT signing |

You will also need **OAuth credentials** from at least one identity provider (Google is the easiest to set up) to enable user authentication.

## What's Covered

- **[Installation](installation.md)** -- Clone the repo, install dependencies, generate JWT keys, and start the database and cache infrastructure.
- **[Quickstart](quickstart.md)** -- Configure an OAuth provider, start the service, and verify everything works end to end.
- **[Configuration](configuration.md)** -- Complete reference for every environment variable, organized by category.
