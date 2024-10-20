import os
import re
import time
import uuid
import json
from hashlib import md5
import requests
import requests.adapters
from librespot.audio.decoders import AudioQuality
from librespot.core import Session
from librespot.zeroconf import ZeroconfServer
from mutagen import File
from mutagen.easyid3 import EasyID3, ID3
from mutagen.flac import Picture, FLAC
from mutagen.id3 import APIC, TXXX, USLT, WOAS
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from ..otsconfig import config, cache_dir
from ..post_download import conv_list_format
from ..runtimedata import get_logger, account_pool
from ..post_download import set_audio_tags
from ..utils import sanitize_data
from ..otsconfig import cache_dir, config
from ..runtimedata import get_logger


logger = get_logger("spotify.api")
requests.adapters.DEFAULT_RETRIES = 10



def spotify_new_session():
    try:
        os.mkdir(os.path.join(cache_dir(), 'onthespot', 'sessions'))
    except FileExistsError:
        logger.info("The session directory already exists.")

    uuid_uniq = str(uuid.uuid4())
    session_json_path = os.path.join(os.path.join(cache_dir(), 'onthespot', 'sessions'),
                 f"ots_login_{uuid_uniq}.json")

    CLIENT_ID: str = "65b708073fc0480ea92a077233ca87bd"
    ZeroconfServer._ZeroconfServer__default_get_info_fields['clientID'] = CLIENT_ID
    zs_builder = ZeroconfServer.Builder()
    zs_builder.device_name = 'OnTheSpot'
    zs_builder.conf.stored_credentials_file = session_json_path
    zs = zs_builder.create()
    logger.info("Zeroconf login service started")

    while True:
        time.sleep(1)
        if zs.has_valid_session():
            logger.info(f"Grabbed {zs._ZeroconfServer__session} for {zs._ZeroconfServer__session.username()}")
            if zs._ZeroconfServer__session.username() in config.get('accounts'):
                logger.info("Account already exists")
                return False
            else:
                # I wish there was a way to get credentials without saving to
                # a file and parsing it as so
                try:  
                    with open(session_json_path, 'r') as file:  
                        zeroconf_login = json.load(file)  
                except FileNotFoundError:  
                    print(f"Error: The file {session_json_path} was not found.")  
                except json.JSONDecodeError:  
                    print("Error: Failed to decode JSON from the file.")  
                except Exception as e:  
                    print(f"An error occurred: {e}")
                cfg_copy = config.get('accounts').copy()
                new_user = {
                    "uuid": uuid_uniq,
                    "service": "spotify",
                    "active": True,
                    "login": {
                        "username": zeroconf_login["username"],
                        "credentials": zeroconf_login["credentials"],
                        "type": zeroconf_login["type"],
                    }
                }
                zs.close()
                cfg_copy.append(new_user)
                config.set_('accounts', cfg_copy)
                config.update()
                logger.info("New account added to config.")
                return True



