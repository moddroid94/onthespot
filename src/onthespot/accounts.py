from .runtimedata import get_logger, account_pool
from .otsconfig import config

from PyQt6.QtCore import QThread, pyqtSignal
from .api.spotify import spotify_login_user, spotify_get_token
from .api.soundcloud import soundcloud_login_user, soundcloud_get_token
from .api.deezer import deezer_login_user, deezer_get_token
from .api.youtube import youtube_login_user

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

            if service == 'deezer':
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
                elif valid_login:
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

            elif service == 'youtube':
                youtube_login_user(account)
                continue

        self.finished.emit()



def get_account_token():
    parsing_index = config.get('parsing_acc_sn')
    service = account_pool[parsing_index]['service']

    if service == 'youtube':
        return

    if config.get("rotate_acc_sn") is True:
        for i in range(parsing_index + 1, parsing_index + len(account_pool) + 1):
            index = i % len(account_pool)
            if account_pool[index]['service'] == service:
                config.set_('parsing_acc_sn', index)
                config.update
                return globals()[f"{service}_get_token"](index)
    else:
        return globals()[f"{service}_get_token"](parsing_index)
