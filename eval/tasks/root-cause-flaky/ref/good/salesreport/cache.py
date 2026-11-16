import random
import threading
import time

from salesreport.summary import summarize

WARMUP_STAGGER_S = 0.05


class SummaryCache:
    def __init__(self, source):
        self._source = source
        self._lock = threading.Lock()
        self._summary = None
        self._warmup = threading.Thread(target=self._warm, daemon=True)
        self._warmup.start()

    def _warm(self):
        time.sleep(random.uniform(0, WARMUP_STAGGER_S))
        self._load()

    def _load(self):
        with self._lock:
            if self._summary is None:
                self._summary = summarize(self._source.fetch())
            return self._summary

    def get(self):
        return self._load()
