# MeterHub

The application captures all meters of the building installation, and makes them available via an HTTP JSON API. 
The different devices (meters, solar inverters, wallboxes, ...) with their different interfaces (USB, RS485, 
Ethernet, WLAN, ...) are available for different applications via a common interface. 
Applications based on this are e.g.: Visualisation and databases, solar-controlled wallboxes, battery storage, ... 
The application is written in Python and usually runs on a Raspberry Pi. The specific configuration is defined directly in meterhub.py.

`meterhub.py` is the basic application 
`app.py` contains the specific queries and assignments
`config.py` contains basic settings and port/address assignments

## Example:

  http://home:8008/

    {
      "time": "2022-01-23 00:08:38", 
      "grid_imp_eto": 3985744,
      "grid_exp_eto": 18804181, 
      "grid_p": 513, 
      "pv1_eto": 16152530, 
      "pv1_p": 0, 
      "car_eto": 735688, 
      "car_p": 0,  
      "car_amp": 6, 
      "car_phase": 1,  
      "car_state": "complete", 
      "water_vto": 1130154, 
      ...
    }

# Supported devices:

* Solar inverters
    * Fronius Symo

* Electricity meter (RS485 Modbus)
    * Eastron SDM72
    * Eastron SDM120
    * Eastron SDM630
    
* Electricity meter (SML IR)
    * ISKRA MT175
    * ISKRA MT631
    * ITRON 3.HZ
    * EMH eHZ

* Wallbox 
  * Go-e HomeFix
    
* Generic HTTP-API
  * ESP32 CAM (https://github.com/jomjol/AI-on-the-edge-device) 

# Usage

## Publish

The query on the MeterHub can be used to send data to the MeterHub and make it accessible to other devices via 
the MeterHub.
 
Example:
A battery storage system polls the MeterHub cyclically. At the same time as the request, the current status of the 
battery storage is transmitted via POST. Only data that is enabled in `publish_config` is transferred. A timeout can 
be set for each variable. 

Request with POST : `{'bat_soc': 85}` --> MeterHub data for all requests: `{... 'bat_soc': 85 ...}`

## Commands

Following the scheme `/command/<target>?....` commands can be sent to the MeterHub and forwarded according to `app.py`
own requirements

Example wallbox: 
Since the MeterHub already queries the data of the wallbox, control is also implemented via it. 
The special URL parameters are simply passed on by the MeterHub.

Setting the wallbox to 8 amps

`http://192.168.0.10:8008/command/goe?amp=8` --> `WALLBOX/api/set?amp=8`


# Install
**Python**
 
    pip3 install -r requirements.txt

**Install Service**  

    sudo cp meterhub.service /etc/systemd/system

# Use Service

**Commands** 

    sudo systemctl start meterhub
    sudo systemctl stop meterhub
    sudo systemctl restart meterhub
    sudo systemctl enable meterhub
    sudo systemctl disable meterhub

**Logging**

    sudo journalctl -u meterhub
    sudo journalctl -u meterhub -f