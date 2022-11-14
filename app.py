import logging

import config
# Devices
from device.eastron import SDM  # Powermeter with Modbus
from device.fronius import Symo  # PV Inverter
from device.goe_api_v2 import GoeApiV2  # GO-E Wallbox
from device.json_request import JsonRequest  # HTTP API for Battery system
from device.sml import Sml  # IP Coupler interface to grid power meter


class App:
    def __init__(self):
        self.log = logging.getLogger('app')

        self.publish_config = (('car_pv_ready', 10),  # only keys in this list can be published
                               ('car_plug', 10),  # key and timeout in seconds
                               ('car_info', 10),
                               ('bat_info', 10),
                               ('bat_soc', 10))


        self.command = {'goe': None}  # enable commands with a key

        self.sml = Sml(port=config.sml_ir_port, lifetime=10, log_name='mt175')
        self.sdm630 = SDM(config.eastron_sdm_port, type="SDM630", address=1, lifetime=10, log_name='sdm630')
        self.sdm72 = SDM(config.eastron_sdm_port, type="SDM72", address=3, lifetime=10, log_name='sdm72')
        self.sdm120 = SDM(config.eastron_sdm_port, type="SDM120", address=2, lifetime=10, log_name='sdm120')
        self.pv = Symo(config.fronius_symo_address, log_name='fronius')
        self.goe = GoeApiV2(config.goe_wallbox_address, log_name='goe', lifetime=30)  # 30sec because of weak WiFi
        self.water = JsonRequest(config.water_meter_address, lifetime=10 * 60 + 10, log_name='water')  # Water-Meter

        self.pv.start_tread(thread_sleep=0.5)  # read fronius in extra thread

    def work(self, data, minute=False):

        # handle received commands (/command/<target>?...)
        if self.command['goe']:
            self.log.info("goe wallbox command: {}".format(self.command['goe']))
            if not self.goe.set(self.command['goe']):
                self.log.info("retry goe wallbox command: {}".format(self.command))
                self.goe.set(self.command['goe'])  # second try
            self.command['goe'] = None

        # read devices
        self.sdm120.read(['p', 'e_import', 'e_export'])  # flat
        self.sdm630.read(['p', 'e_total'])  # home  (legacy e_total, import is better)
        self.sdm72.read(['p', 'e_total'])  # flat  (legacy e_total, import is better)
        self.sml.read()  # read IR coupler
        self.goe.read()  # read Wallbox
        if minute:  # water read only once a minute
            self.water.read()

        # Grid meter
        data['grid_imp_eto'] = self.sml.get('e_import')  # MT175
        data['grid_exp_eto'] = self.sml.get('e_export')  # MT175
        data['grid_p'] = self.sml.get('p')

        # PV
        data['pv1_eto'] = self.pv.get(('e_total', 0))  # Fronius Symo 7 (Süden)
        data['pv2_eto'] = self.pv.get(('e_total', 1))  # Fronius Symo 6 (Norden)
        data['pv1_e_day'] = self.pv.get(('e_day', 0))  # >~21MWh eto has a lower resolution
        data['pv2_e_day'] = self.pv.get(('e_day', 1))
        data['pv1_p'] = self.pv.get(('p', 0))
        data['pv2_p'] = self.pv.get(('p', 1))
        data['pv_p'] = self.pv.get(('p', 0), default=0) + self.pv.get(('p', 1), default=0)

        # Home
        data['home_all_eto'] = self.sdm630.get('e_total')  # SDM630, Haus Gesamtverbrauch
        data['home_all_p'] = self.sdm630.get('p')
        data['home_p'] = self.sdm630.get('p', default=0) - self.goe.get('p', default=0)

        # Flat
        data['flat_eto'] = self.sdm72.get('e_total')  # SDM72, Einliegerwohnung
        data['flat_p'] = self.sdm72.get('p')

        # Battery
        data['bat_imp_eto'] = self.sdm120.get('e_import')  # HomeBattery, Ladung / SDM120
        data['bat_exp_eto'] = self.sdm120.get('e_export')  # HomeBattery, Einspeisung / SDM120
        data['bat_p'] = self.sdm120.get('p')

        # Wallbox
        data['car_eto'] = self.goe.get('eto')
        data['car_p'] = self.goe.get('p')
        data['car_e_cycle'] = self.goe.get('e_cycle')
        data['car_amp'] = self.goe.get('amp')
        data['car_phase'] = self.goe.get('phase')
        data['car_stop'] = self.goe.get('stop')
        data['car_state'] = self.goe.get('state')

        # Water
        data['water_vto'] = self.water.get(('main', 'value'))


""" Example: Full dataset 
{    
    "time": "2022-09-25 00:05:57", 
     "timestamp": 1664049957, 
     "grid_imp_eto": 4539537, 
     "grid_exp_eto": 30636590,
     "grid_p": 304, 
     "pv1_eto": 23824702, 
     "pv2_eto": 15919000, 
     "pv1_e_day": 0, 
     "pv2_e_day": 0, 
     "pv1_p": 0, 
     "pv2_p": 0,
     "pv_p": 0, 
     "home_all_eto": 15159336, 
     "home_all_p": 305, 
     "home_p": 305, 
     "flat_eto": 67189, 
     "flat_p": 0,
     "bat_imp_eto": 1859088, 
     "bat_exp_eto": 900169, 
     "bat_p": -12, 
     "car_eto": 2487641, 
     "car_p": 0, 
     "car_p_set": 1610,
     "car_e_cycle": 2506, 
     "car_amp": 7, 
     "car_phase": 1, 
     "car_stop": True, 
     "car_state": "complete", 
     "water_vto": 1367154,
     "car_mode": "pv", 
     "car_pv_ready": False, 
     "bat_soc": 46, 
     "measure_time": 0.862
}
"""
