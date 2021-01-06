# | Created by Ar4ikov
# | Время: 18.12.2020 - 05:14

from time import sleep, time
from sql_extended_objects import ExtObject as DatabaseObject
from flask import request, jsonify
from uuid import uuid4 as uuid


class GG_API:
    def __init__(self, root):
        self.root = root

        self.MAX_EVENTS_PER_ARRAY = 500
        self.MAX_DATA_PER_ARRAY = 10000

        self.tasks = []
        self.executed_tasks = []

        self.events = []
        self.data = []

        self.preload_data()

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

    def preload_data(self):
        data = self.root.database.select_all("data", DatabaseObject)
        for event in data:
            self.data.append({
                "id": event.id,
                "sensor_id": event.sensor_id,
                "value": event.value,
                "date": event.date,
                "metric": event.metric
            })

            if len(self.data) > self.MAX_DATA_PER_ARRAY:
                self.data.pop(0)

        print(len(self.data))
        return True

    def create_event(self, _object, action, subject):
        event = DatabaseObject()
        event.uuid = str(uuid())
        event.ip = request.remote_addr
        event.object = _object
        event.action = action
        event.subject = subject
        event.ts = time()

        event_id = self.root.database.insert_into("events", event)[0].id

        self.events.append({
            "id": event_id,
            "uuid": event.uuid,
            "ip": event.ip,
            "object": event.object,
            "action": event.action,
            "subject": event.subject,
            "ts": event.ts
        })

        if len(self.events) > self.MAX_EVENTS_PER_ARRAY:
            self.events.pop(0)

        return event_id, event.uuid, event.ip, event.ts

    def route_methods(self) -> bool:

        @self.root.route("/get_data", methods=["GET", "POST"])
        def data_get():
            data = self.get_data()

            response = {}

            for pack in self.data:
                if pack["sensor_id"] not in response:
                    response[pack["sensor_id"]] = []

                date, value, metric = pack["date"], pack["value"], pack["metric"]
                response[pack["sensor_id"]].append({
                    "date": date,
                    "value": value,
                    "metric": metric
                })

            if "latest" in data:
                print(1)
                return self.response(200, {k: v[-1] for k, v in response.items()})

            if "ts" in data:
                try:
                    ts = float(data["ts"])
                except ValueError:
                    return self.error(400, {"error_message": "Некорректный тип для 'ts' -> INT or FLOAT"})

                return self.response(200, {k: [x for x in v if float(x["date"]) > ts] for k, v in response.items()})

            if "from_ts" in data and "past_ts" in data:
                try:
                    if data["past_ts"] == "current_time":
                        from_ts, past_ts = float(data["from_ts"]), time()
                    else:
                        from_ts, past_ts = float(data["from_ts"]), float(data["past_ts"])
                except ValueError:
                    return self.error(
                        400, {"error_message": "Некорректный тип для 'from_ts' и 'past_ts' -> INT or FLOAT"})

                return self.response(
                    200, {k: [
                        x for x in v if from_ts < float(x["date"]) < past_ts
                    ] for k, v in response.items()})

            return self.response(200, response)

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

            self.create_event("sensor", "add", sensor.sensor_id)

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

            self.create_event("sensor", "remove", data["sensor_id"])

            return self.response(200, {"params": data})

        @self.root.route("/add_timer", methods=["GET", "POST"])
        def add_timer():
            data = self.get_data()

            if "name" not in data or "countdown" not in data or "sensor_id" not in data:
                return self.error(400, {"error_message": "Не все параметры были включены", "params": data})

            timer_same = self.root.database.select_all(
                "timers", DatabaseObject, where=f"""`name` = '{data["name"]}' OR `sensor_id` = '{data["sensor_id"]}'"""
            )

            if timer_same:
                return self.error(400, {"error_message": "Таймер с таким именем уже существует", "params": data})

            sensor_same = self.root.database.select_all(
                "sensors", DatabaseObject, where=f"""`sensor_id` = '{data["sensor_id"]}'"""
            )

            if not sensor_same:
                return self.error(400, {"error_message": "Для этого датчика нельзя создать таймер, "
                                                         "поскольку он не существует",
                                        "params": data})

            try:
                countdown = float(data["countdown"])
            except ValueError:
                return self.error(400, {"error_message": "Тип параметра 'countdown' должен быть INT или FLOAT", "params": data})

            timer = DatabaseObject()
            timer.name = data["name"]
            timer.sensor_id = data["sensor_id"]
            timer.first_time_updated = time()
            timer.last_time_updated = time()
            timer.countdown = countdown
            timer.duration = data.get("duration", None)

            timer_id = self.root.database.insert_into("timers", timer)[0].id

            self.create_event("timer", "add", data["name"])

            return self.response(200, {"id": timer_id, "params": data})

        @self.root.route("/remove_timer", methods=["GET", "POST"])
        def remove_timer():
            data = self.get_data()

            if "name" not in data:
                return self.error(400, {"error_message": "Не все параметры были включены", "params": data})

            timer_same = self.root.database.select_all(
                "timers", DatabaseObject, where=f"""`name` = '{data["name"]}'"""
            )

            if not timer_same:
                return self.error(400, {"error_message": "Такого таймера нет или он уже удалён.", "params": data})

            self.root.database.commit(f"""DELETE FROM `timers` WHERE `name` = '{data["name"]}';""")

            self.create_event("timer", "remove", data["name"])

            return self.response(200, {"params": data})

        @self.root.route("/get_sensors", methods=["GET", "POST"])
        def get_sensors():
            data = self.get_data()
            sensors = self.root.database.select_all("sensors", DatabaseObject)

            if "sensor_id" in data:
                sensor = self.root.database.utils.get(sensors, sensor_id=data["sensor_id"])

                if not sensor:
                    return self.error(400, {"error_message": "Датчик с таким ID не найден.", "params": data})

                return self.response(
                    200, {"sensor_id": data["sensor_id"], "name": sensor.name, "metric": sensor.metric}
                )

            return self.response(
                200, {"sensors": [{"name": x.name, "sensor_id": x.sensor_id, "metric": x.metric} for x in sensors]}
            )

        @self.root.route("/get_timers", methods=["GET", "POST"])
        def get_timers():
            data = self.get_data()
            timers = self.root.database.select_all("timers", DatabaseObject)

            if "name" in data:
                timer = self.root.database.utils.get(timers, name=data["name"])

                if not timer:
                    return self.error(400, {"error_message": "Таймер с таким ID не найден.", "params": data})

                return self.response(
                    200, {
                        "name": data["name"], "first_time_updated": timer.first_time_updated,
                        "last_time_updated": timer.last_time_updated, "countdown": timer.countdown,
                        "duration": timer.duration, "sensor_id": timer.sensor_id
                    }
                )

            return self.response(
                200, {"timers": [{
                    "name": x.name, "first_time_updated": x.first_time_updated, "sensor_id": x.sensor_id,
                    "last_time_updated": x.last_time_updated, "countdown": x.countdown, "duration": x.duration
                } for x in timers]}
            )

        @self.root.route("/update_timer", methods=["GET", "POST"])
        def update_timer():
            data = self.get_data()

            if "name" not in data:
                return self.error(400, {"error_message": "Не все параметры были включены", "params": data})

            timer_same = self.root.database.select_all(
                "timers", DatabaseObject, where=f"""`name` = '{data["name"]}'"""
            )

            if not timer_same:
                return self.error(400, {"error_message": "Таймер с таким именем не найден.", "params": data})

            ltu_t = time()
            timer_same[0]["last_time_updated"] = ltu_t

            return self.response(200, {"last_time_updated": ltu_t, "params": data})

        @self.root.route("/add_data", methods=["GET", "POST"])
        def add_data():
            data = self.get_data()

            if "sensor_id" not in data or "value" not in data:
                return self.error(400, {"error_message": "Не все параметры были включены", "params": data})

            data_ = DatabaseObject()
            data_.sensor_id = data["sensor_id"]
            data_.value = data["value"]
            data_.date = time()

            data_id = self.root.database.insert_into("data", data_)[0].id

            self.data.append({
                "id": data_id,
                "sensor_id": data["sensor_id"],
                "value": data["value"],
                "date": data_.date,
                "metric": "const"
            })

            if len(self.data) > self.MAX_DATA_PER_ARRAY:
                self.data.pop(0)

            return self.response(200, {"params": data})

        @self.root.route("/add_task", methods=["GET", "POST"])
        def add_task():
            data = self.get_data()

            if "mode" not in data or "sensor_id" not in data:
                return self.error(400, {"error_message": "Не все параметры были включены", "params": data})

            if data["mode"] not in ["I", "O"]:
                return self.error(400, {"error_message": "Доступны два режима: (I)nput, (O)utput.", "params": data})

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

            if len(self.tasks) > self.MAX_EVENTS_PER_ARRAY:
                self.tasks.pop(0)

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

            if len(self.executed_tasks) > self.MAX_EVENTS_PER_ARRAY:
                self.executed_tasks.pop(0)

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

        @self.root.route("/event_poll", methods=["GET", "POST"])
        def event_poll():
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

                for event in self.events:
                    if float(event["ts"]) >= ts:
                        response.append(event)

                if time() > end_t:
                    break

                sleep(0.001)

            print(response)

            return self.response(200, {"events": response})

        return True
