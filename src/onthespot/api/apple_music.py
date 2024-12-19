import base64
from http.cookiejar import MozillaCookieJar
import json
import m3u8
from pathlib import Path
import requests
import re
import uuid
import xml.etree.ElementTree as ET
from pywidevine import PSSH, Cdm, Device
from pywidevine.license_protocol_pb2 import WidevinePsshData
from ..otsconfig import config
from ..runtimedata import account_pool, get_logger
from ..utils import conv_list_format, make_call

logger = get_logger("api.apple_music")
BASE_URL = 'https://amp-api.music.apple.com/v1'
WVN_LICENSE_URL = "https://play.itunes.apple.com/WebObjects/MZPlay.woa/wa/acquireWebPlaybackLicense"
WVN_KEY = base64.b64decode(b'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QrSyZcBqHO0QrdPcU35GBT7S7+IJr2AAXvnjqnb8yrtpPWN2ZW/IWUJN2z4vZ7/HV4aj3OZhkxC1DIMNyvsusUKoQQuf8gwKiEe8cFwbwFSicywlFk9la2IPe8oFShcxAzHLCCn/TIYUAvEL3/4LgaZvqWm80qCPYbgIP5HT8hPYkKWJ4WYknEWK+3InbnkzteFfGrQFCq4CCAESEGnj6Ji7LD+4o7MoHYT4jBQYjtW+kQUijgIwggEKAoIBAQDY9um1ifBRIOmkPtDZTqH+CZUBbb0eK0Cn3NHFf8MFUDzPEz+emK/OTub/hNxCJCao//pP5L8tRNUPFDrrvCBMo7Rn+iUb+mA/2yXiJ6ivqcN9Cu9i5qOU1ygon9SWZRsujFFB8nxVreY5Lzeq0283zn1Cg1stcX4tOHT7utPzFG/ReDFQt0O/GLlzVwB0d1sn3SKMO4XLjhZdncrtF9jljpg7xjMIlnWJUqxDo7TQkTytJmUl0kcM7bndBLerAdJFGaXc6oSY4eNy/IGDluLCQR3KZEQsy/mLeV1ggQ44MFr7XOM+rd+4/314q/deQbjHqjWFuVr8iIaKbq+R63ShAgMBAAEo8CISgAMii2Mw6z+Qs1bvvxGStie9tpcgoO2uAt5Zvv0CDXvrFlwnSbo+qR71Ru2IlZWVSbN5XYSIDwcwBzHjY8rNr3fgsXtSJty425djNQtF5+J2jrAhf3Q2m7EI5aohZGpD2E0cr+dVj9o8x0uJR2NWR8FVoVQSXZpad3M/4QzBLNto/tz+UKyZwa7Sc/eTQc2+ZcDS3ZEO3lGRsH864Kf/cEGvJRBBqcpJXKfG+ItqEW1AAPptjuggzmZEzRq5xTGf6or+bXrKjCpBS9G1SOyvCNF1k5z6lG8KsXhgQxL6ADHMoulxvUIihyPY5MpimdXfUdEQ5HA2EqNiNVNIO4qP007jW51yAeThOry4J22xs8RdkIClOGAauLIl0lLA4flMzW+VfQl5xYxP0E5tuhn0h+844DslU8ZF7U1dU2QprIApffXD9wgAACk26Rggy8e96z8i86/+YYyZQkc9hIdCAERrgEYCEbByzONrdRDs1MrS/ch1moV5pJv63BIKvQHGvLkaFwoMY29tcGFueV9uYW1lEgd1bmtub3duGioKCm1vZGVsX25hbWUSHEFuZHJvaWQgU0RLIGJ1aWx0IGZvciB4ODZfNjQaGwoRYXJjaGl0ZWN0dXJlX25hbWUSBng4Nl82NBodCgtkZXZpY2VfbmFtZRIOZ2VuZXJpY194ODZfNjQaIAoMcHJvZHVjdF9uYW1lEhBzZGtfcGhvbmVfeDg2XzY0GmMKCmJ1aWxkX2luZm8SVUFuZHJvaWQvc2RrX3Bob25lX3g4Nl82NC9nZW5lcmljX3g4Nl82NDo5L1BTUjEuMTgwNzIwLjAxMi80OTIzMjE0OnVzZXJkZWJ1Zy90ZXN0LWtleXMaHgoUd2lkZXZpbmVfY2RtX3ZlcnNpb24SBjE0LjAuMBokCh9vZW1fY3J5cHRvX3NlY3VyaXR5X3BhdGNoX2xldmVsEgEwMg4QASAAKA0wAEAASABQAA==')


