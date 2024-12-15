Prerequisites

Make sure you have the following installed on your system:
Python (version 3.7 or higher)
pip (Python package installer)
SQLite

Installation:
-Navigate to the project directory
-Create a virtual environment
-Activate the virtual environment
-Install the required dependencies:	pip install -r requirements.txt

Usage:
python app.py
This will create the SQLite database file (music_app_db.sqlite3) and an initial admin user (with username = admin & password = admin).
After running the application, you can access it through a web browser at http://127.0.0.1:5000/ or refer to the console.

Features
-User Authentication:
	Register as a new user or creator.
	Log in with your credentials.
	User types include normal users and creators.
-Song Management:
	Upload songs with details such as title, singer, release date, genre, and lyrics.
	Edit and delete uploaded songs.
	View song details, including ratings.
-Playlist Management:
	Create playlists with selected songs.
	Edit and delete playlists.
	View and play songs in playlists.
-Album Management:
	Create albums with selected songs.
	View and explore albums.
-User Dashboard:
	Different dashboards for normal users and creators.
	Displays song and album statistics for creators.
-Admin Dashboard:
	Accessible only to the admin user.
	Provides an overview of user and music statistics.
	Allows changing the admin password.
-Rating System:
	Users can rate songs, and the average rating is calculated.
-Search Functionality:
	Search for songs based on title.
-Lyrics Management:
	Add and edit lyrics for songs.
-User Profile:
	Change user password.

File Structure:

├── Code
│   └── __pycache__
│   └── instance
│        └── music_app_db.sqlite3
│   └── static
│        └── songs
│             └── '97 Bonnie & Clyde.mp3
│             └── Can't Buy Me Love.mp3
│             └── Fly Me To The Moon.mp3
│             └── Für Elise.mp3
│             └── I'd Rather Go Blind.mp3
│             └── Jolene.mp3
│             └── My Name Is.mp3
│             └── Public Enemy #1.mp3
│             └── Smells Like Teen Spirit.mp3
│             └── So Far Away.mp3
│             └── Stand by Me.mp3
│             └── You Always Sing The Same.mp3
│   └── templates
│             └── add_to_playlist.html
│             └── admin_dashboard.html
│             └── admin_login.html
│             └── base.html
│             └── become_creator.html
│             └── change_admin_password.html
│             └── create_playlist.html
│             └── creator_dashboard.html
│             └── creator_homepage.html
│             └── edit_lyrics.html
│             └── edit_playlist.html
│             └── edit_song.html
│             └── home.html
│             └── login.html
│             └── make_album.html
│             └── manage_all_songs.html
│             └── manage_songs.html
│             └── play.html
│             └── profile.html
│             └── read_lyrics.html
│             └── register.html
│             └── search_results.html
│             └── show_playlist.html
│             └── song_details.html
│             └── upload.html
│             └── user_homepage.html
│             └── view_album.html
├── app.py
├── README.md
├── requirements.txt
