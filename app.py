import json
import os
import csv
import pdfkit
import random
from flask import Flask, render_template, redirect, url_for, request, flash, send_file, make_response, g
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from forms import RegistrationForm, LoginForm, RatingForm
from werkzeug.security import generate_password_hash, check_password_hash
from data_handler import read_json, write_json

app = Flask(__name__)


app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a strong secret key

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to 'login' for @login_required

class User(UserMixin):
    def __init__(self, id, username, password_hash, viewed_movies=None, saved_filters=None, bookmarks=None, watchlist=None):
        self.id = str(id)
        self.username = username
        self.password_hash = password_hash
        self.viewed_movies = viewed_movies or []
        self.saved_filters = saved_filters or {}
        self.bookmarks = bookmarks or []
        self.watchlist = watchlist or []

    @staticmethod
    def get(user_id):
        users = read_json('users.json')
        user_data = next((u for u in users if str(u['id']) == str(user_id)), None)
        if user_data:
            return User(
                id=user_data['id'],
                username=user_data['username'],
                password_hash=user_data['password'],
                viewed_movies=user_data.get('viewed_movies', []),
                saved_filters=user_data.get('saved_filters', {}),
                bookmarks=user_data.get('bookmarks', []),
                watchlist=user_data.get('watchlist', [])
            )
        return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route('/')
def index():
    global movies
    movies = read_json('movies.json')
    ratings = read_json('ratings.json')
    
    # Calculate average ratings for movies
    movie_ratings = {}
    for rating in ratings:
        movie_id = rating['movie_id']
        movie_ratings.setdefault(movie_id, []).append(rating['stars'])
    
    for movie in movies:
        movie['random_id'] = random.randint(0, 200)  # Random URL IMAGE ID between 0 and 200
        ratings_list = movie_ratings.get(movie['id'], [])
        if ratings_list:
            movie['average_rating'] = round(sum(ratings_list) / len(ratings_list), 1)
        else:
            movie['average_rating'] = 'N/A'
    
     # Generate a random ID between 0 and 100
    random_id = random.randint(0, 100)


    # Filter movies based on category section
    in_theatre_movies = [movie for movie in movies if movie['category'] == "In Theatre"]
    popular_movies = [movie for movie in movies if movie['category'] == "Popular"]
    classics_movies = [movie for movie in movies if movie['category'] == "Classic"]
    
    return render_template(
        'index.html', 
        movies=movies,
        in_theatre_movies=in_theatre_movies,
        popular_movies=popular_movies,
        classics_movies=classics_movies,
        random_id=random_id
        )



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
            'password': hashed_pw,
            'viewed_movies': [],
            'saved_filters': {},
            'bookmarks': [],
            'watchlist': []
        }
        users.append(new_user)
        write_json('users.json', users)
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        users = read_json('users.json')
        user_data = next((u for u in users if u['username'] == form.username.data), None)
        if user_data and check_password_hash(user_data['password'], form.password.data):
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                password_hash=user_data['password'],
                viewed_movies=user_data.get('viewed_movies', []),
                saved_filters=user_data.get('saved_filters', {}),
                bookmarks=user_data.get('bookmarks', []),
                watchlist=user_data.get('watchlist', [])
            )
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/discover', methods=['GET', 'POST'])
def discover():
    global movies
    
    genres = sorted(set(genre.strip() for movie in movies for genre in movie.get('genre', '').split(',')))
    countries = sorted(set(movie.get('country', 'Unknown') for movie in movies))
    
    # Get filters from query parameters
    genre_filter = request.args.get('genre')
    country_filter = request.args.get('country')
    year_filter = request.args.get('year')
    
    # Apply filters
    filtered_movies = movies
    if genre_filter:
        filtered_movies = [movie for movie in filtered_movies if genre_filter in movie.get('genre', '').split(', ')]
    if country_filter:
        filtered_movies = [movie for movie in filtered_movies if movie.get('country', 'Unknown') == country_filter]
    if year_filter:
        filtered_movies = [movie for movie in filtered_movies if movie.get('release_date') == year_filter]
    
    # Calculate average ratings
    ratings = read_json('ratings.json')
    movie_ratings = {}
    for rating in ratings:
        m_id = rating['movie_id']
        movie_ratings.setdefault(m_id, []).append(rating['stars'])
    for movie in filtered_movies:
        r = movie_ratings.get(movie['id'], [])
        if r:
            movie['average_rating'] = round(sum(r) / len(r), 1)
        else:
            movie['average_rating'] = 'N/A'
    
    # Handle saving filters
    if request.method == 'GET' and 'save_filters' in request.args and current_user.is_authenticated:
        users = read_json('users.json')
        user = next(u for u in users if u['id'] == int(current_user.id))
        user['saved_filters'] = {
            'genre': genre_filter,
            'country': country_filter,
            'year': year_filter
        }
        write_json('users.json', users)
        flash('Filters saved successfully.', 'success')
    
    # Recommendations based on viewing history
    recommendations = []
    if current_user.is_authenticated:
        users = read_json('users.json')
        user = next(u for u in users if u['id'] == int(current_user.id))
        viewed_movies = user.get('viewed_movies', [])
        # Simple recommendation: find movies with genres matching viewed movies
        viewed_genres = set()
        for vm_id in viewed_movies:
            movie = next((m for m in movies if m['id'] == vm_id), None)
            if movie:
                for genre in movie.get('genre', '').split(', '):
                    viewed_genres.add(genre)
        recommendations = [movie for movie in movies if any(genre in viewed_genres for genre in movie.get('genre', '').split(', ')) and movie['id'] not in viewed_movies]
        # Limit recommendations
        recommendations = recommendations[:10]
        # Calculate average ratings for recommendations
        for movie in recommendations:
            r = movie_ratings.get(movie['id'], [])
            if r:
                movie['average_rating'] = round(sum(r) / len(r), 1)
            else:
                movie['average_rating'] = 'N/A'
    
    return render_template('discover.html', movies=filtered_movies, genres=genres, countries=countries, recommendations=recommendations)


