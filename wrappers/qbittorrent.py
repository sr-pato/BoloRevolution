from qbittorrent import Client

class QBittorrent(Client):
    def __init__(self, host, verify=True, timeout=None):
        super().__init__(host, verify, timeout)