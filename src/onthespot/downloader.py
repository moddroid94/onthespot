import os
import traceback
import time
import subprocess
import threading
import re
import requests
from PyQt6.QtCore import QObject, pyqtSignal
from librespot.audio.decoders import AudioQuality, VorbisOnlyAudioQuality
from librespot.metadata import TrackId, EpisodeId
from yt_dlp import YoutubeDL
from .runtimedata import get_logger, download_queue, download_queue_lock, account_pool, temp_download_path
from .otsconfig import config
from .utils import format_track_path, convert_audio_format, embed_metadata, set_music_thumbnail, fix_mp3_metadata, add_to_m3u_file, strip_metadata
from .api.spotify import spotify_get_track_metadata, spotify_get_episode_metadata, spotify_get_lyrics
from .api.soundcloud import soundcloud_get_track_metadata
from .api.deezer import deezer_get_track_metadata, get_song_info_from_deezer_website, genurlkey, calcbfkey, decryptfile
from .api.youtube import youtube_get_track_metadata
from .api.bandcamp import bandcamp_get_track_metadata
from .api.tidal import tidal_get_track_metadata, tidal_get_lyrics, tidal_get_file_url
from .accounts import get_account_token

logger = get_logger("downloader")


class DownloadWorker(QObject):
    progress = pyqtSignal(dict, str, int)
    def __init__(self, gui=False):
        super().__init__()
        self.gui = gui
        self.thread = threading.Thread(target=self.run)
        self.is_running = True


    def start(self):
        self.thread.start()


    def readd_item_to_download_queue(self, item):
        with download_queue_lock:
            try:
                local_id = item['local_id']
                del download_queue[local_id]
                download_queue[local_id] = item
                download_queue[local_id]['available'] = True
            except (KeyError):
                # Item likely cleared from queue
                return


    def run(self):
        while self.is_running:
            try:
                try:
                    if download_queue:
                        with download_queue_lock:

                            # Mark item as unavailable for other download workers
                            iterator = iter(download_queue)
                            while True:
                                local_id = next(iterator)
                                if download_queue[local_id]['available'] is False:
                                    continue
                                download_queue[local_id]['available'] = False
                                item = download_queue[local_id]
                                break
                    else:
                        time.sleep(0.2)
                        continue

                    item_service = item['item_service']
                    item_type = item['item_type']
                    item_id = item['item_id']

                    if item['item_status'] in (
                        "Cancelled",
                        "Failed",
                        "Unavailable",
                        "Downloaded",
                        "Already Exists",
                        "Deleted"
                    ):
                        time.sleep(0.2)
                        self.readd_item_to_download_queue(item)
                        continue
                except (RuntimeError, OSError, StopIteration):
                    time.sleep(0.2)
                    continue

                item['item_status'] = "Downloading"
                if self.gui:
                    self.progress.emit(item, self.tr("Downloading"), 1)

                token = get_account_token(item_service)

                try:
                    item_metadata = globals()[f"{item_service}_get_{item_type}_metadata"](token, item_id)
                    item_path = format_track_path(item, item_metadata)
                except (Exception, KeyError) as e:
                    logger.error(f"Failed to fetch metadata for '{item_id}', Error: {str(e)}\nTraceback: {traceback.format_exc()}")
                    item['item_status'] = "Failed"
                    self.tr("Failed")
                    if self.gui:
                        self.progress.emit(item, self.tr("Failed"), 0)
                    self.readd_item_to_download_queue(item)
                    continue

                dl_root = config.get("download_root")
                if temp_download_path:
                    dl_root = temp_download_path[0]
                file_path = os.path.join(dl_root, item_path)
                directory, file_name = os.path.split(file_path)
                temp_file_path = os.path.join(directory, '~' + file_name)

                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Skip download if file exists under different extension
                file_directory = os.path.dirname(file_path)
                base_filename = os.path.basename(file_path)

                for entry in os.listdir(file_directory):
                    full_path = os.path.join(file_directory, entry)  # Construct the full file path

                    # Check if the entry is a file and if its name matches the base filename
                    if os.path.isfile(full_path) and os.path.splitext(entry)[0] == base_filename and os.path.splitext(entry)[1] != '.lrc':

                        item['file_path'] = os.path.join(file_directory, entry)

                        if config.get('overwrite_existing_metadata'):

                            logger.info('Overwriting Existing Metadata')

                            # Lyrics
                            if item_service in ("spotify", "tidal"):
                                item['item_status'] = 'Getting Lyrics'
                                if self.gui:
                                    self.progress.emit(item, self.tr("Getting Lyrics"), 99)
                                extra_metadata = globals()[f"{item_service}_get_lyrics"](token, item_id, item_type, item_metadata, file_path)
                                if isinstance(extra_metadata, dict):
                                    item_metadata.update(extra_metadata)

                            strip_metadata(item)
                            embed_metadata(item, item_metadata)

                            # Thumbnail
                            if config.get('save_album_cover') or config.get('embed_cover'):
                                item['item_status'] = 'Setting Thumbnail'
                                if self.gui:
                                    self.progress.emit(item, self.tr("Setting Thumbnail"), 99)
                                set_music_thumbnail(item['file_path'], item_metadata)

                            if os.path.splitext(item['file_path'])[1] == '.mp3':
                                fix_mp3_metadata(item['file_path'])

                        # M3U
                        if config.get('create_m3u_playlists') and item.get('parent_category') == 'playlist':
                            item['item_status'] = 'Adding To M3U'
                            if self.gui:
                                self.progress.emit(item, self.tr("Adding To M3U"), 1)
                                add_to_m3u_file(item, item_metadata)

                        if self.gui:
                            if item['item_status'] in ('Downloading', 'Setting Thumbnail', 'Adding To M3U'):
                                self.progress.emit(item, self.tr("Already Exists"), 100)
                        item['item_status'] = 'Already Exists'
                        logger.info(f"File already exists, Skipping download for track by id '{item_id}'")
                        time.sleep(0.2)
                        self.readd_item_to_download_queue(item)
                        break

                if item['item_status'] == 'Already Exists':
                    continue

                if not item_metadata['is_playable']:
                    logger.error(f"Track is unavailable, track id '{item_id}'")
                    item['item_status'] = 'Unavailable'
                    if self.gui:
                        self.progress.emit(item, self.tr("Unavailable"), 0)
                    self.readd_item_to_download_queue(item)
                    continue

                # Downloading the file here is necessary to animate progress bar through pyqtsignal.
                # Could at some point just update the item manually inside the api file by passing
                # item['gui']['progressbar'] and self.gui into a download_track function.
                try:
                    if item_service == "spotify":
                        # Check if selected account is the same item service and if not find one
                        parsing_index = config.get('parsing_acc_sn')
                        if account_pool[parsing_index]['service'] == item_service:
                            account = account_pool[parsing_index]['login']['session']
                        else:
                            for i in range(len(account_pool)):
                                index = (parsing_index + i + 1) % len(account_pool)
                                account = account_pool[index]
                                if account['service'] == item_service:
                                    account = account_pool[index]['login']['session']
                                    break

                        default_format = ".ogg"
                        temp_file_path += default_format
                        if item_type == "track":
                            audio_key = TrackId.from_base62(item_id)
                        elif item_type == "episode":
                            audio_key = EpisodeId.from_base62(item_id)

                        quality = AudioQuality.HIGH
                        bitrate = "160k"
                        if account.get_user_attribute("type") == "premium" and item_type == 'track':
                            quality = AudioQuality.VERY_HIGH
                            bitrate = "320k"

                        stream = account.content_feeder().load(audio_key, VorbisOnlyAudioQuality(quality), False, None)

                        total_size = stream.input_stream.size
                        downloaded = 0
                        _CHUNK_SIZE = config.get("chunk_size")

                        with open(temp_file_path, 'wb') as file:
                            while downloaded < total_size:
                                data = stream.input_stream.stream().read(_CHUNK_SIZE)
                                downloaded += len(data)
                                if len(data) != 0:
                                    file.write(data)
                                    if self.gui:
                                        self.progress.emit(item, self.tr("Downloading"), int((downloaded / total_size) * 100))
                                if len(data) == 0:
                                    break
                        stream.input_stream.stream().close()
                        stream_internal = stream.input_stream.stream()
                        del stream_internal, stream.input_stream

                    elif item_service == "soundcloud":
                        temp_file_path += default_format
                        # Don't know how to emit progress from ffmpeg
                        command = [config.get('_ffmpeg_bin_path'), "-loglevel", "error", "-i", f"{item_metadata['file_url']}", "-c", "copy", temp_file_path]
                        if os.name == 'nt':
                            subprocess.check_call(command, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                        else:
                            subprocess.check_call(command, shell=False)
                        bitrate = "128k"
                        default_format = ".mp3"

                    elif item_service == 'deezer':
                        song = get_song_info_from_deezer_website(item['item_id'])

                        song_quality = 1
                        song_format = 'MP3_128'
                        bitrate = "128k"
                        default_format = ".mp3"
                        if int(song.get("FILESIZE_FLAC")) > 0:
                            song_quality = 9
                            song_format ='FLAC'
                            bitrate = "1411k"
                            default_format = ".flac"
                        elif int(song.get("FILESIZE_MP3_320")) > 0:
                            song_quality = 3
                            song_format = 'MP3_320'
                            bitrate = "320k"
                        elif int(song.get("FILESIZE_MP3_256")) > 0:
                            song_quality = 5
                            song_format = 'MP3_256'
                            bitrate = "256k"
                        temp_file_path += default_format

                        headers = {
                            'Origin': 'https://www.deezer.com',
                            'Accept-Encoding': 'utf-8',
                            'Referer': 'https://www.deezer.com/login',
                        }

                        track_data = token.post(
                            "https://media.deezer.com/v1/get_url",
                            json={
                                'license_token': account_pool[config.get('parsing_acc_sn')]['login']['license_token'],
                                'media': [{
                                    'type': "FULL",
                                    'formats': [
                                        { 'cipher': "BF_CBC_STRIPE", 'format': song_format }
                                    ]
                                }],
                                'track_tokens': [song["TRACK_TOKEN"]]
                            },
                            headers = headers
                        ).json()

                        try:
                            url = track_data['data'][0]['media'][0]['sources'][0]['url']
                        except KeyError as e:
                            # Fallback to lowest quality
                            logger.error(f'Unable to select Deezer quality, falling back to 128kbps. Error: {str(e)}\nTraceback: {traceback.format_exc()}')
                            song_quality = 1
                            song_format = 'MP3_128'
                            bitrate = "128k"
                            default_format = ".mp3"
                            urlkey = genurlkey(song["SNG_ID"], song["MD5_ORIGIN"], song["MEDIA_VERSION"], song_quality)
                            url = "https://e-cdns-proxy-%s.dzcdn.net/mobile/1/%s" % (song["MD5_ORIGIN"][0], urlkey.decode())

                        file = requests.get(url, stream=True)

                        if file.status_code == 200:
                            total_size = int(file.headers.get('content-length', 0))
                            downloaded = 0
                            data_chunks = b''  # empty bytes object

                            for data in file.iter_content(chunk_size=config.get("chunk_size")):
                                downloaded += len(data)
                                data_chunks += data

                                if self.gui and downloaded != total_size:
                                    self.progress.emit(item, self.tr("Downloading"), int((downloaded / total_size) * 100))

                            key = calcbfkey(song["SNG_ID"])

                            if self.gui:
                                self.progress.emit(item, self.tr("Decrypting"), 99)
                            with open(temp_file_path, "wb") as fo:
                                decryptfile(data_chunks, key, fo)

                        else:
                            logger.info(f"Deezer download attempts failed: {file.status_code}")
                            item['item_status'] = "Failed"
                            if self.gui:
                                self.progress.emit(item, self.tr("Failed"), 0)
                            self.readd_item_to_download_queue(item)

                    elif item_service == "youtube":
                        def yt_dlp_progress_hook(self, item, d):
                            if self.gui:
                                progress_str = re.search(r'(\d+\.\d+)%', d['_percent_str'])
                                self.progress.emit(item, self.tr("Downloading"), round(float(progress_str.group(1))) - 1)
                        progress_hook = lambda d: yt_dlp_progress_hook(self, item, d)

                        with YoutubeDL({
                                'quiet': True,
                                'extract_audio': True,
                                'format': 'bestaudio',
                                'outtmpl': temp_file_path,
                                'progress_hooks': [progress_hook]
                            }) as video:

                            video.download(f'https://www.youtube.com/watch?v={item['item_id']}')
                            default_format = '.m4a'
                            bitrate = "256k"

                    elif item_service == "bandcamp":
                        response = requests.get(item_metadata['file_url'], stream=True)
                        total_size = int(response.headers.get('Content-Length', 0))
                        downloaded = 0
                        data_chunks = b''

                        with open(temp_file_path, 'wb') as file:
                            for data in response.iter_content(chunk_size=config.get("chunk_size", 1024)):
                                if data:
                                    downloaded += len(data)
                                    data_chunks += data
                                    file.write(data)

                                    if total_size > 0 and downloaded != total_size:
                                        if self.gui:
                                            self.progress.emit(item, self.tr("Downloading"), int((downloaded / total_size) * 100))
                        default_format = '.mp3'
                        bitrate = "128k"

                    elif item_service == "tidal":
                        file_url = tidal_get_file_url(token, item_id)
                        response = requests.get(file_url, stream=True)
                        total_size = int(response.headers.get('Content-Length', 0))
                        downloaded = 0
                        data_chunks = b''

                        with open(temp_file_path, 'wb') as file:
                            for data in response.iter_content(chunk_size=config.get("chunk_size", 1024)):
                                if data:
                                    downloaded += len(data)
                                    data_chunks += data
                                    file.write(data)

                                    if total_size > 0 and downloaded != total_size:
                                        if self.gui:
                                            self.progress.emit(item, self.tr("Downloading"), int((downloaded / total_size) * 100))
                        default_format = '.flac'
                        bitrate = "1411k"

                except RuntimeError as e:
                    # Likely Ratelimit
                    logger.info(f"Download failed: {item}, Error: {str(e)}\nTraceback: {traceback.format_exc()}")
                    item['item_status'] = 'Failed'
                    if self.gui:
                        self.progress.emit(item, self.tr("Failed"), 0)
                    self.readd_item_to_download_queue(item)
                    continue

                # Lyrics
                if item_service in ("spotify", "tidal"):
                    item['item_status'] = 'Getting Lyrics'
                    if self.gui:
                        self.progress.emit(item, self.tr("Getting Lyrics"), 99)
                    extra_metadata = globals()[f"{item_service}_get_lyrics"](token, item_id, item_type, item_metadata, file_path)
                    if isinstance(extra_metadata, dict):
                        item_metadata.update(extra_metadata)

                if config.get('force_raw'):
                    file_path += default_format
                elif item_type == "track":
                    file_path += "." + config.get("media_format")
                elif item_type == "episode":
                    file_path += "." + config.get("podcast_media_format")

                os.rename(temp_file_path, file_path)
                item['file_path'] = file_path

                # Convert file format and embed metadata
                if not config.get('force_raw'):
                    item['item_status'] = 'Converting'
                    if self.gui:
                        self.progress.emit(item, self.tr("Converting"), 99)

                    convert_audio_format(file_path, default_format)

                    embed_metadata(item, item_metadata)

                    # Thumbnail
                    if config.get('save_album_cover') or config.get('embed_cover'):
                        item['item_status'] = 'Setting Thumbnail'
                        if self.gui:
                            self.progress.emit(item, self.tr("Setting Thumbnail"), 99)
                        set_music_thumbnail(file_path, item_metadata)

                    if os.path.splitext(file_path)[1] == '.mp3':
                        fix_mp3_metadata(file_path)

                # M3U
                if config.get('create_m3u_playlists') and item.get('parent_category') == 'playlist':
                    item['item_status'] = 'Adding To M3U'
                    if self.gui:
                        self.progress.emit(item, self.tr("Adding To M3U"), 1)
                        add_to_m3u_file(item, item_metadata)

                item['item_status'] = 'Downloaded'
                logger.info("Item Successfully Downloaded")
                if self.gui:
                    self.progress.emit(item, self.tr("Downloaded"), 100)

                time.sleep(config.get("download_delay"))
                self.readd_item_to_download_queue(item)
                continue
            except Exception as e:
                logger.error(f"Unknown Exception: {str(e)}\nTraceback: {traceback.format_exc()}")
                item['item_status'] = "Failed"
                if self.gui:
                    self.progress.emit(item, self.tr("Failed"), 0)

                time.sleep(config.get("download_delay"))
                self.readd_item_to_download_queue(item)

                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                continue


    def stop(self):
        logger.info('Stopping Download Worker')
        self.is_running = False
        self.thread.join()
