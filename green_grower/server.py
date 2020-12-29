# | Created by Ar4ikov
# | Время: 18.12.2020 - 04:50

from flask import Flask, request, jsonify, render_template
from sql_extended_objects import ExtRequests as Database
from sys import path
from sql_extended_objects import ExtObject as DatabaseObject
from green_grower.objects import GG_Errors
from green_grower.api import GG_API


class GreenGrower(Flask):
    def __init__(self, app_name):
        super().__init__(app_name)

        self.database = Database("green_grower.db", check_same_thread=False)
        self.api = GG_API(self)

    def run(self, host, port, debug=False, *args, **kwargs):
        self.api.route_methods()

        @self.route("/")
        def index():
            return self.api.response(200, {"message": "RapidFarm-2020"})

        @self.route("/get_url_map", methods=["GET"])
        def get_url_map():
            return self.api.response(200, {"urls": [x.rule for x in self.url_map.iter_rules()]})

        @self.route("/robots.txt")
        def robots():
            return open(path.join(path.dirname(__file__), "robots.txt"), "r").read()

        super().run(host=host, port=port, debug=debug, threaded=True)
