import os
import pyperclip
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QWidget
from ..otsconfig import config
from ..runtimedata import download_queue, get_logger
from ..utils import open_item
from ..api.spotify import check_if_media_in_library, save_media_to_library, remove_media_from_library, queue_media, play_media


logger = get_logger("worker.utility")


class DownloadActionsButtons(QWidget):
    def __init__(self, item_id, pbar, copy_btn, cancel_btn, retry_btn, play_btn, save_btn, queue_btn, open_btn, locate_btn, delete_btn, parent=None):
        super(DownloadActionsButtons, self).__init__(parent)
        self.item_id = item_id
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(pbar)
        if copy_btn != None:
            self.copy_btn = copy_btn
            copy_btn.clicked.connect(self.copy_link)
            layout.addWidget(copy_btn)
        self.cancel_btn = cancel_btn
        cancel_btn.clicked.connect(self.cancel_item)
        layout.addWidget(cancel_btn)
        self.retry_btn = retry_btn
        retry_btn.clicked.connect(self.retry_item)
        layout.addWidget(retry_btn)
        if play_btn != None:
            self.play_btn = play_btn
            play_btn.clicked.connect(self.play_item)
            layout.addWidget(play_btn)
        if save_btn != None:
            self.save_btn = save_btn
            save_btn.clicked.connect(self.save_item)
            layout.addWidget(save_btn)
        if save_btn != None:
            self.queue_btn = queue_btn
            queue_btn.clicked.connect(self.queue_item)
            layout.addWidget(queue_btn)
        if open_btn != None:
            self.open_btn = open_btn
            open_btn.clicked.connect(self.open_file)
            layout.addWidget(open_btn)
        if locate_btn != None:
            self.locate_btn = locate_btn
            locate_btn.clicked.connect(self.locate_file)
            layout.addWidget(locate_btn)
        if delete_btn != None:
            self.delete_btn = delete_btn
            delete_btn.clicked.connect(self.delete_file)
            layout.addWidget(delete_btn)
        self.setLayout(layout)
        if config.get("download_save_btn"):
            #selected_uuid = config.get('accounts')[config.get('parsing_acc_sn') - 1][3]
            selected_uuid = config.get('accounts')[0][3]
            self.session = session_pool[selected_uuid]
            in_library = check_if_media_in_library(self.session, self.item_id, self.item_type)
            if in_library:
                save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'filled_heart.png'))
                save_btn.setIcon(save_icon)
                self.in_library = True
            elif not in_library:
                save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'empty_heart.png'))
                save_btn.setIcon(save_icon)
                self.in_library = False
            else:
                logger.info(f"Unable to determine if song is in library, value: {in_library}")

    def copy_link(self):
        pyperclip.copy("FIX ME")

    def cancel_item(self):
        download_queue[self.item_id]['gui']['status_label'].setText(self.tr("Cancelled"))
        download_queue[self.item_id]['gui']['progress_bar'].setValue(0)
        self.cancel_btn.hide()
        self.retry_btn.show()

    def retry_item(self):
        download_queue[self.item_id]['gui']['status_label'].setText(self.tr("Waiting"))
        self.retry_btn.hide()
        self.cancel_btn.show()

    def play_item(self):
        play_media(self.session, self.item_id, self.item_type)

    def save_item(self):
        if self.in_library:
            remove_media_from_library(self.session, self.item_id, self.item_type)
            save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'empty_heart.png'))
            self.save_btn.setIcon(save_icon)
            self.in_library = False
            logger.info(f"Song removed from spotify library")
        elif not self.in_library:
            save_media_to_library(self.session, self.item_id, self.item_type)
            save_icon = QIcon(os.path.join(config.app_root, 'resources', 'icons', 'filled_heart.png'))
            self.save_btn.setIcon(save_icon)
            self.in_library = True
            logger.info(f"Song saved to spotify library")
        else:
            logger.info(f"Unable to determine if song is in library cannot save, value: {in_library}")

    def queue_item(self):
        queue_media(self.session, self.item_id, self.item_type)

    def open_file(self):
        file_path = download_queue[self.item_id]['file_path']
        file = os.path.abspath(file_path)
        open_item(file)


    def locate_file(self):
        file_path = download_queue[self.item_id]['file_path']
        file_dir = os.path.dirname(file_path)
        open_item(file_dir)

    def delete_file(self):
        file_path = download_queue[self.item_id]['file_path']
        file = os.path.abspath(file_path)
        os.remove(file)
        self.item["gui"]["status_label"].setText(self.tr("Deleted"))
        self.play_btn.hide()
        self.save_btn.hide()
        self.queue_btn.hide()
        self.open_btn.hide()
        self.locate_btn.hide()
        self.delete_btn.hide()