def apple_music_add_account(file_path):
    with open(file_path, 'r') as file:
        first_line = file.readline().strip()
        if first_line != '# Netscape HTTP Cookie File':
            logger.info("The file is not a valid Netscape cookie file.")
            return False

        cookie_lines = file.readlines()

    cfg_copy = config.get('accounts').copy()
    login_dict = {}

    # Process each line to gather cookies
    for line in cookie_lines[1:]:  # Skip the header line
        parts = line.strip().split('\t')

        if len(parts) >= 7:  # Ensure there are enough parts
            name = parts[5]  # Cookie name
            value = parts[6]  # Cookie value

            # Add each cookie name-value pair to the login dictionary
            login_dict[name] = value

    new_user = {
        "uuid": str(uuid.uuid4()),
        "service": "apple_music",
        "active": True,
        "login": login_dict
    }
    cfg_copy.append(new_user)
    config.set_('accounts', cfg_copy)
    config.update()
    return True


def apple_music_login_user(account):
    try:
        session = requests.Session()
        session.cookies.update(account['login'])
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0",
                "Accept": "application/json",
                "Accept-Language": 'en-US',
                "Accept-Encoding": "gzip, deflate, br",
                "content-type": "application/json",
                "Media-User-Token": session.cookies.get_dict().get("media-user-token", ""),
                "x-apple-renewal": "true",
                "DNT": "1",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-site",
                "origin": "https://music.apple.com",
            }
        )

        # Retrieve token from the homepage
        home_page = session.get("https://beta.music.apple.com").text
        index_js_uri = re.search(r"/(assets/index-legacy-[^/]+\.js)", home_page).group(1)
        index_js_page = session.get(f"https://beta.music.apple.com/{index_js_uri}").text
        token = re.search('(?=eyJh)(.*?)(?=")', index_js_page).group(1)
        session.headers.update({"authorization": f"Bearer {token}"})
        session.params = {"l": 'en-US'}

        account_pool.append({
            "uuid": account['uuid'],
            "username": account['login']['pltvcid'],
            "service": "apple_music",
            "status": "active",
            "account_type": "premium",
            "bitrate": "256k",
            "login": {
                "session": session
            }
        })
        return True
    except Exception as e:
        logger.error(f"Unknown Exception: {str(e)}")
        account_pool.append({
            "uuid": account['uuid'],
            "username": account['login']['pltvcid'],
            "service": "apple_music",
            "status": "error",
            "account_type": "N/A",
            "bitrate": "N/A",
            "login": {
                "session": ""
            }
        })
        return False


def apple_music_get_token(parsing_index):
    return account_pool[parsing_index]['login']['session']


