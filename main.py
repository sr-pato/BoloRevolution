import sqlite3
import telebot
import dotenv
import os
import threading
import datetime
import openai
from wrappers.ttz import TTZ
from wrappers.asc import ASC
from wrappers.qbittorrent import QBittorrent
from tasks import download_progress_message_update, UploadToDrive
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import get_downloader_by_url

load_db = lambda: sqlite3.connect("bolo.db")
get_datetime = lambda: datetime.datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

if not os.path.isfile(".env"):
    raise Exception('Enviroment File does not exists.')
enviroment = dotenv.dotenv_values()

openai.api_key = enviroment["TOKEN_API_OPENAI"]

send_to_bolo = lambda bot, message: bot.send_message(chat_id=enviroment['BOLO_ID'], text=message, parse_mode="HTML")

class Invoker:
    def __init__(self) -> None:
        self.user_id = None
        self.username = None
        self.account_name = None
        self.count_requests = None
        self.is_banned = None
        self.permission_level = None

class HandlerCommand:
    def __init__(self, bot: telebot.TeleBot, command: str, args: list, invoker: Invoker, message: telebot.types.Message) -> None:
        self.telegram_bot = bot
        self.command = command
        self.args = args
        self.invoker = invoker
        self.message = message
        self.conn = load_db()
        self.is_valid = False
        self.min_args = None
        self.description = None
        self.permission_level = None
        self.retrieve_command()
        self.status = None
        self.can_execute = False
        if self.permission_level > self.invoker.permission_level:
            self.status = 'Você não tem permissão de invokar esse comando :D'
        if len(self.args) < self.min_args:
            self.status = 'Quantidade mínima de argumentos não atingida.'
        if not self.is_valid:
            self.status = 'Comando inválido.'
        if self.status is None:
            self.execute()
        if self.status is not None:
            self.telegram_bot.send_message(chat_id=self.message.chat.id, text=self.status, reply_to_message_id=self.message.id, parse_mode="HTML")
    
    def retrieve_command(self):
        commands = self.conn.execute("SELECT command_name, min_args, description, syntax, permission_level FROM comandos").fetchall()
        commands_names = [c[0] for c in commands]
        commands = [{key:value for key, value in zip(['name', 'min_args', 'desc', 'syntax', 'perm_lvl'], command)} for command in commands]
        if self.command in commands_names:
            self.is_valid = True
            for command in commands:
                if command['name'] == self.command:
                    self.min_args = command['min_args']
                    self.description = command['desc']
                    self.permission_level = command['perm_lvl']
                    self.syntax = command['syntax']
                    break
    
    def execute(self):
        if self.command in ['pedido']:
            self.user_request()
        elif self.command in ['managerequest']:
            self.manage_request()
        elif self.command in ['statuspedido']:
            self.status_request()
        elif self.command in ['managestatus']:
            self.manage_status()
        elif self.command in ['search']:
            self.search()
        elif self.command in ['postinfo']:
            self.get_post_info()
        elif self.command in ['linktodrive']:
            self.link_to_drive_downloader()
        elif self.command in ["gerartexto", "gtxt", "gerartxt", "generatetxt"]:
            self.generate_text_openai()
        elif self.command in ["gerarimg"]:
            self.generate_image_openai()
    
    def generate_image_openai(self):
        if 'x' in self.args[0]:
            size = self.args.pop(0)
        else:
            size = '1024x1024'
        prompt = " ".join(self.args)
        try:
            image = openai.Image.create(prompt=prompt, n=1, size=size)
        except Exception as e:
            self.telegram_bot.reply_to(self.message, f"Exception: <code>{e}</code>", parse_mode="html")
        else:
            self.telegram_bot.send_photo(self.message.chat.id, image["data"][0]['url'], reply_to_message_id=self.message.message_id)
    
    def generate_text_openai(self):
        # sintax: /gerartexto texto aqui
        prompt = " ".join(self.args)
        completion = openai.Completion.create(engine="text-davinci-003", prompt=prompt, temperature=0.5, max_tokens=300, n=1, stop=None)
        self.telegram_bot.reply_to(self.message, completion.choices[0].text)
    
    def link_do_drive_downloader(self):
        # sintax: /linktodrive linkhere
        downloader = get_downloader_by_url(self.args[0])
        if downloader is None:
            self.status = "Plataforma não identificada."
            return

        downloader.__init__(self.args[0], self.telegram_bot, self.message, enviroment)
        is_poster = False
        infos = downloader.get_infos()
        # TODO: Extend this if's to a new class
        if infos["type"] == 'ifunny':
            is_poster = True
            caption = f"Infos:\n\nPlataforma: Ifunny\nSimiles: {infos['smiles']}\nComments: {infos['comments']}\nUploader: {infos['uploader']}"
            poster_url = infos['poster']
        # elif infos["type"] == "xvideos":
        
        #-----#
        conn = load_db()
        # TODO: terminar isso daqui, to com sono, vou dormir, fui.
        conn.execute("INSERT INTO downloads")
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton('Download to TG', callback_data='downIfunny ? telegram'.replace("?", self.args[1]))
        )
        
        if is_poster:
            self.telegram_bot.send_photo(self.invoker.chat.id, poster_url, caption, reply_markup=keyboard, parse_mode="HTML")

    def get_post_info(self):
        # sintax: /getpostinfo plataform post_id
        if self.args[0] == 'ttz':
            ttz = TTZ(enviroment['TTZ_USER'], enviroment['TTZ_PASSWORD'])
            msg = self.telegram_bot.send_message(chat_id=self.message.chat.id, text=f"Logando como {enviroment['TTZ_USER']}...")
            ttz.login()
            self.telegram_bot.edit_message_text(f"Logado com sucesso! Buscando infos da postagem...", chat_id=msg.chat.id, message_id=msg.message_id)
            post_info = ttz.get_topic_infos(self.args[1])
            if post_info is None:
                self.status = 'ID da postagem não encontrada.'
                ttz.logout()
                return
            links = [f'<a href="{link}">{title}</a>' for title, link in post_info['links']]
            caption_text = f"Título: {post_info['title']}\nFontes: {' | '.join(links)}"
            self.telegram_bot.send_photo(chat_id=msg.chat.id, photo=post_info['poster'], caption=caption_text, parse_mode="HTML")
            self.telegram_bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
            ttz.logout()
        if self.args[0] == 'asc':
            asc = ASC(enviroment['ASC_USER'], enviroment['ASC_PASSWORD'])
            msg = self.telegram_bot.send_message(chat_id=self.message.chat.id, text=f"Logando como {enviroment['ASC_USER']}...")
            asc.login()
            self.telegram_bot.edit_message_text(f"Logado com sucesso! Buscando infos da postagem...", chat_id=msg.chat.id, message_id=msg.message_id)
            post_info = asc.get_torrent_info(self.args[1])
            if post_info is None:
                self.status = 'ID da postagem não encontrada.'
                asc.logout()
                return
            
            keyboard = InlineKeyboardMarkup()
            keyboard.row_width = 2
            keyboard.add(
                InlineKeyboardButton('Download to TG', callback_data='downTorrentRequest asc ? telegram'.replace("?", self.args[1])),
                InlineKeyboardButton('Download to Gdrive', callback_data='downTorrentRequest asc ? googleDrive'.replace("?", self.args[1]))
            )
            caption_text = f"Título: {post_info['title']}\nTamanho: {post_info['size']}\nSeeders: {post_info['seeders']}\nLeechers: {post_info['leechers']}"
            self.telegram_bot.send_photo(chat_id=msg.chat.id, photo=post_info['poster'], caption=caption_text, reply_markup=keyboard, parse_mode="HTML")
            self.telegram_bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
            asc.logout()
    
    def search(self):
        # sintax: /search platform keywords
        if self.args[0] == 'ttz':
            ttz = TTZ(enviroment['TTZ_USER'], enviroment['TTZ_PASSWORD'])
            msg = self.telegram_bot.send_message(chat_id=self.message.chat.id, text=f"Logando como {enviroment['TTZ_USER']}...")
            ttz.login()
            self.telegram_bot.edit_message_text(f"Logado com sucesso! Pesquisando termo especificado...", chat_id=msg.chat.id, message_id=msg.message_id)
            results = ttz.search_uploads(' '.join(self.args[1:]))
            self.status = f'Total de {len(results)} resultados encontrados.'
            for result in results:
                self.status = f'''{self.status}\n------\nTítulo: <a href="{result['url']}">{result["title"]}</a>\nUploader: <a href="{result['uploader_url']}">{result['uploader']}</a>\nComando: <code>/postinfo ttz {result['topic_id']}</code>'''
            self.telegram_bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
            ttz.logout()
        elif self.args[0] == 'asc':
            asc = ASC(enviroment["ASC_USER"], enviroment["ASC_PASSWORD"])
            msg = self.telegram_bot.send_message(chat_id=self.message.chat.id, text=f"Logando como {enviroment['ASC_USER']}...")
            asc.login()
            self.telegram_bot.edit_message_text(f"Logado com sucesso! Pesquisando termo especificado...", chat_id=msg.chat.id, message_id=msg.message_id)
            results = asc.search_uploads(' '.join(self.args[1:]), ', ')
            if results is None:
                self.status = "Nenhum resultado encontrado."
                asc.logout()
                return
            self.status = f'Total de {len(results)} resultados encontrados.'
            for result in results:
                self.status = f'''{self.status}\n-----\nTítulo: <a href="{result['url']}">{result['title']}</a>\nInfos: <code>{result['infos']}</code>\nComando: <code>/postinfo asc {result['torrent_id']}</code>'''
            asc.logout()
        else:
            self.status = f'Plataforma {self.args[0]} não encontrada'

    def manage_status(self):
        # syntax: /managestatus pedido_id
        pass
    
    def status_request(self):
        # syntax: /statuspedido pedido_id
        request_status = self.conn.execute("SELECT status FROM statuses WHERE user_id = ? AND request_id = ?", (self.invoker.user_id, self.args[0])).fetchone()
        if request_status is not None:
            self.status = request_status[0]
        else:
            self.status = 'Não existe pedido para o seu usuário na id inserida.'
    
    def manage_request(self):
        # syntax: /managerequest action reason
        # this function must be called when has a reply_to_message action.
        if self.message.reply_to_message is None:
            self.status = 'Essa função deve ser chamada quando responde à uma mensagem de pedido.'
            return
        replied_message_id = self.message.reply_to_message.message_id
        request_info = self.conn.execute("SELECT request_id, account_name, username, user_id, created_at, status FROM requests WHERE request_msg_id = ?", (replied_message_id, )).fetchone()
        if request_info is None:
            self.status = 'A mensagem que vc respondeu não é uma mensagem de pedido.'
            return
        reason = " ".join(self.args[2:])
        if self.args[0] in ['aceitar', 'accept', 'y', 'aceito']:
            self.conn.execute("UPDATE request SET status = 2 WHERE request_msg_id = ?", (replied_message_id, ))
            self.conn.commit()
            keyboard = InlineKeyboardMarkup([
                                    InlineKeyboardButton('Sim!', callback_data='responseUser sim ?'.replace("?", request_info[0])),
                                    InlineKeyboardButton('Não...', callback_data='responseUser sim ?}'.replace("?", request_info[0]))
                                ], row_width=2)
            self.telegram_bot.send_message(chat_id=request_info[3], text=f'Olá, {request_info[1]}, seu pedido de script foi aceito. Eis as informações dadas pelo programador:\n{reason}\nVocê aceita estes termos?', reply_markup=keyboard)
            self.status = 'O usuário foi avisado de seus termos para desenvolvimento do script.'
        elif self.args in ['rejeitar', 'reject', 'n', 'rejeito']:
            self.conn.execute("UPDATE request SET status = -1 WHERE requesrs_msg_id = ?", (replied_message_id, ))
            self.conn.commit()
            self.telegram_bot.send_message(chat_id=request_info[3], text=f'Olá, {request_info[1]}, seu pedido de script foi rejeitado. Eis as informações dadas pelo programador:\n{reason}')
            self.status = 'O usuário foi avisado sobre sua rejeição.'
        else:
            self.status = 'Só se pode aceitar ou rejeitar algum pedido, fdp'

    def user_request(self):
        # syntax: /pedido descricao aqui
        description = " ".join(self.args)
        current_datetime = get_datetime()
        self.conn.execute("INSERT INTO requests (account_name, username, user_id, description, created_at, status) VALUES (?, ?, ?, ?, ?, ?)", (self.invoker.account_name, self.invoker.username, self.invoker.user_id, description, current_datetime, 0))
        # This status is:
        # 0 = Open, 1 = Accepted, -1 = rejected, 2 - Waiting Response, 3 = Accepted and programming, -3 = Rejected by user, 4 - Complete and waiting payment., 5 - :D
        self.conn.commit()
        request_id = self.conn.execute("SELECT request_id FROM requests WHERE user_id = ? AND created_at = ?", (self.invoker.user_id, current_datetime))[0]
        request_msg = send_to_bolo(self.telegram_bot, f'Novo Pedido!\nNome: {self.invoker.account_name}\nUserID: {self.invoker.user_id}\nUsername: <a href="tg://user?={self.invoker.user_id}">{self.invoker.username}</a>\nCriado em: {current_datetime}\nRequestID: {request_id}\nDescrição: {description}')
        self.status = f'Pedido recebido com sucesso!\nInformações:\nNome: {self.invoker.account_name}\nUserID: {self.invoker.user_id}\nUsername: <a href="tg://user?={self.invoker.user_id}">{self.invoker.username}</a>\nCriado em: {current_datetime}\nRequestID: {request_id}\nDescrição: {description}'
        self.conn.execute("UPDATE requests SET request_msg_id = ? WHERE user_id = ? AND created_at = ?", (request_msg.message_id, self.invoker.user_id, current_datetime))
        self.conn.commit()

