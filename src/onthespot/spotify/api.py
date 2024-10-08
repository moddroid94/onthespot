import base64
import os
import re
import string
import subprocess
from ..exceptions import *
import requests.adapters
from ..otsconfig import config
import requests
import json
from mutagen import File
from mutagen.easyid3 import EasyID3, ID3
from mutagen.flac import Picture, FLAC
from mutagen.id3 import APIC, TXXX, USLT, WOAS
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from pathlib import Path
from PIL import Image
from io import BytesIO
from hashlib import md5
from ..runtimedata import get_logger
from librespot.audio.decoders import AudioQuality

logger = get_logger("spotutils")
requests.adapters.DEFAULT_RETRIES = 10

def play_media(session, media_id, media_type):
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

def get_artist_albums(session, artist_id):
    logger.info(f"Get albums for artist by id '{artist_id}'")
    access_token = session.tokens().get("user-read-email")
    resp = make_call(f'https://api.spotify.com/v1/artists/{artist_id}/albums?include_groups=album%2Csingle%2Cappears_on%2Ccompilation&limit=50', token=access_token)
    return [resp['items'][i]['id'] for i in range(len(resp['items']))]


def get_playlist_data(session, playlist_id):
    logger.info(f"Get playlist dump for '{playlist_id}'")
    access_token = session.tokens().get("user-read-email")
    resp = make_call(f'https://api.spotify.com/v1/playlists/{playlist_id}', token=access_token, skip_cache=True)
    return resp['name'], resp['owner']['display_name'], resp['description'], resp['external_urls']['spotify']


def get_track_lyrics(session, track_id, metadata, forced_synced):
    lyrics = []
    try:
        url = f'https://spclient.wg.spotify.com/color-lyrics/v2/track/{track_id}'
        token = session.tokens().get("user-read-email")
        params = 'format=json&market=from_token'

        headers = {
        'app-platform': 'WebPlayer',
        'Authorization': f'Bearer {token}',
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.90 Safari/537.36"
        }

        resp = make_call(url, token, headers=headers, params=params)

        for key in metadata.keys():
            value = metadata[key]
            if key == 'artists':
                artist = conv_list_format(value)
            elif key in ['name', 'track_title', 'tracktitle']:
                tracktitle = value
            elif key in ['album_name', 'album']:
                album = value
            elif key in ['writers']:
                author = conv_list_format(value)
        l_ms = metadata['length']
        if config.get("embed_branding"):
            lyrics.append('[re:OnTheSpot]')
        if config.get("embed_name"):
            lyrics.append(f'[ti:{tracktitle}]')
        if config.get("embed_writers"):
            lyrics.append(f'[au:{author}]')
        if config.get("embed_artist"):
            lyrics.append(f'[ar:{artist}]')
        if config.get("embed_album"):
            lyrics.append(f'[al:{album}]')
        lyrics.append(f'[by:{resp["lyrics"]["provider"]}]')
        if config.get("embed_length"):
            if round((l_ms/1000)/60) < 10:
                digit="0"
            else:
                digit=""
            lyrics.append(f'[length:{digit}{round((l_ms/1000)/60)}:{round((l_ms/1000)%60)}]\n')
        if resp["lyrics"]["syncType"] == "LINE_SYNCED":
            for line in resp["lyrics"]["lines"]:
                minutes, seconds = divmod(int(line['startTimeMs']) / 1000, 60)
                lyrics.append(f'[{minutes:0>2.0f}:{seconds:05.2f}] {line["words"]}')
        else:
            # It's un synced lyrics, if not forcing synced lyrics return it
            if not forced_synced:
                lyrics = [line['words'][0]['string'] for line in resp['lines']]
    except (KeyError, IndexError):
        logger.error(f'KeyError/Index Error. Failed to get lyrics for track id: {track_id}, ')
    return None if len(lyrics) <= 2 else {"lyrics": '\n'.join(lyrics), "language": resp["lyrics"]["language"]}


