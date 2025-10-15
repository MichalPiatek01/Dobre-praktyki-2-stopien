import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

engine = create_engine('sqlite:///movies.db')
Base = declarative_base()

Base.metadata.create_all(engine)

print("Schemat bazy danych został utworzony.")

df_movies = pd.read_csv('movies.csv')
df_movies.to_sql('movies', con=engine, if_exists='append', index=False)

df_links = pd.read_csv('links.csv')
df_links.to_sql('links', con=engine, if_exists='append', index=False)

df_ratings = pd.read_csv('ratings.csv')
df_ratings.to_sql('ratings', con=engine, if_exists='append', index=False)

df_tags = pd.read_csv('tags.csv')
df_tags.to_sql('tags', con=engine, if_exists='append', index=False)

print("Dane zostały załadowane do bazy danych.")