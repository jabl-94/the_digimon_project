# DigiFarm

DigiFarm is a Digimon companion proof of concept. Its backend API and installable
frontend are separate applications: the FastAPI service owns the game state and
AI integration, while the same responsive Progressive Web App (PWA) runs in a
PC browser or can be installed on Android and desktop.

## Project layout

- `src/` — FastAPI API, SQLite game engine, and Gemini-powered chat.
- `frontend/` — standalone PWA; it does not need Python or the backend source.
- `tests/` — backend and API security tests.

The frontend retains the existing status, feed, and chat features. Chat training
and study requests continue to use the backend's Gemini tools.

## Run locally

The backend requires a bearer token of at least 32 characters and a Gemini API
key. Store them in a private `.env` file in the workspace root; `.env` is
excluded from Git and the Docker build context. If you need to create it:

```sh
install -m 600 /dev/null .env
```

Open `.env` in VS Code and set `DIGIFARM_API_TOKEN` to a random value of at
least 32 characters (for example, generate one with `openssl rand -hex 32`),
and set `GEMINI_API_KEY` to your key. Keep `.env` private and never commit it.

Start the API container:

```sh
docker compose -f .devcontainer/docker-compose.yml up --build
```

Compose reads `.env` from the workspace root and passes credentials to the
container at startup; they are not stored in the image or Compose file. The
workspace `data/` directory is mounted into the container so changes to
`data/digimon.db` persist when it stops.

In a second terminal, serve the frontend:

```sh
python -m http.server 5173 --directory frontend
```

Open <http://localhost:5173>. Enter `http://localhost:8000` as the backend API
address and the token from `.env`. The frontend remembers the API address and
token in that browser's local storage. Use **Change connection** to clear the
token or select another API. The API container does not serve or bundle the
frontend.

## Android and PC deployment

Host the contents of `frontend/` on a static web host and deploy the API
separately. Serve both over HTTPS for Android installation and production use.
Open the frontend URL in a supported browser and choose **Install app** or **Add
to Home screen**. The frontend is a PWA, not a native Android APK.

On first connection, enter the public HTTPS API origin and the API token. Set
`DIGIFARM_CORS_ORIGINS` on the API to a comma-separated list of exact frontend
origins, including scheme and port if nonstandard (for example,
`https://digifarm.example.com`). The local development defaults allow only
`http://localhost:5173` and `http://127.0.0.1:5173`. Wildcard origins are not
accepted.

For local phone testing on a trusted Wi-Fi network, the frontend and API must
both be reachable from the phone. Set `DIGIFARM_BIND_ADDRESS=0.0.0.0` in the
workspace `.env` to expose the API port on the host network, then allow the
frontend's exact local origin in `DIGIFARM_CORS_ORIGINS` and enter the PC's LAN
address as the backend URL. Do not expose this development HTTP setup to the
public internet; use HTTPS and a trusted reverse proxy for deployment.

Optionally set `DIGIFARM_FRONTEND_URL` to the frontend's public URL; the API
root and legacy `/app` path will redirect there.

## API and security

Every API request requires the bearer token. For example, after starting the
API, replace `<your-api-token>` with the value from `.env`:

```sh
curl -X POST http://127.0.0.1:8000/chat \
  -H "Authorization: Bearer <your-api-token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"Say hello!"}'
```

The API limits request bodies to 16 KiB, chat messages to 4,000 characters, and
requests per client address (60 overall and at most 10 chat requests per
minute). These in-memory limits apply to a single process only; enforce
authentication, HTTPS, and rate limits at a trusted reverse proxy before any
public deployment. If a credential was ever committed or shared, revoke and
rotate it; deleting it from the current file does not remove it from Git
history.

Run the backend tests with:

```sh
python -m unittest discover -s tests -v
```
