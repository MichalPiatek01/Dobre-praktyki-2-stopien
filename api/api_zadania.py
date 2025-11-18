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
