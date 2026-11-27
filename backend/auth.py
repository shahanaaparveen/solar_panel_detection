"""Configurable OIDC/JWKS bearer-token validation and project authorization."""
from functools import lru_cache
import logging
import os
from urllib.parse import urlparse

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from bson import ObjectId

logger = logging.getLogger("solar_inspect.auth")
bearer = HTTPBearer(auto_error=False)


def auth_enabled():
    return os.getenv("AUTH_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def auth_status():
    if not auth_enabled():
        return "DISABLED_DEVELOPMENT"
    try:
        _auth_config()
    except HTTPException:
        return "MISCONFIGURED"
    return "CONFIGURED"


def _auth_config():
    issuer = os.getenv("AUTH_ISSUER", "").strip()
    audience = [value.strip() for value in os.getenv("AUTH_AUDIENCE", "").split(",") if value.strip()]
    jwks_url = os.getenv("AUTH_JWKS_URL", "").strip()
    if not issuer or not audience or not jwks_url:
        raise HTTPException(503, "Authentication is enabled but issuer, audience, or JWKS URL is not configured")
    issuer_url = urlparse(issuer)
    parsed = urlparse(jwks_url)
    localhost = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    issuer_is_local = issuer_url.hostname in {"localhost", "127.0.0.1", "::1"}
    allow_http = os.getenv("AUTH_ALLOW_HTTP_JWKS", "false").lower() == "true"
    if issuer_url.scheme != "https" and not (issuer_url.scheme == "http" and issuer_is_local and allow_http):
        raise HTTPException(503, "OIDC issuer must use HTTPS")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and (localhost or allow_http)):
        raise HTTPException(503, "JWKS URL must use HTTPS")
    if parsed.username or parsed.password:
        raise HTTPException(503, "JWKS URL must not include embedded credentials")
    algorithms = [value.strip() for value in os.getenv("AUTH_ALLOWED_ALGORITHMS", "RS256").split(",") if value.strip()]
    if not algorithms or any(value not in {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"} for value in algorithms):
        raise HTTPException(503, "Only asymmetric JWT signing algorithms are supported")
    try:
        clock_skew = int(os.getenv("AUTH_CLOCK_SKEW_SECONDS", "30"))
    except ValueError:
        raise HTTPException(503, "AUTH_CLOCK_SKEW_SECONDS must be an integer from 0 to 300") from None
    if not 0 <= clock_skew <= 300:
        raise HTTPException(503, "AUTH_CLOCK_SKEW_SECONDS must be an integer from 0 to 300")
    return issuer, audience, jwks_url, algorithms, clock_skew


@lru_cache(maxsize=4)
def _jwks_client(url):
    from jwt import PyJWKClient
    return PyJWKClient(url, timeout=5, cache_keys=True)


def _decode_token(token):
    try:
        import jwt
        issuer, audience, jwks_url, algorithms, clock_skew = _auth_config()
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        return jwt.decode(token, signing_key.key, algorithms=algorithms,
            audience=audience, issuer=issuer,
            options={"require": ["exp", "sub", "iss", "aud"]},
            leeway=clock_skew)
    except HTTPException:
        raise
    except jwt.PyJWKClientConnectionError:
        logger.warning("Configured identity provider JWKS endpoint is unavailable")
        raise HTTPException(503, "Identity provider key service is unavailable") from None
    except Exception as exc:
        logger.info("Bearer-token validation failed (%s)", type(exc).__name__)
        raise HTTPException(401, "Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"}) from None


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not auth_enabled():
        return {"sub": "development", "roles": ["solar-inspect-admin"], "_development_auth": True}
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Bearer access token required", headers={"WWW-Authenticate": "Bearer"})
    return _decode_token(credentials.credentials)


def is_admin(claims):
    claim_name = os.getenv("AUTH_ADMIN_CLAIM", "roles")
    expected = os.getenv("AUTH_ADMIN_VALUE", "solar-inspect-admin")
    values = claims.get(claim_name, [])
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        values = []
    return expected in values or claims.get("solar_inspect_admin") is True


def authorized_project_ids(claims):
    claim_name = os.getenv("AUTH_PROJECTS_CLAIM", "project_ids")
    values = claims.get(claim_name, [])
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, (list, tuple, set)):
        values = []
    return {str(value) for value in values if isinstance(value, (str, int))}


def project_filter(claims):
    if is_admin(claims):
        return {"deletedAt": {"$exists": False}}
    permitted = authorized_project_ids(claims)
    object_ids = [ObjectId(value) for value in permitted if ObjectId.is_valid(value)]
    clauses = [{"ownerSubject": claims["sub"]}]
    if object_ids:
        clauses.append({"_id": {"$in": object_ids}})
    return {"deletedAt": {"$exists": False}, "$or": clauses}


def require_project_access(project_id: str, claims=Depends(get_current_user)):
    if is_admin(claims) or project_id in authorized_project_ids(claims):
        return claims
    from database import projects_col
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(404, "Project not found") from None
    project = projects_col.find_one({"_id": oid}, {"ownerSubject": 1})
    if not project or project.get("ownerSubject") != claims.get("sub"):
        raise HTTPException(404, "Project not found")
    return claims
