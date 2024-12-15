import os
import json
import plotly.express as px
from flask import Flask, request, render_template, redirect, url_for, session, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, ForeignKey, Date, desc
from sqlalchemy.orm import relationship
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/songs'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///music_app_db.sqlite3"
app.config["SECRET_KEY"] = "your_secret_key"
login_manager = LoginManager(app)
db = SQLAlchemy(app)
ALLOWED_EXTENSIONS = {'mp3'}

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    user_type = db.Column(db.String(20), default="user") 
    songs = db.relationship("Song", backref="user", cascade="all, delete-orphan", primaryjoin="User.id == foreign(Song.user_id)")
    playlists = db.relationship("Playlist", backref="user", cascade="all, delete-orphan")
    ratings = db.relationship('Rating', backref='user', lazy=True)
    def get_id(self):
        return str(self.id)
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    @property
    def is_authenticated(self):
        return True
    @property
    def is_anonymous(self):
        return False
    @property
    def is_admin(self):
        return self.user_type == 'admin'
    @staticmethod
    def get_user_count_by_type(user_type):
        return User.query.filter_by(user_type=user_type).count()

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    user = db.relationship('User', backref='admin', uselist=False)

class Song(db.Model):
    __tablename__ = "songs"
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    title = db.Column(db.String(255), nullable=False)
    singer = db.Column(db.String(255))
    artist = db.Column(db.String(255), nullable=False)
    lyrics = db.Column(db.Text)
    album = db.Column(db.String(255))
    release_date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    genre = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    rating = db.Column(db.Float, default=0.0)
    user_rating = db.relationship('Rating', backref='song', lazy=True, cascade='all, delete-orphan')
    playlists_association = db.relationship(
        "Playlist",
        secondary="playlist_song_association",
        back_populates="associated_songs"
    )
    albums_association = db.relationship(
        "Album",
        secondary="album_song_association",
        back_populates="songs"
    )
    def __repr__(self):
        return f"<Song {self.filename}>"
    @staticmethod
    def get_total_tracks_count():
        return db.session.query(db.func.count(Song.id)).scalar()
    @staticmethod
    def get_total_albums_count():
        return Album.query.count()
    @staticmethod
    def get_song_count_by_genre():
        return db.session.query(Song.genre, db.func.count(Song.id)).group_by(Song.genre).all()

class Playlist(db.Model):
    __tablename__ = "playlists"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    songs = db.relationship(
        "Song",
        secondary="playlist_song_association",
        back_populates="playlists_association",
    )
    associated_songs = db.relationship(
        "Song",
        secondary="playlist_song_association",
        back_populates="playlists_association",
    )

playlist_song_association = db.Table(
    'playlist_song_association',
    db.Column('playlist_id', db.Integer, db.ForeignKey('playlists.id')),
    db.Column('song_id', db.Integer, db.ForeignKey('songs.id'))
)

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)

class Album(db.Model):
    __tablename__ = "albums"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    creator = db.relationship("User", backref=db.backref("albums", lazy=True))
    songs = db.relationship(
        "Song",
        secondary="album_song_association",
        back_populates="albums_association",
    )

album_song_association = db.Table(
    'album_song_association',
    db.Column('album_id', db.Integer, db.ForeignKey('albums.id')),
    db.Column('song_id', db.Integer, db.ForeignKey('songs.id'))
)

def create_tables():
    with app.app_context():
        db.create_all()
        admin_username = "admin"
        admin_password = "admin"
        admin_user = User.query.filter_by(username=admin_username, user_type='admin').first()
        if not admin_user:
            admin_user = User(username=admin_username, user_type='admin')
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()

class ChangeAdminPasswordForm(FlaskForm):
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('new_password', message='Passwords must match')])
    submit = SubmitField('Change Password')

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_homepage'))
    return render_template('home.html')

@app.route('/user')
def user_homepage():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if current_user.user_type == 'admin':
        return redirect(url_for('admin_dashboard'))
    recommended_tracks = (
        db.session.query(Song)
        .options(db.joinedload(Song.user_rating))
        .order_by(Song.created_at.desc())
        .limit(3)
        .all()
    )
    recommended_albums = Album.query.order_by(Album.id.desc()).limit(3).all()
    playlists = current_user.playlists
    return render_template('user_homepage.html', recommended_tracks=recommended_tracks, recommended_albums=recommended_albums, playlists=playlists)

@app.route('/creator')
@login_required
def creator_homepage():
    if current_user.user_type != "creator":
        return redirect(url_for('user_homepage'))
    return render_template('creator_homepage.html')

