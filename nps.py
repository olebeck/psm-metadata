from dataclasses import dataclass
import requests


@dataclass
class nps_psm_entry:
    title_id: str
    region: str
    name: str
    url: str
    zrif: str
    content_id: str
    mtime: str
    filesize: str
    sha256: str
    @classmethod
    def from_line(cls, line: str):
        return cls(*line.split("\t"))

class NPS:
    _url = "https://nopaystation.com/tsv/PSM_GAMES.tsv"
    entries: list[nps_psm_entry]

    def list_nps_content_ids(self):
        r = requests.get(self._url)
        lines = r.text.splitlines(False)
        return [nps_psm_entry.from_line(line) for line in lines]

    def __init__(self):
        self.entries = self.list_nps_content_ids()
        self.by_content_id = {entry.content_id: entry for entry in self.entries}

__all__ = ["NPS", "nps_psm_entry"]
