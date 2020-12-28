# | Created by Ar4ikov
# | Время: 28.12.2020 - 20:02

from threading import Thread
from time import sleep


class GG_Errors(Exception):
    def __init__(self, message, errors):
        super().__init__(message)

        self.errors = errors

    def parse_code(self):
        ...


class GG_Thread(Thread):
    def __init__(self, root, name):
        super().__init__()
        self.root = root
        self.name = name

        self.functions = []
        self.is_dead = False

    def is_already_function(self, name):
        for obj in self.functions:
            if obj["name"] == name:
                return True

        return False

    def kill(self) -> None:
        self.is_dead = True

        return None

    def add_function(self, func_name):
        def deco(func, *args, **kwargs):
            # func(*args, **kwargs)

            if self.is_already_function(func_name):
                return True

            self.functions.append(
                {
                    "name": func_name,
                    "function": func,
                    "args": args,
                    "kwargs": kwargs
                }
            )

        return deco

    def run(self):
        print(self.functions)
        while not self.is_dead:
            for func in self.functions:
                func["function"](*func["args"], **func["kwargs"])

            sleep(0.00001)
