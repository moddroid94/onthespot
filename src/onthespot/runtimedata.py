import sys
import os
import tracemalloc
from functools import wraps
import linecache
import logging
import threading
from logging.handlers import RotatingFileHandler
from .otsconfig import config

log_formatter = logging.Formatter(
    '[%(asctime)s :: %(name)s :: %(pathname)s -> %(lineno)s:%(funcName)20s() :: %(levelname)s] -> %(message)s'
)
log_handler = RotatingFileHandler(config.get("_log_file"),
                                  mode='a',
                                  maxBytes=(5 * 1024 * 1024),
                                  backupCount=2,
                                  encoding='utf-8',
                                  delay=0)
stdout_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(log_formatter)
stdout_handler.setFormatter(log_formatter)

parsing = {}
pending = {}
download_queue = {}
account_pool = []

parsing_lock = threading.Lock()
pending_lock = threading.Lock()
download_queue_lock = threading.Lock()

loglevel = int(os.environ.get("LOG_LEVEL", 20))


def get_logger(name):
    logger = logging.getLogger(name)
    logger.addHandler(log_handler)
    logger.addHandler(stdout_handler)
    logger.setLevel(loglevel)
    return logger


logger_ = get_logger("runtimedata")


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger_.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = handle_exception

def log_function_memory(wrap_func):
    tracemalloc.start()
    top_limit = 10
    def display_top(snapshot, snapshot_log_prefix, key_type='lineno'):
        snapshot = snapshot.filter_traces((
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        ))
        top_stats = snapshot.statistics(key_type)

        logger_.debug(f"{snapshot_log_prefix} Top {top_limit} lines")
        for index, stat in enumerate(top_stats[:top_limit], 1):
            frame = stat.traceback[0]
            logger_.debug("#%s: %s:%s: %.1f KiB"
                % (index, frame.filename, frame.lineno, stat.size / 1024))
            line = linecache.getline(frame.filename, frame.lineno).strip()
            if line:
                logger_.debug(f"{snapshot_log_prefix} -- {line}"  )

        other = top_stats[top_limit:]
        if other:
            size = sum(stat.size for stat in other)
            logger_.debug("%s other: %.1f KiB" % (len(other), size / 1024))
        total = sum(stat.size for stat in top_stats)
        logger_.debug("Total allocated size: %.1f KiB" % (total / 1024))

    @wraps(wrap_func)
    def snapshot_function_call(*args, **kwargs):
        prefix = f"{wrap_func.__name__}: "
        before_func = tracemalloc.take_snapshot()
        logger_.debug(f"Snapshotting before {wrap_func.__name__} call")
        ret_val = wrap_func(*args, **kwargs)
        display_top(before_func, prefix)
        logger_.debug(f"Snapshotting after {wrap_func.__name__} call")
        after_func = tracemalloc.take_snapshot()
        display_top(after_func, prefix)
        top_stats = after_func.compare_to(before_func, 'lineno')
        logger_.debug(f"{prefix} Top {top_limit} differences")
        for stat in top_stats[:10]:
            logger_.debug(f"{prefix}{stat}")
        return ret_val
    return snapshot_function_call
