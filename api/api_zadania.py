import csv

from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def hello_world():
    return {"Hello": "World"}


class Movie:
    def __init__(self, movieId, title, genres):
        self.movieId = movieId
        self.title = title
        self.genres = genres


@app.get('/movies')
def get_movies():
    movies = []
    with open('movies.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            movie = Movie(row['movieId'], row['title'], row['genres'])
            movies.append(movie.__dict__)
    return movies


class Link:
    def __init__(self, movieId, imdbId, tmdbId):
        self.movieId = movieId
        self.imdbId = imdbId
        self.tmdbId = tmdbId


@app.get('/links')
def get_links():
    links = []
    with open('links.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            link = Link(row['movieId'], row['imdbId'], row['tmdbId'])
            links.append(link.__dict__)
    return links


class Rating:
    def __init__(self, userId, movieId, rating, timestamp):
        self.userId = userId
        self.movieId = movieId
        self.rating = rating
        self.timestamp = timestamp


@app.get('/ratings')
def get_ratings():
    ratings = []
    with open('ratings.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            rating = Rating(row['userId'], row['movieId'], row['rating'], row['timestamp'])
            ratings.append(rating.__dict__)
    return ratings


class Tag:
    def __init__(self, userId, movieId, tag, timestamp):
        self.userId = userId
        self.movieId = movieId
        self.tag = tag
        self.timestamp = timestamp


@app.get('/tags')
def get_tags():
    tags = []
    with open('tags.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            tag = Rating(row['userId'], row['movieId'], row['tag'], row['timestamp'])
            tags.append(tag.__dict__)
    return tags
