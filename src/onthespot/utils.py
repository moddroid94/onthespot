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