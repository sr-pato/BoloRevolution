from telebot import TeleBot
from wrappers.qbittorrent import QBittorrent
from time import sleep
import subprocess
import threading

from telebot.types import Message

def download_progress_message_update(bot: TeleBot, message: Message, qbit: QBittorrent, category: str, delay: int|float):
    torrent_info = qbit.torrents(category=category)[0]
    torrent_hash = torrent_info['hash']
    torrent_name = torrent_info["name"]
    torrent_size = torrent_info['size']
    torrent_info = qbit.get_torrent(torrent_hash)
    old_message = ''
    while torrent_info['total_downloaded'] < torrent_size:
        percentage = round(torrent_info['total_downloaded']*100/torrent_size, 2)
        text = f"Downloading Status:\n\nTorrent Name: <code>{torrent_name}</code>\nDownloaded: {round(torrent_info['total_downloaded']/1024**2, 2)} MB of {round(torrent_size/1024**2, 2)} MB\nPercent: {percentage}%\nUploaded: {round(torrent_info['total_uploaded']/1024**2, 2)} MB\nSeeders: {torrent_info['seeds']}\nLeechers: {torrent_info['peers']}\nDL Speed: {round(torrent_info['dl_speed']/1024**2, 2)} MB/s\nUP Speed: {round(torrent_info['up_speed']/1024**2, 2)}"
        # downloaded = (x/100) * total_size
        # => downloaded*100/total_size = x
        if text != old_message:
            bot.edit_message_text(text=text, chat_id=message.chat.id, message_id=message.message_id)
            old_message = text
            sleep(delay)
        torrent_info = qbit.get_torrent(torrent_hash)
    torrent_info = qbit.get_torrent(torrent_hash)
    text = f"Torrend Downloaded:\n\nTorrent Name: {torrent_name}\nSize: {round(torrent_size/1024**2, 2)} MB\nUploaded: {round(torrent_info['total_uploaded']/1024**2, 2)} MB"
    bot.send_message(message.chat.id, text, "HTML")
    bot.delete_message(message.chat.id, message.message_id)

def _extract_rclone_progress(buffer: str):
    reg_transferred = [x for x in buffer.split("Transferred:")]
    if reg_transferred: # transferred block is completely buffered    
        out = {}
        try:
            infos = reg_transferred[1].split()
        except:
            return False, None
        else:
            if len(infos) == 10:
                out['sent_bits'] = float(infos[0])
                out['unit_sent'] = infos[1]
                out['total_bits'] = float(infos[3])
                out['unit_total'] = infos[4].strip(',')
                out['progress'] = infos[5].strip(',')
                out['transfer_speed'] = float(infos[6])
                out['transfer_speed_unit'] = infos[7].strip(',')
                out['eta'] = infos[-1]
                return True, out
    return False, None


class UploadToDrive:
    def __init__(self, bot:TeleBot, msg:Message, qbit:QBittorrent, category:str, remote:str, delay:int|float) -> None:
        self.delay = delay
        self.ended_upload = False
        self.can_edit_message = False
        self.edited = False
        threading.Thread(target=self._can_edit_message).start()
        torrent_info = qbit.torrents(category=category)[0]
        torrent_name = torrent_info['name']
        torrent_local = torrent_info['content_path']
        command = f'rclone copy -P "{torrent_local}" {remote}:/Bolo/"{torrent_name}"'
        # From: https://github.com/Johannes11833/rclone_python/blob/ff506f9abe70adb062f0f288eaaa0208848cb010/rclone_python/rclone.py#L262
        proccess = subprocess.Popen(command, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        self.ended_upload = False
        old_progress_text = ''
        buffer = ""
        for char in iter(lambda: proccess.stdout.read(1), b''):
            try:
                var = char.decode('utf-8')
            except:
                pass
            if '\n' not in var: # se não for quebra de linha
                buffer += var # colca como variável
            else: # caso contrário, dfaça tratamento da linha com regex
                buffer += '\n'
                valid, update_dict = _extract_rclone_progress(buffer) # regex >>
                if valid: # se a linha for linha de transferência, define uma mensagemzinha
                    progress_text = f'Uploading <code>{torrent_name}</code>\n\nTotal: {update_dict["total_bits"]} {update_dict["unit_total"]}\nSpeed: {update_dict["transfer_speed"]:.1f} {update_dict["transfer_speed_unit"]}\nETA: {update_dict["eta"]}\nUploaded: {update_dict["sent_bits"]} {update_dict["unit_sent"]}\nProgress: {update_dict["progress"]}'
                    if self.can_edit_message:
                        if progress_text != old_progress_text:
                            bot.edit_message_text(progress_text, msg.chat.id, msg.message_id) # e edita lá
                            old_progress_text = progress_text
                        self.edited = True
                buffer = ""
        self.ended_upload = True
        link = subprocess.Popen(f'rclone link {remote}:/Bolo/"{torrent_name}"', stdout=subprocess.PIPE, shell=True).communicate()[0].decode("utf-8")
        bot.edit_message_text(f'Link: <a href="{link}">{torrent_name}</a>.', msg.chat.id, msg.message_id)

    def _can_edit_message(self):
        while not self.ended_upload:
            self.can_edit_message = False
            sleep(self.delay)
            self.can_edit_message = True
            while not self.edited:
                continue
            self.edited = False