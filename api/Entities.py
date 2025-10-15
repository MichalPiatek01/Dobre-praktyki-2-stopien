from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Movie(Base):
    __tablename__ = 'movies'
    movieId = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    genres = Column(String)


class Link(Base):
    __tablename__ = 'links'
    movieId = Column(Integer, primary_key=True)
    imdbId = Column(String)
    tmdbId = Column(String)


class Rating(Base):
    __tablename__ = 'ratings'
    userId = Column(Integer, primary_key=True)
    movieId = Column(Integer, primary_key=True)
    rating = Column(Float)
    timestamp = Column(Integer)


class Tag(Base):
    __tablename__ = 'tags'
    userId = Column(Integer, primary_key=True)
    movieId = Column(Integer, primary_key=True)
    tag = Column(String, primary_key=True)
    timestamp = Column(Integer)
