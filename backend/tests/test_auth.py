"""Synthetic OIDC/JWKS auth and project isolation integration checks."""
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
import pytest
from fastapi.testclient import TestClient

from main import app
import main
from database import images_col, projects_col


@pytest.fixture(scope="module")
def oidc_test_server():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update(kid="solar-test-key", use="sig", alg="RS256")

    class JwksHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = json.dumps({"keys": [public_jwk]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), JwksHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield private_key, f"http://127.0.0.1:{server.server_port}/jwks"
    server.shutdown()
    server.server_close()


def _configure(monkeypatch, jwks_url):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_ISSUER", "https://identity.example.test/")
    monkeypatch.setenv("AUTH_AUDIENCE", "solar-inspect-api")
    monkeypatch.setenv("AUTH_JWKS_URL", jwks_url)
    monkeypatch.setenv("AUTH_ALLOW_HTTP_JWKS", "true")


def _token(private_key, subject):
    now = int(time.time())
    return jwt.encode({"sub": subject, "iss": "https://identity.example.test/",
                       "aud": "solar-inspect-api", "iat": now, "exp": now + 300,
                       "roles": []}, private_key, algorithm="RS256",
                      headers={"kid": "solar-test-key"})


def _expired_token(private_key, subject):
    now = int(time.time())
    return jwt.encode({"sub": subject, "iss": "https://identity.example.test/",
                       "aud": "solar-inspect-api", "iat": now - 600, "exp": now - 300,
                       "roles": []}, private_key, algorithm="RS256",
                      headers={"kid": "solar-test-key"})


def test_api_requires_valid_token_and_hides_cross_project_records(monkeypatch, oidc_test_server):
    private_key, jwks_url = oidc_test_server
    _configure(monkeypatch, jwks_url)
    owner_token = _token(private_key, "owner-a")
    foreign_token = _token(private_key, "owner-b")
    with TestClient(app) as client:
        assert client.get("/api/projects").status_code == 401
        created = client.post("/api/projects", headers={"Authorization": f"Bearer {owner_token}"},
                              json={"projectName": "Owned by A"})
        assert created.status_code == 200
        project_id = created.json()["_id"]
        assert "ownerSubject" not in created.json()
        assert client.get("/api/projects", headers={"Authorization": f"Bearer {owner_token}"}).json()[0]["_id"] == project_id
        assert client.get(f"/api/projects/{project_id}", headers={"Authorization": f"Bearer {foreign_token}"}).status_code == 404
        assert client.get("/api/projects", headers={"Authorization": "Bearer invalid"}).status_code == 401
        assert client.get("/api/projects", headers={"Authorization": f"Bearer {_expired_token(private_key, 'owner-a')}"}).status_code == 401


def test_enabled_auth_without_provider_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.delenv("AUTH_ISSUER", raising=False)
    monkeypatch.delenv("AUTH_AUDIENCE", raising=False)
    monkeypatch.delenv("AUTH_JWKS_URL", raising=False)
    with TestClient(app) as client:
        assert client.get("/api/health").json()["authentication"] == "MISCONFIGURED"
        response = client.get("/api/projects", headers={"Authorization": "Bearer some-token"})
        assert response.status_code == 503


def test_project_image_content_requires_project_access(monkeypatch, oidc_test_server, tmp_path):
    private_key, jwks_url = oidc_test_server
    _configure(monkeypatch, jwks_url)
    monkeypatch.setattr(main, "UPLOAD_DIR", tmp_path)
    project = {"projectName": "Image fixture", "ownerSubject": "image-owner", "createdAt": "now"}
    project_oid = projects_col.insert_one(project).inserted_id
    project_id = str(project_oid)
    image_id = "synthetic-image-1"
    relative = Path("rgb") / project_id / "fixture.png"
    image_path = tmp_path / relative
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"synthetic image bytes")
    images_col.insert_one({"imageId": image_id, "projectId": project_id,
        "path": str(relative).replace("\\", "/"), "imageName": "fixture.png"})
    owner = _token(private_key, "image-owner")
    other = _token(private_key, "other-owner")
    try:
        with TestClient(app) as client:
            path = f"/api/projects/{project_id}/images/{image_id}/content"
            assert client.get(path, headers={"Authorization": f"Bearer {other}"}).status_code == 404
            upload = client.post(f"/api/projects/{project_id}/upload", headers={"Authorization": f"Bearer {other}"},
                data={"image_type": "rgb"}, files={"files": ("blocked.png", b"not an image", "image/png")})
            assert upload.status_code == 404
            response = client.get(path, headers={"Authorization": f"Bearer {owner}"})
            assert response.status_code == 200
            assert response.content == b"synthetic image bytes"
    finally:
        projects_col.delete_one({"_id": project_oid})
        images_col.delete_one({"imageId": image_id})