def get_tracks_from_playlist(session, playlist_id):
    logger.info(f"Get tracks from playlist by id '{playlist_id}'")
    songs = []
    access_token = session.tokens().get("user-read-email")
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks?additional_types=episode'
    while url:
        resp = make_call(url, token=access_token, skip_cache=True)
        songs.extend(resp['items'])
        url = resp['next']
    return songs


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


def get_album_tracks(session, album_id):
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


def convert_audio_format(filename, quality):
    if os.path.isfile(os.path.abspath(filename)):
        target_path = Path(filename)
        bitrate = "320k" if quality == AudioQuality.VERY_HIGH else "160k"
        temp_name = os.path.join(
            target_path.parent, ".~"+target_path.stem+".ogg"
            )
        if os.path.isfile(temp_name):
            os.remove(temp_name)
        os.rename(filename, temp_name)
        # Prepare default parameters
        command = [
            config.get('_ffmpeg_bin_path'),
            '-i', temp_name
        ]
        # If the media format is set to ogg, just correct the downloaded file
        # and add tags
        if target_path.suffix == '.ogg':
            command = command + ['-c', 'copy']
        else:
            command = command + ['-ar', '44100', '-ac', '2', '-b:a', bitrate]
        if int(os.environ.get('SHOW_FFMPEG_OUTPUT', 0)) == 0:
            command = command + \
                ['-loglevel', 'error', '-hide_banner', '-nostats']
        # Add user defined parameters
        for param in config.get('ffmpeg_args'):
            command.append(param)
        # Add output parameter at last
        command.append(
                filename
            )
        logger.info(
            f'Converting media with ffmpeg. Built commandline {command}'
            )
        # Run subprocess with CREATE_NO_WINDOW flag on Windows
        if os.name == 'nt':
            subprocess.check_call(command, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.check_call(command, shell=False)
        os.remove(temp_name)
    else:
        raise FileNotFoundError


def conv_list_format(items):
    formatted = ""
    for item in items:
        formatted += item + config.get('metadata_seperator')
    return formatted[:-2].strip()


def set_audio_tags(filename, metadata, track_id_str):
    logger.info(
        f"Setting tags for audio media at "
        f"'{filename}', mediainfo -> '{metadata}'"
        )
    type_ = 'track'
    filetype = Path(filename).suffix
    if filetype == '.mp3':
        tags = EasyID3(filename)
    else:
        tags = File(filename)
    if config.get("embed_branding"):
        branding = "Downloaded by OnTheSpot, https://github.com/justin025/onthespot"
        if filetype == '.mp3':
            EasyID3.RegisterTextKey('comment', 'COMM')
            tags['comment'] = branding
        if filetype == '.m4a':
            tags['\xa9cmt'] = branding
        else:
            tags['comment'] = branding
    for key in metadata.keys():
        value = metadata[key]

        if key == 'artists' and config.get("embed_artist"):
            if filetype == '.m4a':
                tags['\xa9ART'] = conv_list_format(value)
            else:
                tags['artist'] = conv_list_format(value)

        elif key in ['album_name', 'album'] and config.get("embed_album"):
            if filetype == '.m4a':
                tags['\xa9alb'] = value
            else:
                tags['album'] = value

        elif key in ['album_artists'] and config.get("embed_albumartist"):
            if filetype == '.m4a':
                tags['\xa9art'] = value
            else:
                tags['albumartist'] = value

        elif key in ['name', 'track_title', 'tracktitle'] and config.get("embed_name"):
            if filetype == '.m4a':
                tags['\xa9nam'] = value
            else:
                tags['title'] = value

        elif key in ['year', 'release_year'] and config.get("embed_year"):
            if filetype == '.m4a':
                tags['\xa9day'] = value
            else:
                tags['date'] = value
        elif key in ['discnumber', 'disc_number', 'disknumber', 'disk_number'] and config.get("embed_discnumber"):
            if filetype == '.m4a':
                tags['\xa9dis'] = str(value) + '/' + str(metadata['total_discs'])
            else:
                # ID3 requires the format value/total, i.e. 3/10
                tags['discnumber'] = str(value) + '/' + str(metadata['total_discs'])
        elif key in ['track_number', 'tracknumber'] and config.get("embed_tracknumber"):
            if filetype == '.m4a':
                tags['trcn'] = str(value) + '/' + str(metadata['total_tracks'])
            else:
                # ID3 requires the format value/total, i.e. 3/10
                tags['tracknumber'] = str(value) + '/' + str(metadata['total_tracks'])

        elif key == 'genre' and config.get("embed_genre"):
            if 'Podcast' in value or 'podcast' in value:
                type_ = 'episode'
            if filetype == '.m4a':
                tags['\xa9gen'] = conv_list_format(value)
            else:
                tags['genre'] = conv_list_format(value)

        elif key == 'performers' and config.get("embed_performers"):
            tags['performer'] = conv_list_format(value)

        elif key == 'producers' and config.get("embed_producers"):
            if filetype == '.mp3':
                EasyID3.RegisterTextKey('producer', 'TIPL')
            tags['producer'] = conv_list_format(value)

        elif key == 'writers' and config.get("embed_writers"):
            tags['author'] = conv_list_format(value)

        elif key == 'label' and config.get("embed_label"):
            if filetype == '.mp3':
                EasyID3.RegisterTextKey('publisher', 'TPUB')
            tags['publisher'] = value

        elif key == 'copyright' and config.get("embed_copyright"):
            tags['copyright'] = conv_list_format(value)

        elif key == 'description' and config.get("embed_description"):
            if filetype == '.mp3':
                EasyID3.RegisterTextKey('comment', 'COMM')
            tags['comment'] = value

        elif key == 'language' and config.get("embed_language"):
            tags['language'] = value

        elif key == 'isrc' and config.get("embed_isrc"):
            tags['isrc'] = value

        elif key == 'length' and config.get("embed_length"):
            tags['length'] = str(value)

        elif key == 'bpm' and config.get("embed_bpm"):
            tags['bpm'] = str(value)

        elif key == 'key' and config.get("embed_key"):
            if filetype == '.mp3':
                EasyID3.RegisterTextKey('key', 'TKEY')
            tags['key'] = str(value)

        elif key == 'album_type' and config.get("embed_compilation"):
            if filetype == '.mp3':
                EasyID3.RegisterTextKey('compilation', 'TCMP')
            tags['compilation'] = f"{int(value == 'compilation')}"
    #tags['website'] = f'https://open.spotify.com/{type_}/{track_id_str}'
    #
    # The EasyID3 'website' tag is mapped to WOAR which according to ID3 is supposed to be the official artist/performer
    # webpage. Since we are mapping to a spotify track url two better options are WOAF (Official audio file webpage) and
    # WOAS (Official audio source webpage). WOAF is supposed to link to a file so WOAS was used below.
    # https://id3.org/id3v2.4.0-frames
    tags.save()

    if filetype == '.mp3':
        tags = ID3(filename)

    if config.get("embed_url"):
        url = f'https://open.spotify.com/{type_}/{track_id_str}'
        if filetype == '.mp3':
            tags.add(WOAS(url))
        elif filetype == '.m4a':
            tags['\xa9web'] = url
        else:
            tags['website'] = url

    for key in metadata.keys():
        value = metadata[key]

        if key == 'explicit' and config.get("embed_explicit"):
            if filetype == '.mp3':
                tags.add(TXXX(encoding=3, desc=u'ITUNESADVISORY', text=f"{value}"))
            elif filetype == '.m4a':
                tags['\xa9exp'] = f"{value}"
            else:
                tags['explicit'] = f"{value}"

        elif key == 'lyrics' and config.get("embed_lyrics"):
            # The following adds unsynced lyrics, not sure how to add synced lyrics (SYLT).
            if filetype == '.mp3':
                tags.add(USLT(encoding=3, lang=u'und', desc=u'desc', text=value))
            elif filetype == '.m4a':
                tags['\xa9lyr'] = value
            else:
                tags['lyrics'] = value

        elif key == 'time_signature' and config.get("embed_timesignature"):
            if filetype == '.mp3':
                tags.add(TXXX(encoding=3, desc=u'TIMESIGNATURE', text=str(value)))
            else:
                tags['TIMESIGNATURE'] = str(value)

        elif key == 'acousticness' and config.get("embed_acousticness"):
            if filetype == '.mp3':
                tags.add(TXXX(encoding=3, desc=u'ACOUSTICNESS', text=str(value)))
            else:
                tags['ACOUSTICNESS'] = str(value)

        elif key == 'danceability' and config.get("embed_danceability"):
            if filetype == '.mp3':
                tags.add(TXXX(encoding=3, desc=u'DANCEABILITY', text=str(value)))
            else:
                tags['DANCEABILITY'] = str(value)

        elif key == 'instrumentalness' and config.get("embed_instrumentalness"):
            if filetype == '.mp3':
                tags.add(TXXX(encoding=3, desc=u'INSTRUMENTALNESS', text=str(value)))
            else:
                tags['INSTRUMENTALNESS'] = str(value)

        elif key == 'liveness' and config.get("embed_liveness"):
            if filetype == '.mp3':
                tags.add(TXXX(encoding=3, desc=u'LIVENESS', text=str(value)))
            else:
                tags['LIVENESS'] = str(value)

        elif key == 'loudness' and config.get("embed_loudness"):
            if filetype == '.mp3':
                tags.add(TXXX(encoding=3, desc=u'LOUDNESS', text=str(value)))
            else:
                tags['LOUDNESS'] = str(value)

        elif key == 'speechiness' and config.get("embed_speechiness"):
            if filetype == '.mp3':
                tags.add(TXXX(encoding=3, desc=u'SPEECHINESS', text=str(value)))
            else:
                tags['SPEECHINESS'] = str(value)

        elif key == 'energy' and config.get("embed_energy"):
            if filetype == '.mp3':
                tags.add(TXXX(encoding=3, desc=u'ENERGY', text=str(value)))
            else:
                tags['ENERGY'] = str(value)

        elif key == 'valence' and config.get("embed_valence"):
            if filetype == '.mp3':
                tags.add(TXXX(encoding=3, desc=u'VALENCE', text=str(value)))
            else:
                tags['VALENCE'] = str(value)
    tags.save()


def set_music_thumbnail(filename, image_url):
    filetype = Path(filename).suffix
    if config.get("embed_cover"):
        logger.info(f"Set thumbnail for audio media at '{filename}' with '{image_url}'")
        img = Image.open(BytesIO(requests.get(image_url).content))
        buf = BytesIO()
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(buf, format=config.get("album_cover_format"))
        buf.seek(0)
        if filetype == '.mp3':
            tags = ID3(filename)
            tags['APIC'] = APIC(
                              encoding=3,
                              mime=f'image/{config.get("album_cover_format")}',
                              type=3, desc=u'Cover',
                              data=buf.read()
                            )
        elif filetype == '.flac':
            tags = FLAC(filename)
            picture = Picture()
            picture.data = buf.read()
            picture.type = 3
            picture.desc = "Cover"
            picture.mime = f"image/{config.get('album_cover_format')}"
            picture_data = picture.write()
            encoded_data = base64.b64encode(picture_data)
            vcomment_value = encoded_data.decode("ascii")
            tags["metadata_block_picture"] = [vcomment_value]
        elif filetype == '.ogg':
            tags = OggVorbis(filename)
            picture = Picture()
            picture.data = buf.read()
            picture.type = 3
            picture.desc = "Cover"
            picture.mime = f"image/{config.get('album_cover_format')}"
            picture_data = picture.write()
            encoded_data = base64.b64encode(picture_data)
            vcomment_value = encoded_data.decode("ascii")
            tags["metadata_block_picture"] = [vcomment_value]
        elif filetype == '.m4a':
            tags = MP4(filename)
            tags['covr'] = [MP4Cover(data=buf.read())]
        else:
            logger.info(f"Unsupported media type: {filetype}")
        tags.save()
    if config.get("save_album_cover"):
        cover_path = os.path.join(
            Path(filename).parent, 'cover' + "." + config.get('album_cover_format'))
        if not os.path.exists(cover_path):
            img.save(cover_path)

def search_by_term(session,
                   search_term,
                   max_results=20,
                   content_types=None) -> dict:
    results: dict = {
        "tracks": [],
        "albums": [],
        "playlists": [],
        "artists": [],
        "shows": [],
        "episodes": [],
        "audiobooks": [],
    }
    logger.info(
        f"Get search result for term '{search_term}', max items '{max_results}'"
        )
    if search_term.strip() == "":
        logger.warning(f"Returning empty data as query is empty !")
        return results
    if content_types is None:
        content_types = ["track", "album", "playlist", "artist", "show", "episode", "audiobook"]
    token = session.tokens().get("user-read-email")
    resp = requests.get(
        "https://api.spotify.com/v1/search",
        {
            "limit": max_results,
            "offset": "0",
            "q": search_term,
            "type": ",".join(c_type for c_type in content_types)
        },
        headers={"Authorization": "Bearer %s" % token},
    )
    for c_type in content_types:
        results[c_type + "s"] = resp.json()[c_type + "s"]["items"]
    if len(results["tracks"]) + len(results["albums"]) + len(results["artists"]) + len(results["playlists"]) + len(results["shows"]) + len(results["episodes"]) + len(results["audiobooks"]) == 0:
        logger.warning(f"No results for term '{search_term}', max items '{max_results}'")
        raise EmptySearchResultException("No result found for search term '{}' ".format(search_term))
    else:
        return results


def check_premium(session):
    return bool(
        session.get_user_attribute("type") == "premium" or config.get("force_premium")
        )


def get_song_info(session, song_id):
    token = session.tokens().get("user-read-email")
    track_data = make_call(f'https://api.spotify.com/v1/tracks?ids={song_id}&market=from_token', token=token)
    credits_data = make_call(f'https://spclient.wg.spotify.com/track-credits-view/v0/experimental/{song_id}/credits', token=token)
    track_audio_data = make_call(f'https://api.spotify.com/v1/audio-features/{song_id}', token=token)
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
        info['name'] = track_data['tracks'][0]['name']
        info['image_url'] = get_thumbnail(track_data['tracks'][0]['album']['images'], preferred_size=640000)
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


def get_episode_info(session, episode_id_str):
    logger.info(f"Get episode info for episode by id '{episode_id_str}'")
    token = session.tokens().get("user-read-email")
    info = make_call("https://api.spotify.com/v1/episodes/" + episode_id_str, token=token)
    if "error" in info:
        return None, None, None
    else:
        return info["show"]["name"], info["name"], get_thumbnail(info['images']), info['release_date'], info['show']['total_episodes'], info['show']['publisher'], info['language'] if info['language'] != "" else info['show']['languages'][0], info['description'] if info['description'] != "" else info['show']['description'], info['show']['copyrights']


def get_show_episodes(session, show_id_str):
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
            episodes.append(episode["id"])

        if len(resp['items']) < limit:
            break

    return episodes


def get_thumbnail(image_dict, preferred_size=22500):
    images = {}
    for image in image_dict:
        try:
            images[image['height'] * image['width']] = image['url']
        except TypeError:
            # Some playlist and media item do not have cover images
            pass
    available_sizes = sorted(images)
    for size in available_sizes:
        if size >= preferred_size:
            return images[size]
    return images[available_sizes[-1]] if len(available_sizes) > 0 else ""

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
