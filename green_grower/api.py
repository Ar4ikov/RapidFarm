# | Created by Ar4ikov
# | Время: 18.12.2020 - 05:14

from time import sleep, time
from sql_extended_objects import ExtObject as DatabaseObject
from flask import request, jsonify
from uuid import uuid4 as uuid


class GG_API:
    def __init__(self, root):
        self.root = root

        self.tasks = []
        self.executed_tasks = []

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

        @self.root.route("/add_task", methods=["GET", "POST"])
        def add_task():
            data = self.get_data()

            if "mode" not in data or "sensor_id" not in data:
                return self.error(400, {"error_message": "Не все параметры были включены", "params": data})

            if data["mode"] == "I" and "value" not in data:
                return self.error(400, {"error_message": "Не указано значение для датчика", "params": data})

            task = DatabaseObject()
            task.uuid = str(uuid())
            task.ip = request.remote_addr
            task.mode = data["mode"]
            task.sensor_id = data["sensor_id"]
            task.value = data.get("value", 0)
            task.ts = time()

            task_id = self.root.database.insert_into("tasks", task)[0].id

            self.tasks.append({
                "id": task_id,
                "uuid": task.uuid,
                "ip": task.ip,
                "mode": task.mode,
                "sensor_id": task.sensor_id,
                "value": task.value,
                "ts": task.ts
            })

            return self.response(200, {"uuid": task.uuid, "params": data})

        @self.root.route("/task_poll", methods=["GET", "POST"])
        def task_poll():
            data = self.get_data()

            if "ts" not in data:
                return self.error(400, {"error_message": "Не все параметры были указаны.", "params": data})

            try:
                ts = float(data["ts"])
            except ValueError:
                return self.error(400, {"error_message": "Тип параметра ts должен быть INT или FLOAT", "params": data})

            timeout = float(data.get("timeout", 25))

            end_t = time() + timeout
            response = []

            while len(response) == 0:

                for event in self.tasks:
                    if float(event["ts"]) >= ts:
                        response.append(event)

                if time() > end_t:
                    break

                sleep(0.001)

            return self.response(200, {"tasks": response})

        @self.root.route("/execute_task", methods=["GET", "POST"])
        def execute_task():
            data = self.get_data()

            if "uuid" not in data or "executed_time" not in data or "response" not in data:
                return self.error(400, {"error_message": "Не все параметры были указаны.", "params": data})

            task = self.root.database.select_all("tasks", DatabaseObject, where=f"""`uuid` = '{data["uuid"]}'""")

            if not task:
                return self.error(400, {
                    "error_message": "Такой задачи не существует или она не была ещё создана", "params": data
                })

            task = task[0]
            task["executed_time"] = data["executed_time"]
            task["response"] = data["response"]
            task["status"] = "processed"

            response_body = {
                "id": task.id,
                "uuid": data["uuid"],
                "mode": task.mode,
                "sensor_id": task.sensor_id,
                "value": task.value,
                "executed_time": data["executed_time"],
                "response": data["response"]
            }

            self.executed_tasks.append(response_body)

            return self.response(200, {})

        @self.root.route("/get_executed_task", methods=["GET", "POST"])
        def get_executed_task():
            data = self.get_data()

            if "uuid" not in data:
                return self.error(400, {"error_message": "Не все параметры были указаны.", "params": data})

            timeout = float(data.get("timeout", 25))
            event_ = None

            end_t = time() + timeout
            while not event_:

                for event in self.executed_tasks:
                    if event["uuid"] == data["uuid"]:
                        event_ = event

                if time() > end_t:
                    break

                sleep(0.0001)

            if event_: self.executed_tasks.remove(event_)

            return self.response(200, {"task": event_})

        return True
