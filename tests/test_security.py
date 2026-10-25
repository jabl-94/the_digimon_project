import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi import HTTPException
from starlette.requests import Request

from src import engine, main


class EngineSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = engine.DB_PATH
        engine.DB_PATH = str(Path(self.temp_dir.name) / "digimon.db")
        engine.init_db()

    def tearDown(self):
        engine.DB_PATH = self.original_db_path
        self.temp_dir.cleanup()

    def test_training_amount_is_bounded(self):
        for amount in (-1, 0, 26, 10.0, True):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError):
                    engine.train_strength(amount)

    def test_training_caps_stats_and_status_omits_database_id(self):
        engine.train_strength(25)
        digimon = engine.get_digimon_status()
        self.assertEqual(digimon["strength"], 35)
        self.assertNotIn("id", digimon)

        with patch.object(engine, "MAX_STAT_VALUE", 35):
            engine.train_strength(25)
        self.assertEqual(engine.get_digimon_status()["strength"], 35)

    def test_database_file_permissions_are_private(self):
        mode = os.stat(engine.DB_PATH).st_mode & 0o777
        self.assertEqual(mode, 0o600)


class ApiSecurityTests(unittest.TestCase):
    def make_request(self, path="/status", headers=()):
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": list(headers),
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 8000),
        }
        return Request(scope)

    def setUp(self):
        main._rate_limit_buckets.clear()

    def test_missing_or_incorrect_token_is_rejected(self):
        token = "a" * 32
        with patch.dict(os.environ, {"DIGIFARM_API_TOKEN": token}):
            request = self.make_request()
            with self.assertRaises(HTTPException) as error:
                asyncio.run(main.authenticate_and_rate_limit(request))
        self.assertEqual(error.exception.status_code, 401)

    def test_chat_rate_limit_applies_after_authentication(self):
        token = "b" * 32
        request = self.make_request(
            path="/chat",
            headers=[(b"authorization", f"Bearer {token}".encode())],
        )
        with patch.dict(os.environ, {"DIGIFARM_API_TOKEN": token}):
            for _ in range(main.RATE_LIMITS["/chat"]):
                asyncio.run(main.authenticate_and_rate_limit(request))
            with self.assertRaises(HTTPException) as error:
                asyncio.run(main.authenticate_and_rate_limit(request))
        self.assertEqual(error.exception.status_code, 429)

    def test_request_body_limit_rejects_large_payloads(self):
        middleware = main.RequestBodyLimitMiddleware(lambda *_args: None)
        response_messages = []

        async def receive():
            return {
                "type": "http.request",
                "body": b"x" * (main.MAX_REQUEST_BODY_BYTES + 1),
                "more_body": False,
            }

        async def send(message):
            response_messages.append(message)

        async def run():
            await middleware(
                {"type": "http", "method": "POST", "path": "/chat", "headers": []},
                receive,
                send,
            )

        asyncio.run(run())
        self.assertEqual(response_messages[0]["status"], 413)

    def test_status_endpoint_requires_authentication(self):
        token = "c" * 32

        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(engine, "DB_PATH", str(Path(temp_dir) / "digimon.db")),
                patch.dict(os.environ, {"DIGIFARM_API_TOKEN": token}),
            ):
                async def exercise_api():
                    async with main.app.router.lifespan_context(main.app):
                        async with httpx.AsyncClient(
                            transport=httpx.ASGITransport(app=main.app),
                            base_url="http://testserver",
                        ) as client:
                            unauthorized = await client.get("/status")
                            self.assertEqual(unauthorized.status_code, 401)
                            response = await client.get(
                                "/status",
                                headers={"Authorization": f"Bearer {token}"},
                            )
                            self.assertEqual(response.status_code, 200)
                            self.assertNotIn("id", response.json())

                            invalid_message = await client.post(
                                "/chat",
                                headers={"Authorization": f"Bearer {token}"},
                                json={"message": "x" * 4001},
                            )
                            self.assertEqual(invalid_message.status_code, 422)

                asyncio.run(exercise_api())


if __name__ == "__main__":
    unittest.main()
