import os
import re
import time
import uuid
import json
import threading
import requests
from librespot.audio.decoders import AudioQuality
from librespot.core import Session
from librespot.zeroconf import ZeroconfServer
from PyQt6.QtCore import QObject
from ..otsconfig import config, cache_dir
from ..runtimedata import get_logger, account_pool, pending, download_queue, pending_lock
from ..utils import make_call, conv_list_format, format_local_id

logger = get_logger("api.spotify")


class MirrorSpotifyPlayback(QObject):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.is_running = False

    def start(self):
        if self.thread is None:
            logger.info('Starting SpotifyMirrorPlayback')
            self.is_running = True
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
        else:
            logger.warning('SpotifyMirrorPlayback is already running.')

    def stop(self):
        if self.thread is not None:
            logger.info('Stopping SpotifyMirrorPlayback')
            self.is_running = False
            self.thread.join()
            self.thread = None
        else:
            logger.warning('SpotifyMirrorPlayback is not running.')

    def run(self):
        while self.is_running:
            time.sleep(3)
            try:
                parsing_index = config.get('parsing_acc_sn')
                if account_pool[parsing_index]['service'] != 'spotify':
                    continue
                token = account_pool[parsing_index]['login']['session'].tokens().get("user-read-currently-playing")
            except IndexError:
                time.sleep(2)
                continue
            except Exception:
                spotify_re_init_session(account_pool[parsing_index])
                token = account_pool[parsing_index]['login']['session'].tokens().get("user-read-currently-playing")
            url = "https://api.spotify.com/v1/me/player/currently-playing"
            resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 200:
                data = resp.json()
                if data['currently_playing_type'] == 'track':
                    item_id = data['item']['id']
                    if item_id not in pending and item_id not in download_queue:
                        parent_category = 'track'
                        playlist_name = ''
                        playlist_by = ''
                        if data['context']['type'] == 'playlist':
                            match = re.search(r'spotify:playlist:(\w+)', data['context']['uri'])
                            if match:
                                playlist_id = match.group(1)
                            else:
                                continue
                            token = account_pool[parsing_index]['login']['session'].tokens().get("user-read-email")
                            playlist_name, playlist_by = spotify_get_playlist_data(token, playlist_id)
                            parent_category = 'playlist'
                        elif data['context']['type'] == 'collection':
                            playlist_name = 'Liked Songs'
                            playlist_by = 'me'
                            parent_category = 'playlist'
                        elif data['context']['type'] in ('album', 'artist'):
                            parent_category = 'album'
                        # Use item id to prevent duplicates
                        #local_id = format_local_id(item_id)
                        with pending_lock:
                            pending[item_id] = {
                                'local_id': item_id,
                                'item_service': 'spotify',
                                'item_type': 'track',
                                'item_id': item_id,
                                'parent_category': parent_category,
                                'playlist_name': playlist_name,
                                'playlist_by': playlist_by,
                                'playlist_number': '?'
                            }
                        logger.info(f'Mirror Spotify Playback added track to download queue: https://open.spotify.com/track/{item_id}')
                        continue
                else:
                    logger.info('Spotify API does not return enough data to parse currently playing episodes.')
                    continue
            else:
                continue


def spotify_new_session():
    os.makedirs(os.path.join(cache_dir(), 'onthespot', 'sessions'), exist_ok=True)

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
    try:
        # I'd prefer to use 'Session.Builder().stored(credentials).create but
        # it seems to be broken, loading from credentials file instead
        uuid = account['uuid']
        username = account['login']['username']

        session_dir = os.path.join(cache_dir(), "onthespot", "sessions")
        os.makedirs(session_dir, exist_ok=True)
        session_json_path = os.path.join(session_dir, f"ots_login_{uuid}.json")
        print(session_json_path)
        try:
            with open(session_json_path, 'w') as file:
                json.dump(account['login'], file)
            print(f"Login information for '{username[:4]}*******' written to {session_json_path}")
        except IOError as e:
            print(f"Error writing to file {session_json_path}: {e}")


        config = Session.Configuration.Builder().set_stored_credential_file(session_json_path).build()
        # For some reason initialising session as None prevents premature application exit
        session = None
        session = Session.Builder(conf=config).stored_file(session_json_path).create()
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
    except Exception as e:
        logger.error(f"Unknown Exception: {str(e)}")
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


