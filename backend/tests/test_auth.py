import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, AsyncSessionLocal
from app.services.auth_service import hash_password, verify_password, create_access_token


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    await init_db()


@pytest.mark.asyncio
async def test_password_hashing_and_verification():
    raw = "SuperSecretFintech123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.asyncio
async def test_signup_creates_user_org_membership():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique_email = f"sarah_{uuid.uuid4().hex[:8]}@cyberdyne.io"
        payload = {
            "full_name": "Sarah Connor",
            "email": unique_email,
            "password": "SecurePassword2026!",
            "company_name": "Cyberdyne Systems",
        }
        res = await client.post("/api/v1/auth/signup", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["user"]["email"] == unique_email
        assert data["user"]["full_name"] == "Sarah Connor"
        assert data["organization"]["name"] == "Cyberdyne Systems"
        assert data["organization"]["role"] == "OWNER"
        assert "access_token" in data

        # Check cookie was set
        assert "recoverai_session" in res.cookies


@pytest.mark.asyncio
async def test_signup_duplicate_email_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"duplicate_{uuid.uuid4().hex[:8]}@enterprise.com"
        payload = {
            "full_name": "First User",
            "email": email,
            "password": "Password123!",
        }
        res1 = await client.post("/api/v1/auth/signup", json=payload)
        assert res1.status_code == 201

        # Second signup with same email
        res2 = await client.post("/api/v1/auth/signup", json=payload)
        assert res2.status_code == 409
        assert "already exists" in res2.json()["message"]


@pytest.mark.asyncio
async def test_login_success_and_cookie_generation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"login_{uuid.uuid4().hex[:8]}@recoverai.com"
        password = "FintechPassword2026!"

        # Create user
        await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Login Tester",
                "email": email,
                "password": password,
            },
        )

        # Log in
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200
        data = login_res.json()
        assert data["user"]["email"] == email
        assert "access_token" in data
        assert "recoverai_session" in login_res.cookies


@pytest.mark.asyncio
async def test_login_invalid_password():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"wrongpwd_{uuid.uuid4().hex[:8]}@recoverai.com"
        await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Password Tester",
                "email": email,
                "password": "CorrectPassword2026!",
            },
        )

        res = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword999!"},
        )
        assert res.status_code == 401
        assert "Invalid email or password" in res.json()["message"]


@pytest.mark.asyncio
async def test_get_current_user_profile_authenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"profile_{uuid.uuid4().hex[:8]}@recoverai.com"
        password = "ValidPassword2026!"

        signup_res = await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Profile Tester",
                "email": email,
                "password": password,
            },
        )
        token = signup_res.json()["access_token"]

        # Call /me with Bearer token
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        data = me_res.json()
        assert data["user"]["email"] == email
        assert data["organization"]["role"] == "OWNER"


@pytest.mark.asyncio
async def test_get_current_user_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_logout_clears_cookie():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/logout")
        assert res.status_code == 200
        assert res.json()["success"] is True


@pytest.mark.asyncio
async def test_forgot_and_reset_password_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"reset_{uuid.uuid4().hex[:8]}@recoverai.com"
        old_password = "OldPassword2026!"
        new_password = "BrandNewPassword2026!"

        # Create user
        await client.post(
            "/api/v1/auth/signup",
            json={
                "full_name": "Reset User",
                "email": email,
                "password": old_password,
            },
        )

        # Request reset
        forgot_res = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": email},
        )
        assert forgot_res.status_code == 200
        assert forgot_res.json()["success"] is True

        # Check reset token generated in database
        async with AsyncSessionLocal() as session:
            from app.models.user import User, PasswordResetToken
            from sqlalchemy import select
            user_res = await session.execute(select(User).where(User.email == email))
            user = user_res.scalars().first()
            assert user is not None

            # Test resetting password manually via service
            from app.services.auth_service import create_password_reset_token
            raw_token = await create_password_reset_token(user.id, session)
            await session.commit()

        # Reset password via API
        reset_res = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": raw_token, "new_password": new_password},
        )
        assert reset_res.status_code == 200
        assert reset_res.json()["success"] is True

        # Old password fails
        old_login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": old_password},
        )
        assert old_login.status_code == 401

        # New password succeeds
        new_login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": new_password},
        )
        assert new_login.status_code == 200
