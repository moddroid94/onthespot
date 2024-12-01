import os
import time
import json
import threading
from flask import Flask, jsonify, render_template, request, send_file, redirect, url_for
from .runtimedata import get_logger, account_pool, pending, download_queue, download_queue_lock, pending_lock
from .otsconfig import config_dir, config
from .accounts import FillAccountPool, get_account_token
from .parse_item import parsingworker, parse_url
from .search import get_search_results
from .api.deezer import deezer_get_track_metadata, deezer_add_account
from .api.soundcloud import soundcloud_get_track_metadata
from .api.spotify import MirrorSpotifyPlayback, spotify_new_session, spotify_get_track_metadata, spotify_get_episode_metadata
from .api.youtube import youtube_get_track_metadata
from .downloader import DownloadWorker

logger = get_logger("web")
app = Flask(__name__)


class QueueWorker(threading.Thread):
    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            if pending:
                local_id = next(iter(pending))
                with pending_lock:
                    item = pending.pop(local_id)
                token = get_account_token()
                item_metadata = globals()[f"{item['item_service']}_get_{item['item_type']}_metadata"](token, item['item_id'])

                with download_queue_lock:
                    download_queue[local_id] = {
                        'local_id': local_id,
                        'available': True,
                        "item_service": item["item_service"],
                        "item_type": item["item_type"],
                        'item_id': item['item_id'],
                        'item_status': 'Waiting',
                        "file_path": None,
                        "item_name": item_metadata["title"],
                        "item_by": item_metadata["artists"],
                        'parent_category': item['parent_category'],
                        'playlist_name': item.get('playlist_name', ''),
                        'playlist_by': item.get('playlist_by', ''),
                        'playlist_number': item.get('playlist_number', ''),
                        'item_thumbnail': item_metadata["image_url"],
                        'item_url': item_metadata["item_url"]
                    }
            else:
                time.sleep(0.2)

@app.route('/items')
def get_items():
    with download_queue_lock:
        return jsonify(download_queue)

@app.route('/icons/<path:filename>')
def serve_icons(filename):
    icon_path = os.path.join(config.app_root, 'resources', 'icons', filename)
    return send_file(icon_path)

@app.route('/download/<path:local_id>')
def download_media(local_id):
    return send_file(download_queue[local_id]['file_path'], as_attachment=True)

@app.route('/delete/<path:local_id>', methods=['DELETE'])
def delete_media(local_id):
    os.remove(download_queue[local_id]['file_path'])
    download_queue[local_id]['item_status'] = 'Deleted'
    return jsonify(success=True)

@app.route('/cancel/<path:local_id>', methods=['POST'])
def cancel_item(local_id):
    download_queue[local_id]['item_status'] = 'Cancelled'
    return jsonify(success=True)

@app.route('/retry/<path:local_id>', methods=['POST'])
def retry_item(local_id):
    download_queue[local_id]['item_status'] = 'Waiting'
    return jsonify(success=True)

@app.route('/download/<path:url>', methods=['POST'])
def download_file(url):
    parse_url(url)
    return jsonify(success=True)

@app.route('/clear', methods=['POST'])
def clear_items():
    keys_to_delete = []

    for local_id, item in download_queue.items():
        if item["item_status"] == "Downloaded" or \
           item["item_status"] == "Already Exists" or \
           item["item_status"] == "Cancelled" or \
           item["item_status"] == "Deleted":
            keys_to_delete.append(local_id)
    for key in keys_to_delete:
        del download_queue[key]
    return jsonify(success=True)

@app.route('/download_queue')
def download_queue_page():
    config_path = os.path.join(config_dir(), 'onthespot', 'otsconfig.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)
        print(config_data)
    return render_template('download_queue.html', config=config_data)

@app.route('/')
def index():
    return redirect(url_for('download_queue_page'))

@app.route('/search')
def search():
    config_path = os.path.join(config_dir(), 'onthespot', 'otsconfig.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)
    return render_template('search.html', config=config_data)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/search_results')
def search_results():
    query = request.args.get('q', '')

    content_types = []
    if config.get('enable_search_tracks'):
        content_types.append('track')
    if config.get('enable_search_playlists'):
        content_types.append('playlist')
    if config.get('enable_search_albums'):
        content_types.append('album')
    if config.get('enable_search_artists'):
        content_types.append('artist')
    if config.get('enable_search_shows'):
        content_types.append('show')
    if config.get('enable_search_episodes'):
        content_types.append('episode')
    if config.get('enable_search_audiobooks'):
        content_types.append('audiobook')

    results = get_search_results(query, content_types=content_types)
    return jsonify(results)


@app.route('/settings')
def settings():
    config_path = os.path.join(config_dir(), 'onthespot', 'otsconfig.json')
    with open(config_path, 'r') as config_file:
        config_data = json.load(config_file)
    return render_template('settings.html', config=config_data, account_pool=account_pool)  # Render the settings.html file

@app.route('/update_settings', methods=['POST'])
def update_settings():
    data = request.json
    for key, value in data.items():
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        config.set_(key, value)
        config.update()
    return jsonify(success=True)

def main():
    fill_account_pool = FillAccountPool()

    fill_account_pool.finished.connect(lambda: print("Finished filling account pool."))
    fill_account_pool.progress.connect(lambda message, status: print(f"{message} {'Success' if status else 'Failed'}"))

    fill_account_pool.start()

    thread = threading.Thread(target=parsingworker)
    thread.daemon = True
    thread.start()

    queue_worker = QueueWorker()
    queue_worker.start()

    for i in range(config.get('maximum_download_workers')):
        downloadworker = DownloadWorker(gui=True)
        downloadworker.start()

    fill_account_pool.wait()

    if config.get('mirror_spotify_playback'):
        mirrorplayback = MirrorSpotifyPlayback()
        mirrorplayback.start()

    app.run(debug=True)

if __name__ == '__main__':
    main()
