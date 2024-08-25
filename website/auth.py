from flask import Blueprint, render_template
from flask import Flask, request, redirect, session, url_for, render_template, flash, jsonify
from .models import User, Artist
from . import db
from dotenv import load_dotenv
import os
import json

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler

auth = Blueprint('auth', __name__)

load_dotenv()

client_id = os.getenv('CLIENT_ID')
client_secret = os.getenv('CLIENT_SECRET')

redirect_uri = "http://localhost:5000/callback"
scope = 'playlist-modify-public, user-library-read' ##separate with comma to add more scope

cache_handler = FlaskSessionCacheHandler(session)



#Authentication mananager 
sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    ##Page where user logs in
    show_dialog=True
)

sp = Spotify(auth_manager=sp_oauth)

@auth.route('/', methods = ['GET', 'POST'])
def home():
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        auth_url = sp_oauth.get_authorize_url()
        return render_template('home.html') 
    
    user_id = session.get('user_id')

    # Query User entry
    user = User.query.filter_by(id=user_id).first()

    if user is None:
        print("sdfkljdsfkjdsflkskldfjsdlkjljsdkfljkdfsljkdfs")


    ##Getting user playlists
    playlists = sp.user_playlists(user.spotify_id)
    playlist_list = []
    for playlist in playlists['items']:
        playlist_name = playlist['name']
        playlist_id = playlist['id']
        playlist_list.append({
            'name': playlist_name,
            'id': playlist_id
        })
    
    ##Retrieving track-names from session
    track_names = session.get('track_names')
    if track_names is None:
        track_names = []
   
    if request.method == 'POST':
        action = request.form.get('action')

        ##Retrieving playlist id
        playlist_id = request.form.get('playlist')
        if playlist_id:
            session['playlist_id'] = playlist_id
            flash('Playlist selected', category='success')
        
        ##Retrieving Exclude Liked Songs
        liked_songs = request.form.get('likedSongs')
        if liked_songs == "yes":
            session['liked_songs'] = "yes"
        
        ##Retrieving Remove Duplicates
        remove_duplicates = request.form.get('removeDuplications')
        if remove_duplicates == "yes":
            session['remove_duplicates'] = "yes"


        ##Artists
        if action == 'add_artist':
            artist_query = request.form.get('artistsToRemove', '').lower()
            request.form = request.form.copy()
            request.form['artistToRemove'] = ""
            
            
         
            if artist_query:
                    results = sp.search(q=artist_query, type='artist', limit=1)
                    artists = results['artists']['items']

                    ##Checks if user input is a valid artist
                    exisisting_artist = Artist.query.filter_by(name=artists[0]['name'].lower(), user_id=user.id).first()
                    print(exisisting_artist)
                    if exisisting_artist:
                        flash('Artist has already been added', category='error')
                    else:
                        if artists[0]['name'].lower() == artist_query:
                            artist_name = artists[0]['name'].lower()
                            new_artist = Artist(name=artist_name, user_id=user.id)
                            db.session.add(new_artist)
                            db.session.commit()
                            
                            flash('Artist added', category='success')
                        else:   
                            flash('Artist not found.', category='error')
        
       
    return render_template(
        'index.html', 
        user=user, 
        artists=user.artists,
        playlists=playlist_list,
        track_names=track_names
        )

@auth.route('/search_artist')
def search_artist():
    query = request.args.get('q', '').lower()
    if query:
        results = sp.search(q=query, type='artist', limit=5)  # Adjust limit as needed
        artists = results['artists']['items']
        artist_list = [{'name': artist['name']} for artist in artists]
        return jsonify(artist_list)
    return jsonify([])  # Return an empty list if no query or no results


#Callback from loggin into Spotify for the User, Will redirect towards home page
@auth.route('/callback', methods = ['GET', 'POST'])
def callback():
    token_info = sp_oauth.get_access_token(request.args['code'])
    
    user_info = sp.current_user()
    spotify_id = user_info['id']
    print(spotify_id)


    user = User.query.filter_by(spotify_id=spotify_id).first()

    #Checking if user has already been created
    if not user:
        new_user = User(
        spotify_id=spotify_id,
        access_token=token_info['access_token'],
        refresh_token=token_info['refresh_token']
                    )
        db.session.add(new_user)
        db.session.commit()
        user = new_user
    else:
        user.access_token = token_info['access_token']
        user.refresh_token = token_info['refresh_token']
        db.session.commit()

  
    session['user_id'] = user.id
    return redirect(url_for('auth.home'))


@auth.route('/process_playlist', methods=['POST'])
def process_playlist():
    tracks_to_remove = []
    track_names = []
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()
    
    ##Fetching playlist_id
    playlist_id = session.get('playlist_id')
    if playlist_id is None:
        print('Pick playlist')
        flash('Pick a plalylist', category='error')
        return redirect(url_for('auth.home'))
    ##Fetching Artists
    artist_list = [artist.name for artist in user.artists]
    if artist_list is None:
        print('Pick playlist')
        flash('Choose Artists to removefgbdcdfg', category='error')
        return redirect(url_for('auth.home'))
    
    

    ##Fetching Other Variables
    remove_duplicates = session.get('remove_duplicates')
    exclude_liked = session.get('liked_songs')
    
    offset = 0
    limit = 100
    
    ##Mapping track positions and gathering uri tracks. Needed for removal
    while True:
        results = sp.playlist_items(playlist_id, limit=limit, offset=offset)
        tracks = results['items']

        if not tracks: 
            break
        for index, item in enumerate(tracks):
            track = item['track']
            track_artists = {artist['name'].lower() for artist in track['artists']}

            ##Checking if track is in liked songs
            track_id = track['id']
            is_liked = sp.current_user_saved_tracks_contains([track_id])
            if is_liked[0]:
                break

            
            for artist in track_artists:
                if artist in artist_list:
                    tracks_to_remove.append({
                        'uri': track['uri'],
                        'positions': [index + offset]
                    })
                    track_names.append((
                        track['name'], track['uri'], artist
                    ))
                    
        offset += limit
    
    ##
    session['tracks_to_remove'] = tracks_to_remove
    session['track_names'] = track_names
    

    return redirect(url_for('auth.home'))
    



@auth.route('/delete-artist', methods=['POST'])
def delete_artist():
    user_id = session.get('user_id')
    user = User.query.filter_by(id=user_id).first()

    artist = json.loads(request.data)
    artist_id = artist['artistId']
    artist = Artist.query.get(artist_id)
    if artist:
        if artist.user_id == user.id:
            db.session.delete(artist)
            db.session.commit()
            

    return jsonify({})

@auth.route('/remove-track', methods=['POST'])
def remove_track():
    print("HELLO")
    
    tracks = json.loads(request.data)
    tracks = tracks['tracks']

    tracks_to_remove = session.get('tracks_to_remove')
    track_names = session.get('track_names')
    
    session['tracks_to_remove'] = tracks_to_remove
    

    return jsonify({})


    

@auth.route('/confirm', methods=['POST'])
def confirm():
    
    tracks_to_remove = session.get('tracks_to_remove')
    
    playlist_id = session.get('playlist_id')

    sp.playlist_remove_specific_occurrences_of_items(playlist_id, tracks_to_remove)

    return redirect(url_for('auth.home'))
    


@auth.route('/login', methods = ['GET'])
def login():
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    



@auth.route('/logout')
def logout():
    return render_template('home.html')


## For item in tracks_to_remove
    ## for val in item