def spotify_re_init_session(account):
    session_json_path = os.path.join(cache_dir(), "onthespot", "sessions", f"ots_login_{account['uuid']}.json")
    try:
        config = Session.Configuration.Builder().set_stored_credential_file(session_json_path).build()
        logger.debug("Session config created")
        session = Session.Builder(conf=config).stored_file(session_json_path).create()
        logger.debug("Session re init done")
        account['login']['session_path'] = session_json_path
        account['login']['session'] = session
        account['status'] = 'active'
        account['account_type'] = session.get_user_attribute("type")
        bitrate = "160k"
        account_type = session.get_user_attribute("type")
        if account_type == "premium":
            bitrate = "320k"
        account['bitrate'] = bitrate
    except:
        logger.error('Failed to re init session !')


def spotify_get_token(parsing_index):
    try:
        token = account_pool[parsing_index]['login']['session'].tokens().get("user-read-email")
    except (OSError, AttributeError):
        logger.info(f'Failed to retreive token for {account_pool[parsing_index]["username"]}, attempting to reinit session.')
        spotify_re_init_session(account_pool[parsing_index])
        token = account_pool[parsing_index]['login']['session'].tokens().get("user-read-email")
    return token


def spotify_get_artist_albums(token, artist_id):
    logger.info(f"Get albums for artist by id '{artist_id}'")
    headers = {"Authorization": f"Bearer {token}"}
    resp = make_call(f'https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=album%2Csingle&limit=50', headers=headers) #%2Cappears_on%2Ccompilation
    return [resp['items'][i]['external_urls']['spotify'] for i in range(len(resp['items']))]


def spotify_get_playlist_data(token, playlist_id):
    logger.info(f"Get playlist dump for '{playlist_id}'")
    headers = {"Authorization": f"Bearer {token}"}
    resp = make_call(f'https://api.spotify.com/v1/playlists/{playlist_id}', headers=headers, skip_cache=True)
    return resp['name'], resp['owner']['display_name']


def spotify_get_lyrics(token, item_id, item_type, metadata, filepath):
    if config.get('inp_enable_lyrics'):
        lyrics = []
        try:
            if item_type == "track":
                url = f'https://spclient.wg.spotify.com/color-lyrics/v2/track/{item_id}'
            elif item_type == "episode":
                url = f"https://spclient.wg.spotify.com/transcript-read-along/v2/episode/{item_id}"

            params = 'format=json&market=from_token'

            headers = {
            'app-platform': 'WebPlayer',
            'Authorization': f'Bearer {token}',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
            }

            resp = make_call(url, headers=headers, params=params)
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
                    artist = value
                    lyrics.append(f'[ar:{artist}]')

                elif key in ['album_name', 'album'] and config.get("embed_album"):
                    album = value
                    lyrics.append(f'[al:{album}]')

                elif key in ['writers'] and config.get("embed_writers"):
                    author = value
                    lyrics.append(f'[au:{author}]')

            if item_type == "track":
                lyrics.append(f'[by:{resp["lyrics"]["provider"]}]')

            if config.get("embed_length"):
                l_ms = int(metadata['length'])
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
                with open(filepath + '.lrc', 'w', encoding='utf-8') as f:
                    f.write(merged_lyrics)
            if config.get('embed_lyrics'):
                if item_type == "track":
                    return {"lyrics": merged_lyrics, "language": resp['lyrics']['language']}
                if item_type == "episode":
                    return {"lyrics": merged_lyrics}
            else:
                return True
    else:
        return False


def spotify_get_playlist_items(token, playlist_id):
    logger.info(f"Getting items in playlist: '{playlist_id}'")
    items = []
    offset = 0
    limit = 100
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?additional_types=track%2Cepisode'

    while True:
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            'limit': limit,
            'offset': offset
            }

        resp = make_call(url, headers=headers, params=params, skip_cache=True)

        offset += limit
        items.extend(resp['items'])

        if resp['total'] <= offset:
            break
    return items


def spotify_get_liked_songs(token):
    logger.info("Getting liked songs")
    items = []
    offset = 0
    limit = 50
    token = account_pool[config.get('parsing_acc_sn')]['login']['session'].tokens().get("user-library-read")

    url = f'https://api.spotify.com/v1/me/tracks'

    while True:
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            'limit': limit,
            'offset': offset
            }

        resp = make_call(url, headers=headers, params=params, skip_cache=True)

        offset += limit
        items.extend(resp['items'])

        if resp['total'] <= offset:
            break
    return items


