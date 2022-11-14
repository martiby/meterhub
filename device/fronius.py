# 19.01.2022 Martin Steppuhn Release

import json
import logging
import threading
import time
import requests


class Symo:
    def __init__(self, ip_address, timeout=5, lifetime=10, log_name='symo'):
        """
        Fronius Symo API Interface    (without network read fails without timeout)

        :param ip_address:  IP-Address
        :param timeout:     Timeout in seconds for request
        :param lifetime:    Lifetime in seconds data ist valid
        """
        self.log = logging.getLogger(log_name)
        self.ip_address = ip_address
        self.timeout = timeout
        self.lifetime = lifetime
        self.data = None
        self.lifetime_timeout = time.perf_counter() + self.lifetime if self.lifetime else None  # set lifetime timeout
        self.thread_sleep = None  # sleep between two gets in thread mode
        self.log.debug("init address: {}".format(ip_address))

    def read(self):
        """
        Read information. Typically 1.5s, regularly also up to 3.5s, occasionally up to 4s

        http://192.168.0.20/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System&DataCollection=CommonInverterData

        :return: None or Dictionary    {'p': [4508, 3213], 'e_total': [9472610, 665262], 'e_day': [11783, 9479]}
        """
        t0 = time.perf_counter()
        url_template = "http://{}/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System&DataCollection=CommonInverterData"
        url = url_template.format(self.ip_address)
        data = None
        try:
            r = requests.get(url, timeout=self.timeout)
            if r.status_code == 200:
                val = json.loads(r.content)
                data = {
                    'p': [v for k, v in sorted(val['Body']['Data']['PAC']['Values'].items())],
                    'e_total': [v for k, v in sorted(val['Body']['Data']['TOTAL_ENERGY']['Values'].items())],
                    'e_day': [v for k, v in sorted(val['Body']['Data']['DAY_ENERGY']['Values'].items())]
                }
                self.lifetime_timeout = t0 + self.lifetime if self.lifetime else None  # set new lifetime timeout
                self.data = data
                self.log.debug("read done in {:.3f}s data: {}".format(time.perf_counter() - t0, data))
            else:
                raise ValueError("status_code={} url={}".format(r.status_code, url))
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
        Get a single value

        :param key: string or tuple
        :param default: default
        :return: value or None
        """
        try:
            if isinstance(key, (tuple, list)):
                return self.data[key[0]][key[1]]
            else:
                return self.data[key]
        except:
            return default

    def start_tread(self, thread_sleep=0.5):
        """
        Start thread with read loop
        :param thread_sleep: time in seconds between two read/ http get
        """
        self.thread_sleep = thread_sleep
        th = threading.Thread(target=self.thread_read, daemon=True)
        self.log.info("start read thread")
        th.start()

    def thread_read(self):
        """
        Endless loop for threaded read
        """
        while True:
            self.read()
            time.sleep(self.thread_sleep)


if __name__ == "__main__":
    import time

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)-10s %(levelname)-6s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    # logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)
    logging.getLogger("symo").setLevel(logging.DEBUG)

    pv = Symo('192.168.0.20', timeout=5, lifetime=10)

    # 1. manual read

    while True:
        pv.read()
        time.sleep(1)

    # 2. threaded read

    # pv.start_tread(thread_sleep=1)
    # while True:
    #     # print(pv.data)
    #     time.sleep(5)
