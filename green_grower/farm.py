# | Created by Ar4ikov
# | Время: 27.12.2020 - 18:28
import random
from threading import Thread

from green_grower.objects import GG_Errors, GG_Thread

from sql_extended_objects import ExtRequests as Database
from sql_extended_objects import ExtObject as DatabaseObject
from serial import Serial
from serial.tools import list_ports
from serial.serialutil import SerialTimeoutException, SerialException
from requests import get, post
from requests.exceptions import ConnectTimeout, ConnectionError, RequestException
from urllib3.exceptions import MaxRetryError, NewConnectionError
from regex import match
from time import time, sleep
from uuid import uuid4 as uuid
from json.decoder import JSONDecodeError


class GG_Client:
    def __init__(self, addr, protocol="http"):
        self.addr = addr
        self.protocol = protocol
        self.scheme = f"{self.protocol}://{self.addr}/"

        self.serial = GG_Serial(self)
        self.serial.queue()

        self.sensors = self.get("sensors")["response"]["sensors"]
        self.timers = self.get("timers")["response"]["timers"]

        self.data_queue = GG_DataQueue(self)
        self.data_queue.compile_threads()

    def add_data(self, sensor_id, value):
        while True:
            request = get(self.scheme + "add_data", params={"sensor_id": sensor_id, "value": value})

            try:
                value_ = request.json()
            except (ConnectionError, TimeoutError, RequestException, Exception):
                print("Connection Error...")
                sleep(1)
            else:
                return value_

    def get(self, _object, **params):
        while True:
            request = self.get_response(self.scheme + f"get_{_object}", params=params)

            try:
                value_ = request.json()
            except Exception:
                print("Connection Error...")
                sleep(1)
            else:
                return value_

    @staticmethod
    def get_response(*args, **kwargs):
        while True:
            try:
                value = get(*args, **kwargs)
            except (ConnectionError, ConnectTimeout, ConnectionRefusedError, ConnectionAbortedError, RequestException,
                    GG_Errors, JSONDecodeError) as e:
                print("Соединение не установлено, повторная попытка через 1 секунду...")
                print(str(e))
            else:
                if value.status_code == 200:
                    try:
                        print(value.json())
                    except Exception:
                        print("Ошибка декодирования, повторная попытка через 1 секунду...")
                    else:
                        return value

            sleep(1)

    def get_tasks(self):
        pass


class GG_DataQueue:
    def __init__(self, root):
        self.root = root

    def compile_threads(self):
        data_io_thread = GG_Thread(self, "Data I/O Thread")
        tasks_io_thread = GG_Thread(self, "Tasks I/O XHR Polling")
        events_thread = GG_Thread(self, "Events XHR Polling")
        timers_thread = GG_Thread(self, "Timers Counting Thread")

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

        tasks_io_thread.ts = time()

        @tasks_io_thread.add_function("task_poll")
        def get_tasks():
            time_start = time()
            request = self.root.get_response(self.root.scheme + "task_poll", params={"ts": tasks_io_thread.ts, "timeout": 20})

            if request.status_code != 200:
                return False

            tasks = request.json()
            tasks_io_thread.ts = tasks["ts"]

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

                if response.status_code == 200:
                    print(response.json())

        events_thread.ts = time()

        @events_thread.add_function("event_poll")
        def get_events():
            time_start = time()
            request = self.root.get_response(self.root.scheme + "event_poll", params={"ts": events_thread.ts, "timeout": 20})

            if request.status_code != 200:
                return False

            events = request.json()
            events_thread.ts = events["ts"]

            for event in events["response"]["events"]:
                print(event)
                uuid_t, _object, action, subject = event["uuid"], event["object"], event["action"], event["subject"]

                if _object == "sensor":
                    if action == "add":
                        sensor = self.root.get("sensors", sensor_id=subject)["response"]
                        self.root.sensors.append(
                            {"name": sensor["name"], "metric": sensor["metric"], "sensor_id": sensor["sensor_id"]}
                        )

                    elif action == "remove":
                        for sensor in self.root.sensors:
                            if sensor["sensor_id"] == subject:
                                self.root.sensors.remove(sensor)
                                break

                elif _object == "timer":
                    if action == "add":
                        timer = self.root.get("timers", name=subject)["response"]
                        self.root.timers.append(
                            {"name": timer["name"], "first_time_updated": timer["first_time_updated"],
                             "last_time_updated": timer["last_time_updated"], "countdown": timer["countdown"],
                             "duration": timer["duration"], "sensor_id": timer["sensor_id"]}
                        )

                    elif action == "remove":
                        for timer in self.root.timers:
                            if timer["name"] == subject:
                                self.root.timers.remove(timer)

                                value = self.root.serial.queue.execute_command(f"""I{timer["sensor_id"]}1""")

                                break

        timers_thread.database = Database("green_grower_client.db")

        @timers_thread.add_function("timers")
        def timers():
            for timer in self.root.timers:
                statement = timers_thread.database.select_all(
                    "statements", DatabaseObject, where=f"""`name` = '{timer["name"]}'""")

                if not statement:
                    statement = DatabaseObject()
                    statement.name = timer["name"]
                    statement.state = True
                    statement.value = 1

                    statement = timers_thread.database.insert_into("statements", statement)[0]
                else:
                    statement = statement[0]

                current_state = statement.state
                current_t = time()
                ltu_t = timer["last_time_updated"]
                delta = current_t - ltu_t

                def check_phase(state_, delta_, duration, countdown):
                    if state_ == 1:
                        if delta_ - duration > 0:
                            timer["last_time_updated"] = time()
                            self.root.get_response(self.root.scheme + "update_timer", params={"name": timer["name"]})
                            return "countdown"
                        else:
                            return "duration"
                    else:
                        if delta_ - countdown > 0:
                            self.root.get_response(self.root.scheme + "update_timer", params={"name": timer["name"]})
                            timer["last_time_updated"] = time()
                            return "duration"
                        else:
                            return "countdown"

                phase = check_phase(statement.state, delta, timer["duration"], timer["countdown"])
                # print(phase)

                if phase == "duration":
                    statement["state"] = 1

                else:
                    statement["state"] = 0

                state = timers_thread.database.select_all(
                    "statements", DatabaseObject, where=f"""`name` = '{timer["name"]}'""")[0].state

                if current_state != state:
                    command = self.root.serial.parse_command({
                                    "mode": "I", "sensor_id": timer["sensor_id"], "value": state
                                })
                    value = self.root.serial.queue.execute_command(command)

        data_io_thread.start()
        tasks_io_thread.start()
        events_thread.start()
        timers_thread.start()


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
            # raise GG_Errors(f"The command what we need and regex does not match. -> {command}", 200)
            pass

        return command

    def execute(self, command):
        value = None

        if self.serial.is_open:
            self.serial.write(command.encode())

            value = self.serial.read_all()
            while not value:
                value = self.serial.readall()
                sleep(0.001)

            value = value.decode().replace("\r\n", "")

        return value or None

    def queue(self):
        class SerialQueue(GG_Thread):
            def __init__(self, root):
                super().__init__(root, "SerialQueue-1")

                self.commands = []
                self.commands_executed = []

            def execute_command(self, command):
                uuid_ = self.add_command(command)
                value = self.get_executed_command(uuid_)[1]

                return value

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
                        # print(uuid_, command_)

                        value = self.root.execute(command_)
                        self.commands_executed.append([uuid_, value])

                        sleep(0.0001)

                    sleep(0.00001)

        self.queue = SerialQueue(self)
        self.queue.start()