def apple_music_get_search_results(session, search_term, content_types):
    search_types = []
    if 'track' in content_types:
        search_types.append('songs')
    if 'album' in content_types:
        search_types.append('albums')
    if 'artist' in content_types:
        search_types.append('artists')
    if 'playlist' in content_types:
        search_types.append('playlists')

    params = {}
    params['term'] = search_term
    params['limit'] = config.get("max_search_results")
    params['types'] = ",".join(search_types)

    results = make_call(f"{BASE_URL}/catalog/{session.cookies.get("itua")}/search", params=params, session=session, skip_cache=True)

    search_results = []
    for result in results['results']:

        if result == 'songs':
            for track in results['results']['songs']['data']:
                search_results.append({
                    'item_id': track['id'],
                    'item_name': track['attributes']['name'],
                    'item_by': track['attributes']['artistName'],
                    'item_type': "track",
                    'item_service': "apple_music",
                    'item_url': track['attributes']['url'],
                    'item_thumbnail_url': track.get("attributes", {}).get("artwork", {}).get("url", "").replace("{w}", "160").replace("{h}", "160")
                })

        if result == 'albums':
            for album in results['results']['albums']['data']:
                search_results.append({
                    'item_id': album['id'],
                    'item_name': album['attributes']['name'],
                    'item_by': album['attributes']['artistName'],
                    'item_type': "album",
                    'item_service': "apple_music",
                    'item_url': album['attributes']['url'],
                    'item_thumbnail_url': album.get("attributes", {}).get("artwork", {}).get("url", "").replace("{w}", "160").replace("{h}", "160")
                })

        if result == 'artists':
            for artist in results['results']['artists']['data']:
                search_results.append({
                    'item_id': artist['id'],
                    'item_name': artist['attributes']['name'],
                    'item_by': artist['attributes']['name'],
                    'item_type': "artist",
                    'item_service': "apple_music",
                    'item_url': artist['attributes']['url'],
                    'item_thumbnail_url': artist.get("attributes", {}).get("artwork", {}).get("url", "").replace("{w}", "160").replace("{h}", "160")
                })

        if result == 'playlists':
            for playlist in results['results']['playlists']['data']:
                search_results.append({
                    'item_id': playlist['id'],
                    'item_name': playlist['attributes']['name'],
                    'item_by': playlist['attributes'].get('curatorName', ''),
                    'item_type': "playlist",
                    'item_service': "apple_music",
                    'item_url': playlist['attributes']['url'],
                    'item_thumbnail_url': playlist.get("attributes", {}).get("artwork", {}).get("url", "").replace("{w}", "160").replace("{h}", "160")
                })

    return search_results


def apple_music_get_track_metadata(session, item_id):
    params = {}
    params['include'] = 'lyrics'
    track_data = make_call(f'{BASE_URL}/catalog/{session.cookies.get("itua")}/songs/{item_id}', params=params, session=session)
    album_id = track_data.get('data', [])[0].get('relationships', {}).get('albums', {}).get('data', [])[0].get('id', {})
    album_data = make_call(f'{BASE_URL}/catalog/{session.cookies.get("itua")}/albums/{album_id}', session=session)

    # Artists
    artists = []
    for artist in track_data.get('data', [])[0].get('attributes', {}).get('artistName', '').replace("&", ",").split(","):
        artists.append(artist.strip())

    # Track Number
    track_number = None
    for i, track in enumerate(album_data.get('data', [])[0].get('relationships', {}).get('tracks', {}).get('data', [])):
        if track.get('id', '') == str(item_id):
            track_number = i + 1
            break
    if not track_number:
        track_number = track_data.get('data', [])[0].get('attributes', {}).get('trackNumber', '')

    # Total Discs
    total_discs = album_data.get('data', [])[0].get('relationships', {}).get('tracks', {}).get('data', [])[-1].get('attributes', {}).get('discNumber', '')

    info = {}
    info['item_id'] = track_data.get('data', [])[0].get('id', '')
    info['album_name'] = track_data.get('data', [])[0].get('attributes', {}).get('albumName', '')
    info['genre'] = conv_list_format(track_data.get('data', [])[0].get('attributes', {}).get('genreNames', []))
    #info['track_number'] = track_data.get('data', [])[0].get('attributes', {}).get('trackNumber', '')
    info['release_year'] = track_data.get('data', [])[0].get('attributes', {}).get('releaseDate', '').split('-')[0]
    info['length'] = str(track_data.get('data', [])[0].get('attributes', {}).get('durationInMillis', ''))
    info['isrc'] = track_data.get('data', [])[0].get('attributes', {}).get('isrc', '')

    image_url = track_data.get('data', [])[0].get('attributes', {}).get('artwork', {}).get('url', '')
    max_height = track_data.get('data', [])[0].get('attributes', {}).get('artwork', {}).get('height', '')
    max_width = track_data.get('data', [])[0].get('attributes', {}).get('artwork', {}).get('width', '')
    info['image_url'] = image_url.replace("{w}", str(max_width)).replace("{h}", str(max_height))

    info['writer'] = track_data.get('data', [])[0].get('attributes', {}).get('composerName', '')
    info['language'] = track_data.get('data', [])[0].get('attributes', {}).get('audioLocale', '')
    info['item_url'] = track_data.get('data', [])[0].get('attributes', {}).get('url', '')
    info['is_playable'] = True if track_data.get('data', [])[0].get('attributes', {}).get('playParams', '') else False
    info['disc_number'] = track_data.get('data', [])[0].get('attributes', {}).get('discNumber', '')
    info['title'] = track_data.get('data', [])[0].get('attributes', {}).get('name', '')
    info['explicit'] = True if track_data.get('data', [])[0].get('attributes', {}).get('contentRating', '') == 'explicit' else False
    info['artists'] = conv_list_format(artists)

    info['copyright'] = album_data.get('data', [])[0].get('attributes', {}).get('copyright', '')
    info['upc'] = album_data.get('data', [])[0].get('attributes', {}).get('upc', '')
    info['label'] = album_data.get('data', [])[0].get('attributes', {}).get('recordLabel', '')
    info['total_tracks'] = album_data.get('data', [])[0].get('attributes', {}).get('trackCount', '')

    album_type = 'album'
    if album_data.get('data', [])[0].get('attributes', {}).get('isSingle', ''):
        album_type = 'single'
    if album_data.get('data', [])[0].get('attributes', {}).get('isCompilation', ''):
        album_type = 'compilation'
    info['album_type'] = album_type

    info['album_artists'] = artists[0]

    info['track_number'] = track_number
    info['total_discs'] = total_discs

    return info


