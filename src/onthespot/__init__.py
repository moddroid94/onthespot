#!/usr/bin/env python3
import os
import sys
from PyQt5.QtCore import QTranslator
from PyQt5.QtWidgets import QApplication
from .gui.mainui import MainWindow
from .gui.minidialog import MiniDialog
from .runtimedata import get_logger
from .otsconfig import config

def main():
    logger = get_logger('__init__')
    logger.info('Starting application in \n3\n2\n1')
    app = QApplication(sys.argv)

    if config.get("language_index") == 0:
        language = "en_US"
    elif config.get("language_index") == 1:
        language = "pt_PT"

    translator = QTranslator()
    path = os.path.join(os.path.join(config.app_root, 'resources', 'translations'),
                 f"{language}.qm")
    translator.load(path)
    app.installTranslator(translator)

    _dialog = MiniDialog()
    window = MainWindow(_dialog, sys.argv[1] if len(sys.argv) >= 2 else '' )
    app.setDesktopFileName('org.eu.casualsnek.onthespot')
    app.exec_()
    logger.info('Good bye ..')


if __name__ == '__main__':
    main()
