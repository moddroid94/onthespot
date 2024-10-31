import os
from ..runtimedata import get_logger, account_pool
import requests
from ..otsconfig import config

logger = get_logger("spotify.api")

DEEZER_BASE = "https://api.deezer.com/"

def deezer_login_user(account):
    # I'd prefer to use 'Session.Builder().stored(credentials).create but
    # it seems to be broken, loading from credentials file instead
    uuid = account['uuid']
    username = 'test'
    bitrate = 'test'
    account_type = 'test'

    try:
        account_pool.append({
            "uuid": uuid,
            "username": username,
            "service": "deezer",
            "status": "active",
            "account_type": account_type,
            "bitrate": bitrate,
            "login": {
                "arl": '00',
            }
        })
        return True
    except ConnectionRefusedError:
        account_pool.append({
            "uuid": uuid,
            "username": username,
            "service": "spotify",
            "status": "error",
            "account_type": "N/A",
            "bitrate": "N/A",
            "login": {
                "session": "",
                "session_path": "",
            }
        })
        return False

def deezer_get_token(parsing_index):
    return ''

def deezer_get_search_results(token, search_term, content_types):
    params = {}
    params["q"] = search_term
    params["limit"] = config.get("max_search_results")

    album_url = f"{DEEZER_BASE}/search/album"
    artist_url = f"{DEEZER_BASE}/search/artist"
    playlist_url = f"{DEEZER_BASE}/search/playlist"
    track_url = f"{DEEZER_BASE}/search/track"

    album_search = requests.get(album_url, params=params).json()
    artist_search = requests.get(artist_url, params=params).json()
    playlist_search = requests.get(playlist_url, params=params).json()
    track_search = requests.get(track_url, params=params).json()

    search_results = []
    for album in album_search['data']:
        search_results.append({
            'item_id': album['id'],
            'item_name': album['title'],
            'item_by': album['artist']['name'],
            'item_type': "album",
            'item_service': "deezer",
            'item_url': album['link'],
            'item_thumbnail_url': album["cover"]
        })
    for artist in artist_search['data']:
        search_results.append({
            'item_id': artist['id'],
            'item_name': artist['name'],
            'item_by': artist['name'],
            'item_type': "artist",
            'item_service': "deezer",
            'item_url': artist['link'],
            'item_thumbnail_url': artist["picture"]
        })
    for playlist in playlist_search['data']:
        search_results.append({
            'item_id': playlist['id'],
            'item_name': playlist['title'],
            'item_by': playlist['user']['name'],
            'item_type': "playlist",
            'item_service': "deezer",
            'item_url': playlist['link'],
            'item_thumbnail_url': playlist["picture"]
        })
    for track in track_search['data']:
        search_results.append({
            'item_id': track['id'],
            'item_name': track['title'],
            'item_by': track['artist']['name'],
            'item_type': "track",
            'item_service': "deezer",
            'item_url': track['link'],
            'item_thumbnail_url': track["album"]["cover"]
        })


    logger.info(search_results)
    return search_results
