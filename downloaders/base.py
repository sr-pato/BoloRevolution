from abc import abstractmethod, abstractproperty
from os import path, getcwd
from telebot.types import Message
from telebot import TeleBot


class Downloader:
    """Base class for Downloaders"""
    @abstractmethod
    def __init__(self, url:str, bot:TeleBot, msg:Message, enviroment:dict={"DOWNLOAD_PATH": path.join(getcwd(), "temp/downloads")}) -> None:
        """Inicializa downloader"""
        self.URL = url
        self.ENVIROMENT = enviroment
        self.video_url = None
        self.msg = Message
        self.bot = bot
    
    @abstractmethod
    def get_infos(self) -> dict:
        """Obtém informações de uma certa URL"""
    
    @abstractmethod
    def download(self) -> None:
        """Faz download da url em questão"""