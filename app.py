from flask import Flask, render_template
from markupsafe import escape
from flask_sqlalchemy import SQLAlchemy
app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/user/<username>')
def show_user_profile(username):
    return 'User %s' % escape(username)


if __name__ == "__main__":
    app.run(debug=True)
