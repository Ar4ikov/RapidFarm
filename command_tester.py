# | Created by Ar4ikov
# | Время: 28.12.2020 - 21:09

from requests import get
from time import sleep

while True:
    mode = input("(mode) ")
    sensor = input("(sensor) ")
    value = input("(value) ")

    request = get("http://127.0.0.1:80/add_task", params={
        "mode": mode, "sensor_id": sensor, "value": value
    })

    r_response = request.json()["response"]

    response = get("http://127.0.0.1:80/get_executed_task", params={
        "uuid": r_response["uuid"]
    })

    print(response.json())

    sleep(0.0001)