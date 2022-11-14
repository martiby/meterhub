# 19.01.2022 Martin Steppuhn

import json
import logging
import time
import requests


class JsonRequest:
    """
    Simplified HTTP Request for JSON APIs.

    Sends an HTTP request. The response (JSON) is converted to a dictionary.
    With Lifetime a timeout for data can be specified. Even if there is an error or no read, data is still valid for
    the specified period.
    """

    def __init__(self, url, timeout=1, lifetime=10, log_name='api'):
        """
        :param url:  string
        :param timeout: timeout for request in seconds
        :param lifetime: timeout for data in seconds
        :param log_name: name for logger
        """
        self.url = url
        self.timeout = timeout
        self.lifetime = lifetime
        self.log = logging.getLogger(log_name)
        self.data = None  # Data
        self.lifetime_timeout = time.perf_counter() + self.lifetime if self.lifetime else None  # set lifetime timeout
        self.log.debug("init url: {}".format(url))

    def read(self, post=None):
        """
        Read

        :return: data (dictionary)
        """
        t0 = time.perf_counter()
        data = None
        try:
            if post is None:
                r = requests.get(self.url, timeout=self.timeout)
            else:
                r = requests.post(self.url, timeout=self.timeout, json=post)
            if r.status_code == 200:
                data = json.loads(r.content)
            else:
                raise ValueError("status_code={} url={}".format(r.status_code, self.url))

            self.lifetime_timeout = t0 + self.lifetime if self.lifetime else None  # set new lifetime timeout
            self.data = data
            self.log.debug("read done in {:.3f}s data: {}".format(time.perf_counter() - t0, data))

        except Exception as e:
            self.log.debug("read failed {:.3f}s error: {}".format(time.perf_counter() - t0, e))
            if self.lifetime:
                if self.lifetime_timeout and time.perf_counter() > self.lifetime_timeout:
                    self.log.error("data lifetime expired")
                    self.lifetime_timeout = None  # disable timeout, restart with next valid receive
                    self.data = None  # clear data
            else:
                self.data = None  # without lifetime set self.data instantly to read result

        return data

    def get(self, key, default=None):
        """
        Get a value from data.

        :param key: String (key for data dictionary, or list with nested keys and index)
        :param default: return für invalid get
        :return: value
        """
        try:
            value = self.data
            if isinstance(key, (tuple, list)):
                for k in key:
                    value = value[k]
            else:
                value = value[key]
            return value
        except:
            return default


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)-10s %(levelname)-6s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    api = JsonRequest("http://192.168.0.10:8888/api/data", timeout=1, lifetime=10)

    while True:
        data = api.read()
        print(api.get('home_p'), data, api.data)
        time.sleep(3)
