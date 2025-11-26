from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Entities import Movie, Link, Rating, Tag, User, Base

app = FastAPI()

engine = create_engine('sqlite:///movies.db', connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

SECRET_KEY = "super_secret_key"
ALGORITHM = "HS256"


class LoginData(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


def require_admin(payload: dict = Depends(verify_token)):
    roles = payload.get("roles", [])
    if isinstance(roles, str):
        roles = [r.strip() for r in roles.split(",") if r.strip()]

    if "ROLE_ADMIN" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return payload


@app.get("/")
def hello_world(payload: dict = Depends(verify_token)):
    return {"Hello": "World"}


@app.get("/movies")
def get_movies(payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        movies = session.query(Movie).all()
        return [
            {k: v for k, v in m.__dict__.items() if k != "_sa_instance_state"}
            for m in movies
        ]
    finally:
        session.close()


@app.get("/links")
def get_links(payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        links = session.query(Link).all()
        return [
            {k: v for k, v in l.__dict__.items() if k != "_sa_instance_state"}
            for l in links
        ]
    finally:
        session.close()


@app.get("/ratings")
def get_ratings(payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        ratings = session.query(Rating).all()
        return [
            {k: v for k, v in r.__dict__.items() if k != "_sa_instance_state"}
            for r in ratings
        ]
    finally:
        session.close()


@app.get("/tags")
def get_tags(payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        tags = session.query(Tag).all()
        return [
            {k: v for k, v in t.__dict__.items() if k != "_sa_instance_state"}
            for t in tags
        ]
    finally:
        session.close()


@app.post("/users", response_model=UserOut)
def create_user(
        user: UserCreate,
        payload: dict = Depends(require_admin)
):
    session = SessionLocal()
    try:
        existing = session.query(User).filter(User.username == user.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")

        db_user = User(
            username=user.username,
            hashed_password=hash_password(user.password),
            roles="ROLE_USER"
        )
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user
    finally:
        session.close()


@app.post("/login")
def login(data: LoginData):
    session = SessionLocal()
    try:
        db_user = session.query(User).filter(User.username == data.username).first()
        if not db_user or not verify_password(data.password, db_user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        roles_str = db_user.roles or ""
        roles_list = [r.strip() for r in roles_str.split(",") if r.strip()]

        payload = {
            "sub": db_user.username,
            "roles": roles_list,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        return {"access_token": token, "token_type": "bearer"}
    finally:
        session.close()


@app.get("/user_details")
def user_details(payload: dict = Depends(verify_token)):
    return {
        "username": payload.get("sub"),
        "roles": payload.get("roles", []),
        "issued_at": payload.get("iat"),
        "expires_at": payload.get("exp")
    }


@app.post("/movies", status_code=status.HTTP_201_CREATED)
def create_movie(movie: Movie, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        session.add(movie)
        session.commit()
        session.refresh(movie)
        return movie
    finally:
        session.close()


@app.get("/movies/{movie_id}")
def get_movie(movie_id: int, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        movie = session.query(Movie).filter(Movie.id == movie_id).first()
        if movie is None:
            raise HTTPException(status_code=404, detail="Movie not found")
        return movie
    finally:
        session.close()


@app.put("/movies/{movie_id}")
def update_movie(movie_id: int, updated_movie: Movie, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        movie = session.query(Movie).filter(Movie.id == movie_id).first()
        if movie is None:
            raise HTTPException(status_code=404, detail="Movie not found")

        movie.title = updated_movie.title
        movie.description = updated_movie.description
        movie.release_date = updated_movie.release_date
        session.commit()
        session.refresh(movie)
        return movie
    finally:
        session.close()


@app.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_movie(movie_id: int, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        movie = session.query(Movie).filter(Movie.id == movie_id).first()
        if movie is None:
            raise HTTPException(status_code=404, detail="Movie not found")

        session.delete(movie)
        session.commit()
    finally:
        session.close()
    return {"message": "Movie deleted"}


@app.post("/links", status_code=status.HTTP_201_CREATED)
def create_link(link: Link, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        session.add(link)
        session.commit()
        session.refresh(link)
        return link
    finally:
        session.close()


@app.get("/links/{link_id}")
def get_link(link_id: int, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        link = session.query(Link).filter(Link.id == link_id).first()
        if link is None:
            raise HTTPException(status_code=404, detail="Link not found")
        return link
    finally:
        session.close()


@app.put("/links/{link_id}")
def update_link(link_id: int, updated_link: Link, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        link = session.query(Link).filter(Link.id == link_id).first()
        if link is None:
            raise HTTPException(status_code=404, detail="Link not found")

        # Update the link fields
        link.url = updated_link.url
        link.description = updated_link.description
        session.commit()
        session.refresh(link)
        return link
    finally:
        session.close()


@app.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(link_id: int, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        link = session.query(Link).filter(Link.id == link_id).first()
        if link is None:
            raise HTTPException(status_code=404, detail="Link not found")

        session.delete(link)
        session.commit()
    finally:
        session.close()
    return {"message": "Link deleted"}


@app.post("/ratings", status_code=status.HTTP_201_CREATED)
def create_rating(rating: Rating, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        session.add(rating)
        session.commit()
        session.refresh(rating)
        return rating
    finally:
        session.close()


@app.get("/ratings/{rating_id}")
def get_rating(rating_id: int, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        rating = session.query(Rating).filter(Rating.id == rating_id).first()
        if rating is None:
            raise HTTPException(status_code=404, detail="Rating not found")
        return rating
    finally:
        session.close()


@app.put("/ratings/{rating_id}")
def update_rating(rating_id: int, updated_rating: Rating, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        rating = session.query(Rating).filter(Rating.id == rating_id).first()
        if rating is None:
            raise HTTPException(status_code=404, detail="Rating not found")

        rating.score = updated_rating.score
        rating.review = updated_rating.review
        session.commit()
        session.refresh(rating)
        return rating
    finally:
        session.close()


@app.delete("/ratings/{rating_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rating(rating_id: int, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        rating = session.query(Rating).filter(Rating.id == rating_id).first()
        if rating is None:
            raise HTTPException(status_code=404, detail="Rating not found")

        session.delete(rating)
        session.commit()
    finally:
        session.close()
    return {"message": "Rating deleted"}


@app.post("/tags", status_code=status.HTTP_201_CREATED)
def create_tag(tag: Tag, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        session.add(tag)
        session.commit()
        session.refresh(tag)
        return tag
    finally:
        session.close()


@app.get("/tags/{tag_id}")
def get_tag(tag_id: int, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        tag = session.query(Tag).filter(Tag.id == tag_id).first()
        if tag is None:
            raise HTTPException(status_code=404, detail="Tag not found")
        return tag
    finally:
        session.close()


@app.put("/tags/{tag_id}")
def update_tag(tag_id: int, updated_tag: Tag, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        tag = session.query(Tag).filter(Tag.id == tag_id).first()
        if tag is None:
            raise HTTPException(status_code=404, detail="Tag not found")

        # Update the tag fields
        tag.name = updated_tag.name
        session.commit()
        session.refresh(tag)
        return tag
    finally:
        session.close()


@app.delete("/tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, payload: dict = Depends(verify_token)):
    session = SessionLocal()
    try:
        tag = session.query(Tag).filter(Tag.id == tag_id).first()
        if tag is None:
            raise HTTPException(status_code=404, detail="Tag not found")

        session.delete(tag)
        session.commit()
    finally:
        session.close()
    return {"message": "Tag deleted"}