@app.route('/song/<int:song_id>')
def song_details(song_id):
    song = Song.query.get(song_id)
    if song:
        ratings = Rating.query.filter_by(song_id=song.id).all()
        total_ratings = len(ratings)
        average_rating = 0 if total_ratings == 0 else sum(rating.rating for rating in ratings) / total_ratings
        return render_template('song_details.html', song=song, ratings=ratings, average_rating=average_rating)
    else:
        abort(404)

@app.route('/create_playlist', methods=['GET', 'POST'])
@login_required
def create_playlist():
  songs = Song.query.all()
  if request.method == 'POST':
    playlist_name = request.form.get('playlist_name')
    if not playlist_name:
      return render_template('create_playlist.html', error="Playlist name is required.", songs=songs)
    selected_song_ids = request.form.getlist('selected_songs')
    if len(selected_song_ids) == 0:
      return render_template('create_playlist.html', error="Please select at least one song for the playlist.", songs=songs)
    playlist = Playlist(name=playlist_name, user_id=current_user.id)
    for song_id in selected_song_ids:
      song = Song.query.get(song_id)
      playlist.associated_songs.append(song)
    db.session.add(playlist)
    db.session.commit()
    return redirect(url_for('user_homepage'))
  return render_template('create_playlist.html', songs=songs)

@app.route('/show_playlist/<int:playlist_id>')
def show_playlist(playlist_id):
    playlist = Playlist.query.get(playlist_id)
    if not playlist:
        abort(404)
    songs = playlist.songs
    return render_template('show_playlist.html', playlist=playlist, songs=songs)

@app.route('/edit_playlist/<int:playlist_id>', methods=['GET', 'POST'])
@login_required
def edit_playlist(playlist_id):
    playlist = Playlist.query.get(playlist_id)
    if not playlist:
        abort(404)
    if playlist.user_id != current_user.id:
        abort(403)
    if request.method == 'POST':
        new_playlist_name = request.form.get('new_playlist_name')
        if not new_playlist_name:
            return render_template('edit_playlist.html', error="Playlist name is required.")
        playlist.name = new_playlist_name
        db.session.commit()
        return redirect(url_for('show_playlist', playlist_id=playlist.id))
    return render_template('edit_playlist.html', playlist=playlist)

@app.route('/search_results', methods=['GET'])
def search_results():
    query = request.args.get('query', '')
    matching_songs = Song.query.filter(Song.title.ilike(f'%{query}%')).all()
    return render_template('search_results.html', matching_songs=matching_songs)

@app.route('/add_lyrics/<int:song_id>', methods=['GET', 'POST'])
def add_lyrics(song_id):
    if current_user.user_type != "creator":
        return redirect(url_for('index'))
    song = Song.query.get(song_id)
    if request.method == 'POST':
        lyrics = request.form.get('lyrics')
        song.lyrics = lyrics
        db.session.commit()
    return render_template('add_lyrics.html', song=song)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if current_user.user_type != "creator":
        return redirect(url_for('index'))
    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = file.filename
            title, _ = os.path.splitext(os.path.basename(filename))
            if not title:
                flash("Title is required.", 'danger')
                return render_template('upload.html', songs=Song.query.all())
            central_upload_folder = app.config['UPLOAD_FOLDER']
            os.makedirs(central_upload_folder, exist_ok=True)
            file_path = os.path.join(central_upload_folder, filename)
            try:
                file.save(file_path)
                title = request.form.get('title')
                singer = request.form.get('singer')
                release_date = datetime.strptime(request.form.get('release_date'), '%Y-%m-%d').date()
                genre = request.form.get('genre')
                lyrics = request.form.get('lyrics')
                artist = current_user.username
                user_id = current_user.id
                song = Song(filename=filename, title=title, singer=singer, release_date=release_date,
                            genre=genre, artist=artist, user_id=user_id, lyrics=lyrics)
                db.session.add(song)
                db.session.commit()
                flash("Song successfully uploaded!", 'success')
                return redirect(url_for('creator_homepage'))
            except Exception as e:
                flash(f"An error occurred: {str(e)}", 'danger')
    return render_template('upload.html', songs=Song.query.all())

@app.route('/edit_song/<int:song_id>', methods=['GET', 'POST'])
@login_required
def edit_song(song_id):
    if current_user.user_type != "creator":
        return redirect(url_for('index'))
    song = Song.query.get(song_id)
    if not song:
        abort(404)
    if request.method == 'POST':
        song.title = request.form.get('title')
        song.singer = request.form.get('singer')
        song.release_date = datetime.strptime(request.form.get('release_date'), '%Y-%m-%d').date()
        song.genre = request.form.get('genre')
        song.lyrics = request.form.get('lyrics')
        db.session.commit()
        flash("Song details successfully updated!", 'success')
        return redirect(url_for('creator_dashboard'))
    return render_template('edit_song.html', song=song)

