import re
import time
from .otsconfig import config
from .api.spotify import spotify_get_liked_songs, spotify_get_your_episodes, spotify_get_album_tracks, spotify_get_playlist_data, spotify_get_playlist_items, spotify_get_artist_albums, spotify_get_show_episodes
from .api.soundcloud import soundcloud_parse_url, soundcloud_get_set_items
from .runtimedata import get_logger, parsing, download_queue, pending, account_pool, parsing_lock, pending_lock
from .accounts import get_account_token
from .api.deezer import deezer_get_album_items, deezer_get_playlist_items, deezer_get_playlist_data, deezer_get_artist_albums
from .utils import format_local_id

logger = get_logger('parse_item')

DEEZER_URL_REGEX = re.compile(r'https://www.deezer.com/(?:[a-z]{2}/)?(?P<type>album|playlist|track|artist)/(?P<id>\d+)')
SOUNDCLOUD_URL_REGEX = re.compile(r"https://soundcloud.com/[-\w:/]+")
SPOTIFY_URL_REGEX = re.compile(r"https://open.spotify.com/(intl-([a-zA-Z]+)/|)(?P<type>track|album|artist|playlist|episode|show)/(?P<id>[0-9a-zA-Z]{22})(\?si=.+?)?$")
YOUTUBE_URL_REGEX = re.compile(r"https://(www\.|music\.)?youtube\.com/watch\?v=(?P<video_id>[a-zA-Z0-9_-]+)(&list=(?P<list_id>[a-zA-Z0-9_-]+))?")
#QOBUZ_INTERPRETER_URL_REGEX = re.compile(r"https?://www\.qobuz\.com/\w\w-\w\w/interpreter/[-\w]+/([-\w]+)")

def parse_url(url):
    account_service = account_pool[config.get('parsing_acc_sn')]['service']

    if account_service == 'deezer' and re.match(DEEZER_URL_REGEX, url):
        match = re.search(DEEZER_URL_REGEX, url)
        item_id = match.group("id")
        item_type = match.group("type")
        item_service = 'deezer'

    elif account_service == 'soundcloud' and re.match(SOUNDCLOUD_URL_REGEX, url):
        token = get_account_token()
        item_type, item_id = soundcloud_parse_url(url, token)
        item_service = "soundcloud"

    elif account_service == 'spotify' and re.match(SPOTIFY_URL_REGEX, url):
        match = re.search(SPOTIFY_URL_REGEX, url)
        item_id = match.group("id")
        item_type = match.group("type")
        item_service = "spotify"
    elif account_service == 'spotify' and url == 'https://open.spotify.com/collection/tracks':
        item_id = None
        item_type = 'liked_songs'
        item_service = "spotify"
    elif account_service == 'spotify' and url == 'https://open.spotify.com/collection/your-episodes':
        item_id = None
        item_type = 'your_episodes'
        item_service = "spotify"

    elif account_service == 'youtube' and re.match(YOUTUBE_URL_REGEX, url):
        match = re.search(YOUTUBE_URL_REGEX, url)
        if match:
            item_service = 'youtube'
            item_type = 'track'
            item_id = match.group('video_id')
            list_id = match.group('list_id') if match.group('list_id') else None
            #if list_id:
            #    item_type = 'playlist'
    else:
        logger.info(f'Invalid Url: {url}')
        return False
    with parsing_lock:
        parsing[item_id] = {
            'item_url': url,
            'item_service': item_service,
            'item_type': item_type,
            'item_id': item_id
        }

