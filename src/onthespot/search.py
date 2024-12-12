import os
from .runtimedata import account_pool, get_logger
from .accounts import get_account_token
from .parse_item import parse_url
from .otsconfig import config
from .api.spotify import spotify_get_search_results
from .api.soundcloud import soundcloud_get_search_results
from .api.deezer import deezer_get_search_results
from .api.youtube import youtube_get_search_results
from .api.bandcamp import bandcamp_get_search_results
from .api.tidal import tidal_get_search_results

logger = get_logger("search")


def get_search_results(search_term, content_types=None):
    if len(account_pool) <= 0:
        return None

    if search_term == '':
        logger.warning(f"Returning empty data as query is empty !")
        return False

    if search_term.startswith('https://'):
        logger.info(f"Search clicked with value with url {search_term}")
        result = parse_url(search_term)
        if result is False:
            return False
        return True
    else:
        if os.path.isfile(search_term):
            with open(search_term, 'r', encoding='utf-8') as sf:
                links = sf.readlines()
                for link in links:
                    link = link.strip()
                    if link.startswith("https://"):
                        logger.debug(f'Parsing link from {search_term}: {link}')
                        parse_url(link)
            return True

        logger.info(f"Search clicked with value term {search_term}")
        if search_term != "":
            account_type = config.get('accounts')[config.get('parsing_acc_sn')]['service']
            token = get_account_token(account_type)
            return globals()[f"{account_type}_get_search_results"](token, search_term, content_types)
