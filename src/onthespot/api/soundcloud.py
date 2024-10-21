import re
import requests
from ..otsconfig import config
from ..runtimedata import get_logger, account_pool, parsing
from ..utils import sanitize_data, make_call

SOUNDCLOUD_BASE = "https://api-v2.soundcloud.com"

SOUNDCLOUD_CLIENT_ID = "AADp6RRMinJzmrc26qh92jqzJOF69SwF"
SOUNDCLOUD_APP_VERSION = "1728640498"
SOUNDCLOUD_APP_LOCALE = "en"

logger = get_logger("worker.utility")

def soundcloud_parse_url(url):
        headers = {}
        headers["user-agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"

        params = {}
        params["client_id"] = SOUNDCLOUD_CLIENT_ID
        params["app_version"] = SOUNDCLOUD_APP_VERSION
        params["app_locale"] = SOUNDCLOUD_APP_LOCALE
        params["url"] = url

        resp = make_call(f"{SOUNDCLOUD_BASE}/resolve", headers=headers, params=params)
        print(resp.status_code)

        data = resp.json()

        item_id = str(data["id"])
        print(item_id)
        item_type = data["kind"]
        print(item_type)
        return item_type, item_id

def soundcloud_login_user(account):

    # Add support for logging in
    if account['uuid'] == 'public_soundcloud':
        response = requests.get("https://soundcloud.com")


        page_text = response.text

        client_id_url_match = re.finditer(
            r"<script\s+crossorigin\s+src=\"([^\"]+)\"",
                page_text,
            )

        *_, client_id_url_match = client_id_url_match

        #if client_id_url_match:
            #logger.info("Found client_id_url:", client_id_url_match.group(1))  # Access the captured group  
        #else:
            #logger.info(f"Failed to fetch free soundcloud client_id: {response.status_code}")

        client_id_url = client_id_url_match.group(1)

        app_version_match = re.search(
            r'<script>window\.__sc_version="(\d+)"</script>',
            page_text,
        )
        if app_version_match is None:
            raise Exception("Could not find app version in %s" % client_id_url)

        app_version = app_version_match.group(1)

        response2 = requests.get(client_id_url)

        page_text2 = response2.text

        client_id_match = re.search(r'client_id:\s*"(\w+)"', page_text2)
        assert client_id_match is not None  
        client_id = client_id_match.group(1)

        accounts = config.get('accounts') 
        # Remove public from list
        accounts = [account for account in accounts if account["uuid"] != "public_soundcloud"]

        new_user = {
            "uuid": "public_soundcloud",
            "service": "soundcloud",
            "active": True,
            "login": {
                "client_id": client_id,
                "app_version": app_version,
                "app_locale": "en",
            }
        }
        accounts.insert(0, new_user)

        config.set_('accounts', accounts)
        config.update()

        account_pool.append({
            "uuid": "public_soundcloud",
            "username": client_id,
            "service": "soundcloud",
            "status": "active",
            "account_type": "public",
            "bitrate": "128k",
            "login": {
                "client_id": client_id,
                "app_version": app_version,
                "app_locale": "en",
            }
        })


        logger.info(f"Refreshed SoundCloud tokens as {client_id} {app_version}")
        return True

def soundcloud_get_token(parsing_index):
    accounts = config.get("accounts")
    client_id = accounts[parsing_index]['login']["client_id"]
    app_version = accounts[parsing_index]['login']["app_version"]
    app_locale = accounts[parsing_index]['login']["app_locale"]
    return {"client_id": client_id, "app_version": app_version, "app_locale": app_locale}

def soundcloud_get_search_results(token, search_term, content_types):
    headers = {}
    headers["user-agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"

    params = {}
    params["client_id"] = token['client_id']
    params["app_version"] = token['app_version']
    params["app_locale"] = token['app_locale']
    params["q"] = search_term

    track_url = f"{SOUNDCLOUD_BASE}/search/tracks"
    playlist_url = f"{SOUNDCLOUD_BASE}/search/playlists"

    track_search = requests.get(track_url, headers=headers, params=params).json()
    playlist_search = requests.get(playlist_url, headers=headers, params=params).json()

    search_results = []
    for track in track_search['collection']:
        search_results.append({
            'item_id': track['id'],
            'item_name': track['title'],
            'item_by': track['user']['username'],
            'item_type': "track",
            'item_service': "soundcloud",
            'item_url': track['permalink_url'],
            'item_thumbnail_url': track["artwork_url"]
        })
    for playlist in playlist_search['collection']:
        search_results.append({
            'item_id': playlist['id'],
            'item_name': playlist['title'],
            'item_by': playlist['user']['username'],
            'item_type': "playlist",
            'item_service': "soundcloud",
            'item_url': playlist['permalink_url'],
            'item_thumbnail_url': playlist["artwork_url"]
        })

    return search_results


def soundcloud_get_set_items(token, url):
    headers = {}
    headers["user-agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"

    params = {}
    params["client_id"] = token['client_id']
    params["app_version"] = token['app_version']
    params["app_locale"] = token['app_locale']
    params["url"] = url

    tracks = []
    try:
        set_data = make_call(f"{SOUNDCLOUD_BASE}/resolve", headers=headers, params=params)

        for track in set_data.get('tracks'):
            parsing[track.get('id')] = {
                'item_url': track.get('permalink_url'), 
                'item_service': 'soundcloud',
                'item_type': 'track', 
                'item_id': track.get('id')
            }
    except (TypeError, KeyError):
        logger.info(f"Failed to parse tracks for set: {url}")

def soundcloud_get_track_metadata(token, item_id):
        headers = {}
        headers["user-agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"

        params = {}
        params["client_id"] = token['client_id']
        params["app_version"] = token['app_version']
        params["app_locale"] = token['app_locale']

        track_data = make_call(f"{SOUNDCLOUD_BASE}/tracks/{item_id}", headers=headers, params=params)
        track_file = requests.get(track_data["media"]["transcodings"][0]["url"], headers=headers, params=params).json()
        track_webpage = requests.get(f"{track_data['permalink_url']}/albums").text
        # Parse album webpage
        start_index = track_webpage.find('<h2>Appears in albums</h2>')
        if start_index != -1:
            album_href = re.search(r'href="([^"]*)"', track_webpage[start_index:])
            if album_href:
                params["url"] = f"https://soundcloud.com{album_href.group(1)}"
                album_data = make_call(f"{SOUNDCLOUD_BASE}/resolve", headers=headers, params=params)

        info = {}

        # Many soundcloud songs are missing publisher metadata, parse if exists.
        # Label
        try:
            label = track_data['label_name']
        except (KeyError, TypeError):
            label = ""
        # Artists
        try:
            artists = [item.strip() for item in track_data['publisher_metadata']['artist'].split(',')]
        except (KeyError, TypeError):
            artists = [track_data['user']['username']]
        # Track Number
        try:
            total_tracks = album_data['track_count']
            track_number = 0
            for track in album_data['tracks']:
                track_number = track_number + 1
                if track['id'] == track_data['id']:
                    break
        except (KeyError, TypeError):
            total_tracks = '1'
            track_number = '1'
        # Album Name
        try:
            album_name = track_data['publisher_metadata']['album_name']
        except (KeyError, TypeError):
            start_index = track_webpage.find('<h2>Appears in albums</h2>')
            if start_index != -1:
                a_tag_match = re.search(r'<a[^>]*>(.*?)</a>', track_webpage[start_index:])
                if a_tag_match:
                    album_name = a_tag_match.group(1)
            if album_name.startswith("Users who like"):
                album_name = track_data['title']
        # Explicit
        try:
            explicit = track_data['publisher_metadata']['explicit']
        except (KeyError, TypeError):
            explicit = ""
        # Copyright
        try:
            copyright = [item.strip() for item in track_data['publisher_metadata']['c_line'].split(',')]
        except (KeyError, TypeError):
            copyright = ""
        
        #'media': {'transcodings': [{'url': 'https://api-v2.soundcloud.com/media/soundcloud:tracks:1893576612/5f63586d-5f78-452d-87ed-135a12e3b09d/stream/hls', 'preset': 'mp3_1_0', 'duration': 186723, 'snipped': False, 'format': {'protocol': 'hls', 'mime_type': 'audio/mpeg'}, 'quality': 'sq'},

        info['image_url'] = track_data["artwork_url"]
        info['description'] = track_data["description"]
        info['genre'] = [track_data['genre']]
        info['label'] = label
        info['item_url'] = track_data['permalink_url']
        info['release_year'] = track_data["release_date"].split("-")[0] if track_data["release_date"] is not None else track_data["last_modified"].split("-")[0]
        info['title'] = track_data["title"]
        # Add function to ensure progressive stream was grabbed instead of arbitrary number
        info['track_number'] = track_number
        info['total_tracks'] = total_tracks
        info['file_url'] = track_file["url"]
        info['length'] = track_data["media"]["transcodings"][0]["duration"]
        info['artists'] = artists
        info['album_name'] = album_name
        info['explicit'] = explicit
        info['copyright'] = copyright
        info['is_playable'] = track_data["streamable"]
        return info

def soundcloud_format_track_path(item_metadata, is_playlist_item, playlist_name, playlist_by):
    if config.get("translate_file_path"):
        def translate(string):
            return requests.get(f"https://translate.googleapis.com/translate_a/single?dj=1&dt=t&dt=sp&dt=ld&dt=bd&client=dict-chrome-ex&sl=auto&tl={config.get('language')}&q={string}").json()["sentences"][0]["trans"]
        _name = translate(item_metadata['title'])
        #_album = translate(item_metadata['album_name'])
    else:
        _name = item_metadata['title']
        #_album=item_metadata['album_name']

    _artist = item_metadata['artists'][0]    

    # FIX ME
    playlist_name = None

    if playlist_name != None and config.get("use_playlist_path"):
        path = config.get("playlist_path_formatter")
    else:
        path = config.get("track_path_formatter")
    item_path = path.format(
        artist = sanitize_data(_artist),
        album = sanitize_data(item_metadata['album_name']),
        name = sanitize_data(_name),
        rel_year = sanitize_data(item_metadata['release_year']),
        disc_number = "",
        track_number = item_metadata['track_number'],
        genre = sanitize_data(item_metadata['genre'][0] if len(item_metadata['genre']) > 0 else ''),
        label = sanitize_data(item_metadata['label']),
        explicit = sanitize_data(str(config.get('explicit')) if item_metadata['explicit'] else ''),
        trackcount = item_metadata['total_tracks'],
        disccount = "",
        playlist_name = sanitize_data(playlist_name),
        playlist_owner = sanitize_data(playlist_by),
    )
    if not config.get("force_raw"):
        item_path = item_path + "." + config.get("media_format")
    else:
        item_path = item_path + ".mp3"
    return item_path

