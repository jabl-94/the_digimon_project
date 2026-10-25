# How to use DigiFarm

DigiFarm has two separate parts:

- The **backend** is a FastAPI server on port `8000`. It stores game data and
  handles chat.
- The **frontend** is a static web app served on port `5173`. It connects to
  the backend from your browser.

You need to start both parts. The backend requires a private API token and a
Gemini API key.

## 1. Configure credentials

From the workspace root, create a private `.env` file if you do not already
have one:

```sh
install -m 600 /dev/null .env
```

Open `.env` in VS Code and add:

```dotenv
DIGIFARM_API_TOKEN=replace-with-a-random-secret-of-at-least-32-characters
GEMINI_API_KEY=your-gemini-api-key
```

Keep these values private. Do not commit `.env` or share the API token. The
backend will not accept API requests unless the token is at least 32 characters.

## 2. Start the backend server

### Recommended: start it with Docker Compose

From the workspace root, run:

```sh
docker compose -f .devcontainer/docker-compose.yml up --build
```

This starts the backend container and runs the API server automatically. Leave
this terminal open while using the app. The API is available at
`http://localhost:8000`; game data is saved under `data/` in the workspace.

If the container is already running but the API is not, start or restart the
Compose service with:

```sh
docker compose -f .devcontainer/docker-compose.yml up
```

To stop it, press `Ctrl+C` in the Compose terminal. You can also stop the
service from another terminal with:

```sh
docker compose -f .devcontainer/docker-compose.yml down
```

### Alternative: run the backend inside the VS Code Dev Container

If you opened the project using **Reopen in Container** and are not using the
Compose command above to run the API, open a terminal at the workspace root and
start Uvicorn:

```sh
set -a
. ./.env
set +a
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

This loads the credentials from `.env` into the terminal environment and runs
the API with auto-reload enabled. Keep this terminal open. Stop the server with
`Ctrl+C`.

Use only one backend startup method at a time; both methods use port `8000`.

## 3. Start the frontend

Open a **second terminal** at the workspace root and serve the frontend files:

```sh
python -m http.server 5173 --directory frontend
```

Keep this terminal open too. Stop the frontend server with `Ctrl+C`.

## 4. Open and connect the app

In your browser, open <http://localhost:5173>. On the connection screen:

1. Enter `http://localhost:8000` as the backend API address.
2. Enter the value of `DIGIFARM_API_TOKEN` from `.env`.
3. Connect to start using DigiFarm.

The frontend saves the API address and token in that browser's local storage.
Use **Change connection** to update the address or clear the saved token.

## Common checks

- If the frontend does not load, check that its terminal is still running and
  that it says it is serving on port `5173`.
- If the app cannot reach the API, check that the backend terminal/container is
  running and that the address is `http://localhost:8000`.
- If the API reports that authentication is not configured, check that
  `DIGIFARM_API_TOKEN` is set in `.env` and has at least 32 characters. When
  running Uvicorn directly, restart it after changing `.env`.
- If chat does not work, check that `GEMINI_API_KEY` is set correctly and
  restart the backend.
- You can see the API's interactive documentation at
  <http://localhost:8000/docs>. API operations still require authentication.

## Run backend tests

From the workspace root, run:

```sh
python -m unittest discover -s tests -v
```