def apple_music_get_lyrics(session, item_id, item_type, metadata, filepath):
    params = {}
    params['include'] = 'lyrics'
    track_data = make_call(f'{BASE_URL}/catalog/{session.cookies.get("itua")}/songs/{item_id}', params=params, session=session)

    time_synced = track_data.get('data', [])[0].get('attributes', {}).get('hasTimeSyncedLyrics', '')
    if config.get('only_synced_lyrics') and not time_synced:
        return False

    if len(track_data.get('data', [])[0].get('relationships', {}).get('lyrics', {}).get('data', [])):
        ttml_data = track_data.get('data', [])[0].get('relationships', {}).get('lyrics', {}).get('data', [])[0].get('attributes', {}).get('ttml', '')
        lyrics_list = []

        if config.get("embed_branding"):
            lyrics_list.append('[re:OnTheSpot]')

        for key in metadata.keys():
            value = metadata[key]

            if key in ['title', 'track_title', 'tracktitle'] and config.get("embed_name"):
                lyrics_list.append(f'[ti:{value}]')

            elif key == 'artists' and config.get("embed_artist"):
                lyrics_list.append(f'[ar:{value}]')

            elif key in ['album_name', 'album'] and config.get("embed_album"):
                lyrics_list.append(f'[al:{value}]')

            elif key in ['writers'] and config.get("embed_writers"):
                lyrics_list.append(f'[au:{value}]')

        if config.get("embed_length"):
            l_ms = int(metadata['length'])
            if round((l_ms/1000)/60) < 10:
                digit="0"
            else:
                digit=""
            lyrics_list.append(f'[length:{digit}{round((l_ms/1000)/60)}:{round((l_ms/1000)%60)}]\n')

        default_length = len(lyrics_list)

        for p in ET.fromstring(ttml_data.replace('`', '')).findall('.//{http://www.w3.org/ns/ttml}p'):
            begin_time = p.attrib.get('begin')
            lyric = p.text
            if lyric:
                if time_synced:
                    if ':' in begin_time:
                        time_parts = begin_time.split(':')
                        if len(time_parts) == 3:  # Format: HH:MM:SS.mmm
                            hours, minutes, seconds = time_parts
                            seconds, milliseconds = seconds.split('.')
                            minutes = int(minutes) + (int(hours) * 60)
                        elif len(time_parts) == 2:  # Format: MM:SS.mmm
                            minutes, seconds = time_parts
                            seconds, milliseconds = seconds.split('.')
                            hours = '0'
                    else: # Format: SS.mmm
                        seconds, milliseconds = begin_time.split('.')
                        minutes = '0'
                    formatted_time = f"{int(minutes):02}:{int(seconds):02}.{int(milliseconds.replace('s', ''))}"
                    lyric = f'[{formatted_time}] {lyric}'

                lyrics_list.append(lyric)

        merged_lyrics = '\n'.join(lyrics_list)
        if len(merged_lyrics) <= default_length:
            return False

        if config.get('use_lrc_file'):
            with open(filepath + '.lrc', 'w', encoding='utf-8') as f:
                f.write(merged_lyrics)
        if config.get('embed_lyrics'):
            return {"lyrics": merged_lyrics}
        else:
            return False


