import os
import pathlib
import sys
import time
import uuid
from librespot.zeroconf import ZeroconfServer
from ..otsconfig import config_dir, config
from ..runtimedata import get_logger

logger = get_logger("worker.session")

def new_session():
    try:
        os.mkdir(os.path.join(config_dir(), 'onthespot', 'sessions'))
    except FileExistsError:
        logger.info("The session directory already exists.")

    uuid_uniq = str(uuid.uuid4())
    session_json_path = os.path.join(os.path.join(config_dir(), 'onthespot', 'sessions'),
                 f"ots_login_{uuid_uniq}.json")

    CLIENT_ID: str = "65b708073fc0480ea92a077233ca87bd"
    ZeroconfServer._ZeroconfServer__default_get_info_fields['clientID'] = CLIENT_ID
    zs_builder = ZeroconfServer.Builder()
    zs_builder.device_name = 'OnTheSpot'
    zs_builder.conf.stored_credentials_file = session_json_path
    zs = zs_builder.create()
    logger.info("Zeroconf login service started")

    while True:
        time.sleep(1)
        if zs.has_valid_session():
            logger.info(f"Grabbed {zs._ZeroconfServer__session} for {zs._ZeroconfServer__session.username()}")

            if {zs._ZeroconfServer__session.username()} in [user[0] for user in config.get('accounts')]:
                logger.info("Account already exists")
                return
            else:
                cfg_copy = config.get('accounts').copy()
                new_user = [
                    zs._ZeroconfServer__session.username(),
                    "true",
                    int(time.time()),
                    uuid_uniq,
                ]
                zs.close()
                cfg_copy.append(new_user)
                config.set_('accounts', cfg_copy)
                config.update()
                logger.info("Config updated, restarting...")
                os.execl(sys.executable, sys.executable, * sys.argv)
                return