@app.route('/delete_song/<int:song_id>', methods=['POST'])
@login_required
def delete_song(song_id):
    if current_user.user_type not in ["admin", "creator"]:
        raise Forbidden()
    if request.method == 'POST':
        confirmation = request.form.get('confirmation')
        if confirmation and confirmation.lower() == 'yes':
            song = Song.query.get(song_id)
            if song:
                if current_user.user_type == "admin" or song.user_id == current_user.id:
                    if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], song.filename)):
                        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], song.filename))
                    db.session.delete(song)
                    db.session.commit()
                    return redirect(url_for('creator_dashboard'))
                else:
                    raise Forbidden("You don't have permission to delete this song.")
            else:
                return "Song not found", 404
    return "Deletion canceled. If you want to delete the song, please confirm.", 200

@app.route('/manage_songs')
@login_required
def manage_songs():
    if current_user.user_type != "creator":
        return redirect(url_for('index'))
    songs = Song.query.filter_by(user_id=current_user.id).all()
    return render_template('manage_songs.html', songs=songs)

@app.route('/play')
def play_all():
    return render_template('play.html', songs=Song.query.all())

@app.route('/add_to_playlist/<int:song_id>', methods=['GET', 'POST'])
@login_required
def add_to_playlist(song_id):
    if current_user.user_type != "normal":
        abort(403)
    song = Song.query.get(song_id)
    if not song:
        abort(404)
    if request.method == 'POST':
        playlist_id = request.form.get('playlist_id')
        if not playlist_id or not playlist_id.isdigit():
            abort(400)
        playlist = Playlist.query.filter_by(id=playlist_id, user_id=current_user.id).first()
        if not playlist:
            flash('Playlist not found or you do not have permission to add to this playlist.', 'error')
            return redirect(url_for('user_homepage'))
        playlist.songs.append(song)
        db.session.commit()
        flash('Song successfully added to the playlist!', 'success')
        return redirect(url_for('show_playlist', playlist_id=playlist.id))
    playlists = current_user.playlists
    return render_template('add_to_playlist.html', song=song, playlists=playlists)

@app.route('/read_lyrics/<int:song_id>')
def read_lyrics(song_id):
    song = Song.query.get(song_id)
    if not song:
        abort(404)
    return render_template('read_lyrics.html', song=song)

@app.route('/edit_lyrics/<int:song_id>', methods=['GET', 'POST'])
@login_required
def edit_lyrics(song_id):
    song = Song.query.get(song_id)
    if song is None or song.user_id != current_user.id:
        flash("Song not found or you don't have permission to edit its lyrics.", 'danger')
        return redirect(url_for('manage_songs'))
    if request.method == 'POST':
        edited_lyrics = request.form.get('edited_lyrics')
        song.lyrics = edited_lyrics
        db.session.commit()
        flash("Lyrics updated successfully!", 'success')
        return redirect(url_for('manage_songs'))
    return render_template('edit_lyrics.html', song=song)

@app.route('/make_album', methods=['GET', 'POST'])
@login_required
def make_album():
    if current_user.user_type != "creator":
        return redirect(url_for('index'))
    if request.method == 'POST':
        album_name = request.form.get('album_name')
        selected_song_ids = request.form.getlist('selected_songs[]')
        if not album_name:
            flash("Album name is required.", 'danger')
            return render_template('make_album.html', songs=Song.query.filter_by(user_id=current_user.id).all())
        if not selected_song_ids:
            flash("Please select at least one song for the album.", 'danger')
            return render_template('make_album.html', songs=Song.query.filter_by(user_id=current_user.id).all())
        album = Album(name=album_name, creator=current_user)
        db.session.add(album)
        for song_id in selected_song_ids:
            song = Song.query.get(song_id)
            if song and song.user_id == current_user.id:
                album.songs.append(song)
        db.session.commit()
        flash("Album successfully created!", 'success')
        return redirect(url_for('creator_homepage'))
    return render_template('make_album.html', songs=Song.query.filter_by(user_id=current_user.id).all())

@app.route('/view_album/<int:album_id>')
def view_album(album_id):
    album = Album.query.get(album_id)
    if album:
        return render_template('view_album.html', album=album)
    else:
        abort(404)