def apple_music_get_webplayback_info(session, item_id):
    json = {}
    json['salableAdamId'] = item_id  # Corrected variable name from track_id to item_id
    webplayback_info = session.post('https://play.itunes.apple.com/WebObjects/MZPlay.woa/wa/webPlayback', json=json).json()
    return webplayback_info.get("songList")[0]


def apple_music_get_decryption_key(session, stream_url, item_id):
    # Extract the PSSH (Protection System Specific Header) from the m3u8 object
    m3u8_obj = m3u8.load(stream_url)
    pssh = m3u8_obj.keys[0].uri if m3u8_obj.keys else None

    try:
        widevine_pssh_data = WidevinePsshData()
        widevine_pssh_data.algorithm = 1
        widevine_pssh_data.key_ids.append(base64.b64decode(pssh.split(",")[1]))

        pssh_obj = PSSH(widevine_pssh_data.SerializeToString())
        cdm = Cdm.from_device(Device.loads(WVN_KEY))

        cdm_session = cdm.open()
        challenge = base64.b64encode(
            cdm.get_license_challenge(cdm_session, pssh_obj)
        ).decode()

        json = {}
        json['challenge'] = challenge
        json['key-system'] = 'com.widevine.alpha'
        json['uri'] = pssh
        json['adamId'] = item_id
        json['isLibrary'] = False
        json['user-initiated'] = True

        license_data = session.post(WVN_LICENSE_URL, json=json).json()

        wvn_license = license_data.get("license", '')

        cdm.parse_license(cdm_session, wvn_license)
        decryption_key = next(
            key for key in cdm.get_keys(cdm_session) if key.type == "CONTENT"
        ).key.hex()

    finally:
        cdm.close(cdm_session)

    return decryption_key


def apple_music_get_album_track_ids(session, album_id):
    logger.info(f"Getting tracks from album: {album_id}")
    album_data = make_call(f'{BASE_URL}/catalog/{session.cookies.get("itua")}/albums/{album_id}', session=session)
    item_ids = []
    for track in album_data.get('data', [])[0].get('relationships', {}).get('tracks', {}).get('data', []):
        if track['type'] == 'songs':
            item_ids.append(track['id'])
    return item_ids


def apple_music_get_artist_album_ids(session, artist_id):
    logger.info(f"Getting album ids for artist: '{artist_id}'")

    params = {}
    params['include'] = 'albums'
    params['views'] = 'full-albums,singles,live-albums'

    album_data = make_call(f'{BASE_URL}/catalog/{session.cookies.get("itua")}/artists/{artist_id}', params=params, session=session)

    item_ids = []
    for album in album_data.get('data', [])[0].get('relationships', {}).get('albums', {}).get('data', []):
        item_ids.append(album.get("id", ''))
    return item_ids


def apple_music_get_playlist_data(session, playlist_id):
    logger.info(f"Get playlist data for playlist: {playlist_id}")
    playlist_data = make_call(f"{BASE_URL}/catalog/{session.cookies.get("itua")}/playlists/{playlist_id}", session=session, skip_cache=True)

    playlist_name = playlist_data.get('data', [])[0].get('attributes', {}).get('name', '')
    playlist_by =  playlist_data.get('data', [])[0].get('attributes', {}).get('curatorName', '')

    track_ids = []
    for track in playlist_data.get('data', [])[0].get('relationships', {}).get('tracks', {}).get('data', []):
        track_ids.append(track['id'])
    return playlist_name, playlist_by, track_ids
