from utils import generate_default_session, sanitize_str_html, sanitize_url_html
from bs4 import BeautifulSoup
from urllib.parse import parse_qs, urlparse
import re

class ASC:
    def __init__(self, user, password) -> None:
        self.USER = user
        self.PASSW = password
        self.session = None
        self.BASE_URL = 'https://cliente.amigos-share.club'

    def login(self):
        self.session = generate_default_session()
        self.session.get(self.BASE_URL)
        self.session.post(f"{self.BASE_URL}/account-login.php", data={"returnto": "/", "username": self.USER, "password": self.PASSW, "autologout": "yes"})
    
    def logout(self):
        if self.session is None:
            raise Exception("Not logged.")
        self.session.get(f"{self.BASE_URL}/account-logout.php")
    
    def search_uploads(self, keywords:str, _infos_sep:str="|"):
        if self.session is None:
            raise Exception("Not Logged.")
        response = self.session.get(f"{self.BASE_URL}/torrents-search.php", params={"search": keywords})
        soup = BeautifulSoup(response.content, "html.parser")
        div_results = soup.find("div", {"id": "fancy-list-group"})
        if div_results is None:
            return div_results
        results = []
        for result in div_results.find_all("li"):
            div_content = result.find("div", {"class": "list-group-item-content"})
            title = sanitize_str_html(div_content.find("a").text)
            url = div_content.find("a").get("href")
            infos = [sanitize_str_html(info.text) for info in div_content.find("p", {"class": "list-group-item-text m-0"}).find_all("span")]
            torrent_id = parse_qs(urlparse(url).query)["id"][0]
            results.append({
                "title": title,
                "url": url,
                "infos": f"{_infos_sep}".join(infos),
                "torrent_id": torrent_id
            })
        return results
        # TODO: add pagination scrap.
    
    def get_torrent_info(self, torrent_id:int|str):
        if self.session is None:
            raise Exception("nod logged")
        response = self.session.get(f"{self.BASE_URL}/torrents-details.php", params={"id": torrent_id})
        soup = BeautifulSoup(response.content, "html.parser")
        seeders = sanitize_str_html(soup.find("button", {"class": "btn btn-success"}).get_text())
        seeders = re.search("[0-9]+", seeders).group()
        leechers = sanitize_str_html(soup.find("button", {"class": "btn btn-danger"}).get_text())
        leechers = re.search("[0-9]+", leechers).group()
        table = soup.find("table")
        lines = table.find_all("tr")
        title = sanitize_str_html(lines[0].find_all("td")[1].get_text())
        size = [sanitize_str_html(line.find_all("td")[1].text) for line in lines if 'Tamanho' in line.find("td").text][0]
        poster_url = sanitize_url_html(soup.find("a", {"data-fancybox": "gallery"}).get("href"))
        infos = {
            "title": title,
            "seeders": int(seeders),
            "leechers": int(leechers),
            "size": size,
            "poster": poster_url
        }
        
        return infos
    
    def download_torrent_file(self, torrent_id:str|int):
        if self.session is None:
            raise Exception("not logged.")
        response = self.session.get(f"{self.BASE_URL}/download.php", params={"id": torrent_id})
        return response.content