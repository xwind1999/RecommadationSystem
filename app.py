from flask import Flask, render_template, redirect, flash, url_for
from markupsafe import escape
from forms import RegistrationForm, LoginForm

import mysql.connector as conn

app = Flask(__name__)

app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'

connection = conn.connect(user='root', password='', host='127.0.0.1', database='recommender_system')

cursor = connection.cursor()


def pull_data():
    query = "SELECT user_name,password_md5 from user "

    cursor.execute(query)
    dictionary = {}
    for (user_name, password_md5) in cursor:
        dictionary[user_name] = password_md5

    return dictionary


def check_valid(username, password):
    dictionary = pull_data()
    if username in dictionary:
        if dictionary[username] == password:
            return True
    return False


def check_valid_user(username):
    dictionary = pull_data()
    if username in dictionary:
        return False
    return True


@app.route('/<current_user>')
def index(current_user):
    return render_template('index.html',user = current_user)


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
            return redirect(url_for('index', current_user=str(form.username.data)))
        else:
            flash("username or password is incorrect", 'danger')
    return render_template('login.html', form=form)


if __name__ == "__main__":
    app.run(debug=True)