@app.route('/advanced_search', methods=['GET', 'POST'])
def advanced_search():
    global movies

    # Get Search Parameters
    title = request.args.get('title', '').lower()
    director = request.args.get('director', '').lower()
    genre = request.args.get('genre', '').lower()
    country = request.args.get('country', '').lower()
    year = request.args.get('year', '').lower()
    
    # Apply filters
    filtered_movies = movies
    if title:
        filtered_movies = [movie for movie in filtered_movies if title in movie['title'].lower()]
    if director:
        filtered_movies = [movie for movie in filtered_movies if director in movie.get('director', '').lower()]
    if genre:
        filtered_movies = [movie for movie in filtered_movies if genre in [g.lower() for g in movie.get('genre', '').split(', ')]]
    if country:
        filtered_movies = [movie for movie in filtered_movies if country == movie.get('country', '').lower()]
    if year:
        filtered_movies = [movie for movie in filtered_movies if year == movie.get('release_date', '').lower()]
    
    # Calculate average ratings
    ratings = read_json('ratings.json')
    movie_ratings = {}
    for rating in ratings:
        m_id = rating['movie_id']
        movie_ratings.setdefault(m_id, []).append(rating['stars'])
    for movie in filtered_movies:
        r = movie_ratings.get(movie['id'], [])
        if r:
            movie['average_rating'] = round(sum(r) / len(r), 1)
        else:
            movie['average_rating'] = 'N/A'
    
    # Export functionality
    if 'export' in request.args:
        export_format = request.args.get('export')
        if export_format == 'csv':
            return export_to_csv(filtered_movies)
        elif export_format == 'pdf':
            return export_to_pdf(filtered_movies)
    
    return render_template('advanced_search.html', movies=filtered_movies, result_num=len(filtered_movies))


def export_to_csv(movies):
    fieldnames = ['id', 'title', 'genre', 'director', 'release_date', 'country']
    output = []
    for movie in movies:
        output.append({field: movie.get(field, '') for field in fieldnames})
    
    csv_path = 'export.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output)
    
    return send_file(csv_path, as_attachment=True)


def export_to_pdf(movies):
    rendered = render_template('export_template.html', movies=movies)
    try:
        pdf = pdfkit.from_string(rendered, False)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'attachment; filename=export.pdf'
        return response
    except Exception as e:
        flash('Failed to generate PDF. Ensure wkhtmltopdf is installed.', 'danger')
        return redirect(request.referrer or url_for('advanced_search'))


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('query', '').lower()
    global movies
    if query:
        filtered_movies = [movie for movie in movies if query in movie['title'].lower() or query in [g.lower() for g in movie.get('genre', '').split(', ')]]
    else:
        filtered_movies = movies
    
    # Calculate average ratings
    ratings = read_json('ratings.json')
    movie_ratings = {}
    for rating in ratings:
        m_id = rating['movie_id']
        movie_ratings.setdefault(m_id, []).append(rating['stars'])
    for movie in filtered_movies:
        r = movie_ratings.get(movie['id'], [])
        if r:
            movie['average_rating'] = round(sum(r) / len(r), 1)
        else:
            movie['average_rating'] = 'N/A'
    
    return render_template('search_result.html', movies=filtered_movies, result_num=len(filtered_movies))


