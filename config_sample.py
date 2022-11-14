#!/usr/bin/env python3
#  -*- coding: utf-8 -*-

from utils.backup import backup

# IR Coupler for SML-Meter interface, USB-Serial
sml_ir_port = "/dev/serial/by-path/platform-3f980000.usb-usb-0:1.1.3:1.0-port0"

# USB/RS485/Modbus Interface for Eastron Meters
eastron_sdm_port = "/dev/serial/by-path/platform-3f980000.usb-usb-0:1.2:1.0-port0"

# Fronius PV Inverter IP Address
fronius_symo_address = '192.168.0.20'

# GoE Wollbox IP-Address
goe_wallbox_address = '192.168.0.25'

# ESP32 CAM for Water Meter recognition
water_meter_address = 'http://192.168.0.24/json'

# Directory for Logfiles
log_path = 'log'

# Directory for CSV Backup
backup_path = 'backup'

# CSV Backup, keys saved as CSV
backup.config = ['time', 'timestamp', 'grid_imp_eto', 'grid_exp_eto', 'pv1_eto', 'pv2_eto', 'home_all_eto',
                 'flat_eto', 'bat_imp_eto', 'bat_exp_eto', 'car_eto', 'water_vto', 'test_martin']

# Save interval in hours
backup.save_hour_interval = 1

# Backup CSV to FTP
# backup.ftp_config = None
backup.ftp_config = {'server': '192.168.0.1',
                     'user': 'fritz.nas.pi',
                     'password': '*******',
                     'path': 'USB_STICK/MeterHub-Backup'}

# Port for the MeterHub Webserver
webserver_port = 8008