def parsingworker():
    while True:
        if parsing:
            item_id = next(iter(parsing))
            with parsing_lock:
                item = parsing.pop(item_id)

            if item_id in pending or item_id in download_queue:
                logger.info(f"Item Already Parsed: {item}")
                continue
            else:
                logger.info(f"Parsing: {item}")

                current_service = item['item_service']
                current_type = item['item_type']
                current_id = item['item_id']
                token = get_account_token()

                if current_service == "spotify":
                    if current_type == "track":
                        local_id = format_local_id(item_id)
                        with pending_lock:
                            pending[local_id] = {
                                'local_id': local_id,
                                'item_service': current_service,
                                'item_type': current_type,
                                'item_id': item_id,
                                'parent_category': 'track'
                                }
                        continue

                    elif current_type == "album":
                        tracks = spotify_get_album_tracks(token, current_id)
                        for index, track in enumerate(tracks):
                            item_id = track['id']
                            local_id = format_local_id(item_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_service': 'spotify',
                                    'item_type': 'track',
                                    'item_id': item_id,
                                    'parent_category': 'album'
                                    }
                        continue

                    elif current_type == "playlist":
                        items = spotify_get_playlist_items(token, current_id)
                        playlist_name, playlist_by = spotify_get_playlist_data(token, current_id)
                        for index, item in enumerate(items):
                            try:
                                item_id = item['track']['id']
                                item_type = item['track']['type']
                                local_id = format_local_id(item_id)
                                with pending_lock:
                                    pending[local_id] = {
                                        'local_id': local_id,
                                        'item_service': 'spotify',
                                        'item_type': item_type,
                                        'item_id': item_id,
                                        'parent_category': 'playlist',
                                        'playlist_name': playlist_name,
                                        'playlist_by': playlist_by,
                                        'playlist_number': str(index + 1)
                                        }
                            except TypeError:
                                logger.error(f'TypeError for {item}')
                        continue

                    elif current_type == "artist":
                        album_urls = spotify_get_artist_albums(token, current_id)
                        for index, album_url in enumerate(album_urls):
                            parse_url(album_url)
                        continue

                    elif current_type == "episode":
                        local_id = format_local_id(item_id)
                        with pending_lock:
                            pending[local_id] = {
                                'local_id': local_id,
                                'item_service': current_service,
                                'item_type': current_type,
                                'item_id': item_id,
                                'parent_category': 'episode'
                                }
                        continue

                    elif current_type in ['show', 'audiobook']:
                        episode_ids = spotify_get_show_episodes(token, current_id)
                        for index, episode_id in enumerate(episode_ids):
                            local_id = format_local_id(episode_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_service': 'spotify',
                                    'item_type': 'episode',
                                    'item_id': episode_id,
                                    'parent_category': current_type
                                    }
                        continue

                    elif current_type == "liked_songs":
                        tracks = spotify_get_liked_songs(token)
                        for index, track in enumerate(tracks):
                            item_id = track['track']['id']
                            local_id = format_local_id(item_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_service': 'spotify',
                                    'item_type': 'track',
                                    'item_id': item_id,
                                    'parent_category': 'playlist',
                                    'playlist_name': 'Liked Songs',
                                    'playlist_by': 'me',
                                    'playlist_number': str(index + 1)
                                    }
                        continue

                    elif current_type == "your_episodes":
                        tracks = spotify_get_your_episodes(token)
                        for index, track in enumerate(tracks):
                            item_id = track['show']['id']
                            local_id = format_local_id(item_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_service': 'spotify',
                                    'item_type': 'episode',
                                    'item_id': item_id,
                                    'parent_category': 'playlist',
                                    'playlist_name': 'Your Episodes',
                                    'playlist_by': 'me',
                                    'playlist_number': str(index + 1)
                                    }
                        continue

                elif current_service == "soundcloud":

                    if current_type == "track":
                        local_id = format_local_id(item_id)
                        with pending_lock:
                            pending[local_id] = {
                                'local_id': local_id,
                                'item_service': current_service,
                                'item_type': current_type,
                                'item_id': item_id,
                                'parent_category': 'track'
                                }
                        continue

                    if current_type in ["album", "playlist"]:
                        # Items are added to pending in function to avoid complexity
                        set_data = soundcloud_get_set_items(token, item['item_url'])
                        for index, track in enumerate(set_data['tracks']):
                            item_id = track['id']
                            local_id = format_local_id(item_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_url': track.get('permalink_url', ''),
                                    'item_service': 'soundcloud',
                                    'item_type': 'track',
                                    'item_id': item_id,
                                    'parent_category': 'playlist' if not set_data['is_album'] else 'album',
                                    'playlist_name': set_data['title'],
                                    'playlist_by': set_data['user']['username'],
                                    'playlist_number': str(index + 1)
                                }

                elif current_service == "deezer":

                    if current_type == "track":
                        local_id = format_local_id(item_id)
                        with pending_lock:
                            pending[local_id] = {
                                'local_id': local_id,
                                'item_service': current_service,
                                'item_type': current_type,
                                'item_id': item_id,
                                'parent_category': 'track'
                                }
                        continue
                    elif current_type == "album":
                        tracks = deezer_get_album_items(current_id)
                        for index, track in enumerate(tracks):
                            item_id = track['id']
                            local_id = format_local_id(item_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_service': 'deezer',
                                    'item_type': 'track',
                                    'item_id': item_id,
                                    'parent_category': 'album'
                                    }
                        continue
                    elif current_type == "playlist":
                        tracks = deezer_get_playlist_items(current_id)
                        playlist_name, playlist_by = deezer_get_playlist_data(current_id)
                        for index, track in enumerate(tracks):
                            item_id = track['id']
                            local_id = format_local_id(item_id)
                            with pending_lock:
                                pending[local_id] = {
                                    'local_id': local_id,
                                    'item_service': 'deezer',
                                    'item_type': 'track',
                                    'item_id': item_id,
                                    'parent_category': 'playlist',
                                    'playlist_name': playlist_name,
                                    'playlist_by': playlist_by,
                                    'playlist_number': str(index + 1)
                                    }
                        continue
                    elif current_type == "artist":
                        album_urls = deezer_get_artist_albums(current_id)
                        for index, album_url in enumerate(album_urls):
                            parse_url(album_url)
                        continue

                elif current_service == "youtube":

                    if current_type == "track":
                        local_id = format_local_id(item_id)
                        with pending_lock:
                            pending[local_id] = {
                                'local_id': local_id,
                                'item_service': current_service,
                                'item_type': current_type,
                                'item_id': item_id,
                                'parent_category': 'track'
                                }
                        continue
        else:
            time.sleep(0.2)
