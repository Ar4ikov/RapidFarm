# | Created by Ar4ikov
# | Время: 27.12.2020 - 18:28
import random
from threading import Thread

from green_grower.objects import GG_Errors, GG_Thread

from serial import Serial
from serial.tools import list_ports
from serial.serialutil import SerialTimeoutException, SerialException
from requests import get, post
from regex import match
from time import time, sleep
from uuid import uuid4 as uuid


class GG_Client:
    def __init__(self, addr, protocol="http"):
        self.addr = addr
        self.protocol = protocol
        self.scheme = f"{self.protocol}://{self.addr}/"

        self.serial = GG_Serial(self)
        self.serial.queue()
        self.sensors = self.get("sensors")["response"]["sensors"]
        print(self.sensors)

        self.data_queue = GG_DataQueue(self)
        self.data_queue.compile_threads()

    def add_data(self, sensor_id, value):
        request = post(self.scheme + "add_data", data={"sensor_id": sensor_id, "value": value})

        if request.status_code != 200:
            raise GG_Errors(request.json())

        return request.json()["ts"]

    def get(self, _object):
        request = get(self.scheme + f"get_{_object}")

        if request.status_code != 200:
            raise GG_Errors(request.json())

        return request.json()

    def get_tasks(self):
        pass


class GG_DataQueue:
    def __init__(self, root):
        self.root = root

    def compile_threads(self):
        data_io_thread = GG_Thread(self, "Data I/O Thread")
        tasks_io_thread = GG_Thread(self, "Tasks I/O Thread")

        @data_io_thread.add_function("data_temps")
        def get_sensors_data():
            for sensor in self.root.sensors:
                command = self.root.serial.parse_command(
                    {"mode": "O", "sensor_id": sensor["sensor_id"], "value": random.randint(0, 1)}
                )

                uuid_ = self.root.serial.queue.add_command(command)
                value = self.root.serial.queue.get_executed_command(uuid_)[1]

                self.root.add_data(sensor_id=sensor["sensor_id"], value=value)

            sleep(10)

        @tasks_io_thread.add_function("task_poll")
        def get_tasks():
            time_start = time()
            request = get(self.root.scheme + "task_poll", params={"ts": time_start, "timeout": 20})
            tasks = request.json()

            for task in tasks["response"]["tasks"]:
                uuid_t, mode, sensor_id, value = task["uuid"], task["mode"], task["sensor_id"], task["value"]
                command = self.root.serial.parse_command(
                    {"mode": mode, "sensor_id": sensor_id, "value": value}
                )

                uuid_ = self.root.serial.queue.add_command(command)
                value = self.root.serial.queue.get_executed_command(uuid_)[1]

                end_time = time()
                response = post(self.root.scheme + "/execute_task", data={
                    "uuid": uuid_t,
                    "executed_time": abs(float(task["ts"]) - end_time),
                    "response": value
                })

                print(response.json())

        # data_io_thread.start()
        tasks_io_thread.start()
        # data_io_thread2.start()


class GG_Serial:
    def __init__(self, root, port=None, timeout=1, baudrate=115200):
        self.root = root
        self.port, self.baudrate, self.timeout = port or self.get_connection_port(), baudrate, timeout
        self.serial = Serial(self.port, baudrate=self.baudrate, timeout=self.timeout)
        # self.serial.close()

        self.on_ready()

        self.SERIAL_COMMAND_SCHEME = "{mode}{sensor_id}{value}"
        self.SERIAL_COMMAND_REGEX = "[I|O]\\w{1}\\d{0,}.{1}"

    def on_ready(self):
        value = self.execute("")

        while not value or "ready" not in value:
            value = self.execute("")
            sleep(0.0001)

        print("Farm is ready to work.")
        return True

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
                _ = Serial(port.device, 9600, timeout=0)
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
        value = None

        if self.serial.is_open:
            print(command)
            self.serial.write(command.encode())

            value = self.serial.read_all()
            while not value:
                value = self.serial.readall()
                sleep(0.001)

            print(value)

            value = value.decode().replace("\r\n", "")

        return value or None

    def queue(self):
        class SerialQueue(GG_Thread):
            def __init__(self, root):
                super().__init__(root, "SerialQueue-1")

                self.commands = []
                self.commands_executed = []

            def add_command(self, command):
                uuid_ = str(uuid())
                self.commands.append([uuid_, command])

                return uuid_

            def get_executed_command(self, uuid_):
                while True:
                    for command in self.commands_executed:
                        if command[0] == uuid_:
                            self.commands_executed.remove(command)
                            return command

                    sleep(0.0001)

            def get_new_command(self):
                if self.commands:
                    yield self.commands.pop(0)

                yield None

            def run(self):
                while not self.is_dead:
                    command = next(self.get_new_command())

                    if command:
                        uuid_, command_ = command
                        print(uuid_, command_)

                        value = self.root.execute(command_)
                        self.commands_executed.append([uuid_, value])

                        sleep(0.0001)

                    sleep(0.00001)

        self.queue = SerialQueue(self)
        self.queue.start()
