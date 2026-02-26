import os
from fastapi.testclient import TestClient


def test_refresh_rotates_and_revokes_old_token(monkeypatch):
    os.environ["DATABASE_URL"] = "sqlite:///./test_auth.db"
    os.environ["JWT_SECRET_KEY"] = "testsecret"

    # ensure DB tables exist (remove stale test DB first)
    db_file = os.path.join(os.getcwd(), "test_auth.db")
    if os.path.exists(db_file):
        os.remove(db_file)

    # ensure DB tables exist (import models so their tables are registered)
    import app.models.user
    import app.models.refresh_token
    from app.db.session import Base, engine

    Base.metadata.create_all(bind=engine)

    # import app after env is set so the DB engine uses the test DATABASE_URL
    from main import app, COOKIE_NAME, create_refresh_token

    with TestClient(app) as client:
        # create user directly via ORM to avoid db helper transactional issues in tests
        from app.db.session import SessionLocal
        from app.models.user import User as ORMUser

        db = SessionLocal()
        try:
            new = ORMUser(username="rot_user", password_hash="passhash", role="user")
            db.add(new)
            db.commit()
            db.refresh(new)
            uid = new.id
        finally:
            db.close()

        # create initial refresh token
        initial = create_refresh_token({"sub": "rot_user", "role": "user"})

        # set cookie and call /refresh -> should succeed and rotate cookie
        client.cookies.set(COOKIE_NAME, initial, path="/refresh")
        r = client.post("/refresh")
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data

        # cookie should be updated to a new refresh token (parse from Set-Cookie)
        sc = r.headers.get("set-cookie") or ""
        new_token = None
        if "refresh_token=" in sc:
            # extract value between 'refresh_token=' and first ';'
            part = sc.split("refresh_token=", 1)[1]
            new_token = part.split(";", 1)[0]
        assert new_token is not None and new_token != initial

        # using the old refresh token should now fail (send cookie explicitly)
        r2 = client.post("/refresh", headers={"Cookie": f"{COOKIE_NAME}={initial}"})
        assert r2.status_code == 401


def test_logout_all_revokes_every_token():
    os.environ["DATABASE_URL"] = "sqlite:///./test_auth2.db"
    os.environ["JWT_SECRET_KEY"] = "testsecret"

    # ensure DB tables exist (remove stale test DB first)
    db_file = os.path.join(os.getcwd(), "test_auth2.db")
    if os.path.exists(db_file):
        os.remove(db_file)

    # ensure DB tables exist (import models so their tables are registered)
    import app.models.user
    import app.models.refresh_token
    from app.db.session import Base, engine

    Base.metadata.create_all(bind=engine)

    # import app after env is set so DB engine uses the test DATABASE_URL
    from main import app, COOKIE_NAME, create_refresh_token, create_access_token

    from app.db.session import SessionLocal
    from app.models.user import User as ORMUser

    with TestClient(app) as client:
        db = SessionLocal()
        try:
            new = ORMUser(username="multi_user", password_hash="passhash", role="user")
            db.add(new)
            db.commit()
            db.refresh(new)
            uid = new.id
        finally:
            db.close()

        # create multiple refresh tokens
        t1 = create_refresh_token({"sub": "multi_user", "role": "user"})
        t2 = create_refresh_token({"sub": "multi_user", "role": "user"})

        # perform authenticated request using a bearer token
        access_token = create_access_token({"sub": "multi_user", "role": "user"})
        headers = {"Authorization": f"Bearer {access_token}"}
        r = client.post("/logout/all", headers=headers)
        assert r.status_code == 200

        # after logout/all, using the refresh tokens should fail
        client.cookies.set(COOKIE_NAME, t1, path="/refresh")
        r1 = client.post("/refresh")
        assert r1.status_code == 401
        client.cookies.set(COOKIE_NAME, t2, path="/refresh")
        r2 = client.post("/refresh")
        assert r2.status_code == 401
