# | Created by Ar4ikov
# | Время: 18.12.2020 - 04:50

from flask import Flask, request, jsonify, render_template
from sql_extended_objects import ExtRequests as Database
from sql_extended_objects import ExtObject as DatabaseObject
from green_grower.api import GG_API, GG_Errors


class GreenGrower(Flask):
    def __init__(self, app_name=__name__):
        super().__init__(app_name)

        self.api = GG_API(self)
        self.database = Database("green_grower.db", check_same_thread=False)

    def run(self, host, port, debug=False, **kwargs):
        self.api.route_methods()

        @self.route("/")
        def index():
            return self.api.response(200, {"message": "RapidFarm-2020"})

        @self.route("/send", methods=["GET", "POST"])
        def send():
            data = request.json or request.args.to_dict() or request.form.to_dict() or request.data or {}

            try:
                command = self.serial.parse_command(data)
            except KeyError or GG_Errors as e:
                print(e)
                return self.api.error(400, {"error_message": "Client data error: use format with regex."})
            else:
                self.serial.execute(command)

            return self.api.response(200, {"params": data})

        @self.route("/get_url_map", methods=["GET"])
        def get_url_map():
            return self.api.response({"urls": [x.rule for x in self.url_map.iter_rules()]}, 200)

        super().run(host=host, port=port, debug=debug, threaded=True)
