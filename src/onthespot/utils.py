import os
import platform
import time
import requests
from librespot.core import Session
import re
from .otsconfig import config, config_dir
from .runtimedata import get_logger
#from .api.spotify import get_currently_playing_url
import subprocess
import asyncio
import traceback
import json
from hashlib import md5

logger = get_logger("utils")
media_tracker_last_query = ''


def re_init_session(session_pool: dict, session_uuid: str, wait_connectivity: bool = False,
                    connectivity_test_url: str = 'https://spotify.com', timeout=60) -> bool:
    start = int(time.time())
    session_json_path = os.path.join(os.path.join(cache_dir(), 'onthespot', 'sessions'),
                                     f"ots_login_{session_uuid}.json")
    if not os.path.isfile(session_json_path):
        return False
    if wait_connectivity:
        status = 0
        while status != 200 and int(time.time()) - start < timeout:
            try:
                r = requests.get(connectivity_test_url)
                status = r.status_code
                logger.info(f'Connectivity check done ! Status code "{status}" ')
            except:
                logger.info('Connectivity issue ! Waiting ... ')
        if status == 0:
            return False
    try:
        config = Session.Configuration.Builder().set_stored_credential_file(session_json_path).build()
        logger.debug("Session config created")
        session = Session.Builder(conf=config).stored_file(session_json_path).create()
        logger.debug("Session re init done")
        session_pool[session_uuid] = session
    except:
        logger.error('Failed to re init session !')
        return False
    return True





def remove_user(username: str, login_data_dir: str, config, session_uuid: str, thread_pool: dict,
                session_pool: dict) -> bool:
    logger.info(f"Removing user '{username[:4]}*******' from saved entries, uuid {session_uuid}")
    # Try to stop the thread using this account
    if session_uuid in thread_pool.keys():
        thread_pool[session_uuid][0].stop()
        logger.info(f'Waiting for worker bound to account : {session_uuid} to exit !')
        while not thread_pool[session_uuid][0].is_stopped():
            time.sleep(0.1)
        logger.info(f'Waiting for thread bound to worker bound account : {session_uuid} to exit !')
        while thread_pool[session_uuid][1].isRunning():
            thread_pool[session_uuid][1].quit()
        logger.info(f'Workers and threads associated with account : {session_uuid} cleaned up !')
        thread_pool.pop(session_uuid)
    # Remove from session pool
    if session_uuid in session_pool:
        session_pool.pop(session_uuid)
    session_json_path = os.path.join(login_data_dir, f"ots_login_{session_uuid}.json")
    if os.path.isfile(session_json_path):
        os.remove(session_json_path)
    removed = False
    accounts_copy = config.get("accounts").copy()
    accounts = config.get("accounts")
    for i in range(0, len(accounts)):
        if accounts[i][3] == session_uuid:
            accounts_copy.pop(i)
            removed = True
            break
    if removed:
        logger.info(f"Saved Account user '{username[:4]}*******' found and removed, uuid: {session_uuid}")
        config.set_("accounts", accounts_copy)
        config.update()
    return removed


def get_now_playing_local(session):
    global media_tracker_last_query
    if platform.system() == "Linux":
        logger.debug("Linux detected ! Use playerctl to get current track information..")
        try:
            playerctl_out = subprocess.check_output(["playerctl", "-p", "spotify", "metadata", "xesam:url"])
        except subprocess.CalledProcessError:
            logger.debug("Spotify not running. Fetching track via api..")
            return get_currently_playing_url(session)
        spotify_url = playerctl_out.decode()
        return spotify_url
    else:
        logger.debug("Unsupported platform for auto download. Fetching track via api..")
        return get_currently_playing_url(session)


def name_by_from_sdata(d_key: str, item: dict):
    item_name = item_by = None
    if d_key == "tracks":
        item_name = f"{config.get('explicit_label') if item['explicit'] else '       '} {item['name']}"
        item_by = f"{config.get('metadata_seperator').join([artist['name'] for artist in item['artists']])}"
    elif d_key == "albums":
        rel_year = re.search(r'(\d{4})', item['release_date']).group(1)
        item_name = f"[Y:{rel_year}] [T:{item['total_tracks']}] {item['name']}"
        item_by = f"{config.get('metadata_seperator').join([artist['name'] for artist in item['artists']])}"
    elif d_key == "playlists":
        item_name = f"{item['name']}"
        item_by = f"{item['owner']['display_name']}"
    elif d_key == "artists":
        item_name = item['name']
        if f"{'/'.join(item['genres'])}" != "":
            item_name = item['name'] + f"  |  GENERES: {'/'.join(item['genres'])}"
        item_by = f"{item['name']}"
    elif d_key == "shows":
        item_name = f"{config.get('explicit_label') if item['explicit'] else '       '} {item['name']}"
        item_by = f"{item['publisher']}"
    elif d_key == "episodes":
        item_name = f"{config.get('explicit_label') if item['explicit'] else '       '} {item['name']}"
        item_by = ""
    elif d_key == "audiobooks":
        item_name = f"{config.get('explicit_label') if item['explicit'] else '       '} {item['name']}"
        item_by = f"{item['publisher']}"
    return item_name, item_by


def latest_release():
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