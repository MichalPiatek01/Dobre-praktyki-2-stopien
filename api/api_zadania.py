from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from Entities import Movie, Link, Rating, Tag

app = FastAPI()
engine = create_engine('sqlite:///movies.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@app.get("/")
def hello_world():
    return {"Hello": "World"}


@app.get('/movies')
def get_movies():
    session = SessionLocal()
    try:
        movies = session.query(Movie).all()
        return [m.__dict__ for m in movies]
    finally:
        session.close()


@app.get('/links')
def get_links():
    session = SessionLocal()
    try:
        links = session.query(Link).all()
        return [l.__dict__ for l in links]
    finally:
        session.close()


@app.get('/ratings')
def get_ratings():
    session = SessionLocal()
    try:
        ratings = session.query(Rating).all()
        return [r.__dict__ for r in ratings]
    finally:
        session.close()


@app.get('/tags')
def get_tags():
    session = SessionLocal()
    try:
        tags = session.query(Tag).all()
        return [t.__dict__ for t in tags]
    finally:
        session.close()
