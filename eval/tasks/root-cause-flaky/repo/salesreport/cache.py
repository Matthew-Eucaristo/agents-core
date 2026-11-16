import random
import threading
import time

from salesreport.summary import summarize

WARMUP_STAGGER_S = 0.05
READ_GRACE_S = 0.03


class SummaryCache:
    def __init__(self, source):
        self._source = source
        self._summary = summarize([])
        self._warmup = threading.Thread(target=self._warm, daemon=True)
        self._warmup.start()

    def _warm(self):
        time.sleep(random.uniform(0, WARMUP_STAGGER_S))
        self._summary = summarize(self._source.fetch())

    def get(self):
        self._warmup.join(READ_GRACE_S)
        return self._summary
