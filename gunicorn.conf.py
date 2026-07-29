import multiprocessing
import os
import fcntl


bind = "0.0.0.0:8999"
worker_class = "uvicorn.workers.UvicornWorker"
workers = int(os.environ.get("WEB_CONCURRENCY", 4))
loglevel = os.environ.get("LOG_LEVEL", "info")
accesslog = "-"
errorlog = "-"
timeout = 60
graceful_timeout = 30
keepalive = 2
max_requests = 10000
max_requests_jitter = 200

LOCK_PATH = "/tmp/app_scheduler.lock"


def post_fork(server, worker):
    try:
        fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.environ["IS_LEADER"] = "1"
        worker.tmp_lock_fd = fd
        worker.log.info("This worker is LEADER")
    except OSError:
        os.environ["IS_LEADER"] = "0"
        worker.tmp_lock_fd = None

        try:
            os.close(fd)
        except Exception:
            pass


def worker_exit(server, worker):
    fd = getattr(worker, "tmp_lock_fd", None)
    if fd:
        try:
            os.close(fd)
        except Exception:
            pass
