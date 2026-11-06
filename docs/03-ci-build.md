# 03 – CI: Build Docker image

## Goal

After the tests pass, the pipeline automatically builds the Docker image and verifies that the container actually starts and responds. A broken image never reaches the later stages (security scan, push, deploy).

## How it works

The `build` job in `.github/workflows/ci-cd.yml` depends on the `test` job (`needs: test`), so it only runs when all tests are green.

Steps:

1. **Check out code** – `actions/checkout@v5`
2. **Set up Docker Buildx** – `docker/setup-buildx-action@v4`
3. **Build image** – `docker/build-push-action@v7`
   - `push: false` – the image is not pushed yet (see issue #5)
   - `load: true` – the image is loaded into the runner's local Docker so it can be started
   - tag: `cicd-sg:<commit SHA>` – every build is traceable to its commit
   - `cache-from` / `cache-to: type=gha` – layers are cached in the GitHub Actions cache, so later builds are faster
4. **Smoke test**
   - the container is started on port 8000
   - `curl` calls the `/health` endpoint, retrying up to 10 times
   - `docker exec smoke whoami` must return `appuser` (the container does not run as root)
5. **Show container logs** and **Clean up** – run even if a previous step failed (`if: always()`), which helps debugging

The runner is pinned to `ubuntu-24.04` so a change to `ubuntu-latest` can't break the build unexpectedly.

## Branch protection

`Build docker image` is a required status check on `main`, alongside `Run tests`. A pull request can only be merged if the image builds and passes the smoke test.


## Verify locally

```powershell
docker build -t cicd-sg:local .
docker run -d --name cicd-test -p 8000:8000 cicd-sg:local
curl http://localhost:8000/health
docker exec cicd-test whoami
docker rm -f cicd-test
```