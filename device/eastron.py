# 28.05.2021 Martin Steppuhn    Full featured
# 21.11.2021 Martin Steppuhn    renamed get()
# 19.01.2022 Martin Steppuhn    Release

import logging
import time
try:
    from device import minimalmodbus
except:
    import minimalmodbus


class SDM:
    """
    Eastron SDM Powermeter

    Read information from Eastron powermeters.
    With Lifetime a timeout for data can be specified. Even if there is an error or no read, data is still valid for
    the specified period.
    """

    cfg = {"SDM120": {'p': (0x0C, 1), 'e_total': (0x156, 1000), 'e_import': (0x48, 1000), 'e_export': (0x4A, 1000)},
           "SDM72": {'p': (0x34, 1), 'e_total': (0x156, 1000)},
           "SDM630": {'p': (0x34, 1), 'e_total': (0x156, 1000)}}

    def __init__(self, port, type, address, lifetime=10, log_name='sdmx'):
        """
        Init for a Device

        :param port:    '/dev/ttyUSB0' or 'COM6', ...
        :param type:    'SDM120', 'SDM72' or 'SDM630'
        :param address:  Deviceaddress as integer
        :param lifetime: Number of get cycles that may fail and data remains valid
        """
        self.port = port
        self.type = type
        self.address = address
        self.lifetime = lifetime
        self.log = logging.getLogger(log_name)
        self.log.debug('init type={} port={}'.format(type, port))
        self.data = None  # Data
        self.lifetime_timeout = time.perf_counter() + self.lifetime if self.lifetime else None  # set lifetime timeout

    def read(self, keys, timeout=1):
        """
        Read the requested keys (registers) from the device.

        SDM120 @9600Baud , 'p', 'e_import', 'e_export' = ~0.200ms

        :param keys: Registers to read
        :param timeout: total time in seconds for the complete cycle
        :return: Dictionary with result of this read
        """

        t0 = time.perf_counter()
        time_timeout = t0 + timeout
        error = None
        data = {k: None for k in keys}  # init all requested keys with None

        # ====== open port ======
        bus = None
        while time.perf_counter() < time_timeout:
            try:
                # port name, slave address (in decimal)
                bus = minimalmodbus.Instrument(self.port, self.address, close_port_after_each_call=True)
                bus.serial.baudrate = 9600
                bus.serial.timeout = 0.1
                break
            except Exception as e:
                error = "{}".format(e)
                time.sleep(0.1)

        # ====== read data ======

        for k in keys:
            while time.perf_counter() < time_timeout:
                try:
                    data[k] = round(bus.read_float(self.cfg[self.type][k][0], 4) * self.cfg[self.type][k][1])
                    break
                except Exception as e:
                    if not error:
                        error = "{}".format(e)
                    time.sleep(0.01)

        if time.perf_counter() < time_timeout:  # valid data received
            self.lifetime_timeout = t0 + self.lifetime if self.lifetime else None  # set new lifetime timeout
            self.data = data
            self.log.debug("read done in {:.3f}s data: {}".format(time.perf_counter() - t0, data))
        else:
            self.log.debug("read failed {:.3f}s error: {}".format(time.perf_counter() - t0, error))
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
            v = self.data
            if isinstance(key, (tuple, list)):
                for k in key:
                    v = v[k]
            else:
                v = v[key]
            return v
        except:
            return default


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)-10s %(levelname)-6s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    sdm_port = "/dev/serial/by-path/platform-3f980000.usb-usb-0:1.2:1.0-port0"  # USB-RS485

    sdm120 = SDM(sdm_port, type="SDM120", address=2, lifetime=5, log_name='sdm120')
    while True:
        data = sdm120.read(['p', 'e_import', 'e_export'])
        # print(data, sdm120.data)
        time.sleep(1)
