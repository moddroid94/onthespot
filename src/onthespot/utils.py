import os
import platform
import time
import subprocess
import requests
import json
from hashlib import md5
from librespot.core import Session
from .otsconfig import config, config_dir
from .runtimedata import get_logger

logger = get_logger("utils")


def is_latest_release():
    url = "https://api.github.com/repos/justin025/onthespot/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        current_version = str(config.get("version")).replace('v', '').replace('.', '')
        latest_version = response.json()['name'].replace('v', '').replace('.', '')
        if int(latest_version) > int(current_version):
            logger.info(f"Update Available: {int(latest_version)} > {int(current_version)}")
            return False

def open_item(item):
    if platform.system() == 'Windows':
        os.startfile(item)
    elif platform.system() == 'Darwin':  # For MacOS
        subprocess.Popen(['open', item])
    else:  # For Linux and other Unix-like systems
        subprocess.Popen(['xdg-open', item])


def sanitize_data(value, allow_path_separators=False, escape_quotes=False):
    logger.info(
        f'Sanitising string: "{value}"; '
        f'Allow path separators: {allow_path_separators}'
        )
    if value is None:
        return ''
    char = config.get("illegal_character_replacement")
    if os.name == 'nt':
        value = value.replace('\\', char)
        value = value.replace('/', char)
        value = value.replace(':', char)
        value = value.replace('*', char)
        value = value.replace('?', char)
        value = value.replace('"', char)
        value = value.replace('<', char)
        value = value.replace('>', char)
        value = value.replace('|', char)
    else:
        value = value.replace('/', char)
    return value

def translate(string):
    try:
        response = requests.get(
            f"https://translate.googleapis.com/translate_a/single?dj=1&dt=t&dt=sp&dt=ld&dt=bd&client=dict-chrome-ex&sl=auto&tl={config.get('language')}&q={string}"
        )
        return response.json()["sentences"][0]["trans"]
    except (requests.exceptions.RequestException, KeyError, IndexError):
        return string 

def make_call(url, params=None, headers=None, skip_cache=False):
    if not skip_cache:
        request_key = md5(f'{url}'.encode()).hexdigest()
        req_cache_file = os.path.join(config.get('_cache_dir'), 'reqcache', request_key+'.json')
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

def conv_list_format(items):
    if len(items) == 0:
        return ''
    if len(items) == 1:
        return items[0]
    formatted = ""
    for item in items:
        formatted += item + config.get('metadata_seperator')
    return formatted[:-2].strip()

def format_track_path(item_metadata, item_service, item_type, is_playlist_item, playlist_name, playlist_by):
    if config.get("translate_file_path"):
        name = translate(item_metadata.get('title', ''))
        album = translate(item_metadata.get('album_name', ''))
    else:
        name = item_metadata.get('title', '')
        album = item_metadata.get('album_name', '')

    if is_playlist_item and config.get("use_playlist_path"):
        path = config.get("playlist_path_formatter")
    elif item_type == 'track':
        path = config.get("track_path_formatter")
    elif item_type == 'episode':
        path = config.get("podcast_path_formatter")

    item_path = path.format(
        artist=sanitize_data(item_metadata.get('artists', '')),
        album=sanitize_data(album),
        album_artist=sanitize_data(item_metadata.get('album_artists', '')),
        name=sanitize_data(name),
        year=sanitize_data(item_metadata.get('release_year', '')),
        disc_number=item_metadata.get('disc_number', ''),
        track_number=item_metadata.get('track_number', ''),
        genre=sanitize_data(item_metadata.get('genre', '')),
        label=sanitize_data(item_metadata.get('label', '')),
        explicit=sanitize_data(str(config.get('explicit_label')) if item_metadata.get('explicit') else ''),
        trackcount=item_metadata.get('total_tracks', ''),
        disccount=item_metadata.get('total_discs', ''),
        playlist_name=sanitize_data(playlist_name),
        playlist_owner=sanitize_data(playlist_by),
    )

    if item_service == 'soundcloud' and config.get("force_raw"):
        item_path += ".mp3"
    if item_service == 'spotify' and config.get("force_raw"):
        item_path += ".ogg"
    else:
        item_path += "." + config.get("media_format")

    return item_path
