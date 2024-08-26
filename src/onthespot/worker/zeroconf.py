import logging
import os
import pathlib
import sys
import time
import uuid
from librespot.zeroconf import ZeroconfServer
from ..otsconfig import config

def new_session():
    zs = ZeroconfServer.Builder().set_device_name("OnTheSpot").create()
    logging.info("Transfer playback from desktop client to librespot-python via Spotify Connect in order to store session")

    while True:
        time.sleep(1)
        if zs._ZeroconfServer__session:
            logging.info(f"Grabbed {zs._ZeroconfServer__session} for {zs._ZeroconfServer__session.username()}")

            if pathlib.Path("credentials.json").exists():
                logging.info("Session stored in credentials.json.")

                if {zs._ZeroconfServer__session.username()} in [user[0] for user in config.get('accounts')]:
                    logging.info("Account already exists")
                    return
                else:
                    uuid_uniq = str(uuid.uuid4())
                    session_json_path = os.path.join(os.path.join(os.path.expanduser('~'), '.config', 'casualOnTheSpot', 'sessions'),
                                         f"ots_login_{uuid_uniq}.json")

                    os.rename("credentials.json", session_json_path)


                    cfg_copy = config.get('accounts').copy()

                    new_user = [
                        zs._ZeroconfServer__session.username(),
                        "true",
                        int(time.time()),
                        uuid_uniq,
                    ]

                    cfg_copy.append(new_user)
                    config.set_('accounts', cfg_copy)
                    config.update()

                    logging.info("Config updated, restarting...")
                    os.execl(sys.executable, sys.executable, * sys.argv)

                return
