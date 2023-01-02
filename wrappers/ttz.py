import requests
from bs4 import BeautifulSoup
from utils import sanitize_str_html
from urllib.parse import urlparse, parse_qs

class TTZ:
    def __init__(self, user: str, password: str):
        self.USER = user
        self.PASSWORD = password
        self.BASE_URL = 'https://www.thetoonz.com'
        self.session = None
    
    def login(self):
        self.session = requests.session()
        self.session.headers["user-agent"] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        # TODO: get user-agent from .env
        response = self.session.get(f"{self.BASE_URL}/")
        soup = BeautifulSoup(response.content, "html.parser")
        form_login = soup.find("form", {"id": "login"})
        post_form = {
            key:value for key, value in 
            [(tag.get("name", ""), tag.get("value", "")) for tag in form_login.find_all("input", {"type": "hidden"})]
        }
        post_form.update({
            "username": self.USER,
            "password": self.PASSWORD,
            "autologin": "on",
            "viewonline": "on",
            "login": "Entrar"
        })
        self.session.post(f"{self.BASE_URL}/ucp.php?mode=login", data=post_form,  headers={'referer': f"{self.BASE_URL}/portal?sid={post_form['sid']}"})
        self.SID = post_form["sid"]
        # TODO: Add self.is_logged()
    
    def search_uploads(self, keywords:str,  terms:str='all', sf:str='titleonly'):
        """Search Uploads from the Site

        Args:
            keywords (str): The search
            terms (str, optional): Define if search `all` or `any` terms of keyword. Defaults to `all`.
            sf (str, optional): Define only titles or in body description in uploads. Defaults to 'titleonly'.
        
        Returns:
            list: List of dicts info of results.
        """
        
        if self.session is None:
            raise Exception('Not Logged')
        # self.session.get(f"{self.BASE_URL}/search.php", headers={'referer': f"{self.BASE_URL}/index.html?&sid={self.SID}"})
        post_params = {
            "keywords": keywords,
            "terms": terms,
            "sf": sf,
            # 'sr': 'topics' # NO!
        }
        response = self.session.get(f"{self.BASE_URL}/search.php", params=post_params, headers={"referer": "{self.BASE_URL}/search.php"})
        results = []
        soup = BeautifulSoup(response.content, "html.parser")
        div_results = soup.find("div", {"class": "postrow_container"})
        if div_results is None:
            self.logout()
            self.login()
            return self.search_uploads(keywords=keywords, terms=terms, sf=sf)
        for div_result in div_results.find_all("div", {"class": "clearfix"})[:-1]:
            try:
                a_tags = div_result.find_all("a")
                post_title = sanitize_str_html(a_tags[0].text)
                post_url = f"{self.BASE_URL}/{a_tags[0].get('href').lstrip('./')}" # href = "./viewpost... "
                post_uploader = sanitize_str_html(a_tags[1].text)
                post_uploader_url = f"{self.BASE_URL}/{a_tags[1].get('href').lstrip('/')}"
                results.append({
                    "title": post_title,
                    "url": post_url,
                    "uploader": post_uploader,
                    "uploader_url": post_uploader_url,
                    "topic_id": parse_qs(urlparse(post_url).query).get("p")[0]
                })
            except:
                pass
        # TODO: Navigate in the paginations
        return results
    
    def logout(self):
        if self.session is None:
            raise Exception('Not Logged')
        self.session.get(f'{self.BASE_URL}/ucp.php', params={"mode": "logout", "sid": self.SID})
        return "Success"
    
    def get_topic_infos(self, topic_id:str|int, retrie:bool=False):
        """Get a links from any post to download or stream

        Args:
            topic_url (str): Topic url to get links
        
        Returns:
            dict: infos where keys = ['title', 'poster', 'infos', 'final', 'sinopse', 'links']
        """
        if self.session is None:
            raise Exception('Not Logged')
        topic_url = f'{self.BASE_URL}/viewtopic.php'
        response = self.session.get(topic_url, params={'p': topic_id})
        topic_content = None
        soup = BeautifulSoup(response.content, "html.parser")
        div_content = soup.find("div", {"class": "postrow_container"})
        if div_content is None and not retrie:
            self.logout()
            self.login()
            return self.get_topic_infos(topic_id, True)
        profile_id = div_content.find("div", {"class": "clearfix"}).get("id").strip("p")
        try:
            thanks_url = div_content.find("a", {"id": f"lnk_thanks_post{profile_id}"}).get('href').lstrip("./")
            thanks_url = f"{self.BASE_URL}/{thanks_url}"
            soup = BeautifulSoup(self.session.get(thanks_url).content, "html.parse")
        except:
            pass
        response = self.session.get(topic_url, params={'p': topic_id})
        soup = BeautifulSoup(response.content, "html.parser")
        div_content = soup.find("div", {"class": "content"})
        content_lines = [line for line in div_content.text.splitlines() if line.strip() != '']
        topic_poster = soup.find('img', {"class": "img-responsive img-post"}).get('src')
        topic_infos = []
        topic_title = []
        topic_final = []
        keywords = ['Título Brasil / Original', 'Gênero', 'Classificação Indicativa', 'Ano', 'Qualidade', 'Idiomas', 'Legendas', 'Formato', 'Vídeo Info', 'Resolução', 'Áudio Info', 'Duração', 'Tamanho', 'Ripador', 'Subber', 'Uploader', 'Server']
        has = False
        for i, line in enumerate(content_lines.copy()):
            if line.count(": ") == 1 and line.split(": ")[0] in keywords:
                has = True
                topic_infos.append(sanitize_str_html(content_lines[i]))
            else:
                if not has:
                    topic_title.append(sanitize_str_html(line))
                else:
                    topic_final.append(sanitize_str_html(line))
        div_links = soup.find("div", {"class": "hidebox hidebox_visible"})
        links = [(' '.join(a.find('img').get('title', 'title').split()[2:]), a.get("href")) for a in div_links.find_all('a')[1:]]
        topic_content = {
            'title': topic_title[0],
            'sinopse': ''.join(topic_title[2:]),
            'poster': topic_poster,
            'infos': '\n'.join(topic_infos),
            'final': '\n'.join(topic_final),
            'links': links
        }
        return topic_content
