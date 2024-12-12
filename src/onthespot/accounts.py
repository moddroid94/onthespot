from PyQt6.QtCore import QThread, pyqtSignal
from .runtimedata import get_logger, account_pool
from .otsconfig import config
from .api.spotify import spotify_login_user, spotify_get_token
from .api.soundcloud import soundcloud_login_user, soundcloud_get_token
from .api.deezer import deezer_login_user, deezer_get_token
from .api.youtube import youtube_login_user
from .api.bandcamp import bandcamp_login_user
from .api.tidal import tidal_login_user, tidal_get_token

logger = get_logger("accounts")


class FillAccountPool(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(str, bool)

    def __init__(self, gui=False):
        self.gui = gui
        super().__init__()


    def run(self):
        accounts = config.get('accounts')
        for account in accounts:
            service = account['service']
            if not account['active']:
                continue

            if service == 'bandcamp':
                bandcamp_login_user(account)
                continue

            elif service == 'deezer':
                if self.gui is True:
                    self.progress.emit(self.tr('Attempting to create session for\n{0}...').format(account['login']['arl'][:30]), True)
                try:
                    if deezer_login_user(account) is True:
                        if self.gui is True:
                            self.progress.emit(self.tr('Session created for\n{0}...!').format(account['login']['arl'][:30]), True)
                        continue
                    else:
                        if self.gui is True:
                            self.progress.emit(self.tr('Login failed for \n{0}...!').format(account['login']['arl'][:30]), True)
                        continue
                except Exception as e:
                    if self.gui is True:
                        self.progress.emit(self.tr('Login failed for \n{0}...!').format(account['login']['arl'][:30]), True)
                    continue

            elif service == 'soundcloud':
                if self.gui is True:
                    self.progress.emit(self.tr('Attempting to create session for\n{0}...').format(account['login']['client_id']), True)

                valid_login = soundcloud_login_user(account)
                if valid_login and account['uuid'] == 'public_soundcloud':
                    if self.gui is True:
                        self.progress.emit(self.tr('Session created for\n{0}!').format(account['login']['client_id']), True)
                    continue
                else:
                    if self.gui is True:
                        self.progress.emit(self.tr('Login failed for \n{0}!').format(account['login']['client_id']), True)
                    continue

            elif service == 'spotify':
                if self.gui is True:
                    self.progress.emit(self.tr('Attempting to create session for\n{0}...').format(account['login']['username']), True)
                try:
                    if spotify_login_user(account) is True:
                        if self.gui is True:
                            self.progress.emit(self.tr('Session created for\n{0}!').format(account['login']['username']), True)
                        continue
                    else:
                        if self.gui is True:
                            self.progress.emit(self.tr('Login failed for \n{0}!').format(account['login']['username']), True)
                        continue
                except Exception as e:
                    if self.gui is True:
                        self.progress.emit(self.tr('Login failed for \n{0}!').format(account['login']['username']), True)
                    continue

            elif service == 'tidal':
                if self.gui is True:
                    self.progress.emit(self.tr('Attempting to create session for\n{0}...').format(account['login']['username']), True)

                valid_login = tidal_login_user(account)
                if valid_login:
                    if self.gui is True:
                        self.progress.emit(self.tr('Session created for\n{0}!').format(account['login']['username']), True)
                    continue
                else:
                    if self.gui is True:
                        self.progress.emit(self.tr('Login failed for \n{0}!').format(account['login']['username']), True)
                    continue

            elif service == 'youtube':
                youtube_login_user(account)
                continue

        self.finished.emit()


def get_account_token(item_service):
    if item_service in ('bandcamp', 'youtube'):
        return
    parsing_index = config.get('parsing_acc_sn')
    service = account_pool[parsing_index]['service']
    if item_service == service and not config.get("rotate_acc_sn"):
        return globals()[f"{item_service}_get_token"](parsing_index)
    else:
        for i in range(parsing_index + 1, parsing_index + len(account_pool) + 1):
            index = i % len(account_pool)
            if account_pool[index]['service'] == item_service:
                if config.get("rotate_acc_sn"):
                    config.set_('parsing_acc_sn', index)
                    config.update
                return globals()[f"{item_service}_get_token"](index)
