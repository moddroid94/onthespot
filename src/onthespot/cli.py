import logging
import threading
from cmd import Cmd
import os
import time
import curses
from .runtimedata import account_pool, pending, download_queue, download_queue_lock, pending_lock
from .otsconfig import config_dir, config
from .accounts import FillAccountPool, get_account_token
from .parse_item import parsingworker, parse_url
from .search import get_search_results
from .api.deezer import deezer_get_track_metadata, deezer_add_account
from .api.soundcloud import soundcloud_get_track_metadata
from .api.spotify import MirrorSpotifyPlayback, spotify_new_session, spotify_get_track_metadata, spotify_get_episode_metadata
from .api.youtube import youtube_get_track_metadata
from .downloader import DownloadWorker
from .casualsnek import start_snake_game

logging.disable(logging.CRITICAL)


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
                        'playlist_number': item.get('playlist_number', '')
                        }
            else:
                time.sleep(0.2)

def main():
    print('\033[32mLogging In...\033[0m\n', end='', flush=True)

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

    CLI().cmdloop()


class CLI(Cmd):
    intro = '\033[32mWelcome to OnTheSpot. Type help or ? to list commands.\033[0m'
    prompt = '(OTS) '


    def do_help(self, arg):
        print("\033[32mAvailable commands:\033[0m")
        print("  help                - Show this help message")
        print("  config              - Display configuration options")
        print("  search [term]/[url] - Search for a term or parse a url")
        print("  download_queue      - View the download queue")
        print("  casualsnek          - Something to pass the time")
        print("  exit                - Exit the CLI application")


    def do_config(self, arg):
        parts = arg.split()
        if arg == "reset_settings":
            config.rollback()
            print('\033[32mReset settings, please restart the app.\033[0m')

        if arg == "list_accounts":
            print('\033[32mLegend:\033[0m\n\033[34m>\033[0mSelected: Service, Status\n\n\033[32mAccounts:\033[0m')
            for index, item in enumerate(account_pool):
                print(f"{'\033[34m>\033[0m' if config.get('parsing_acc_sn') == index else ' '}[{index}] {item['username']}: {item['service']}, {item['status']}")
            return

        elif arg == "add_account":
            print("soundcloud")
            print("spotify")
            print("deezer")

        elif arg == "add_account spotify":
            print("\033[32mLogin service started, select 'OnTheSpot' under devices in the Spotify Desktop App.\033[0m")

            def add_spotify_account_worker():
                session = spotify_new_session
                if session == True:
                    print("\033[32mAccount added, please restart the app.\033[0m")
                    config.set_('parsing_acc_sn', config.get('parsing_acc_sn') + 1)
                    config.update()
                elif session == False:
                    print("\033[32mAccount already exists.\033[0m")

            login_worker = threading.Thread(target=add_spotify_account_worker)
            login_worker.daemon = True
            login_worker.start()

        elif arg == "add_account soundcloud":
            print("not implemented yet")

        elif arg == "add_account deezer":
            print("\033[32madd_account deezer [arl]\033[0m")

        elif len(parts) == 3 and parts[0] == "add_account" and parts[1] == "deezer":
            deezer_add_account(parts[2])

        elif len(parts) == 2 and parts[0] == "select_account":

            try:
                account_number = int(parts[1])
                config.set_('parsing_acc_sn', account_number)
                config.update()
                print(f"\033[32mSelected account number: {account_number}\033[0m")
            except ValueError:
                print("\033[32mInvalid account number. Please enter a valid integer.\033[0m")

        elif len(parts) == 2 and parts[0] == "delete_account":

            try:
                account_number = int(parts[1])
                accounts = config.get('accounts').copy()
                del accounts[account_number]
                config.set_('accounts', accounts)
                config.update()
                del account_pool[account_number]
                print(f"\033[32mDeleted account number: {account_number}\033[0m")
            except ValueError:
                print("\033[32mInvalid account number. Please enter a valid integer.\033[0m")

        else:
            print("\033[32mConfiguration options:\033[0m")
            print("  list_accounts")
            print("  add_account [service]")
            print("  select_account [index]")
            print("  delete_account [index]")
            print("  reset_settings")
            print(f"  \033[36mAdditional options can be found at {config_dir()}{os.path.sep}otsconfig.json\033[0m")


    def do_search(self, arg):
        """Search for a term."""
        if arg:
            print(f"\033[32mSearching for: {arg}\033[0m")
            results = get_search_results(arg)

            if results is True:
                print(f"\033[32mParsing Item...\033[0m")
                return
            elif results:
                print("\033[32mSearch Results:\033[0m")
                for index, item in enumerate(results):
                    print(f"[{index + 1}] {item['item_type']}: {item['item_name']} by {item['item_by']}")
                print(f"[0] Exit")
                choice = input("\033[32mEnter the number of the item you want to download: \033[0m")
                try:
                    choice_index = int(choice) - 1
                    if 0 <= choice_index < len(results):
                        selected_item = results[choice_index]
                        parse_url(selected_item['item_url'])
                    else:
                        print("Invalid number entered, exiting.")
                except ValueError:
                    print("Please enter a valid number.")
            else:
                print("No results found.")
        else:
            print("Please provide a term to search.")


    def do_casualsnek(self, arg):
        curses.wrapper(start_snake_game)


    def do_download_queue(self, arg):
        curses.wrapper(self.display_queue)


    def display_queue(self, stdscr):
        keep_running = True
        #curses.curs_set(0)
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        stdscr.addstr(0, 0, "Download Queue", curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, 0, "(Press 'c' to cancel pending downloads, 'd' to clear completed, 'q' to exit.)")

        current_row = 2
        max_height = curses.LINES - 3
        selected_index = 0
        first_item_index = 0

        def refresh_queue():
            while keep_running:
                time.sleep(0.2)
                stdscr.clear()
                stdscr.addstr(0, 0, "Download Queue", curses.color_pair(1) | curses.A_BOLD)
                stdscr.addstr(1, 0, "(Press 'c' to cancel pending downloads, 'd' to clear completed, 'q' to exit.)")

                keys = list(download_queue.keys())
                num_items = len(keys)

                num_items_to_display = min(max_height, num_items)

                for idx in range(num_items_to_display):
                    key = keys[first_item_index + idx]
                    status = download_queue[key]['item_status']
                    item_name = download_queue[key]['item_name']
                    item_by = download_queue[key]['item_by']
                    if idx == selected_index:
                        stdscr.addstr(current_row + idx, 0, f"{item_name} by {item_by}: {status}", curses.color_pair(2))
                    else:
                        stdscr.addstr(current_row + idx, 0, f"{item_name} by {item_by}: {status}")

                stdscr.refresh()

        threading.Thread(target=refresh_queue, daemon=True).start()

        while True:
            key = stdscr.getch()
            keys = list(download_queue.keys())
            num_items = len(keys)

            num_items_to_display = min(max_height, num_items)

            if key == curses.KEY_UP:
                if selected_index > 0:
                    selected_index -= 1
                elif first_item_index > 0:
                    first_item_index -= 1
                    selected_index = min(selected_index, num_items_to_display - 1)
            elif key == curses.KEY_DOWN:
                if selected_index < num_items_to_display - 1:
                    selected_index += 1
                elif first_item_index + num_items_to_display < num_items:
                    first_item_index += 1
                    selected_index = min(selected_index, num_items_to_display - 1)
            elif key == ord('q'):
                keep_running = False
                break
            elif key == ord('c'):
                with download_queue_lock:
                    for key in list(download_queue.keys()):
                        if download_queue[key]['item_status'] == 'Waiting':
                            download_queue[key]['item_status'] = 'Cancelled'
            elif key == ord('d'):
                with download_queue_lock:
                    selected_index = 0
                    first_item_index = 0
                    for key in list(download_queue.keys()):
                        if download_queue[key]['item_status'] in (
                                "Cancelled",
                                "Downloaded",
                                "Already Exists"
                            ):
                            download_queue.pop(key)
            elif key == ord('r'):
                with download_queue_lock:
                    for key in list(download_queue.keys()):
                        if download_queue[key]['item_status'] == 'Failed':
                            download_queue[key]['item_status'] = 'Waiting'
        time.sleep(0.3)
        stdscr.clear()
        stdscr.refresh()



    def do_exit(self, arg):
        """Exit the CLI application."""
        print("Exiting the CLI application.")
        os._exit(0)



if __name__ == '__main__':
    main()
