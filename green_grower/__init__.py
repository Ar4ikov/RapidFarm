# | Created by Ar4ikov
# | Время: 18.12.2020 - 05:04

from green_grower.server import GreenGrower
from green_grower.farm import GG_Client
from sql_extended_objects import ExtRequests as Database
from sql_extended_objects import ExtObject as DatabaseObject

database = Database("green_grower.db", check_same_thread=False)

database.commit(
    """
        CREATE TABLE IF NOT EXISTS `sensors` (
            `id` INTEGER PRIMARY KEY AUTOINCREMENT ,
            `name` TEXT NOT NULL ,
            `sensor_id` TEXT NOT NULL UNIQUE ,
            `metric` TEXT DEFAULT 'const'
        );
    """
)

database.commit(
    """
        CREATE TABLE IF NOT EXISTS `data` (
            `id` INTEGER PRIMARY KEY AUTOINCREMENT ,
            `sensor_id` TEXT NOT NULL ,
            `value` TEXT NOT NULL ,
            `date` DATE
        );
    """
)

database.commit(
    """
        CREATE TABLE IF NOT EXISTS `timers` (
            `id` INTEGER PRIMARY KEY AUTOINCREMENT ,
            `name` TEXT NOT NULL ,
            `first_time_updated` DATE NOT NULL ,
            `last_time_updated` DATE NOT NULL ,
            `countdown` INTEGER NOT NULL ,
            `duration` FLOAT DEFAULT 0.001
        );
    """
)

database.commit(
    """
        CREATE TABLE IF NOT EXISTS `statements` (
            `id` INTEGER PRIMARY KEY AUTOINCREMENT ,
            `name` TEXT NOT NULL ,
            `value` INTEGER ,
            `state` BOOLEAN
        );
    """
)
