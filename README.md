This is the repository to my personal project to leverage AI to make digimon "real".

After seeing that Bandai Namco is sleeping at the wheel, and that Meta is going ahead with a similar concept with Muse. I decided that I would begin taking a crack at this idea of mine.

First with a proof of concept, then we will see where this takes us

## Running locally

The API requires a bearer token of at least 32 characters. The chat endpoint also
requires a Gemini API key. Store both in a local `.env` file in the workspace
root; `.env` is excluded from Git and the Docker build context:

```sh
cp .env
chmod 600 .env
```

Open `.env` in VS Code, replace the API token with a random value of at least
32 characters (for example, the output of `openssl rand -hex 32`), and replace
the Gemini API key with your key. Keep `.env` private and never commit it.

Start the container with:

```sh
docker compose -f .devcontainer/docker-compose.yml up --build
```

Compose reads `.env` from the workspace root and passes the credentials to the
container at startup; they are not stored in the image or Compose file.

Compose mounts the workspace `data/` directory into the container, so the app
uses `data/digimon.db` and its changes remain on the host when the container
stops.

To verify the API and Gemini connection, run this in another terminal after
starting the container, replacing `<your-api-token>` with the token from `.env`:

```sh
curl -X POST http://127.0.0.1:8000/chat \
  -H "Authorization: Bearer <your-api-token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"Say hello!"}'
```

The Compose port is bound to localhost. Use the bearer token on every API
request.

The API limits request bodies to 16 KiB, chat messages to 4,000 characters, and
requests per client address (60 requests overall and at most 10 chat requests
per minute). These in-memory limits apply to a single process only; enforce
authentication, HTTPS, and rate limits at a trusted reverse proxy before any
public deployment. If a credential was ever committed or shared, revoke and
rotate it; deleting it from the current file does not remove it from Git history.
