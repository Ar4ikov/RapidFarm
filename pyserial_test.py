# | Created by Ar4ikov
# | Время: 15.12.2020 - 15:41

from serial import Serial

COM_PORT = "COM7"
arduino = Serial(COM_PORT, baudrate=9600, timeout=1)

while True:
    if arduino.is_open:
        arduino.write(input(">> ").encode())
