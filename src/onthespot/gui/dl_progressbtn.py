import platform
import os
import subprocess
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QHBoxLayout, QWidget
from ..otsconfig import config
from ..runtimedata import downloaded_data, cancel_list, failed_downloads, downloads_status, download_queue, session_pool, get_logger
from showinfm import show_in_file_manager
from ..utils.spotify import check_if_media_in_library, save_media_to_library, remove_media_from_library

logger = get_logger("worker.utility")


class DownloadActionsButtons(QWidget):
    def __init__(self, dl_id, media_type, pbar, cancel_btn, remove_btn, save_btn, play_btn, locate_btn, parent=None):
        super(DownloadActionsButtons, self).__init__(parent)
        self.__id = dl_id
        self.media_type = media_type
        self.cancel_btn = cancel_btn
        self.remove_btn = remove_btn
        self.save_btn = save_btn
        self.play_btn = play_btn
        self.locate_btn = locate_btn
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        cancel_btn.clicked.connect(self.cancel_item)
        remove_btn.clicked.connect(self.retry_item)
        save_btn.clicked.connect(self.save_item)
        play_btn.clicked.connect(self.play_file)
        locate_btn.clicked.connect(self.locate_file)
        layout.addWidget(pbar)
        layout.addWidget(cancel_btn)
        layout.addWidget(remove_btn)
        layout.addWidget(save_btn)
        layout.addWidget(play_btn)
        layout.addWidget(locate_btn)
        self.setLayout(layout)
        if config.get("download_save_btn"):
            selected_uuid = config.get('accounts')[config.get('parsing_acc_sn') - 1][3]
            self.session = session_pool[selected_uuid]
            in_library = check_if_media_in_library(self.session, self.__id, self.media_type)
            if in_library:
                save_ico = QIcon(os.path.join(config.app_root, 'resources', 'filled-heart.png'))
                save_btn.setIcon(save_ico)
                self.in_library = True
            elif not in_library:
                save_ico = QIcon(os.path.join(config.app_root, 'resources', 'empty-heart.png'))
                save_btn.setIcon(save_ico)
                self.in_library = False
            else:
                logger.info(f"Unable to determine if song is in library, value: {in_library}")

    def save_item (self):
        if self.in_library:
            remove_media_from_library(self.session, self.__id, self.media_type)
            save_ico = QIcon(os.path.join(config.app_root, 'resources', 'empty-heart.png'))
            self.save_btn.setIcon(save_ico)
            self.in_library = False
            logger.info(f"Song removed from spotify library")
        elif not self.in_library:
            save_media_to_library(self.session, self.__id, self.media_type)
            save_ico = QIcon(os.path.join(config.app_root, 'resources', 'filled-heart.png'))
            self.save_btn.setIcon(save_ico)
            self.in_library = True
            logger.info(f"Song saved to spotify library")
        else:
            logger.info(f"Unable to determine if song is in library cannot save, value: {in_library}")

    def play_file (self):
        file_path = os.path.abspath(downloaded_data[self.__id]['media_path'])
        if platform.system() == 'Windows':
            os.startfile(file_path)
        elif platform.system() == 'Darwin':  # For MacOS
            subprocess.call(['open', file_path])
        else:  # For Linux and other Unix-like systems
            subprocess.run(['xdg-open', file_path])

    def locate_file(self):
        if self.__id in downloaded_data:
            if downloaded_data[self.__id].get('media_path', None):
                show_in_file_manager(os.path.abspath(downloaded_data[self.__id]['media_path']))

    def cancel_item(self):
        cancel_list[self.__id] = {}
        self.cancel_btn.hide()

    def retry_item(self):
        if self.__id in failed_downloads:
            downloads_status[self.__id]["status_label"].setText("Waiting")
            self.remove_btn.hide()
            download_queue.put(failed_downloads[self.__id])
            self.cancel_btn.show()
