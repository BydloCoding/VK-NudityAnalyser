from SDK.user import User
from SDK.setExtension import SetExtension
import vk_api
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from SDK.listExtension import ListExtension
from SDK.database import ProtectedProperty, Struct
from SDK.thread import threaded
from SDK.cmd import after_func, command, start_command
from urllib.parse import urlparse
import math
import time
import os
import shutil
import requests

class UserProfile(Struct):
    def __init__(self, *args, **kwargs):
        self.user_id = 0
        self.save_by = ProtectedProperty("user_id")
        self.balance = 0
        self.token = ""
        super().__init__(*args, **kwargs)

@start_command
def start_function(self):
    UserProfile(user_id = self.user.id)
    self.reply(f"Здравствуйте, {self.user.user_name}! Я с легкостью вычислю твою зависимость от порно. В ходе анализа будут проанализированы все твои фотографии. Напиши \"Продолжить\", если согласен на обработку.", keyboard = "Продолжить")
    self.set_after("continue_actions")

@after_func("continue_actions")
def continue_actions(self):
    if self.text == "Продолжить".lower():
        profile = UserProfile(user_id = self.user.id)
        if not profile.token:
            return self.reply("Необходимо пройти авторизацию. Перейдите по ссылке https://vk.cc/c5Jag1 и нажмите \"Разрешить\".")
        return analyze(self)
    else:
        self.reply("Возвращайся, когда будешь готов.", keyboard="в меню")


@command("анализ")
def analyze_command(self):
    return analyze(self)

def analyze(self):
    profile = UserProfile(user_id = self.user.id)
    if not profile.token:
        return self.reply("Необходимо пройти авторизацию. Перейдите по ссылке https://vk.cc/c5Jag1 и нажмите \"Разрешить\".")
    if profile.balance - 100 < 0:
        return self.reply("Недостаточно денег на счету! Пополните, пожалуйста, счет. (Стоимосить обработки составляет 100 рублей)")
    self.reply("Процесс анализа запущен, ожидайте.")
    analyze_function(self, profile)

def get_all(get_function, **get_function_kwargs):
    final = SetExtension()
    offset = 100
    objects = SetExtension(get_function())
    final += objects
    while len(objects) > 0:
        get_function_kwargs["offset"] = offset
        objects = SetExtension(get_function(**get_function_kwargs))
        final += objects
        offset += len(objects)
    return final


from nudenet import NudeClassifier
classifier = NudeClassifier()

@threaded(name="Analyze")
def analyze_function(self, profile):
    vk = vk_api.VkApi(token=profile.token).get_api()
    groups = get_all(lambda offset=0: vk.groups.get(offset=offset)['items'])
    groups_analyzed = len(list(filter(lambda it: it in self.config['known_porn_groups'], groups))) / len(groups) * 100
    urls = get_all(lambda offset=0: map(lambda it: it['sizes'][3]['url'], vk.photos.get(album_id='saved', rev=1, offset=offset)['items']))
    urls += get_all(lambda offset=0: map(lambda it: it['sizes'][3]['url'], vk.photos.getAll(offset=offset)['items']))
    analyzed = min(analyze_images(urls) + groups_analyzed, 100)
    User(self.vk, profile.user_id).write(f"Ты зависим на порно на {analyzed:.2f}%")

session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

def analyze_images(urls):
    file_paths = ListExtension()
    for url in urls:
        parsed = urlparse(url)
        basename = os.path.basename(parsed.path)
        file_path = f"data/images/{basename}"
        file_paths.append(file_path)
        with open(file_path, "wb") as f:
            with session.get(url, stream=True) as r:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)  
                time.sleep(0.01)
    classified = classifier.classify(file_paths)
    value = len(list(filter(lambda it: it['unsafe'] > 0.8, classified.values()))) / len(classified) * 100
    # cleanup
    for file in os.listdir("data/images"):
        os.remove(f"data/images/{file}")
    return value