def spotify_get_your_episodes(token):
    logger.info("Getting your episodes")
    items = []
    offset = 0
    limit = 50
    token = account_pool[config.get('parsing_acc_sn')]['login']['session'].tokens().get("user-library-read")
    url = f'https://api.spotify.com/v1/me/shows'

    while True:
        headers = {'Authorization': f'Bearer {token}'}
        params = {
            'limit': limit,
            'offset': offset
            }

        resp = make_call(url, headers=headers, params=params, skip_cache=True)

        offset += limit
        items.extend(resp['items'])

        if resp['total'] <= offset:
            break
    return items

def get_album_name(token, album_id):
    logger.info(f"Get album info from album by id ''{album_id}'")
    headers = {"Authorization": f"Bearer {token}"}
    resp = make_call(
        f'https://api.spotify.com/v1/albums/{album_id}',
        headers=headers
        )
    if m := re.search(r'(\d{4})', resp['release_date']):
        return resp['artists'][0]['name'],\
            m.group(1), resp['name'],\
            resp['total_tracks']
    else:
        return resp['artists'][0]['name'],\
            resp['release_date'], resp['name'],\
            resp['total_tracks']


def spotify_get_album_tracks(token, album_id):
    logger.info(f"Get tracks from album by id '{album_id}'")
    songs = []
    offset = 0
    limit = 50
    include_groups = 'album,compilation'

    while True:
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            'limit': limit,
            'include_groups': include_groups,
            'offset': offset
            }
        resp = make_call(
            f'https://api.spotify.com/v1/albums/{album_id}/tracks',
            headers=headers,
            params=params
            )

        offset += limit
        songs.extend(resp['items'])

        if resp['total'] <= offset:
            break
    return songs


def spotify_get_search_results(token, search_term, content_types):
    logger.info(
        f"Get search result for term '{search_term}'"
        )
    if content_types is None:
        content_types = ["track", "album", "playlist", "artist", "show", "episode", "audiobook"]
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
            elif item_type == "show":
                item_name = f"{config.get('explicit_label') if item['explicit'] else ''} {item['name']}"
                item_by = f"{item['publisher']}"
                item_thumbnail_url = item['images'][-1]["url"] if len(item['images']) > 0 else ""
            elif item_type == "episode":
                item_name = f"{config.get('explicit_label') if item['explicit'] else ''} {item['name']}"
                item_by = ""
                item_thumbnail_url = item['images'][-1]["url"] if len(item['images']) > 0 else ""
            elif item_type == "audiobook":
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
    return search_results