@app.route('/rate/<int:song_id>', methods=['POST'])
def rate_song(song_id):
    rating_value = int(request.form.get('rating'))
    song = Song.query.get(song_id)
    existing_rating = Rating.query.filter_by(user_id=current_user.id, song_id=song.id).first()
    if existing_rating:
        flash('You have already rated this song!', 'info')
    else:
        total_ratings = Rating.query.filter_by(song_id=song.id).count()
        current_rating_sum = Rating.query.filter_by(song_id=song.id).with_entities(db.func.sum(Rating.rating)).scalar() or 0
        new_rating_sum = current_rating_sum + rating_value
        new_average_rating = new_rating_sum / (total_ratings + 1)
        song.rating = new_average_rating
        db.session.add(Rating(user_id=current_user.id, song_id=song.id, rating=rating_value))
        db.session.commit()
        flash('Song successfully rated!', 'success')
    return redirect(url_for('user_homepage'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.user_type == "admin":
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_homepage'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.user_type == 'admin':
                return redirect(url_for('admin_login'))
            login_user(user)
            return redirect(url_for('user_homepage'))
        else:
            return render_template('login.html', error="Incorrect username or password.")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('user_homepage'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        if not username or not password or not user_type:
            return render_template('register.html', error="Username, password, and user type are required.")
        if User.query.filter_by(username=username).first():
            return render_template('register.html', error="Username already taken.")
        user = User(username=username, user_type=user_type)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('user_homepage'))
    return render_template('register.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin_user = User.query.filter_by(username=username, user_type='admin').first()
        if admin_user and admin_user.check_password(password):
            login_user(admin_user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Incorrect admin username or password.", 'danger')
    return render_template('admin_login.html')

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
    total_users_user_type_user = User.get_user_count_by_type('user')
    total_users_user_type_creator = User.get_user_count_by_type('creator')
    total_tracks_uploaded = Song.get_total_tracks_count()
    total_albums_uploaded = Song.get_total_albums_count()
    genre_wise_song_count = Song.get_song_count_by_genre()
    all_songs = Song.query.all()
    if genre_wise_song_count:
        genres, song_counts = zip(*genre_wise_song_count)
    else:
        genres, song_counts = [], []
    chart_data = {
        'labels': genres,
        'data': song_counts,
    }
    genre_chart_html = json.dumps(chart_data)
    return render_template('admin_dashboard.html',
                           total_users_user_type_user=total_users_user_type_user,
                           total_users_user_type_creator=total_users_user_type_creator,
                           total_tracks_uploaded=total_tracks_uploaded,
                           total_albums_uploaded=total_albums_uploaded,
                           genres=genres,
                           song_counts=song_counts,
                           all_songs=all_songs,
                           genre_chart_html=genre_chart_html)

@app.route('/admin_logout')
def admin_logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/change_admin_password', methods=['GET', 'POST'])
@login_required
def change_admin_password():
    form = ChangeAdminPasswordForm()
    if form.validate_on_submit():
        new_password = form.new_password.data
        current_user.set_password(new_password)
        db.session.commit()
        flash('Admin password changed successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('change_admin_password.html', form=form)

@app.route('/become_creator', methods=['GET', 'POST'])
@login_required
def become_creator():
    if current_user.user_type == "creator":
        return redirect(url_for('creator_homepage'))
    if request.method == 'POST':
        current_user.user_type = "creator"
        db.session.commit()
        return redirect(url_for('creator_homepage'))
    return render_template('become_creator.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        if not new_password:
            flash("New password is required.", 'error')
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash("Password updated successfully.", 'success')
    return render_template('profile.html')

@app.route('/creator_dashboard')
@login_required
def creator_dashboard():
  if current_user.user_type != "creator":
    return redirect(url_for('index'))
  creator_songs = Song.query.filter_by(user_id=current_user.id).all()
  total_songs = len(creator_songs)
  total_ratings = 0
  average_rating = 0
  for song in creator_songs:
    ratings = Rating.query.filter_by(song_id=song.id).all()
    total_ratings += len(ratings)
    for rating in ratings:
      average_rating += rating.rating
  if total_ratings > 0:
    average_rating = average_rating / total_ratings
  user_albums = User.query.filter_by(id=current_user.id).first().albums
  total_albums = len(user_albums)
  return render_template('creator_dashboard.html',
                        total_songs=total_songs,
                        average_rating=average_rating,
                        total_albums=total_albums,
                        creator_songs=creator_songs)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin/manage_all_songs')
@login_required
def manage_all_songs():
    if not current_user.is_admin:
        abort(403)
    all_songs = Song.query.all()
    return render_template('manage_all_songs.html', all_songs=all_songs)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
  create_tables()
  app.run(host='0.0.0.0', port=80)