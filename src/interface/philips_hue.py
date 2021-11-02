from phue import Bridge
from time import sleep
from pathlib import Path
import logging
import socket


class PhilipsHue ():
    def __init__(self, config):
        self.config = config
        self.connect()

    def connect(self):
        registered = Path(self.config['registered_file']).is_file()
        success = False
        while success == False:
            try:
                logging.info("Connecting to hue bridge")
                self.bridge = Bridge(self.config['bridge_ip'])
                self.bridge.connect()
                success = True
            except Exception as e:
                logging.info("Failed to connect to bridge")
                success = False
                if registered == False:
                    logging.info("Trying again in 5 seconds..")
                    sleep(5)
                else:
                    raise e

        logging.info("Connected to hue bridge")
        if registered == False:
            # register
            logging.info("Saving registration")
            Path(self.config['registered_file']).touch()

    def get_state(self):
        return self.__execute__(lambda: self.bridge.get_api())

    def get_scenes(self):
        return self.__execute__(lambda: self.bridge.get_scene())

    def get_scene_by_name(self, name):
        for key, scene in self.get_scenes().items():
            if scene['name'] == name:
                scene['id'] = key
                return scene
        return None

    def set_light(self, lights, command):
        return self.__execute__(lambda: self.bridge.set_light(lights, command))

    def get_light(self, id, command=None):
        return self.__execute__(lambda: self.bridge.get_light(id, command))

    def set_group(self, groups, command):
        return self.__execute__(lambda: self.bridge.set_group(groups, command))

    def get_group(self, id, command=None):
        return self.__execute__(lambda: self.bridge.get_group(id, command))

    def set_group_scene(self, group_name, scene_name):
        scene_id = self.get_scene_by_name(scene_name)['id']
        return self.__execute__(lambda: self.set_group(group_name, self.create_conf({'scene': scene_id})))

    def create_conf(self, conf):
        if 'transitiontime' not in conf.keys():
            conf['transitiontime'] = self.config['transition_time']
        return conf

    def __execute__(self, function):
        try:
            return function()
        except socket.timeout as e:
            # Try to reconnect
            logging.exception(
                "Could not execute function. Trying to reconnect to bridge")
            logging.exception(str(e))
            try:
                self.connect()
            except Exception as e:
                logging.exception(
                    "Reconnect did not succeed, skipping execution")
                logging.exception(str(e))
                return
            # Now try again
            return function()