def spotify_get_track_metadata(token, item_id):
    headers = {"Authorization": f"Bearer {token}"}
    track_data = make_call(f'https://api.spotify.com/v1/tracks?ids={item_id}&market=from_token', headers=headers)
    credits_data = make_call(f'https://spclient.wg.spotify.com/track-credits-view/v0/experimental/{item_id}/credits', headers=headers)
    track_audio_data = make_call(f'https://api.spotify.com/v1/audio-features/{item_id}', headers=headers)
    album_data = make_call(track_data['tracks'][0]['album']['href'], headers=headers)
    artist_data = make_call(track_data['tracks'][0]['artists'][0]['href'], headers=headers)

    info = {}

    artists = []
    for data in track_data.get('tracks', [{}])[0].get('artists', []):
        artists.append(data.get('name', ''))
    artists = conv_list_format(artists)

    credits = {}
    for credit_block in credits_data.get('roleCredits', []):
        role_title = credit_block.get('roleTitle', '').lower()
        credits[role_title] = [
            artist.get('name', '') for artist in credit_block.get('artists', [])
        ]

    info['artists'] = artists
    info['album_name'] = track_data.get('tracks', [{}])[0].get('album', {}).get("name", '')
    info['album_type'] = album_data.get('album_type', '')
    info['album_artists'] = album_data.get('artists', [{}])[0].get('name', '')
    info['title'] = track_data.get('tracks', [{}])[0].get('name', '')

    try:
        info['image_url'] = track_data.get('tracks', [{}])[0].get('album', {}).get('images', [{}])[0].get('url', '')
    except IndexError:
        info['image_url'] = ''
        logger.info('Invalid thumbnail')

    info['release_year'] = track_data.get('tracks', [{}])[0].get('album', {}).get('release_date', '').split("-")[0]
    info['track_number'] = track_data.get('tracks', [{}])[0].get('track_number', '')
    info['total_tracks'] = track_data.get('tracks', [{}])[0].get('album', {}).get('total_tracks', '')
    info['disc_number'] = track_data.get('tracks', [{}])[0].get('disc_number', '')

    info['total_discs'] = sorted([trk.get('disc_number', 0) for trk in album_data.get('tracks', {}).get('items', [])])[-1] if 'tracks' in album_data else 1

    info['genre'] = conv_list_format(artist_data.get('genres', []))
    info['performers'] = conv_list_format([item for item in credits.get('performers', []) if isinstance(item, str)])
    info['producers'] = conv_list_format([item for item in credits.get('producers', []) if isinstance(item, str)])
    info['writers'] = conv_list_format([item for item in credits.get('writers', []) if isinstance(item, str)])
    info['label'] = album_data.get('label', '')
    info['copyright'] = conv_list_format([holder.get('text', '') for holder in album_data.get('copyrights', [])])
    info['explicit'] = track_data.get('tracks', [{}])[0].get('explicit', False)
    info['isrc'] = track_data.get('tracks', [{}])[0].get('external_ids', {}).get('isrc', '')
    info['length'] = str(track_data.get('tracks', [{}])[0].get('duration_ms', ''))
    info['item_url'] = track_data.get('tracks', [{}])[0].get('external_urls', {}).get('spotify', '')
    info['popularity'] = track_data.get('tracks', [{}])[0].get('popularity', '')  # unused
    info['item_id'] = track_data.get('tracks', [{}])[0].get('id', '')
    info['is_playable'] = track_data.get('tracks', [{}])[0].get('is_playable', False)

    key_mapping = {
        0: "C",
        1: "C♯/D♭",
        2: "D",
        3: "D♯/E♭",
        4: "E",
        5: "F",
        6: "F♯/G♭",
        7: "G",
        8: "G♯/A♭",
        9: "A",
        10: "A♯/B♭",
        11: "B"
    }
    if track_audio_data is not None:
        info['bpm'] = str(track_audio_data.get('tempo', ''))
        info['key'] = str(key_mapping.get(track_audio_data.get('key', ''), ''))
        info['time_signature'] = track_audio_data.get('time_signature', '')
        info['acousticness'] = track_audio_data.get('acousticness', '')
        info['danceability'] = track_audio_data.get('danceability', '')
        info['energy'] = track_audio_data.get('energy', '')
        info['instrumentalness'] = track_audio_data.get('instrumentalness', '')
        info['liveness'] = track_audio_data.get('liveness', '')
        info['loudness'] = track_audio_data.get('loudness', '')
        info['speechiness'] = track_audio_data.get('speechiness', '')
        info['valence'] = track_audio_data.get('valence', '')
    return info


def spotify_get_episode_metadata(token, episode_id_str):
    logger.info(f"Get episode info for episode by id '{episode_id_str}'")

    headers = {"Authorization": f"Bearer {token}"}

    episode_data = make_call(f"https://api.spotify.com/v1/episodes/{episode_id_str}", headers=headers)
    info = {}

    languages = episode_data.get('languages', '')

    info['album_name'] = episode_data.get("show", {}).get("name", "")
    info['title'] = episode_data.get('name', "")
    info['image_url'] = episode_data.get('images', [{}])[0].get('url', "")
    info['release_year'] = episode_data.get('release_date', "")
    info['total_tracks'] = episode_data.get('show', {}).get('total_episodes', 0)
    info['artists'] = conv_list_format([episode_data.get('show', {}).get('publisher', "")])
    info['album_artists'] = conv_list_format([episode_data.get('show', {}).get('publisher', "")])
    info['language'] = conv_list_format(languages)
    info['description'] = str(episode_data.get('description', "") if episode_data.get('description', "") != "" else "")
    info['copyright'] = conv_list_format(episode_data.get('show', {}).get('copyrights', ''))
    info['length'] = str(episode_data.get('duration_ms', ''))
    info['explicit'] = episode_data.get('explicit', '')
    info['is_playable'] = episode_data.get('is_playable', '')
    info['item_url'] = episode_data.get('show', {}).get('external_urls', {}).get('spotify', '')

    return info


def spotify_get_show_episodes(token, show_id_str):
    logger.info(f"Get episodes for show by id '{show_id_str}'")
    episodes = []
    offset = 0
    limit = 50
    while True:
        headers = {'Authorization': f'Bearer {token}'}
        params = {'limit': limit, 'offset': offset}
        resp = make_call(f'https://api.spotify.com/v1/shows/{show_id_str}/episodes', headers=headers, params=params)
        offset += limit
        for episode in resp["items"]:
            episodes.append(episode["id"])

        if len(resp['items']) < limit:
            break
    return episodes
