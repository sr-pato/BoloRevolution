from .base import Downloader
from utils import generate_default_session, sanitize_str_html, sanitize_url_html
from bs4 import BeautifulSoup
from re import search
import os

class Ifunny(Downloader):
    def get_infos(self):
        self.sesh = generate_default_session()
        soup = BeautifulSoup(self.sesh.get(self.URL).content, "html.parser")
        infos = {"type": "ifunny"}
        buttons = soup.find_all("button", {"color": "grayDark"})
        infos["smiles"] = search("[0-9]+", buttons[1].find("span").get_text()).group()
        infos["comments"] = search("[0-9]+", buttons[2].find("span").get_text()).group()
        infos["poster"] = sanitize_url_html(soup.find("video").get("data-poster"))
        infos["uploader"] = sanitize_str_html(soup.find("a", {"class": "WiQc mVpV HJSX"}).find("span"))
        self.video_url = sanitize_url_html(soup.find("video").get("src"))
        return infos
    
    def download(self) -> None:
        if self.video_url is None:
            self.sesh = generate_default_session()
            soup = BeautifulSoup(self.sesh.get(self.URL).content, "html.parser")
            self.video_url = sanitize_url_html(soup.find("video").get("src"))
        msg = self.bot.send_message(self.msg.chat.id, f"Downloading... Progress: 0%",)
        block_size = 1024
        update_block_size = 500*(1024**2) # 500 KiB
        download_path = self.ENVIROMENT.get("DOWNLOAD_PATH")
        filename = "temp_video_ifunny.mp4"
        save_path = os.path.join(download_path, filename)
        if os.path.isfile(save_path):
            os.remove(save_path)
        response = self.sesh.get(self.video_url, stream=True)
        total = float(response.headers["Content-Length"])
        count = 0
        with open(f"{download_path}/{filename}", "wb") as f:
            for chunk in response.iter_content(block_size):
                count += block_size
                if not count%update_block_size:
                    self.bot.edit_message_text(f"Downloading...\nTotal: {total/1024**2} KiB\nDownloaded: {count/1024**2} KiB\nProgress: {round(100*count/total), 2}%", msg.chat.id, msg.message_id)
                    f.write(chunk)
        self.bot.edit_message_text(f"Downloaded!\nTotal: {total/1024**2} KiB", msg.chat.id, msg.message_id)
        return open(f"{download_path}/{filename}", "rb")