from salesreport.cache import SummaryCache
from salesreport.summary import render


class ReportService:
    def __init__(self, source):
        self._cache = SummaryCache(source)

    def summary(self):
        return self._cache.get()

    def text(self):
        return render(self.summary())
