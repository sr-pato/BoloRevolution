import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

class FW:
    def __init__(self, user:str, passsword:str) -> None:
        self.USER = user
        self.PASSWORD = passsword
        self.session = None
        self.BASE_URL = 'https://filewarez.tv'
    
    def login(self):
        self.session = requests.session()
        self.session.headers["user-agent"] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        response = self.session.get(self.BASE_URL)
        soup = BeautifulSoup(response.content, "html.parser")
        form = soup.find("form")
        endpoint = f'{self.BASE_URL}/{form.get("action")}'
        form_post = {
            key:value for key, value in [(x.get("name"), x.get("value")) for x in form.find_all("input")]
        }
        form_post.update({
            "vb_login_md5password": self.PASSWORD,
            "vb_login_md5password_utf": self.PASSWORD,
            "vb_login_username": self.USER,
            "vb_login_password": '',
        })
        self.session.post(endpoint, data=form_post)
    
    def search(self, query):
        if self.session is None:
            raise Exception("Not logged.")

    def get_topic_info(self):
        pass
    
    
    def logout(self):
        pass
