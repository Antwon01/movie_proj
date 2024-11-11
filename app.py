from flask import Flask, render_template, redirect, url_for, request, flash
from forms import RegistrationForm, LoginForm, RatingForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from data_handler import read_json, write_json
import os

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with your secret key

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User Class
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = str(id)
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        users = read_json('users.json')
        user_data = next((u for u in users if str(u['id']) == str(user_id)), None)
        if user_data:
            return User(user_data['id'], user_data['username'], user_data['password'])
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Routes

# Home Page
@app.route('/')
def index():
    movies = read_json('movies.json')
    ratings = read_json('ratings.json')
    return render_template('index.html', movies=movies, ratings=ratings)

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        users = read_json('users.json')
        if any(u['username'] == form.username.data for u in users):
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(form.password.data, method='sha256')
        new_user = {
            'id': users[-1]['id'] + 1 if users else 1,
            'username': form.username.data,
            'password': hashed_pw
        }
        users.append(new_user)
        write_json('users.json', users)
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        users = read_json('users.json')
        user_data = next((u for u in users if u['username'] == form.username.data), None)
        if user_data and check_password_hash(user_data['password'], form.password.data):
            user = User(user_data['id'], user_data['username'], user_data['password'])
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Movie Details
@app.route('/movie/<int:movie_id>', methods=['GET', 'POST'])
def movie_detail(movie_id):
    movies = read_json('movies.json')
    movie = next((m for m in movies if m['id'] == movie_id), None)
    if not movie:
        flash('Movie not found.', 'danger')
        return redirect(url_for('index'))

    form = RatingForm()
    ratings = read_json('ratings.json')
    movie_ratings = [r for r in ratings if r['movie_id'] == movie_id]
    users = read_json('users.json')

    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_rating = {
                'id': ratings[-1]['id'] + 1 if ratings else 1,
                'stars': form.stars.data,
                'review': form.review.data,
                'user_id': int(current_user.id),
                'movie_id': movie_id
            }
            ratings.append(new_rating)
            write_json('ratings.json', ratings)
            flash('Your rating has been submitted.', 'success')
            return redirect(url_for('movie_detail', movie_id=movie_id))
        else:
            flash('You need to log in to submit a rating.', 'warning')
            return redirect(url_for('login'))

    return render_template('movie.html', movie=movie, form=form, ratings=movie_ratings, users=users)

# User Profile
@app.route('/profile')
@login_required
def profile():
    ratings = read_json('ratings.json')
    user_ratings = [r for r in ratings if r['user_id'] == int(current_user.id)]
    movies = read_json('movies.json')
    for rating in user_ratings:
        movie = next((m for m in movies if m['id'] == rating['movie_id']), None)
        rating['movie'] = movie
    return render_template('profile.html', ratings=user_ratings)

if __name__ == '__main__':
    app.run(debug=True)