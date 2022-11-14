# 1.03.2022  Martin Steppuhn
# 7.4.2022   New set structure

import json
import logging
import requests
import time
"""

http://192.168.0.25/api/set?psm=1    3 --> 1
http://192.168.0.25/api/set?psm=2    1 --> 3

{"psm":true}

"""


class GoeApiV2:
    def __init__(self, ip_address, timeout=1, lifetime=10, log_name='goe'):
        """
        :param ip_address:  IP-Address
        :param timeout:     Timeout in seconds for request.
        :param lifetime:    Lifetime in seconds data ist valid
        """
        self.log = logging.getLogger(log_name)
        self.ip_address = ip_address
        self.timeout = timeout
        self.lifetime = lifetime
        self.data = None
        self.lifetime_timeout = time.perf_counter() + self.lifetime if self.lifetime else None  # set lifetime timeout
        self.log.debug("init address: {}".format(ip_address))

    def read(self):
        """
        Read information. Typically s, regularly also up to
        :return: None or Dictionary
        """
        t0 = time.perf_counter()
        url_template = "http://{}/api/status?filter=amp,frc,fsp,eto,nrg,car,wh"
        url = url_template.format(self.ip_address)
        d = None
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                r = json.loads(resp.content)
                # print(r)
                d = {}

                d['amp'] = r.get('amp', None)

                if r.get('fsp', None) == True:  # fsp = force single phase
                    d['phase'] = 1
                elif r.get('fsp', None) == False:  # fsp = force single phase
                    d['phase'] = 3
                else:
                    d['phase'] = None

                try:
                    d['p_set'] = d['amp'] * d['phase'] * 230
                except:
                    d['p_set'] = None

                try:
                    d['p'] = r['nrg'][11]
                except:
                    d['p'] = None

                # d['stop'] = (r.get('frc', None) == 1)  # until 25.04.2022

                if r.get('frc', None) == 1:
                    d['stop'] = True
                elif r.get('frc', None) == 0:
                    d['stop'] = False
                else:
                    d['stop'] = r.get('frc', None)

                try:
                    d['e_cycle'] = round(r['wh'])
                except:
                    d['e_cycle'] = None

                d['eto'] = r.get('eto', None)

                car = r.get('car', None)
                if car == 1:
                    d['state'] = 'idle'
                elif car == 2:
                    d['state'] = 'charge'
                elif car == 3:
                    d['state'] = 'wait'
                elif car == 4:
                    d['state'] = 'complete'
                else:
                    d['state'] = 'error'

                self.lifetime_timeout = t0 + self.lifetime if self.lifetime else None  # set new lifetime timeout
                self.data = d
                self.log.debug("read done in {:.3f}s data: {}".format(time.perf_counter() - t0, d))
            else:
                raise ValueError("failed with status_code={}".format(resp.status_code))

        except Exception as e:
            self.log.debug("read failed {:.3f}s error: {}".format(time.perf_counter() - t0, e))
            if self.lifetime:
                if self.lifetime_timeout and time.perf_counter() > self.lifetime_timeout:
                    self.log.error("data lifetime expired")
                    self.lifetime_timeout = None  # disable timeout, restart with next valid receive
                    self.data = None  # clear data
            else:
                self.data = None  # without lifetime set self.data instantly to read result
        return d

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

    # def set(self, stop=None, amp=None, phase=None):
    #     """
    #     cmd= amp=6&frc=0&psm=1
    #     api/set?amp=6&frc=0&psm=1
    #
    #     amp=1..16   1..16 Ampere
    #     frc=0,1     0=force release, 1=force stop
    #     psm=1,2     1=1-Phase 2=3-Phase
    #     """
    #     cmd = []
    #     if amp is not None and 6 <= amp <= 16:
    #         cmd.append('amp={}'.format(amp))
    #
    #     if stop is True:
    #         cmd.append('frc=1')
    #     elif stop is False:
    #         cmd.append('frc=0')
    #
    #     if phase is not None and phase == 1:
    #         cmd.append('psm=1')
    #     if phase is not None and phase == 3:
    #         cmd.append('psm=2')
    #
    #     if cmd:
    #         cmd = "&".join(cmd)
    #
    #         self.log.info("set cmd: {}".format(cmd))
    #         try:
    #             r = requests.get('http://{}/api/set?{}'.format(self.ip_address, cmd), timeout=1)
    #             if r.status_code == 200:  # {"amp":true}
    #                 data = json.loads(r.content)
    #                 return True
    #             else:
    #                 raise ValueError("failed with status_code={}".format(r.status_code))
    #         except Exception as e:
    #             self.log.error("set exception: {}".format(e))
    #             return False
    #     else:
    #         self.log.error("no set cmd: {}".format(cmd))



    def set(self, command):
        """
        command: amp=6&frc=0&psm=1   -->      api/set?amp=6&frc=0&psm=1

        amp=1..16   1..16 Ampere
        frc=0,1     0=force release, 1=force stop
        psm=1,2     1=1-Phase 2=3-Phase
        """
        try:
            r = requests.get('http://{}/api/set?{}'.format(self.ip_address, command), timeout=1)
            if r.status_code == 200:  # {"amp":true}
                data = json.loads(r.content)
                return True
            else:
                raise ValueError("failed with status_code={}".format(r.status_code))
        except Exception as e:
            self.log.error("send exception: {}".format(e))
            return False


if __name__ == "__main__":
    import time

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)-10s %(levelname)-6s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    logging.getLogger("goe").setLevel(logging.DEBUG)

    wallbox = GoeApiV2('192.168.0.25', timeout=5, lifetime=10)

    while True:
        wallbox.read()
        time.sleep(0.1)
        print(wallbox.data)
        time.sleep(2)
