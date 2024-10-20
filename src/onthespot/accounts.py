from .runtimedata import get_logger, account_pool
from .otsconfig import config

from PyQt6.QtCore import QThread, pyqtSignal
from .api.spotify import spotify_login_user, spotify_get_token
from .api.soundcloud import soundcloud_login_user, soundcloud_get_token


logger = get_logger("spotify.downloader")

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

            if service == 'spotify':
                if self.gui is True:
                    self.progress.emit(self.tr('Attempting to create session for\n{0}...').format(account['login']['username']), True)

                if spotify_login_user(account) is True:
                    if self.gui is True:
                        self.progress.emit(self.tr('Session created for\n{0}!').format(account['login']['username']), True)
                    continue
                else:
                    if self.gui is True:
                        self.progress.emit(self.tr('Login failed for \n{0}!').format(account['login']['username']), True)
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
 
                print("s")
        print(account_pool)
        self.finished.emit()



def get_account_token(download=False):
    parsing_index = config.get('parsing_acc_sn') - 1
    service = account_pool[parsing_index]['service']
    
    if config.get("rotate_acc_sn") is True and download is True:
        #for account in account_pool:
        #    if account["service"] == service:
        #    print(account["uuid"])  # Print the UUID
        #if download == True and parsing_index < (len(config.get('accounts'))-1):
        #    config.set_('parsing_acc_sn', parsing_index + 1)
        #else:
        #    config.set_('parsing_acc_sn', 0)
        selected_uuid = config.get('accounts')[parsing_index][0]
    else:
        token = globals()[f"{service}_get_token"](parsing_index)
    return token