class HandlerCallBack:
    def __init__(self, bot, callback: telebot.types.CallbackQuery, invoker) -> None:
        self.telegram_bot = bot
        self.callback = callback
        self.invoker = invoker
        self.status = None
        self.analysis()
        if self.status is not None:
            self.telegram_bot.send_message(chat_id=self.invoker.user_id, text=self.status, parse_mode="HTML")
    
    def analysis(self):
        self.args = [x.strip() for x in self.callback.data.split()]
        if self.args[0] == 'responseUser':
            # args = responseUser option eventId
            self.response_user(self.args[1], self.args[2])
        if self.args[0] == 'downTorrentRequest':
            # args = downTorrentRequest forum torrent_id cloud
            self.handle_torrent_download(self.args[1], self.args[2], self.args[3])
    
    def handle_torrent_download(self, forum:str, torrent_id:str, cloud:str):
        qb = QBittorrent(enviroment["QBIT_HOST"])
        qb.login(enviroment["QBIT_USER"], enviroment['QBIT_PASSWORD'])
        category_name = f"asc {torrent_id}"
        if forum == 'asc':
            # self.telegram_bot.send_message(chat_id=self.callback.message.chat.id, text=f"Você selecionou fazer download do torrent_id {torrent_id} do fórum {forum} para a cloud {cloud} forém esta função ainda está em construção :p")
            asc = ASC(enviroment['ASC_USER'], enviroment['ASC_PASSWORD'])
            asc.login()
            raw_torrent_file = asc.download_torrent_file(torrent_id)
            status = qb.download_from_file(raw_torrent_file, category=category_name)
            msg = self.telegram_bot.send_message(chat_id=self.callback.message.chat.id, text=status, parse_mode="HTML")
            download_progress_message_update(self.telegram_bot, msg, qb, category_name, float(enviroment['UPDATE_PROGRESS_MSG_SECS_DELAY']))
        msg = self.telegram_bot.send_message(chat_id=self.callback.message.chat.id, text="Uploading...")
        if cloud == 'googleDrive':
            UploadToDrive(self.telegram_bot, msg, qb, category_name, enviroment["REMOTE_RCLONE"], float(enviroment["UPDATE_PROGRESS_MSG_SECS_DELAY"]))

    def response_user(self, request_id, option):
        self.conn = load_db()
        status = self.conn.execute("SELECT status FROM requests WHERE request_id = ?", (request_id, )).fetchone()[0]
        if status != 2:
            return
        if option == 'sim':
            self.conn.execute("UPDATE requests SET status = 3 WHERE request_id = ?", (request_id, ))
            self.conn.commit()
            # TODO: add management of the chats to conversations to users.
            send_to_bolo(self.telegram_bot, f'O usuário <a href="tg://user?id={self.invoker.user_id}">{self.invoker.account_name}</a> aceitou os termos do pedido de número {request_id}, comece a trabalhar, @Sr_Yuu vagabundo.')
            self.status = f'Seu pedido está sendo processado, mais informações a partir daqui é com AGENTEKSKS' # TODO: provavelmente vai ser a afrodite.
        elif option == 'nao':
            self.conn.execute("UPDATE requests SET status = -3 WHERE request_id = ?", (request_id, ))
            self.conn.commit()
            send_to_bolo(self.telegram_bot, f'O usuário <a href="tg://user?id={self.invoker.user_id}">{self.invoker.account_name}</a> rejeitou os termos do pedido de número {request_id}, bye bye, já vai tarde.')
            self.status = f"Okay, volte sempre."