@app.route('/movie/<int:movie_id>', methods=['GET', 'POST'])
def movie_detail(movie_id):
    global movies
    movie = next((m for m in movies if m['id'] == movie_id), None)
    if not movie:
        flash('Movie not found.', 'danger')
        return redirect(url_for('index'))
    
    form = RatingForm()
    ratings = read_json('ratings.json')
    movie_ratings = [r for r in ratings if r['movie_id'] == movie_id]
    users = read_json('users.json')
    
    # Calculate average rating
    if movie_ratings:
        avg_rating = round(sum(r['stars'] for r in movie_ratings) / len(movie_ratings), 1)
    else:
        avg_rating = 'N/A'
    
    # Handle rating submission
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_rating = {
                'id': ratings[-1]['id'] + 1 if ratings else 1,
                'stars': form.stars.data,
                'review': form.review.data,
                'user_id': int(current_user.id),
                'movie_id': movie_id,
                'likes': 0,
                'dislikes': 0,
                'comments': []
            }
            ratings.append(new_rating)
            write_json('ratings.json', ratings)
            flash('Your rating has been submitted.', 'success')
            return redirect(url_for('movie_detail', movie_id=movie_id))
        else:
            flash('You need to log in to submit a rating.', 'warning')
            return redirect(url_for('login'))
    
    # Track viewing history
    if current_user.is_authenticated:
        users = read_json('users.json')
        user = next(u for u in users if u['id'] == int(current_user.id))
        if movie_id not in user.get('viewed_movies', []):
            user['viewed_movies'].append(movie_id)
            write_json('users.json', users)
    
    referrer = request.referrer  # Get the previous URL
    
    return render_template('movie.html', movie=movie, form=form, ratings=movie_ratings, users=users, average_rating=avg_rating,  referrer=referrer)


@app.route('/like_review/<int:review_id>', methods=['POST'])
@login_required
def like_review(review_id):
    ratings = read_json('ratings.json')
    rating = next((r for r in ratings if r['id'] == review_id), None)
    if rating:
        rating['likes'] = rating.get('likes', 0) + 1
        write_json('ratings.json', ratings)
    return redirect(request.referrer or url_for('index'))


@app.route('/dislike_review/<int:review_id>', methods=['POST'])
@login_required
def dislike_review(review_id):
    ratings = read_json('ratings.json')
    rating = next((r for r in ratings if r['id'] == review_id), None)
    if rating:
        rating['dislikes'] = rating.get('dislikes', 0) + 1
        write_json('ratings.json', ratings)
    return redirect(request.referrer or url_for('index'))

@app.route('/add_comment/<int:review_id>', methods=['POST'])
@login_required
def add_comment(review_id):
    comment_text = request.form.get('comment')
    if not comment_text:
        flash('Comment cannot be empty.', 'warning')
        return redirect(request.referrer or url_for('index'))
    
    ratings = read_json('ratings.json')
    rating = next((r for r in ratings if r['id'] == review_id), None)
    if rating:
        comment = {
            'user': current_user.username,
            'text': comment_text
        }
        if 'comments' not in rating:
            rating['comments'] = []
        rating['comments'].append(comment)
        write_json('ratings.json', ratings)
        flash('Comment added.', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route('/bookmark_movie/<int:movie_id>', methods=['POST'])
@login_required
def bookmark_movie(movie_id):
    users = read_json('users.json')
    user = next(u for u in users if u['id'] == int(current_user.id))
    bookmarks = user.get('bookmarks', [])
    if movie_id not in bookmarks:
        bookmarks.append(movie_id)
        user['bookmarks'] = bookmarks
        write_json('users.json', users)
        flash('Movie bookmarked.', 'success')
    else:
        flash('Movie already bookmarked.', 'info')
    return redirect(request.referrer or url_for('index'))


@app.route('/add_to_watchlist/<int:movie_id>', methods=['POST'])
@login_required
def add_to_watchlist(movie_id):
    users = read_json('users.json')
    user = next(u for u in users if u['id'] == int(current_user.id))
    watchlist = user.get('watchlist', [])
    if movie_id not in watchlist:
        watchlist.append(movie_id)
        user['watchlist'] = watchlist
        write_json('users.json', users)
        flash('Movie added to watchlist.', 'success')
    else:
        flash('Movie already in watchlist.', 'info')
    return redirect(request.referrer or url_for('index'))


@app.route('/profile')
@login_required
def profile():
    users = read_json('users.json')
    user = next(u for u in users if u['id'] == int(current_user.id))
    
    ratings = read_json('ratings.json')
    user_ratings = [r for r in ratings if r['user_id'] == int(current_user.id)]
    
    movies = read_json('movies.json')
    for rating in user_ratings:
        movie = next((m for m in movies if m['id'] == rating['movie_id']), None)
        rating['movie'] = movie
    
    return render_template('profile.html', ratings=user_ratings)


@app.route('/export_template')
def export_template():
    # This route is used internally for PDF export
    movies = read_json('movies.json')
    return render_template('export_template.html', movies=movies)


if __name__ == '__main__':
    # Ensure data directory exists
    if not os.path.exists('data'):
        os.makedirs('data')
        # Initialize JSON files
        write_json('movies.json', [])
        write_json('users.json', [])
        write_json('ratings.json', [])
    
    app.run(debug=True)