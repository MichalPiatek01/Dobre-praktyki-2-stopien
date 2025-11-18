import bcrypt
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from Entities import Base, User

engine = create_engine('sqlite:///movies.db')

Base.metadata.create_all(bind=engine)

print("Schemat bazy danych został utworzony.")

df_movies = pd.read_csv('movies.csv')
df_movies.to_sql('movies', con=engine, if_exists='append', index=False)

df_links = pd.read_csv('links.csv')
df_links.to_sql('links', con=engine, if_exists='append', index=False)

df_ratings = pd.read_csv('ratings.csv')
df_ratings.to_sql('ratings', con=engine, if_exists='append', index=False)

df_tags = pd.read_csv('tags.csv')
df_tags.to_sql('tags', con=engine, if_exists='append', index=False)

SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

admin_username = "admin"
admin_password = "123"
roles = "ROLE_ADMIN"

hashed = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

existing = session.query(User).filter(User.username == admin_username).first()

if not existing:
    admin_user = User(username=admin_username, hashed_password=hashed, roles=roles)
    session.add(admin_user)
    session.commit()
    print("Admin user created successfully.")
else:
    print("Admin already exists – skipped.")

session.close()

print("Dane zostały załadowane do bazy danych.")
