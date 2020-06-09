import collections

from flask import Flask, render_template, redirect, flash, url_for
from markupsafe import escape
from forms import RegistrationForm, LoginForm
from user import User
import numpy as np
import pandas as pd
import os
import sys
from sklearn.neighbors import NearestNeighbors
from scipy.sparse import csr_matrix
import mysql.connector as conn

app = Flask(__name__)

app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'

connection = conn.connect(user='root', password='', host='127.0.0.1', database='recommender_system')

cursor = connection.cursor()

data_path = os.path.join(sys.path[0], "dataset-csv")
movies_filename = os.path.join(data_path, 'movies.csv')
ratings_filename = os.path.join(data_path, 'ratings.csv')

# Load relevant movies file into dataFrame
film = pd.read_csv(
    movies_filename,
    usecols=['movieId', 'title'],
    dtype={'movieId': 'int32', 'title': 'str'})

# Load relevant ratings file into dataFrame
rating = pd.read_csv(
    ratings_filename,
    usecols=['userId', 'movieId', 'rating'],
    dtype={'userId': 'int32', 'movieId': 'int32', 'rating': 'float32'})

watched = collections.defaultdict(dict)
for i in rating.values.tolist():
    watched[i[0]][i[1]] = i[2]

# Create a pivot table with index as userId, columns as movieId, values as rating
# This is user-item matrix btw
rating_pivot = rating.pivot(index='userId', columns='movieId', \
                            values='rating').fillna(0)

# Convert the pivot table into a sparse matrix
rating_matrix = csr_matrix(rating_pivot.values)

# Initialise k nearest neighbours model
knn = NearestNeighbors(metric='minkowski', algorithm='brute')
knn.fit(rating_matrix)

# Initialise k
k = 25


def generate_default_ratings():
    return film.sample(10).values.tolist()


def generate_vote_movies(user_id):
    # Configure file path
    user_data = rating.loc[rating['userId'] == user_id]
    user_join_rating = pd.merge(user_data, film, on='movieId').drop(['userId'], axis=1)
    rating_list = user_join_rating.values.tolist()
    return rating_list


def knn_predict(user_index, k):
    # Find nearest neighbours
    distances, indices = knn.kneighbors(rating_pivot.iloc[user_index, :].values.reshape(1, -1), n_neighbors=k)
    # Films the user has watched
    user_watched = set(watched[rating_pivot.index[user_index]])

    neighbours_watched = {}

    # Print neighbours and their distance from the user
    for i in range(0, len(distances.flatten())):
        if i == 0:
            print('Closest users to user {}:\n'.format(rating_pivot.index[user_index] - 1))

        else:
            print(
                '{0}: {1} - distance: {2}'.format(i, rating_pivot.index[indices.flatten()[i]], distances.flatten()[i]))

        neighbours_watched[rating_pivot.index[indices.flatten()[i]]] = watched[
            rating_pivot.index[indices.flatten()[i]]].copy()

        # Save information in order to calculate predicted rating
        for key, v in neighbours_watched[rating_pivot.index[indices.flatten()[i]]].items():
            neighbours_watched[rating_pivot.index[indices.flatten()[i]]][key] = [1 - distances.flatten()[i], v]
    print('----\n')

    # Get unwatched movies list
    unwatched_films = []
    for movies in neighbours_watched:
        unwatched_films_list = neighbours_watched[movies].keys() - user_watched.intersection(
            neighbours_watched[movies].keys())
        for unwatched_movies in unwatched_films_list:
            unwatched_films.append(unwatched_movies)

    # Find unwatched films that are common among neighbours
    common_unwatched = [item for item, count in collections.Counter(unwatched_films).items() if count > 1]

    # Predict rating the user would give for the unwatched films
    common_unwatched_rating = []
    for movie in common_unwatched:
        m = []
        w = []
        for neighbours_movie in neighbours_watched:
            if neighbours_watched[neighbours_movie].get(movie) is not None:
                m.append(neighbours_watched[neighbours_movie].get(movie)[0] *
                         neighbours_watched[neighbours_movie].get(movie)[1])
                w.append(neighbours_watched[neighbours_movie].get(movie)[0])

        common_unwatched_rating.append([np.sum(m) / np.sum(w), movie])
    common_unwatched_rating = sorted(common_unwatched_rating, reverse=True)

    print('20 best recommendations based on what similar users liked:\n')
    res = []
    for item in common_unwatched_rating[:20]:
        res.append([item[1], film.loc[film['movieId'] == item[1]]['title'].values[0], item[0]])
    return res


def pull_data():
    query = "SELECT user_id,user_name,password_md5 from user "
    cursor.execute(query)
    dictionary = {}
    for (user_id, user_name, password_md5) in cursor:
        c = User(user_id, user_name, password_md5)
        dictionary[user_name] = c
    return dictionary


def check_valid(username, password):
    dictionary = pull_data()
    if username in dictionary:
        if dictionary[username].password == password:
            return True
    return False


def check_valid_user(username):
    dictionary = pull_data()
    if username in dictionary:
        return False
    return True


def get_user(username):
    dictionary = pull_data()
    return dictionary[username]


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/<current_user>')
def index(current_user):
    if get_user(current_user).user_id <= 9:
        return render_template('index.html', user=get_user(current_user),
                               rates=generate_vote_movies(get_user(current_user).user_id),
                               predictions=knn_predict(get_user(current_user).user_id - 1, k))
    else:
        return render_template('index.html', user=get_user(current_user), predictions=generate_default_ratings())


@app.route('/register', methods=['Get', 'Post'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        if check_valid_user(form.username.data):
            query = ("INSERT INTO user "
                     "(user_name, password_md5) "
                     "VALUES (%s, %s)")
            values = (form.username.data, form.password.data)
            cursor.execute(query, values)
            connection.commit()
            flash("Register Successfully", 'success')
            return redirect('/login')
        else:
            flash("This username has been used, try another name", 'danger')
    return render_template('register.html', form=form)


@app.route('/login', methods=['Get', 'Post'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if check_valid(form.username.data, form.password.data):
            flash("Login Successfully", 'success')
            return redirect(url_for('index', current_user=form.username.data))
        else:
            flash("username or password is incorrect", 'danger')
    return render_template('login.html', form=form)


if __name__ == "__main__":
    app.run(debug=True)
