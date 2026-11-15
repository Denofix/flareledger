# Container implementation

The implemented application Dockerfiles live in [backend/](../../backend/Dockerfile)
and [frontend/](../../frontend/Dockerfile). Backend and frontend CI build the actual
images. Compose keeps writable SQLite state in its own volume and mounts the
source corpus read-only. The local web image serves the compiled frontend with
Caddy; the public frontend is hosted on Vercel. See [local container startup](../README.md)
and the dated [release audit](../../docs/RELEASE_AUDIT.md).
