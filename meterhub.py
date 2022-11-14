#!/usr/bin/env python3

# 23.01.2022    Martin Steppuhn     MeterHub project bundle
# 24.09.2022    Martin Steppuhn     Restructuring

"""
MeterHub
========

http://192.168.0.10:8008  --> JSON  {"time": "2021-10-21 09:24:54", "pv1_eto": 15240930, "pv1_p": 2688, ... }

Publish
=======
The query on the MeterHub can be used to send data to the MeterHub and make it accessible to other devices via
the MeterHub.
Request with POST : {'bat_soc': 85} -->  MeterHub dataset: {... 'bat_soc': 85 ...}

Commands
========
Send commands /command/<target>?.... via MeterHub to a device. Arguments can be handeld by app.py. Targes must be
enabled in app.py command variable.

http://192.168.0.10:8008/command/goe?amp=8 --> WALLBOX/api/set?amp=8
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from bottle import Bottle, request, response
from utils.backup import backup
from utils.trace import trace
import config
from app import App


class MeterHub:
    def __init__(self):
        self.name = "meterhub"
        self.version = "1.0.1"
        self.log = logging.getLogger('meterhub')
        self.app = App()

        self.data = None  # primary dataset
        self.publish_data = {}  # storage for publised data from the devices   "key" :{"value": 99, "timeout": 3412341 }
        self.t_minute = 0  # timer for minute interval

        self.web = Bottle()  # webserver
        self.web.route('/', callback=self.web_data_request, method=('POST', 'GET'))
        self.web.route('/version', callback=lambda: {'name': self.name, 'version': self.version})
        self.web.route('/command/<target>', callback=self.web_command)
        self.web.route('/log', callback=self.web_log)  # access to logfile

        logging.getLogger('waitress.queue').setLevel(logging.ERROR)  # hide waitress info log
        # start webserver thread
        threading.Thread(target=self.web.run, daemon=True,
                         kwargs=dict(host='0.0.0.0', port=config.webserver_port, server='waitress')).start()

    def start(self):
        self.log.info('start {} {}'.format(self.name, self.version))
        while True:
            t0 = time.perf_counter()  # store start time
            data = {}
            data['time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data['timestamp'] = int(datetime.utcnow().timestamp())

            if t0 > self.t_minute:  # flag every minute     # ToDo: universal interval
                self.t_minute = t0 + 60
                minute_flag = True
            else:
                minute_flag = False

            self.app.work(data, minute=minute_flag)  # aquire data

            self.publish_process(data)

            data['measure_time'] = round(time.perf_counter() - t0, 3)
            # self.log.info("main {}".format(self.data))

            trace.push(data)  # save dataset to trace module
            backup.push(data)  # save 5min Dataset to local Backup (additional to FTP)

            self.data = data  # accessable by webserver

            while time.perf_counter() < t0 + 1:
                time.sleep(0.01)

    def web_data_request(self):
        """
        Process data access. If request includes POST Data. They will be stored in self.publish_data

        Returns: Dictionary with dataset
        """
        try:
            post = json.loads(request.body.read())
            self.log.debug("publish post received: {}".format(post))
            for k, timeout in self.app.publish_config:
                if k in post:  # publish key found in post
                    self.publish_data[k] = {'value': post[k], 'timeout': time.perf_counter() + timeout}
                    self.log.debug("publish key={} data={}".format(k, self.publish_data[k]))
        except:
            pass

        if self.data is None:
            response.status = 404
        return self.data

    def web_command(self, target=None):
        """
        Handle commands: /command/<target>

        Returns: Dictionary with dataset
        """
        if target in self.app.command:
            self.app.command[target] = request.query_string
            self.log.debug("web_command target={} command={}".format(target, request.query_string))
        else:
            self.log.debug("web_command target={} not allowed".format(target))

        if self.data is None:
            response.status = 404
        return self.data

    def publish_process(self, data):
        """
        Copy received publish data from devices to main dataset.
        """
        if self.app.publish_config:
            for k, timeout in self.app.publish_config:
                try:
                    # remove old data
                    if time.perf_counter() > self.publish_data[k]['timeout']:  # clean with timeout timer
                        del (self.publish_data[k])
                        self.log.info("publish timeout: {}".format(k))
                except:
                    pass
                data[k] = self.publish_data.get(k, {}).get('value', None)  # copy from publish to data

    def web_log(self):
        """
        /log    Webserver interface to access the logfile
        """
        response.content_type = 'text/plain'
        return open(os.path.join('log', 'log.txt'), 'r').read()


if __name__ == "__main__":

    # Create Directorys
    os.makedirs(config.log_path, exist_ok=True)
    os.makedirs(config.backup_path, exist_ok=True)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[TimedRotatingFileHandler(os.path.join(config.log_path, 'log.txt'), when='midnight'),
                                  logging.StreamHandler()])

    # logging.getLogger('meterhub').setLevel(logging.DEBUG) # enable debug logging for a specific module

    meterhub = MeterHub()
    meterhub.start()  # start application mainloop
