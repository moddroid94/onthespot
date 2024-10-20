

from .api.spotify import spotify_get_search_results
from .api.soundcloud import soundcloud_get_search_results
from .runtimedata import account_pool, get_logger
import os
from .accounts import get_account_token
from .parse_item import parse_url
logger = get_logger("spotify.api")
from .otsconfig import config

def get_search_results(search_term, content_types=None):
    if len(account_pool) <= 0:
            return None
    if search_term.startswith('https://'):
        logger.info(f"Search clicked with value with url {search_term}")
        parse_url(search_term)
        return True
    else:
        if os.path.isfile(search_term):
            with open(search_term, 'r', encoding='utf-8') as sf:
                links = sf.readlines()
                for link in links:
                    logger.info(f'Reading link "{link}" from file at "{search_term}"')
                    parse_url(link)
            return True


        logger.info(f"Search clicked with value term {search_term}")
        if search_term != "":
            token = get_account_token()
            account_type = config.get('accounts')[config.get('parsing_acc_sn') - 1]['service']
            return globals()[f"{account_type}_get_search_results"](token, search_term, content_types)