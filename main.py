# /server.py

from models import get_notes, get_note, create_note_sql, edit_note_sql, delete_note_sql, check_note_exists

from functools import wraps
import json
from os import environ as env
from werkzeug.exceptions import HTTPException

from dotenv import load_dotenv, find_dotenv
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import session
from flask import url_for
from flask import request
from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode

from functools import wraps

app = Flask(__name__)

app.secret_key = 'dsogrein324r3foin'

oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id='06F6PVKlsBK5xXyHHc6QiBnDYPox7ctx',
    client_secret='aaiBeWRLV5y3laeFlzBrDraJiNdJfyi4p3kXELOqdauyz-GmurLiHm1qWt48__M6',
    api_base_url='https://dev-w24y1oq2.us.auth0.com',
    access_token_url='https://dev-w24y1oq2.us.auth0.com/oauth/token',
    authorize_url='https://dev-w24y1oq2.us.auth0.com/authorize',
    client_kwargs={
        'scope': 'openid profile email',
    },
)

# Here we're using the /callback route.
@app.route('/callback')
def callback_handling():
    # Handles response from token endpoint
    auth0.authorize_access_token()
    resp = auth0.get('userinfo')
    userinfo = resp.json()

    # Store the user information in flask session.
    session['jwt_payload'] = userinfo
    session['profile'] = {
        'user_id': userinfo['sub'],
        'name': userinfo['name'],
        'picture': userinfo['picture']
    }
    return redirect('/home')

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'profile' not in session:
            # Redirect to Login page here
            return redirect('/')
        return f(*args, **kwargs)

    return decorated


@app.route("/")
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri='https://private-notes-326216.uk.r.appspot.com/callback')


@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to logout endpoint
    return redirect(auth0.api_base_url + '/v2/logout?returnTo=https%3A%2F%2Fprivate-notes-326216.uk.r.appspot.com/&client_id=06F6PVKlsBK5xXyHHc6QiBnDYPox7ctx')


@app.route("/home")
@requires_auth
def home():
    try:
        user_notes = get_notes(session['profile']['user_id'])
    except:
        return render_template('error.html', error_message="Sorry, there was an error loading your notes. Please try again later.")
    links = ['display_note?id=' + str(note[0]) for note in user_notes]

    notes_exist = False
    if len(user_notes) > 0:
        notes_exist = True
    return render_template('home.html', userinfo=session['profile'], notes=user_notes, links=links, notes_exist=notes_exist, indent=4)


@app.route("/createNote")
@requires_auth
def create_note():
    return render_template('create_note.html')


@app.route("/createNoteAction", methods=["GET", "POST"])
@requires_auth
def create_note_action():
    if request.method == 'POST':
        try:
            title = request.form["title"]
            entry = request.form["entry"]
            if len(title) == 0 or len(entry) == 0:
                return render_template('error.html', error_message='Your note title and note entry must both have text.')
            if check_note_exists(title, session['profile']['user_id']):
                return render_template('error.html', error_message='You already have a note with that title')

            create_note_sql(session['profile']['user_id'], title, entry)
        except:
            return render_template('error.html', error_message='Sorry, note could not be created. Try again later.')

    return redirect('/home')


@app.route("/editNoteAction", methods=["GET", "POST"])
@requires_auth
def edit_note_action():
    if request.method == 'POST':
        try:
            title = request.form["title"]
            entry = request.form["entry"]
            note_id = request.args.get("id")

            success = edit_note_sql(title, entry, note_id)
            if not success:
                raise Exception('Could not edit note')
        except:
            return render_template('error.html', error_message='Sorry, note could not be edited. Try again later.')

        return redirect('/display_note?id=' + note_id)

    return redirect('/home')

@app.route("/deleteNoteAction")
@requires_auth
def delete_note_action():
    try:
        note_id = request.args.get('id')
        success = delete_note_sql(note_id)
        if not success:
            raise Exception('Could not delete note')
    except:
        return render_template('error.html', error_message='Sorry, note could not be deleted. Try again later.')

    return redirect('/home')


@app.route("/display_note")
@requires_auth
def display_note():
    try:
        note_id = request.args.get("id")

        note = get_note(note_id)

        note_title = note[0][2]
        note_entry = note[0][3]

        # confirm that the note being requested is for this user
        if session['profile']['user_id'] != note[0][1]:
            return redirect('/note_not_authorized')

        edit_link = '/edit_note?id=' + note_id
        delete_link = '/deleteNoteAction?id=' + note_id
    except:
        return render_template('error.html', error_message='Sorry, could not display this note. Try again later.')
    
    return render_template('display_note.html', note_title=note_title, note_entry=note_entry, edit_link=edit_link, delete_link=delete_link)


@app.route("/edit_note")
@requires_auth
def edit_note():
    note_id = request.args.get("id")
    try:
        note = get_note(note_id)

        note_title = note[0][2]
        note_entry = note[0][3]
    except:
        return render_template('error.html', error_message='Sorry, could not load this note. Try again later.')

    action_link = 'editNoteAction?id=' + note_id

    return render_template('edit_note.html', note_title=note_title, note_entry=note_entry, note_id=note_id, action_link=action_link)

@app.route("/profile")
@requires_auth
def profile():
    return render_template('your_profile.html', userinfo=session["profile"])

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/note_not_authorized")
def note_not_authorized():
    return render_template('note_not_authorized.html')