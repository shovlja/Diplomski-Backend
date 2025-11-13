# tests/test_auth.py
import pytest
import time
import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import text

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.database import engine
from app.models.user import User

API_PREFIX = "/api/v1/auth"


@pytest.mark.asyncio
async def test_register_success(async_client):
    payload = {
        "email": "user1@example.com",
        "password": "Passw0rd!",
        "display_name": "User One"
    }
    r = await async_client.post(f"{API_PREFIX}/register", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["email"] == payload["email"]
    assert data["display_name"] == payload["display_name"]
    assert "id" in data
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email(async_client):
    payload = {
        "email": "dup@example.com",
        "password": "Passw0rd!",
        "display_name": "Dup"
    }
    r1 = await async_client.post(f"{API_PREFIX}/register", json=payload)
    assert r1.status_code == 201, r1.text

    r2 = await async_client.post(f"{API_PREFIX}/register", json=payload)
    assert r2.status_code == 400
    assert r2.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_login_success_and_me(async_client):
    email = "login_ok@example.com"
    password = "Passw0rd!"
    await async_client.post(f"{API_PREFIX}/register", json={
        "email": email,
        "password": password,
        "display_name": "Login OK"
    })

    # OAuth2PasswordRequestForm -> form-data (username/password)
    r = await async_client.post(f"{API_PREFIX}/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    assert token

    r_me = await async_client.get(f"{API_PREFIX}/me", headers={"Authorization": f"Bearer {token}"})
    assert r_me.status_code == 200, r_me.text
    me = r_me.json()
    assert me["email"] == email
    assert me["is_active"] is True


@pytest.mark.asyncio
async def test_login_wrong_password(async_client):
    email = "wrongpass@example.com"
    await async_client.post(f"{API_PREFIX}/register", json={
        "email": email,
        "password": "Passw0rd!",
        "display_name": "WP"
    })

    r = await async_client.post(f"{API_PREFIX}/login", data={"username": email, "password": "badpass"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_me_requires_auth(async_client):
    r = await async_client.get(f"{API_PREFIX}/me")
    assert r.status_code == 401
    assert r.json()["detail"] in ("Not authenticated", "Could not validate credentials")

@pytest.mark.asyncio
async def test_register_normalizes_email_to_lower(async_client):
    payload = {
        "email": "MiXED.Case+tag@Example.COM",
        "password": "Passw0rd!",
        "display_name": "Mixed"
    }
    r = await async_client.post(f"{API_PREFIX}/register", json=payload)
    assert r.status_code == 201, r.text
    data = r.json()
    # treba da bude snimljeno i vraćeno kao lowercase
    assert data["email"] == payload["email"].lower()
    # i da je ID validan UUID string
    uuid.UUID(data["id"])  # neće baciti grešku ako je ok


@pytest.mark.asyncio
async def test_register_validation_errors(async_client):
    # loš email
    bad_email = {
        "email": "not-an-email",
        "password": "Passw0rd!",
        "display_name": "Xy"
    }
    r1 = await async_client.post(f"{API_PREFIX}/register", json=bad_email)
    assert r1.status_code == 422

    # prekratka lozinka
    bad_pwd = {
        "email": "shortpwd@example.com",
        "password": "short",
        "display_name": "Xy"
    }
    r2 = await async_client.post(f"{API_PREFIX}/register", json=bad_pwd)
    assert r2.status_code == 422

    # prekratko ime
    bad_name = {
        "email": "ok@example.com",
        "password": "Passw0rd!",
        "display_name": "X"  # min_length=2
    }
    r3 = await async_client.post(f"{API_PREFIX}/register", json=bad_name)
    assert r3.status_code == 422


@pytest.mark.asyncio
async def test_login_returns_bearer_and_me_has_uuid(async_client):
    email = "bearer@example.com"
    password = "Passw0rd!"
    await async_client.post(f"{API_PREFIX}/register", json={
        "email": email,
        "password": password,
        "display_name": "Bearer"
    })
    r = await async_client.post(f"{API_PREFIX}/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    token = body["access_token"]

    r_me = await async_client.get(f"{API_PREFIX}/me", headers={"Authorization": f"Bearer {token}"})
    assert r_me.status_code == 200, r_me.text
    u = r_me.json()
    # validan UUID string
    uuid.UUID(u["id"])


@pytest.mark.asyncio
async def test_password_is_hashed_in_db(async_client):
    email = "hashcheck@example.com"
    password = "Passw0rd!"
    await async_client.post(f"{API_PREFIX}/register", json={
        "email": email,
        "password": password,
        "display_name": "Hash Check"
    })

    # proveri direktno u bazi da nije raw lozinka
    async with engine.connect() as conn:
        res = await conn.execute(
            text("SELECT password_hash FROM users WHERE email = :email"),
            {"email": email.lower()},
        )
        row = res.first()
        assert row is not None
        assert row[0] != password
        assert isinstance(row[0], str) and len(row[0]) > 20  # heuristika


@pytest.mark.asyncio
async def test_login_inactive_user_forbidden(async_client):
    email = "inactive@example.com"
    password = "Passw0rd!"
    await async_client.post(f"{API_PREFIX}/register", json={
        "email": email,
        "password": password,
        "display_name": "Inactive"
    })

    # deaktiviraj korisnika direktno u bazi
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET is_active = false WHERE email = :email"),
            {"email": email.lower()},
        )

    r = await async_client.post(f"{API_PREFIX}/login", data={"username": email, "password": password})
    assert r.status_code == 403
    assert r.json()["detail"] == "User is inactive"


@pytest.mark.asyncio
async def test_me_with_tampered_token_fails(async_client):
    email = "tamper@example.com"
    password = "Passw0rd!"
    await async_client.post(f"{API_PREFIX}/register", json={
        "email": email,
        "password": password,
        "display_name": "Tamper"
    })
    r = await async_client.post(f"{API_PREFIX}/login", data={"username": email, "password": password})
    token = r.json()["access_token"]

    # pokvari poslednji karakter (signature mismatch)
    bad = token[:-1] + ("A" if token[-1] != "A" else "B")

    r_me = await async_client.get(f"{API_PREFIX}/me", headers={"Authorization": f"Bearer {bad}"})
    assert r_me.status_code == 401
    assert r_me.json()["detail"] in ("Could not validate credentials", "Not authenticated")


@pytest.mark.asyncio
async def test_me_with_expired_token_fails(async_client):
    email = "expired@example.com"
    password = "Passw0rd!"
    reg = await async_client.post(f"{API_PREFIX}/register", json={
        "email": email,
        "password": password,
        "display_name": "Expired"
    })
    assert reg.status_code == 201

    login = await async_client.post(f"{API_PREFIX}/login", data={"username": email, "password": password})
    assert login.status_code == 200
    me_resp = await async_client.get(
        f"{API_PREFIX}/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    user_id = me_resp.json()["id"]

    # ručno napravimo EXPIRED JWT
    secret = settings.jwt_secret or "dev-secret-change-me"
    alg = settings.jwt_alg
    expired_claims = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) - timedelta(seconds=10),
        "iat": datetime.now(timezone.utc) - timedelta(seconds=20),
    }
    expired_token = jwt.encode(expired_claims, secret, algorithm=alg)

    r_me = await async_client.get(f"{API_PREFIX}/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert r_me.status_code == 401
    assert r_me.json()["detail"] in ("Could not validate credentials", "Not authenticated")

    
@pytest.mark.asyncio
async def test_me_tampered_token_unauthorized(async_client):
    email = "tamper@example.com"
    await async_client.post(f"{API_PREFIX}/register", json={
        "email": email, "password": "Passw0rd!", "display_name": "Tamper"
    })
    good = (await async_client.post(f"{API_PREFIX}/login",
            data={"username": email, "password": "Passw0rd!"})).json()["access_token"]

    # Bez verifikacije potpisa:
    header = jwt.get_unverified_header(good)
    payload = jwt.get_unverified_claims(good)

    # Malo ga "pokvarimo"
    payload["sub"] = str(uuid.uuid4())

    # Potpišemo pogrešnim ključem
    bad = jwt.encode(payload, "WRONG_KEY", algorithm=header.get("alg", settings.jwt_alg))

    r = await async_client.get(f"{API_PREFIX}/me", headers={"Authorization": f"Bearer {bad}"})
    assert r.status_code == 401
    assert r.json()["detail"] in ("Could not validate credentials", "Not authenticated")



@pytest.mark.asyncio
async def test_me_token_with_nonexistent_sub(async_client):
    # Token sa sub koji ne postoji u bazi → 401
    bogus_sub = str(uuid.uuid4())
    payload = {"sub": bogus_sub, "exp": int(time.time()) + 60}
    tok = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)

    r = await async_client.get(f"{API_PREFIX}/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401
    assert r.json()["detail"] in ("Could not validate credentials", "Not authenticated")


@pytest.mark.asyncio
async def test_default_role_and_created_at_in_db(async_client):
    email = "role_created_at@example.com"
    await async_client.post(f"{API_PREFIX}/register", json={
        "email": email, "password": "Passw0rd!", "display_name": "RoleTest"
    })

    # direktno u bazu da vidimo system_role i created_at
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as s:
        user = await s.scalar(select(User).where(User.email == email))
        assert user is not None
        assert user.system_role.value == "USER"
        assert user.created_at is not None


@pytest.mark.asyncio
async def test_email_trimmed_on_register_and_login(async_client):
    raw = "   TrimUser@Example.com   "
    clean = "trimuser@example.com"

    # register sa razmacima i upper-case
    r = await async_client.post(f"{API_PREFIX}/register", json={
        "email": raw, "password": "Passw0rd!", "display_name": "Trim"
    })
    # backend treba da normalizuje
    assert r.status_code == 201, r.text
    assert r.json()["email"] == clean

    # login sa razmacima i upper-case – backend opet treba da normalizuje
    r2 = await async_client.post(f"{API_PREFIX}/login", data={"username": raw, "password": "Passw0rd!"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["token_type"] == "bearer"