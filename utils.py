import re
import requests
from downloaders.base import Downloader

def sanitize_str_html(string: str) -> str:
    string = re.sub("\n\t", "", string).strip()
    while '  ' in string:
        string = string.replace("  ", "")
    return string.strip()

def generate_default_session() -> requests.Session:
    session = requests.session()
    session.headers["user-agent"] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    session.headers["pragma"] = "no-cache"
    return session

def sanitize_url_html(url:str) -> str:
    ## Specifique case.
    while url.count("//") > 1:
        position = url.find("//", 7)
        url = url[:position] + url[position+1:]
    return url

def get_downloader_by_url(url:str) -> Downloader:
    """Obtém um downloader baseado na URL inserida."""
    patterns = {
        "ifunny": ["https?://br.ifunny.co", "https?://ifunny.co"],
        "vimeo": ["https?://vimeo.com", "https?://player.vimeo.com"],
        "youtube": ["https?://youtube.com", "https?://youtu.be"],
        "xvideos": ["https?://xvideos.com", ],
        "any": ["http?://"]
    }

    for pattern in patterns["ifunny"]:
        if re.search(pattern, url):
            from downloaders.ifunny import Ifunny
            return Ifunny
    
    for pattern in patterns["vimeo"]:
        if re.search(pattern, url):
            from downloaders.vimeo import Vimeo
            return Vimeo
    
    for pattern in patterns["youtube"]:
        if re.search(pattern, url):
            from downloaders.youtube import Youtube
            return Youtube
    
    for pattern in patterns["xvideos"]:
        if re.search(pattern, url):            
            from downloaders.xvideos import Xvideos
            return Xvideos
    
    for pattern in pattern["any"]:
        from downloaders.http import HttpGet
        return HttpGet
    
    return None