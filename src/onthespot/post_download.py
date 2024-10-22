import os
import subprocess
import requests
from pathlib import Path
from PIL import Image
from io import BytesIO
from mutagen import File
from mutagen.easyid3 import EasyID3, ID3
from mutagen.flac import Picture, FLAC
from mutagen.id3 import APIC, TXXX, USLT, WOAS
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis
from .otsconfig import config
from .runtimedata import get_logger

logger = get_logger("worker.media")


def convert_audio_format(filename, bitrate, default_format):
    if os.path.isfile(os.path.abspath(filename)):
        target_path = Path(filename)
        temp_name = os.path.join(
            target_path.parent, ".~"+target_path.stem
            )
        print(temp_name)
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
        if target_path.suffix == default_format:
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

        elif key in ['title', 'track_title', 'tracktitle'] and config.get("embed_name"):
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
            tags['comment'] = str(value)

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



    for key in metadata.keys():
        value = metadata[key]

        if key == 'item_url' and config.get("embed_url"):
            if filetype == '.mp3':
                tags.add(WOAS(value))
            elif filetype == '.m4a':
                tags['\xa9web'] = value
            else:
                tags['website'] = value

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
    logger.info(f"Fetch thumbnail at '{image_url}'")
    img = Image.open(BytesIO(requests.get(image_url).content))
    buf = BytesIO()
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img.save(buf, format=config.get("album_cover_format"))
    buf.seek(0)

    if config.get("embed_cover") and not config.get("force_raw"):
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

