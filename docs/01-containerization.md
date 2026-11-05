# 01 – Containerization

This document describes how the Flask application is packaged into a Docker image, and the design decisions behind it.

Related issue: #1 – Create Dockerfile

## Goal

Run the application in a container so that it behaves the same way on a developer machine, in the CI pipeline and in production. The image built here is the artifact that the pipeline later tests, scans and publishes.

## Key concepts

| Term | Meaning in this project |
|---|---|
| **Dockerfile** | The recipe describing how the image is built |
| **Image** | The immutable build result (e.g. `cicd-sg:local`), later pushed to the registry |
| **Container** | A running instance of the image |

## Production server

Flask's built-in development server is not suitable for production. The image runs the app with **gunicorn**, a production-grade WSGI server with multiple worker processes.

Dependencies are split into two files:

- `requirements.txt` – runtime dependencies only (`flask`, `gunicorn`); installed into the image
- `requirements-dev.txt` – adds test tools (`pytest`); used locally and in CI, **not** in the image

Fewer packages in the image means a smaller attack surface and fewer findings in the security scan.

## Dockerfile design

The Dockerfile uses a **multi-stage build**:

**Stage 1 – `builder`**
- Starts from `python:3.12-slim`
- Creates a virtual environment in `/opt/venv`
- Copies only `requirements.txt` first, then installs dependencies. This keeps the dependency layer cached, so changing application code does not trigger a reinstall.

**Stage 2 – final image**
- Starts again from a clean `python:3.12-slim`
- Copies only the finished virtual environment and the `app/` directory; build tools and tests are left behind
- Creates and switches to a **non-root user** (`appuser`, UID 10001)
- Exposes port `8000`
- Defines a `HEALTHCHECK` against the `/health` endpoint
- Starts gunicorn with two workers: `gunicorn --bind 0.0.0.0:8000 --workers 2 app.main:app`

### Security-related decisions

| Decision | Reason |
|---|---|
| Slim base image | Fewer OS packages, fewer potential vulnerabilities |
| Multi-stage build | Build-time files and tools do not reach the final image |
| No test dependencies in the image | Smaller attack surface |
| Non-root user | Limits the impact if the application is compromised |
| `.dockerignore` | Keeps `.git`, `.venv`, caches, tests and docs out of the build context |

### Health check

The health check calls `http://localhost:8000/health` every 30 seconds using Python's standard library (the slim image has no `curl`, and adding it would mean an extra package). After three consecutive failures the container is marked `unhealthy`. This status is used later to verify deployments.

## Building and running locally

```bash
docker build -t cicd-sg:local .
docker run -d --name cicd-test -p 8000:8000 cicd-sg:local
```

Verification:

```bash
docker ps                          # STATUS shows (healthy)
docker exec cicd-test whoami       # prints: appuser
curl http://localhost:8000/health  # {"status":"ok"}
```

Clean up:

```bash
docker rm -f cicd-test
```

## Troubleshooting notes

Issues encountered during development and how they were resolved:

| Symptom | Cause | Fix |
|---|---|---|
| `container name "/cicd-test" is already in use` | A container from a previous run still existed | `docker rm -f cicd-test`, then run again |
| Container stuck in `Created` status | The container could not start; the `docker run` output shows the reason | Read the error message from `docker run` |
| `exec: "gunicorn": executable file not found in $PATH` | The image was built from a `requirements.txt` that did not yet include gunicorn | Save the file, rebuild the image; check installed packages with `docker run --rm cicd-sg:local pip list` |

## Next steps

The same Dockerfile is used by the CI pipeline, which builds the image automatically (#3) and scans it with Trivy before publishing (#4).
