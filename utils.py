import re
import requests

def sanitize_str_html(string: str) -> str:
    string = re.sub("\n\t", "", string).strip()
    while '  ' in string:
        string = string.replace("  ", "")
    return string.strip()

def generate_default_session() -> requests.Session:
    session = requests.session()
    session.headers["user-agent"] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    return session