class HandlerMessage:
    def __init__(self, bot, msg, is_callback) -> None:
        self.telegram_bot = bot
        self.is_callback = is_callback
        self.retrieve_user_informations(msg)
        self.message = msg
        if not is_callback:
            self.is_command = True if msg.text.startswith("/") else False
            # self.is_openai_command = True if msg.text.startswith(enviroment["OPENAI_PREFIX"]) else False
            self.retrieve_message_informations(msg)
            if self.is_command and not self.invoker.is_banned:
                self.args = [x.strip() for x in self.message.text.split()]
                self.command = self.args.pop(0)[1:]
                HandlerCommand(self.telegram_bot, self.command, self.args, self.invoker, self.message)
        else:
            HandlerCallBack(self.telegram_bot, self.message, self.invoker)
            
    def retrieve_message_informations(self, msg):
        self.message = msg
    
    def retrieve_user_informations(self, msg):
        self.invoker = Invoker()
        self.invoker.user_id = msg.from_user.id
        self.invoker.username = msg.from_user.username
        self.invoker.account_name = f"{msg.from_user.first_name if msg.from_user.first_name is not None else ''} {msg.from_user.last_name if msg.from_user.last_name is not None else ''}"
        conn = load_db()
        has_iteracted = conn.execute("SELECT requests, has_banned, permission_level FROM users WHERE user_id = ?", (self.invoker.user_id, )).fetchone()
        if not has_iteracted:
            conn.execute("INSERT INTO users (user_id, account_name, requests, has_banned, permission_level) VALUES (?, ?, ?, ?, ?)", (self.invoker.user_id, self.invoker.account_name, 0, 0, 1))
            conn.commit()
            conn.close()
            return self.retrieve_message_informations(msg)
        self.invoker.count_requests = has_iteracted[0] if has_iteracted is not None else 0
        self.invoker.is_banned = bool(has_iteracted[1])
        self.invoker.permission_level = has_iteracted[2] if has_iteracted is not None else 1 # 0 = Banido, 1 = User, 2 = mod, 3 = adm, 4 = dono.
        conn.close()


class Escritorio:
    def __init__(self) -> None:
        
        self.enviromnent = enviroment
        if self.enviromnent.get('TOKEN'):
            self.telegram_bot = telebot.TeleBot(self.enviromnent['TOKEN'])
        else:
            raise ValueError("TOKEN on enviromnment variables is not defined.")
        
        @self.telegram_bot.message_handler(content_types=["text"])
        def call_message(msg):
            threading.Thread(target=HandlerMessage, args=(self.telegram_bot, msg, False)).start()
        
        @self.telegram_bot.callback_query_handler(lambda callback: True)
        def call_callback(callback):
            threading.Thread(target=HandlerMessage, args=(self.telegram_bot, callback, True)).start()
        
        self.telegram_bot.polling()

Escritorio()