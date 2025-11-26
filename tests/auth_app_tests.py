import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.api_zadania import app
from api.Entities import Base, User

TEST_DB_URL = "sqlite:///movies.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        admin = session.query(User).filter_by(username="admin").first()
        if not admin:
            hashed_admin = (
                bcrypt.hashpw(b"123", bcrypt.gensalt()).decode("utf-8")
            )
            admin = User(
                username="admin",
                hashed_password=hashed_admin,
                roles="ROLE_ADMIN",
            )
            session.add(admin)

        user = session.query(User).filter_by(username="user").first()
        if not user:
            hashed_user = (
                bcrypt.hashpw(b"user123", bcrypt.gensalt()).decode("utf-8")
            )
            user = User(
                username="user",
                hashed_password=hashed_user,
                roles="ROLE_USER",
            )
            session.add(user)

        session.commit()
    finally:
        session.close()

    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def get_token(client: TestClient, username: str, password: str) -> str:
    resp = client.post(
        "/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    return data["access_token"]


def test_login_success(client: TestClient):
    resp = client.post(
        "/login",
        json={"username": "admin", "password": "123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    resp = client.post(
        "/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


def test_login_nonexistent_user(client: TestClient):
    resp = client.post(
        "/login",
        json={"username": "no_such_user", "password": "whatever"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


def test_create_user_as_admin(client: TestClient):
    token = get_token(client, "admin", "123")

    resp = client.post(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "new_user_from_admin", "password": "secret123"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "new_user_from_admin"
    assert "id" in data


def test_create_user_as_non_admin_forbidden(client: TestClient):
    token = get_token(client, "user", "user123")

    resp = client.post(
        "/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "should_fail", "password": "secret123"},
    )

    assert resp.status_code == 403
    assert resp.json()["detail"] == "Admin role required"


def test_user_details_with_valid_token(client: TestClient):
    token = get_token(client, "user", "user123")

    resp = client.get(
        "/user_details",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "user"
    assert "roles" in data
    assert "ROLE_USER" in data["roles"]


def test_user_details_without_token(client: TestClient):
    resp = client.get("/user_details")
    assert resp.status_code in (401, 403)


def test_get_movies_requires_auth(client: TestClient):
    resp = client.get("/movies")
    assert resp.status_code in (401, 403)

    token = get_token(client, "user", "user123")
    resp = client.get("/movies", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_movies_crud(client: TestClient):
    token = get_token(client, "user", "user123")

    # CREATE
    resp = client.post(
        "/movies",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "movieId": 1001,
            "title": "Test Movie",
            "genres": "Action",
        },
    )
    assert resp.status_code == 201
    movie = resp.json()
    assert movie["title"] == "Test Movie"
    movie_id = movie["movieId"]

    # READ
    resp = client.get(f"/movies/{movie_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["movieId"] == movie_id

    # UPDATE
    resp = client.put(
        f"/movies/{movie_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "movieId": movie_id,
            "title": "Updated Movie",
            "genres": "Drama",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Movie"

    # DELETE
    resp = client.delete(f"/movies/{movie_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    # READ AFTER DELETE
    resp = client.get(f"/movies/{movie_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_links_crud(client: TestClient):
    token = get_token(client, "user", "user123")

    # CREATE
    resp = client.post(
        "/links",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "movie_id": 1,
            "imdb_id": "tt999",
            "tmdb_id": "tmdb777",
        },
    )
    assert resp.status_code == 201
    link_id = resp.json()["movieId"]

    # READ
    resp = client.get(f"/links/{link_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

    # UPDATE
    resp = client.put(
        f"/links/{link_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "movie_id": link_id,
            "imdb_id": "ttUPDATED",
            "tmdb_id": "tmdbUPDATED",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["imdb_id"] == "ttUPDATED"

    # DELETE
    resp = client.delete(f"/links/{link_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    # READ AFTER DELETE
    resp = client.get(f"/links/{link_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_ratings_crud(client: TestClient):
    token = get_token(client, "user", "user123")

    # CREATE
    resp = client.post(
        "/ratings",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "userId": 1,
            "movieId": 1,
            "rating": 4.5,
        },
    )
    assert resp.status_code == 201
    rating_user_id = resp.json()["userId"]
    rating_movie_id = resp.json()["movieId"]

    # READ
    resp = client.get(f"/ratings/{rating_user_id}/{rating_movie_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["rating"] == 4.5

    # UPDATE
    resp = client.put(
        f"/ratings/{rating_user_id}/{rating_movie_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "userId": rating_user_id,
            "movieId": rating_movie_id,
            "rating": 3.0,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["rating"] == 3.0

    # DELETE
    resp = client.delete(f"/ratings/{rating_user_id}/{rating_movie_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    # READ AFTER DELETE
    resp = client.get(f"/ratings/{rating_user_id}/{rating_movie_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_tags_crud(client: TestClient):
    token = get_token(client, "user", "user123")

    # CREATE
    resp = client.post(
        "/tags",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "userId": 1,
            "movieId": 1,
            "tag": "Adventure",
        },
    )
    assert resp.status_code == 201
    tag_user_id = resp.json()["userId"]
    tag_movie_id = resp.json()["movieId"]
    tag_name = resp.json()["tag"]

    # READ
    resp = client.get(f"/tags/{tag_user_id}/{tag_movie_id}/{tag_name}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["tag"] == "Adventure"

    # UPDATE
    resp = client.put(
        f"/tags/{tag_user_id}/{tag_movie_id}/{tag_name}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "userId": tag_user_id,
            "movieId": tag_movie_id,
            "tag": "UpdatedTag",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["tag"] == "UpdatedTag"

    # DELETE
    resp = client.delete(f"/tags/{tag_user_id}/{tag_movie_id}/{tag_name}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204

    # READ AFTER DELETE
    resp = client.get(f"/tags/{tag_user_id}/{tag_movie_id}/{tag_name}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
