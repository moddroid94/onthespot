import time
#from .parse_url import parse_url
import queue
from .otsconfig import config

from .api.spotify import spotify_get_token, spotify_get_album_tracks, spotify_get_playlist_data, spotify_get_playlist_items, spotify_get_artist_albums, spotify_get_show_episodes


from .api.soundcloud import soundcloud_parse_url, soundcloud_get_set_items


from .runtimedata import get_logger, download_queue, downloads_status, downloaded_data, failed_downloads, cancel_list, \
    session_pool, thread_pool

from .runtimedata import parsing, download_queue, pending, failed, completed, cancelled
from .accounts import get_account_token
import re

logger = get_logger('gui.main_ui')

SOUNDCLOUD_URL_REGEX = re.compile(r"https://soundcloud.com/[-\w:/]+")
SPOTIFY_URL_REGEX = re.compile(r"^(https?://)?open\.spotify\.com/(?P<Type>track|album|artist|playlist|episode|show)/(?P<ID>[0-9a-zA-Z]{22})(\?si=.+?)?$")
SPOTIFY_INTERNATIONAL_URL_REGEX = re.compile(r"^(https?://)?open\.spotify\.com/intl-([a-zA-Z]+)/(?P<Type>track|album|artist|playlist|episode|show)/(?P<ID>[0-9a-zA-Z]{22})(\?si=.+?)?$")
#QOBUZ_INTERPRETER_URL_REGEX = re.compile(r"https?://www\.qobuz\.com/\w\w-\w\w/interpreter/[-\w]+/([-\w]+)")
#YOUTUBE_URL_REGEX = re.compile(r"https://www\.youtube\.com/watch\?v=[-\w]")




def parse_url(url):
    if re.match(SOUNDCLOUD_URL_REGEX, url):
        item_type, item_id = soundcloud_parse_url(url)
        item_service = "soundcloud"
    elif re.match(SPOTIFY_URL_REGEX, url) or re.match(SPOTIFY_INTERNATIONAL_URL_REGEX, url):
        match = re.search(SPOTIFY_URL_REGEX, url)
        item_id = match.group("ID")
        item_type = match.group("Type")
        item_service = "spotify"
    parsing[item_id] = {
        'item_url': url, 
        'item_service': item_service,
        'item_type': item_type, 
        'item_id': item_id
    }

# Worker function to process items in the tasks list  
def worker():
    time.sleep(8)
    token = get_account_token()
    while True:
        # Check if there are tasks to process  
        if parsing:
            # Pop the first item from the tasks list
            item_id = next(iter(parsing))  # Get the first key  
            item = parsing.pop(item_id)

            if item_id in pending:
                logger.info(f"Item Already Parsed: {item}")
            else:
                # Print the service type and ID  
                logger.info(f"Parsing: {item}")

                current_service = item['item_service']
                current_type = item['item_type']
                current_id = item['item_id']

                if current_service == "spotify":
                    if current_type == "track":
                        pending[item_id] = {
                            'item_service': current_service,
                            'item_type': current_type,
                            'item_id': item_id,
                            'is_playlist_item': False,
                            }
                        time.sleep(4)
                        continue

                    elif current_type == "album":
                        tracks = spotify_get_album_tracks(token, current_id)
                        for index, track in enumerate(tracks):
                            item_id = track['id']
                            pending[item_id] = {
                                'item_service': 'spotify',
                                'item_type': 'track',
                                'item_id': item_id,
                                'is_playlist_item': False,
                                }
                        time.sleep(4)
                        continue

                    elif current_type == "playlist":
                        data = spotify_get_playlist_items(token, current_id)
                        playlist_name, playlist_by = spotify_get_playlist_data(token, current_id)
                        for index, track in enumerate(data["items"]):
                            item_id = track['track']['id']
                            item_type = track['track']['type']
                            pending[item_id] = {
                                'item_service': 'spotify',
                                'item_type': item_type,
                                'item_id': item_id,
                                'is_playlist_item': True,
                                'playlist_name': playlist_name,
                                'playlist_by': playlist_by
                                }
                        time.sleep(4)
                        continue

                    elif current_type == "artist":
                        album_urls = spotify_get_artist_albums(token, current_id)
                        for index, album_url in enumerate(album_urls):
                            parse_url(album_url)
                        continue

                    elif current_type == "episode":
                        pending[item_id] = {
                            'item_service': current_service,
                            'item_type': current_type,
                            'item_id': item_id,
                            'is_playlist_item': False,
                            }
                        continue

                    # Fix ME
                    elif current_type in ['show', 'audiobook']:
                        episode_urls = spotify_get_show_episodes(token, current_id)
                        for index, episode_url in enumerate(episode_urls):
                            parse_url(episode_url)
                        continue

                elif current_service == "soundcloud":

                    if current_type == "track":
                        pending[item_id] = {
                            'item_service': current_service,
                            'item_type': current_type,
                            'item_id': item_id,
                            'is_playlist_item': False,
                            }
                        time.sleep(10)
                        continue

                    if current_type in ["album", "playlist"]:
                        # Items are added to pending in function to avoid complexity
                        track_urls = soundcloud_get_set_items(token, item['item_url'])

        else:
            time.sleep(4)
