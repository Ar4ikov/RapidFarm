# | Created by Ar4ikov
# | Время: 18.12.2020 - 05:14
from time import sleep, time

from regex import match
from threading import Thread, main_thread
from serial import Serial
from serial.tools import list_ports
from sql_extended_objects import ExtObject as DatabaseObject
from serial.serialutil import SerialException, SerialTimeoutException
from flask import request


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
        return str(self.key_sorting({"status": code, "response": data})), code

    def error(self, code, data):
        return str(self.key_sorting({"status": code, "response": data})), code

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


class GG_DataQueue:
    def __init__(self, root):
        self.root = root
        self.database = self.root.database

    def compile_threads(self):
        data_io_thread = GG_Thread(self, "Data I/O Thread")

        @data_io_thread.add_function("data_temps")
        def get_sensors_data():
            sensors = self.root.database.select_all("sensors", DatabaseObject)

            for sensor in sensors:
                command = self.root.serial.parse_command(
                    {"mode": "O", "sensor": sensor.name, "sensor_id": sensor.sensor_id, "value": 0}
                )

                value = self.root.serial.execute(command)
                sleep(0.1)
                if not value:
                    continue

                sensor_value = DatabaseObject()
                sensor_value.sensor_id = sensor.sensor_id
                sensor_value.value = value
                sensor_value.date = time()
                sensor_value.metric = sensor.metric

                self.database.insert_into("data", sensor_value)
                sleep(0.1)

            sleep(2)

        data_io_thread.start()
        # data_io_thread2.start()


class GG_Serial:
    def __init__(self, root, port=None, timeout=0, baudrate=115200):
        self.root = root
        self.port, self.baudrate, self.timeout = port or self.get_connection_port(), baudrate, timeout
        self.serial = Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
        # self.serial.close()

        self.SERIAL_COMMAND_SCHEME = "{mode}|{sensor}|{sensor_id}|{value}"
        self.SERIAL_COMMAND_REGEX = "[I|O]\\|\\w{1,}\\|\\w{1,2}\\d{1,2}\\|{0,}.{0,}"

    def reopen_port(self) -> bool:
        if self.serial:
            if self.serial.is_open:
                self.serial.close()

        self.serial.open()

        return True

    def switch_port_state(self) -> bool:
        if self.serial:
            if self.serial.is_open:
                self.serial.close()
            else:
                self.serial.open()

        return True

    @staticmethod
    def get_connection_port():
        ports = list_ports.comports()

        if not ports:
            return None

        for port in ports:
            try:
                _ = Serial(port.device, 9600, timeout=1)
            except SerialException or SerialTimeoutException:
                continue
            else:
                print(port.device)
                return port.device

        raise GG_Errors("There is no COM ports, try to reconnect Arduino and restart server", 100)

    def parse_command(self, data_json) -> str or GG_Errors:
        command = self.SERIAL_COMMAND_SCHEME.format(**data_json)

        if match(self.SERIAL_COMMAND_REGEX, command) is None:
            raise GG_Errors(f"The command what we need and regex does not match. -> {command}", 200)

        return command

    def execute(self, command):
        # TODO: Нужен хотфикс
        # self.reopen_port()
        """
        v = b''
            t = self.serial.read(1)
            while t != b';':
                print(t)
                v += t
                t = self.serial.read(1)

            value = v.decode()
        :param command:
        :return:
        """

        # print(self.serial.is_open)

        # self.switch_port_state()
        value = None

        if self.serial.is_open:
            print(command)
            self.serial.write(command.encode())
            sleep(0.1)
            value = self.serial.read_all()
            print(value)

            value = value.decode().replace("\r\n", "")

        # self.switch_port_state()

        return value or None
