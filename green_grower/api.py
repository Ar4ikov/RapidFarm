# | Created by Ar4ikov
# | Время: 18.12.2020 - 05:14
from time import sleep, time

from regex import match
from threading import Thread, main_thread
from serial import Serial
from serial.tools import list_ports
from sql_extended_objects import ExtObject as DatabaseObject
from serial.serialutil import SerialException, SerialTimeoutException
from flask import request, jsonify


class GG_API:
    def __init__(self, root):
        self.root = root

    @staticmethod
    def key_sorting(data: dict):
        code_keys = ["status", "response", "error"]
        sorting = lambda x: code_keys.index(str(x[0])) if str(x[0]) in code_keys else len(str(x[0]))

        return dict(sorted(list(data.items()), key=sorting))

    @staticmethod
    def get_data():
        return request.args.to_dict() or request.form.to_dict() or request.data or request.json or {}

    def response(self, code, data):
        return jsonify(self.key_sorting({"status": code, "response": data, "ts": time()})), code

    def error(self, code, data):
        return jsonify(self.key_sorting({"status": code, "response": data, "ts": time()})), code

    def route_methods(self) -> bool:

        @self.root.route("/add_sensor", methods=["GET", "POST"])
        def add_sensor():
            data = self.get_data()

            if "name" not in data or "sensor_id" not in data:
                return self.error(400, {"error_message": "Не все параметры были включены", "params": data})

            sensor_same = self.root.database.select_all(
                "sensors", DatabaseObject, where=f"""`sensor_id` = '{data["sensor_id"]}'"""
            )

            if sensor_same:
                return self.error(400, {"error_message": "Датчик с таким ID уже существует", "params": data})

            sensor = DatabaseObject()
            sensor.name = data["name"]
            sensor.sensor_id = data["sensor_id"]

            if "metric" in data:
                sensor.metric = data["metric"]

            self.root.database.insert_into("sensors", sensor)

            return self.response(200, {"params": data})

        @self.root.route("/remove_sensor", methods=["GET", "POST"])
        def remove_sensor():
            data = self.get_data()

            if "sensor_id" not in data:
                return self.error(400, {"error_message": "Не все параметры были включены", "params": data})

            sensor_same = self.root.database.select_all(
                "sensors", DatabaseObject, where=f"""`sensor_id` = '{data["sensor_id"]}'"""
            )

            if not sensor_same:
                return self.error(400, {"error_message": "Такого датчика нет или он уже удалён.", "params": data})

            self.root.database.commit(f"""DELETE FROM `sensors` WHERE `sensor_id` = '{data["sensor_id"]}';""")

            return self.response(200, {"params": data})

        @self.root.route("/get_sensors", methods=["GET", "POST"])
        def get_sensors():
            sensors = self.root.database.select_all("sensors", DatabaseObject)

            return self.response(
                200, {"sensors": [{"name": x.name, "sensor_id": x.sensor_id, "metric": x.metric} for x in sensors]}
            )

        @self.root.route("/add_data", methods=["GET", "POST"])
        def add_data():
            data = self.get_data()

            if "sensor_id" not in data or "value" not in data:
                return self.error(400, {"error_message": "Не все параметры были включены", "params": data})

            data_ = DatabaseObject()
            data_.sensor_id = data["sensor_id"]
            data_.value = data["value"]
            data_.date = time()

            self.root.database.insert_into("data", data_)

            return self.response(200, {"params": data})

        return True


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