def spotify_login_user(account):
    # I'd prefer to use 'Session.Builder().stored(credentials).create but
    # it seems to be broken, loading from credentials file instead
    uuid = account['uuid']
    username = account['login']['username']

    session_dir = os.path.join(cache_dir(), "onthespot", "sessions")
    os.makedirs(session_dir, exist_ok=True)
    session_json_path = os.path.join(session_dir, f"ots_login_{uuid}.json")

    try:
        with open(session_json_path, 'w') as file:
            json.dump(account['login'], file)
        print(f"Login information for '{username}' written to {session_json_path}")
    except IOError as e:
        print(f"Error writing to file {session_json_path}: {e}")

    try:
        config = Session.Configuration.Builder().set_stored_credential_file(session_json_path).build()
        # For some reason initialising session as None prevents premature application exit
        session = None
        session = Session.Builder().stored_file(session_json_path).create()
        logger.debug("Session created") 
        logger.info(f"Login successful for user '{username[:4]}*******'")
        account_type = session.get_user_attribute("type")
        bitrate = "160k"
        if account_type == "premium":
            bitrate = "320k"
        account_pool.append({
            "uuid": uuid,
            "username": username,
            "service": "spotify",
            "status": "active",
            "account_type": account_type,
            "bitrate": bitrate,
            "login": {
                "session": session,
                "session_path": session_json_path,
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


def spotify_get_token(parsing_index):
    return account_pool[parsing_index]['login']['session']

def spotify_format_track_path(item_metadata, is_playlist_item, playlist_name, playlist_by):
    if config.get("translate_file_path"):
        def translate(string):
            return requests.get(f"https://translate.googleapis.com/translate_a/single?dj=1&dt=t&dt=sp&dt=ld&dt=bd&client=dict-chrome-ex&sl=auto&tl={config.get('language')}&q={string}").json()["sentences"][0]["trans"]
        _name = translate(item_metadata['title'])
        _album = translate(item_metadata['album_name'])
    else:
        _name = item_metadata['title']
        _album=item_metadata['album_name']

    _artist = item_metadata['artists'][0]    

    if is_playlist_item is True and config.get("use_playlist_path"):
        path = config.get("playlist_path_formatter")
    else:
        path = config.get("track_path_formatter")
    item_path = path.format(
        artist = sanitize_data(_artist),
        album = sanitize_data(_album),
        name = sanitize_data(_name),
        rel_year = sanitize_data(item_metadata['release_year']),
        disc_number = item_metadata['disc_number'],
        track_number = item_metadata['track_number'],
        genre = sanitize_data(item_metadata['genre'][0] if len(item_metadata['genre']) > 0 else ''),
        label = sanitize_data(item_metadata['label']),
        explicit = sanitize_data(str(config.get('explicit')) if item_metadata['explicit'] else ''),
        trackcount = item_metadata['total_tracks'],
        disccount = item_metadata['total_discs'],
        playlist_name = sanitize_data(playlist_name),
        playlist_owner = sanitize_data(playlist_by),
    )
    if not config.get("force_raw"):
        item_path = item_path + "." + config.get("media_format")
    else:
        item_path = item_path + ".ogg"
    return item_path

def spotify_format_episode_path(item_metadata, is_playlist_item, playlist_name, playlist_by):
    if config.get("translate_file_path"):
        def translate(string):
            return requests.get(f"https://translate.googleapis.com/translate_a/single?dj=1&dt=t&dt=sp&dt=ld&dt=bd&client=dict-chrome-ex&sl=auto&tl={config.get('language')}&q={string}").json()["sentences"][0]["trans"]
        _name = translate(item_metadata['title'])
        _album = translate(item_metadata['album_name'])
    else:
        _name = item_metadata['title']
        _album=item_metadata['album_name']

    _artist = item_metadata['artists'][0]    

    if is_playlist_item is True and config.get("use_playlist_path"):
        path = config.get("playlist_path_formatter")
    else:
        path = config.get("podcast_path_formatter")
    item_path = path.format(
        artist = sanitize_data(_artist),
        podcast_name = sanitize_data(_album),
        episode_name = sanitize_data(_name),
        release_date = sanitize_data(item_metadata['release_year']),
        explicit = sanitize_data(str(config.get('explicit')) if item_metadata['explicit'] else ''),
        total_episodes = item_metadata['total_tracks'],
        language = item_metadata['language'],
        playlist_name = sanitize_data(playlist_name),
        playlist_owner = sanitize_data(playlist_by),
    )
    if not config.get("force_raw"):
        item_path = item_path + "." + config.get("media_format")
    else:
        item_path = item_path + ".ogg"
    return item_path


def play_media(session, media_id, media_type):
    session = account_pool['login']['session']
    access_token = session.tokens().get("user-modify-playback-state")
    url = 'https://api.spotify.com/v1/me/player/play'

    payload = {
        "context_uri": f"spotify:{media_type}:{media_id}",
        "offset": {
            "position": 5
        },
        "position_ms": 0
    }
    headers = {
    'Authorization': f'Bearer {access_token}'
    }

    resp = requests.put(url, headers=headers)
    logger.info(f"Playing item: {resp}")

def queue_media(session, media_id, media_type):
    access_token = session.tokens().get("user-modify-playback-state")
    url = f'https://api.spotify.com/v1/me/player/queue?uri=spotify%3A{media_type}%3A{media_id}'
    headers = {
    'Authorization': f'Bearer {access_token}'
    }
    resp = requests.post(url, headers=headers)
    logger.info(f"Item Queued: {resp}")

def check_if_media_in_library(session, media_id, media_type):
    access_token = session.tokens().get("user-library-read")
    url = f'https://api.spotify.com/v1/me/{media_type}s/contains?ids={media_id}'
    headers = {
    'Authorization': f'Bearer {access_token}'
    }
    resp = requests.get(url, headers=headers)
    logger.info(f"Checking if item is in library: {resp}")
    if resp.json() == [True]:
        return True
    else:
        return False

def save_media_to_library(session, media_id, media_type):
    access_token = session.tokens().get("user-library-modify")
    url = f'https://api.spotify.com/v1/me/{media_type}s?ids={media_id}'
    headers = {
    'Authorization': f'Bearer {access_token}'
    }
    resp = requests.put(url, headers=headers)
    logger.info(f"Item saved to library: {resp}")

def remove_media_from_library(session, media_id, media_type):
    if media_type == 'track' or media_type == 'episode':
        access_token = session.tokens().get("user-library-modify")
        url = f'https://api.spotify.com/v1/me/{media_type}s?ids={media_id}'
        headers = {
        'Authorization': f'Bearer {access_token}'
        }
        resp = requests.delete(url, headers=headers)
        logger.info(f"Item removed from library: {resp}")

def get_currently_playing_url(session):
    url = "https://api.spotify.com/v1/me/player/currently-playing"
    access_token = session.tokens().get("user-read-currently-playing")
    resp = requests.get(url, headers={"Authorization": "Bearer %s" % access_token})
    if resp.status_code == 200:
        return resp.json()['item']['external_urls']['spotify']
    else:
        return ""

def spotify_get_artist_albums(session, artist_id):
    logger.info(f"Get albums for artist by id '{artist_id}'")
    access_token = session.tokens().get("user-read-email")
    resp = make_call(f'https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=album%2Csingle&limit=50', token=access_token) #%2Cappears_on%2Ccompilation
    return [resp['items'][i]['external_urls']['spotify'] for i in range(len(resp['items']))]


def spotify_get_playlist_data(session, playlist_id):
    logger.info(f"Get playlist dump for '{playlist_id}'")
    access_token = session.tokens().get("user-read-email")
    resp = make_call(f'https://api.spotify.com/v1/playlists/{playlist_id}', token=access_token, skip_cache=True)
    return resp['name'], resp['owner']['display_name']


def spotify_get_lyrics(session, item_id, item_type, metadata, filepath):
                       

    if config.get('inp_enable_lyrics'):
        lyrics = []
        try:
            if item_type == "track":
                url = f'https://spclient.wg.spotify.com/color-lyrics/v2/track/{item_id}'
            elif item_type == "episode":
                url = f"https://spclient.wg.spotify.com/transcript-read-along/v2/episode/{item_id}"

            token = session.tokens().get("user-read-email")
            params = 'format=json&market=from_token'

            headers = {
            'app-platform': 'WebPlayer',
            'Authorization': f'Bearer {token}',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
            }

            resp = make_call(url, token, headers=headers, params=params)
            if resp == None:
                logger.info(f"Failed to find lyrics for {item_type}: {item_id}")
                return None

            if config.get("embed_branding"):
                lyrics.append('[re:OnTheSpot]')

            for key in metadata.keys():
                value = metadata[key]

                if key in ['title', 'track_title', 'tracktitle'] and config.get("embed_name"):
                    title = value
                    lyrics.append(f'[ti:{title}]')

                elif key == 'artists' and config.get("embed_artist"):
                    artist = conv_list_format(value)
                    lyrics.append(f'[ar:{artist}]')

                elif key in ['album_name', 'album'] and config.get("embed_album"):
                    album = value
                    lyrics.append(f'[al:{album}]')

                elif key in ['writers'] and config.get("embed_writers"):
                    author = conv_list_format(value)
                    lyrics.append(f'[au:{author}]')

            if item_type == "track":
                lyrics.append(f'[by:{resp["lyrics"]["provider"]}]')

            if config.get("embed_length"):
                l_ms = metadata['length']
                if round((l_ms/1000)/60) < 10:
                    digit="0"
                else:
                    digit=""
                lyrics.append(f'[length:{digit}{round((l_ms/1000)/60)}:{round((l_ms/1000)%60)}]\n')

            if item_type == "track":
                if resp["lyrics"]["syncType"] == "LINE_SYNCED":
                    for line in resp["lyrics"]["lines"]:
                        minutes, seconds = divmod(int(line['startTimeMs']) / 1000, 60)
                        lyrics.append(f'[{minutes:0>2.0f}:{seconds:05.2f}] {line["words"]}')
                else:
                    # It's un synced lyrics, if not forcing synced lyrics return it
                    if not config.get("only_synced_lyrics"):
                        lyrics = [line['words'][0]['string'] for line in resp['lines']]

            elif item_type == "episode":
                if resp["timeSyncedStatus"] == "SYLLABLE_SYNCED":
                    for line in resp["section"]:
                        try:
                            minutes, seconds = divmod(int(line['startMs']) / 1000, 60)
                            lyrics.append(f'[{minutes:0>2.0f}:{seconds:05.2f}] {line["text"]["sentence"]["text"]}')
                        except KeyError as e:
                            logger.debug("Invalid line, likely title, skipping..")

                else:
                    logger.info("Unsynced episode lyrics, please open a bug report.")

        except (KeyError, IndexError):
            logger.error(f'KeyError/Index Error. Failed to get lyrics for track id: {item_id}, ')

        merged_lyrics = '\n'.join(lyrics)

        if lyrics:
            logger.info(lyrics)
            if len(lyrics) <= 2:
                return False
            if config.get('use_lrc_file'):
                with open(filepath[0:-len(config.get('media_format'))] + 'lrc', 'w', encoding='utf-8') as f:
                    f.write(merged_lyrics)
            if config.get('embed_lyrics'):
                if item_type == "track":
                    set_audio_tags(filepath, {"lyrics": merged_lyrics, "language": resp['lyrics']['language']}, item_id)
                if item_type == "episode":
                    set_audio_tags(filepath, {"lyrics": merged_lyrics}, item_id)
    else:
        return False


def spotify_get_playlist_items(token, playlist_id):
    logger.info(f"Getting items in playlist: '{playlist_id}'")
    access_token = token.tokens().get("playlist-read-private")
    print(access_token)
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?additional_types=track%2Cepisode'
    resp = requests.get(url, headers=headers)
    #resp = make_call(url, token=access_token)
    print(resp.status_code)
    return resp.json()


def get_album_name(session, album_id):
    logger.info(f"Get album info from album by id ''{album_id}'")
    access_token = session.tokens().get("user-read-email")
    resp = make_call(
        f'https://api.spotify.com/v1/albums/{album_id}',
        token=access_token
        )
    if m := re.search(r'(\d{4})', resp['release_date']):
        return resp['artists'][0]['name'],\
            m.group(1), resp['name'],\
            resp['total_tracks']
    else:
        return resp['artists'][0]['name'],\
            resp['release_date'], resp['name'],\
            resp['total_tracks']


def spotify_get_album_tracks(session, album_id):
    logger.info(f"Get tracks from album by id '{album_id}'")
    access_token = session.tokens().get("user-read-email")
    songs = []
    offset = 0
    limit = 50
    include_groups = 'album,compilation'

    while True:
        params = {
            'limit': limit,
            'include_groups': include_groups,
            'offset': offset
            }
        resp = make_call(
            f'https://api.spotify.com/v1/albums/{album_id}/tracks',
            token=access_token,
            params=params
            )
        offset += limit
        songs.extend(resp['items'])

        if len(resp['items']) < limit:
            break
    return songs

def spotify_get_search_results(session, search_term, content_types):
    logger.info(
        f"Get search result for term '{search_term}'"
        )
    if search_term.strip() == "":
        logger.warning(f"Returning empty data as query is empty !")
        return results
    if content_types is None:
        content_types = ["track", "album", "playlist", "artist", "show", "episode", "audiobook"]
    token = session.tokens().get("user-read-email")
    print(token)
    data = requests.get(
        "https://api.spotify.com/v1/search",
        {
            "limit": config.get("max_search_results"),
            "offset": "0",
            "q": search_term,
            "type": ",".join(c_type for c_type in content_types)
        },
        headers={"Authorization": "Bearer %s" % token},
    ).json()

    search_results = []

    # Iterate over the keys in the response  
    for key in data.keys():
        for item in data[key]["items"]:
            item_type = item['type']
            if item_type == "track":
                item_name = f"{config.get('explicit_label') if item['explicit'] else ''} {item['name']}"
                item_by = f"{config.get('metadata_seperator').join([artist['name'] for artist in item['artists']])}"
                item_thumbnail_url = item['album']['images'][-1]["url"] if len(item['album']['images']) > 0 else ""
            elif item_type == "album":
                rel_year = re.search(r'(\d{4})', item['release_date']).group(1)
                item_name = f"[Y:{rel_year}] [T:{item['total_tracks']}] {item['name']}"
                item_by = f"{config.get('metadata_seperator').join([artist['name'] for artist in item['artists']])}"
                item_thumbnail_url = item['images'][-1]["url"] if len(item['images']) > 0 else ""
            elif item_type == "playlist":
                item_name = f"{item['name']}"
                item_by = f"{item['owner']['display_name']}"
                item_thumbnail_url = item['images'][-1]["url"] if len(item['images']) > 0 else ""
            elif item_type == "artist":
                item_name = item['name']
                if f"{'/'.join(item['genres'])}" != "":
                    item_name = item['name'] + f"  |  GENERES: {'/'.join(item['genres'])}"
                item_by = f"{item['name']}"
                item_thumbnail_url = item['images'][-1]["url"] if len(item['images']) > 0 else ""
            elif item_type == "shows":
                item_name = f"{config.get('explicit_label') if item['explicit'] else ''} {item['name']}"
                item_by = f"{item['publisher']}"
                item_thumbnail_url = item['images'][-1]["url"] if len(item['images']) > 0 else ""
            elif item_type == "episodes":
                item_name = f"{config.get('explicit_label') if item['explicit'] else ''} {item['name']}"
                item_by = ""
                item_thumbnail_url = item['images'][-1]["url"] if len(item['images']) > 0 else ""
            elif item_type == "audiobooks":
                item_name = f"{config.get('explicit_label') if item['explicit'] else ''} {item['name']}"
                item_by = f"{item['publisher']}"
                item_thumbnail_url = item['images'][-1]["url"] if len(item['images']) > 0 else ""

            search_results.append({
                'item_id': item['id'],
                'item_name': item_name,
                'item_by': item_by,
                'item_type': item['type'],
                'item_service': "spotify",
                'item_url': item['external_urls']['spotify'],
                'item_thumbnail_url': item_thumbnail_url
            })
    print(search_results)
    return search_results






def check_premium(session):
    return bool(
        session.get_user_attribute("type") == "premium" or config.get("force_premium")
        )


def spotify_get_track_metadata(session, item_id):
    print(session)
    token = session.tokens().get("user-read-email")
    track_data = make_call(f'https://api.spotify.com/v1/tracks?ids={item_id}&market=from_token', token=token)
    credits_data = make_call(f'https://spclient.wg.spotify.com/track-credits-view/v0/experimental/{item_id}/credits', token=token)
    track_audio_data = make_call(f'https://api.spotify.com/v1/audio-features/{item_id}', token=token)
    album_data = make_call(track_data['tracks'][0]['album']['href'], token=token)
    artist_data = make_call(track_data['tracks'][0]['artists'][0]['href'], token=token)

    info = {}

    # Add Default Track Keys
    try:
        # Format Artists
        artists = []
        for data in track_data['tracks'][0]['artists']:
            artists.append(data['name'])

        # Format Credits
        credits = {}
        for credit_block in credits_data.get('roleCredits', []):
            credits[credit_block['roleTitle'].lower()] = [
                    artist['name']
                    for artist
                    in
                    credit_block['artists']
                ]

        info['artists'] = artists
        info['album_name'] = track_data['tracks'][0]['album']["name"]
        info['album_type'] = album_data['album_type']
        info['album_artists'] = album_data['artists'][0]['name']
        info['title'] = track_data['tracks'][0]['name']
        info['image_url'] = track_data['tracks'][0]['album']['images'][0]['url']
        info['release_year'] = track_data['tracks'][0]['album']['release_date'].split("-")[0]
        info['track_number'] = track_data['tracks'][0]['track_number']
        info['total_tracks'] = track_data['tracks'][0]['album']['total_tracks']
        info['disc_number'] = track_data['tracks'][0]['disc_number']
        info['total_discs'] = sorted([trk['disc_number'] for trk in album_data['tracks']['items']])[-1] if 'tracks' in album_data else 1
        # https://developer.spotify.com/documentation/web-api/reference/get-track
        # List of genre is supposed to be here, genre from album API is deprecated and it always seems to be unavailable
        # Use artist endpoint to get artist's genre instead
        info['genre'] = artist_data['genres']
        info['performers'] = [item for item in credits['performers'] if isinstance(item, str)]
        info['producers'] = [item for item in credits['producers'] if isinstance(item, str)]
        info['writers'] = [item for item in credits['writers'] if isinstance(item, str)]
        info['label'] = album_data['label']
        info['copyright'] = [holder['text'] for holder in album_data['copyrights']]
        info['explicit'] = track_data['tracks'][0]['explicit']
        info['isrc'] = track_data['tracks'][0]['external_ids'].get('isrc', '')
        info['length'] = track_data['tracks'][0]['duration_ms']
        info['item_url'] = track_data['tracks'][0]['external_urls']['spotify']
        info['popularity'] = track_data['tracks'][0]['popularity'] # unused
        info['scraped_song_id'] = track_data['tracks'][0]['id']
        info['is_playable'] = track_data['tracks'][0]['is_playable']
    except TypeError:
        logger.info('Caught a TypeError: Something went wrong in the default track keys, please file a bug report.')

    # Add Audio Analysis Keys
    try:
        # Format Key
        if track_audio_data['key'] == 0:
            key = "C"
        elif track_audio_data['key'] == 1:
            key = "C♯/D♭"
        elif track_audio_data['key'] == 2:
            key = "D"
        elif track_audio_data['key'] == 3:
            key = "D♯/E♭"
        elif track_audio_data['key'] == 4:
            key = "E"
        elif track_audio_data['key'] == 5:
            key = "F"
        elif track_audio_data['key'] == 6:
            key = "F♯/G♭"
        elif track_audio_data['key'] == 7:
            key = "G"
        elif track_audio_data['key'] == 8:
            key = "G♯/A♭"
        elif track_audio_data['key'] == 9:
            key = "A"
        elif track_audio_data['key'] == 10:
            key = "A♯/B♭"
        elif track_audio_data['key'] == 11:
            key = "B"
        else:
            key = ""

        info['bpm'] = track_audio_data['tempo']
        info['key'] = key
        info['time_signature'] = track_audio_data['time_signature']
        info['acousticness'] = track_audio_data['acousticness']
        info['danceability'] = track_audio_data['danceability']
        info['energy'] = track_audio_data['energy']
        info['instrumentalness'] = track_audio_data['instrumentalness']
        info['liveness'] = track_audio_data['liveness']
        info['loudness'] = track_audio_data['loudness']
        info['speechiness'] = track_audio_data['speechiness']
        info['valence'] = track_audio_data['valence']
    except TypeError:
        logger.info('Caught a TypeError: Audio analysis likely does not exist for this track.')

    return info


def spotify_get_episode_metadata(token, episode_id_str):
    logger.info(f"Get episode info for episode by id '{episode_id_str}'")
    token = token.tokens().get("user-read-email")
    episode_data = make_call("https://api.spotify.com/v1/episodes/" + episode_id_str, token=token)
    info = {}

    languages = []
    for language in episode_data['languages']:
        languages.append(language)

    info['album_name'] = episode_data["show"]["name"]
    info['title'] = episode_data['name']
    info['image_url'] = episode_data['images'][0]['url']
    info['release_year'] = episode_data['release_date']
    info['total_tracks'] = episode_data['show']['total_episodes']
    info['artists'] = [episode_data['show']['publisher']]
    info['language'] = conv_list_format(languages)
    info['description'] = episode_data['description'] if episode_data['description'] != "" else info['show']['description'], 
    info['copyright'] = episode_data['show']['copyrights']
    info['length'] = episode_data['duration_ms']
    info['explicit'] = episode_data['explicit']
    info['is_playable'] = episode_data['is_playable']

    return info


def spotify_get_show_episodes(session, show_id_str):
    logger.info(f"Get episodes for show by id '{show_id_str}'")
    access_token = session.tokens().get("user-read-email")
    episodes = []
    offset = 0
    limit = 50
    while True:
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'limit': limit, 'offset': offset}
        resp = make_call(f'https://api.spotify.com/v1/shows/{show_id_str}/episodes', token=access_token, params=params)
        offset += limit
        for episode in resp["items"]:
            episodes.append(episode["external_urls"]["spotify"])

        if len(resp['items']) < limit:
            break

    return episodes

def make_call(url, token, params=None, headers=None, skip_cache=False):
    if params is None:
        params = {}
    if headers is None:
        headers = {"Authorization": f"Bearer {token}"}
    if not skip_cache:
        request_key = md5(f'{url}'.encode()).hexdigest()
        req_cache_file = os.path.join(config.get('_cache_dir'), 'reqcache', request_key+'.otcache')
        os.makedirs(os.path.dirname(req_cache_file), exist_ok=True)
        if os.path.isfile(req_cache_file):
            logger.debug(f'URL "{url}" cache found ! HASH: {request_key}')
            try:
                with open(req_cache_file, 'r', encoding='utf-8') as cf:
                    json_data = json.load(cf)
                return json_data
            except json.JSONDecodeError:
                logger.error(f'URL "{url}" cache has invalid data, retring request !')
                pass
        logger.debug(f'URL "{url}" has cache miss ! HASH: {request_key}; Fetching data')
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        if not skip_cache:
            with open(req_cache_file, 'w', encoding='utf-8') as cf:
                cf.write(response.text)
        return json.loads(response.text)