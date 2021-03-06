# based on VK-SDK v1.3

import re

import requests
import vk_api
from flask import Flask, redirect, request
from vk_api.longpoll import VkEventType, VkLongPoll

from SDK import cmd, database, imports, jsonExtension, user
from SDK.listExtension import ListExtension
from SDK.stringExtension import StringExtension
from SDK.thread import Thread, ThreadManager, requires_start

config = jsonExtension.load("config.json")

#https://oauth.vk.com/authorize?client_id=7944022&scope=73732&redirect_uri=http://127.0.0.1:5000/callback&display=page&response_type=code&revoke=1
app = Flask(__name__)
@app.route("/callback")
@requires_start
def callback_route():
    code = request.url.split("=")[1]
    if code.startswith("access_denied"):
        return redirect("https://oauth.vk.com/blank.html", code=200)
    response = requests.get(f"https://oauth.vk.com/access_token?client_id={config['client_id']}&client_secret={config['client_secret']}&redirect_uri={config['redirect_uri']}&code={code}").json()
    access_token = response["access_token"]
    user_id = response['user_id']
    database.ThreadedStruct("user_profile", one_time=True, user_id = user_id).token = access_token
    user.User(ThreadManager.get_main_thread().vk, user_id).write("Авторизация прошла успешно! Напишите \"Анализ\", чтобы начать анализ.", keyboard="Анализ")
    return redirect("https://oauth.vk.com/blank.html", code=200)

class LongPoll(VkLongPoll):
    def __init__(self, instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance

    def listen(self):
        while True:
            try:
                self.instance.check_tasks()
                updates = self.check()
                for event in updates:
                    yield event
            except:
                # we shall participate in large amount of tomfoolery
                pass


class MainThread(Thread):
    def run(self):
        self.config = config
        imports.ImportTools(["packages", "Structs"])
        self.database = database.Database(
            config["db_file"], config["db_backups_folder"], self)
        self.db = self.database
        database.db = self.database
        self.vk_session = vk_api.VkApi(token=self.config["vk_api_key"])
        self.longpoll = LongPoll(self, self.vk_session)
        self.vk = self.vk_session.get_api()
        self.group_id = "-" + re.findall(r'\d+', self.longpoll.server)[0]
        self.started = True
        print("Bot started!")
        super().__init__(name="Main")
        self.poll()

    def parse_attachments(self):
        for attachmentList in self.attachments_last_message:
            attachment_type = attachmentList['type']
            attachment = attachmentList[attachment_type]
            access_key = attachment.get("access_key")
            if attachment_type != "sticker":
                self.attachments.append(
                    f"{attachment_type}{attachment['owner_id']}_{attachment['id']}") if access_key is None \
                    else self.attachments.append(
                    f"{attachment_type}{attachment['owner_id']}_{attachment['id']}_{access_key}")
            else:
                self.sticker_id = attachment["sticker_id"]

    def reply(self, *args, **kwargs):
        return self.user.write(*args, **kwargs)

    def wait(self, x, y):
        return cmd.set_after(x, self.user.id, y)

    def write(self, user_id, *args, **kwargs):
        user.User(self.vk, user_id).write(*args, **kwargs)

    def set_after(self, x, y=None):
        if y is None:
            y = []
        cmd.set_after(x, self.user.id, y)

    def poll(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                self.attachments = ListExtension()
                self.sticker_id = None
                self.user = user.User(self.vk, event.user_id)
                self.raw_text = StringExtension(event.message.strip())
                self.event = event
                self.text = StringExtension(self.raw_text.lower().strip())
                self.txtSplit = self.text.split()
                self.command = self.txtSplit[0] if len(
                    self.txtSplit) > 0 else ""
                self.args = self.txtSplit[1:]
                self.messages = self.user.messages.getHistory(count=3)["items"]
                self.last_message = self.messages[0]
                self.attachments_last_message = self.last_message["attachments"]
                self.parse_attachments()
                cmd.execute_command(self)


if __name__ == "__main__":
    _thread = MainThread()
    _thread.start()
    _flask = Thread(target=app.run, name="Flask")
    _flask.start()
