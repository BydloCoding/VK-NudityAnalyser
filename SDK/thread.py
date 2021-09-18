import threading

from . import listExtension


class ThreadManager(object):
    thread_poll = listExtension.ListExtension()
    
    @classmethod
    def get_main_thread(cls):
        return cls.threadByName("Main")

    @classmethod
    def threadByName(cls, name):
        return cls.thread_poll.find(lambda item: item.name == name)

    def changeInterval(self, name, newInterval):
        thread = self.threadByName(name)
        thread.interval = newInterval

    @classmethod
    def create_task(cls, name, task, *args, **kwargs):
        thread = cls.threadByName(name)
        thread.create_task(task, *args, **kwargs)

    def __getitem__(self, key):
        return self.threadByName(key)


class Thread(threading.Thread):
    def __init__(self, *args, **kwargs) -> None:
        ThreadManager.thread_poll.append(self)
        self.tasks = []
        super().__init__(*args, **kwargs)

    def create_task(self, task, *args, **kwargs):
        self.tasks.append((task, args, kwargs))

    def check_tasks(self):
        while len(self.tasks) > 0:
            task = self.tasks.pop(0)
            task[0](*task[1], **task[2])

def requires_start(func):
    def call_wrap(*args, **kwargs):
        thread = ThreadManager.get_main_thread()
        if not hasattr(thread, "started") or not thread.started:
            def dummy():
                thread = ThreadManager.get_main_thread()
                if not hasattr(thread, "started") or not thread.started:
                    return
                threading.current_thread().stopped = True
                func(*args, **kwargs)
            every(interval=5)(dummy)
        else:
            func(*args, **kwargs)

    return call_wrap

def threaded(*args, **kwargs):
    def func_wrap(func):
        def call_wrap(*a, **b):
            Thread(*args, **kwargs, target=func, args=a, kwargs=b).start()
        return call_wrap      
    return func_wrap

class Every(Thread):
    def __init__(self, interval, *args, onExecCallback=None, callback = None, **kwargs):
        if callback is not None:
            self.callback = callback
        elif hasattr(self, "loop"):
            self.callback = self.loop
        else:
            raise Exception("Callback wasn't provided.")
        self.interval = interval
        self.stopped = False
        self.event = threading.Event()
        self.onExecCallback = onExecCallback
        self.args = args
        super().__init__(**kwargs)
        self.start()

    # override
    def run(self):
        self.callback(*self.args)
        while not self.event.wait(self.interval) and not self.stopped:
            if self.onExecCallback is not None:
                self.onExecCallback()
            self.check_tasks()
            self.callback(*self.args)


def every(interval, *myArgs, callback=None, **myKwargs):
    def func_wrap(func):
        return Every(interval, *myArgs, onExecCallback=callback, **myKwargs, callback=func)

    return func_wrap
