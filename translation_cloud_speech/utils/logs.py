import threading

from .parameters import LOG_TITLE


def print_logs(msg, log_type=None):
    log_title = f"{LOG_TITLE} ({log_type})" if log_type else f"{LOG_TITLE} "
    log = log_title + f" {msg}\n"
    print(log)


def print_logs_threads(msg):
    print_logs(f"{msg}: {[t.name for t in threading.enumerate()]}", log_type="threads")