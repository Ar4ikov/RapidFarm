# | Created by Ar4ikov
# | Время: 27.12.2020 - 18:28

from green_grower.api import GG_Errors, GG_Thread

from serial import Serial
from serial.tools import list_ports
from serial.serialutil import SerialTimeoutException, SerialException
from requests import get, post
from regex import match
from time import time, sleep


class GG_Client:
    def __init__(self, addr, protocol="http"):
        self.addr = addr
        self.protocol = protocol
        self.scheme = f"{self.protocol}://{self.addr}/"

        self.serial = GG_Serial(self)
        self.data_queue = GG_DataQueue(self)
        self.sensors = self.get("sensors")["response"]["sensors"]

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
        self.database = self.root.database

    def compile_threads(self):
        data_io_thread = GG_Thread(self, "Data I/O Thread")

        @data_io_thread.add_function("data_temps")
        def get_sensors_data():
            for sensor in self.root.sensors:
                command = self.root.serial.parse_command(
                    {"mode": "O", "sensor": sensor["name"], "sensor_id": sensor["sensor_id"], "value": 0}
                )

                value = self.root.serial.execute(command)
                if not value:
                    continue

                self.root.add_data(sensor_id=sensor["sensor_id"], value=value)

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
        value = None

        if self.serial.is_open:
            print(command)
            self.serial.write(command.encode())
            sleep(0.1)
            value = self.serial.read_all()
            print(value)

            value = value.decode().replace("\r\n", "")

        return value or None
