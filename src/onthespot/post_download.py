import os
import subprocess
from pathlib import Path
from io import BytesIO
import requests
from PIL import Image
from .otsconfig import config
from .runtimedata import get_logger

logger = get_logger("worker.media")


def convert_audio_format(filename, metadata, bitrate, default_format):
    if os.path.isfile(os.path.abspath(filename)):
        target_path = Path(filename)
        filetype = target_path.suffix
        temp_name = os.path.join(
            target_path.parent, "."+target_path.stem
            )
        if os.path.isfile(temp_name):
            os.remove(temp_name)
        os.rename(filename, temp_name)
        # Prepare default parameters
        # Existing command initialization
        command = [
            config.get('_ffmpeg_bin_path'),
            '-i', temp_name
        ]

        # Set log level based on environment variable
        if int(os.environ.get('SHOW_FFMPEG_OUTPUT', 0)) == 0:
            command = command + ['-loglevel', 'error', '-hide_banner', '-nostats']

        # Fetch thumbnail
        if config.get('save_album_cover') or config.get('embed_cover'):
            image_path = os.path.join(os.path.dirname(filename), 'cover')
            image_path += "." + config.get("album_cover_format")
            logger.info(f"Fetching item thumbnail")
            img = Image.open(BytesIO(requests.get(metadata['image_url']).content))
            buf = BytesIO()
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(buf, format=config.get("album_cover_format"))
            buf.seek(0)

            with open(image_path, 'wb') as cover:
                cover.write(buf.read())
            if config.get('embed_cover') and filetype != '.wav':
                command += [
                    '-i', image_path, '-map', '0:a', '-map', '1:v', '-metadata:s:v:0', 'comment=Cover (front)'
                    ]
                if filetype == '.flac':
                    command += ['-disposition:v', 'attached_pic']
                else:
                    command += ['-disposition:v:1', 'attached_pic']

        # Check if media format is service default
        if filetype == default_format:
            command = command + ['-c:a', 'copy']
        else:
            command = command + ['-ar', '44100', '-ac', '2', '-b:a', bitrate]

        # Add user defined parameters
        for param in config.get('ffmpeg_args'):
            command.append(param)

        # Append metadata
        for key in metadata.keys():
            value = metadata[key]

            if key == 'artists' and config.get("embed_artist"):
                command += ['-metadata', 'artist={}'.format(value)]

            elif key in ['album_name', 'album'] and config.get("embed_album"):
                command += ['-metadata', 'album={}'.format(value)]

            elif key in ['album_artists'] and config.get("embed_albumartist"):
                if filetype == '.mp3':
                    command += ['-metadata', 'TPE2={}'.format(value)]
                else:
                    command += ['-metadata', 'album_artist={}'.format(value)]

            elif key in ['title', 'track_title', 'tracktitle'] and config.get("embed_name"):
                command += ['-metadata', 'title={}'.format(value)]

            elif key in ['year', 'release_year'] and config.get("embed_year"):
                command += ['-metadata', 'date={}'.format(value)]

            elif key in ['discnumber', 'disc_number', 'disknumber', 'disk_number'] and config.get("embed_discnumber"):
                command += ['-metadata', 'disc={}/{}'.format(value, metadata['total_discs'])]

            elif key in ['track_number', 'tracknumber'] and config.get("embed_tracknumber"):
                command += ['-metadata', 'track={}/{}'.format(value, metadata['total_tracks'])]

            elif key == 'genre' and config.get("embed_genre"):
                command += ['-metadata', 'genre={}'.format(value)]

            elif key == 'performers' and config.get("embed_performers"):
                command += ['-metadata', 'performer={}'.format(value)]

            elif key == 'producers' and config.get("embed_producers"):
                if filetype == '.mp3':
                    command += ['-metadata', 'TIPL={}'.format(value)]
                else:
                    command += ['-metadata', 'producer={}'.format(value)]

            elif key == 'writers' and config.get("embed_writers"):
                if filetype == '.mp3':
                    command += ['-metadata', 'TOLY={}'.format(value)]
                else:
                    command += ['-metadata', 'author={}'.format(value)]

            elif key == 'label' and config.get("embed_label"):
                if filetype == '.mp3':
                    command += ['-metadata', 'publisher={}'.format(value)]

            elif key == 'copyright' and config.get("embed_copyright"):
                command += ['-metadata', 'copyright={}'.format(value)]

            elif key == 'description' and config.get("embed_description"):
                if filetype == '.mp3':
                    command += ['-metadata', 'COMM={}'.format(value)]
                else:
                    command += ['-metadata', 'comment={}'.format(value)]

            elif key == 'language' and config.get("embed_language"):
                if filetype == '.mp3':
                    command += ['-metadata', 'TLAN={}'.format(value)]
                else:
                    command += ['-metadata', 'language={}'.format(value)]

            elif key == 'isrc' and config.get("embed_isrc"):
                if filetype == '.mp3':
                    command += ['-metadata', 'TSRC={}'.format(value)]
                else:
                    command += ['-metadata', 'isrc={}'.format(value)]

            elif key == 'length' and config.get("embed_length"):
                if filetype == '.mp3':
                    command += ['-metadata', 'TLEN={}'.format(value)]
                else:
                    command += ['-metadata', 'length={}'.format(value)]

            elif key == 'bpm' and config.get("embed_bpm"):
                if filetype == '.mp3':
                    command += ['-metadata', 'TBPM={}'.format(value)]
                if filetype == '.m4a':
                    command += ['-metadata', 'tmpo={}'.format(value)]
                else:
                    command += ['-metadata', 'bpm={}'.format(value)]

            elif key == 'key' and config.get("embed_key"):
                if filetype == '.mp3':
                    command += ['-metadata', 'TKEY={}'.format(value)]
                else:
                    command += ['-metadata', 'initialkey={}'.format(value)]

            elif key == 'album_type' and config.get("embed_compilation"):
                command += ['-metadata', 'compilation={}'.format(int(value == 'compilation'))]

            elif key == 'item_url' and config.get("embed_url"):
                if filetype == '.mp3':
                    command += ['-metadata', 'WOAS={}'.format(value)]
                else:
                    command += ['-metadata', 'website={}'.format(value)]

            elif key == 'explicit' and config.get("embed_explicit"):
                if filetype == '.mp3':
                    command += ['-metadata', 'ITUNESADVISORY={}'.format(value)]
                else:
                    command += ['-metadata', 'explicit={}'.format(value)]

            elif key == 'lyrics' and config.get("embed_lyrics"):
                command += ['-metadata', 'lyrics={}'.format(value)]

            elif key == 'time_signature' and config.get("embed_timesignature"):
                command += ['-metadata', 'timesignature={}'.format(value)]

            elif key == 'acousticness' and config.get("embed_acousticness"):
                command += ['-metadata', 'acousticness={}'.format(value)]

            elif key == 'danceability' and config.get("embed_danceability"):
                command += ['-metadata', 'danceability={}'.format(value)]

            elif key == 'instrumentalness' and config.get("embed_instrumentalness"):
                command += ['-metadata', 'instrumentalness={}'.format(value)]

            elif key == 'liveness' and config.get("embed_liveness"):
                command += ['-metadata', 'liveness={}'.format(value)]

            elif key == 'loudness' and config.get("embed_loudness"):
                command += ['-metadata', 'loudness={}'.format(value)]

            elif key == 'speechiness' and config.get("embed_speechiness"):
                command += ['-metadata', 'speechiness={}'.format(value)]

            elif key == 'energy' and config.get("embed_energy"):
                command += ['-metadata', 'energy={}'.format(value)]

            elif key == 'valence' and config.get("embed_valence"):
                command += ['-metadata', 'valence={}'.format(value)]

        # Add output parameter at last
        command.append(filename)
        logger.info(
            f'Converting media with ffmpeg. Built commandline {command}'
            )
        # Run subprocess with CREATE_NO_WINDOW flag on Windows
        if os.name == 'nt':
            subprocess.check_call(command, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            subprocess.check_call(command, shell=False)
        os.remove(temp_name)
        if not config.get('save_album_cover'):
            os.remove(image_path)
    else:
        raise FileNotFoundError
