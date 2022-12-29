# SML Decoder
# CRC Decodeing based on http://www.stefan-weigert.de/php_loader/sml.php
#
# Testet with (entered PIN):
# ISKRA  MT175
# ITRON  3.HZ
# EMH    eHZ
#
# 21.05.2021 Martin Steppuhn
# 24.05.2021 Martin Steppuhn    lifetime added
# 25.05.2021 Martin Steppuhn    added logging
# 10.11.2021 Martin Steppuhn    Test mit weiterem MT175
# 28.11.2021 Martin Steppuhn    neuer Zähler, EMH eHZ
# 29.12.2022 Martin Steppuhn    full obis datatype support

import logging
import struct
import time
import serial

class Sml:
    def __init__(self, port=None, lifetime=10, log_name='sml'):
        self.port = port
        self.log = logging.getLogger(log_name)
        self.data = None
        self.lifetime = lifetime
        self.lifetime_timeout = time.perf_counter() + self.lifetime if self.lifetime else None  # set lifetime timeout
        self.com = None
        self.rx_buf = bytes()
        self.log.debug("init port:{}".format(port))

    def calc_crc(self, buffer):
        crc16_x25_table = [
            0x0000, 0x1189, 0x2312, 0x329B, 0x4624, 0x57AD, 0x6536, 0x74BF,
            0x8C48, 0x9DC1, 0xAF5A, 0xBED3, 0xCA6C, 0xDBE5, 0xE97E, 0xF8F7,
            0x1081, 0x0108, 0x3393, 0x221A, 0x56A5, 0x472C, 0x75B7, 0x643E,
            0x9CC9, 0x8D40, 0xBFDB, 0xAE52, 0xDAED, 0xCB64, 0xF9FF, 0xE876,
            0x2102, 0x308B, 0x0210, 0x1399, 0x6726, 0x76AF, 0x4434, 0x55BD,
            0xAD4A, 0xBCC3, 0x8E58, 0x9FD1, 0xEB6E, 0xFAE7, 0xC87C, 0xD9F5,
            0x3183, 0x200A, 0x1291, 0x0318, 0x77A7, 0x662E, 0x54B5, 0x453C,
            0xBDCB, 0xAC42, 0x9ED9, 0x8F50, 0xFBEF, 0xEA66, 0xD8FD, 0xC974,
            0x4204, 0x538D, 0x6116, 0x709F, 0x0420, 0x15A9, 0x2732, 0x36BB,
            0xCE4C, 0xDFC5, 0xED5E, 0xFCD7, 0x8868, 0x99E1, 0xAB7A, 0xBAF3,
            0x5285, 0x430C, 0x7197, 0x601E, 0x14A1, 0x0528, 0x37B3, 0x263A,
            0xDECD, 0xCF44, 0xFDDF, 0xEC56, 0x98E9, 0x8960, 0xBBFB, 0xAA72,
            0x6306, 0x728F, 0x4014, 0x519D, 0x2522, 0x34AB, 0x0630, 0x17B9,
            0xEF4E, 0xFEC7, 0xCC5C, 0xDDD5, 0xA96A, 0xB8E3, 0x8A78, 0x9BF1,
            0x7387, 0x620E, 0x5095, 0x411C, 0x35A3, 0x242A, 0x16B1, 0x0738,
            0xFFCF, 0xEE46, 0xDCDD, 0xCD54, 0xB9EB, 0xA862, 0x9AF9, 0x8B70,
            0x8408, 0x9581, 0xA71A, 0xB693, 0xC22C, 0xD3A5, 0xE13E, 0xF0B7,
            0x0840, 0x19C9, 0x2B52, 0x3ADB, 0x4E64, 0x5FED, 0x6D76, 0x7CFF,
            0x9489, 0x8500, 0xB79B, 0xA612, 0xD2AD, 0xC324, 0xF1BF, 0xE036,
            0x18C1, 0x0948, 0x3BD3, 0x2A5A, 0x5EE5, 0x4F6C, 0x7DF7, 0x6C7E,
            0xA50A, 0xB483, 0x8618, 0x9791, 0xE32E, 0xF2A7, 0xC03C, 0xD1B5,
            0x2942, 0x38CB, 0x0A50, 0x1BD9, 0x6F66, 0x7EEF, 0x4C74, 0x5DFD,
            0xB58B, 0xA402, 0x9699, 0x8710, 0xF3AF, 0xE226, 0xD0BD, 0xC134,
            0x39C3, 0x284A, 0x1AD1, 0x0B58, 0x7FE7, 0x6E6E, 0x5CF5, 0x4D7C,
            0xC60C, 0xD785, 0xE51E, 0xF497, 0x8028, 0x91A1, 0xA33A, 0xB2B3,
            0x4A44, 0x5BCD, 0x6956, 0x78DF, 0x0C60, 0x1DE9, 0x2F72, 0x3EFB,
            0xD68D, 0xC704, 0xF59F, 0xE416, 0x90A9, 0x8120, 0xB3BB, 0xA232,
            0x5AC5, 0x4B4C, 0x79D7, 0x685E, 0x1CE1, 0x0D68, 0x3FF3, 0x2E7A,
            0xE70E, 0xF687, 0xC41C, 0xD595, 0xA12A, 0xB0A3, 0x8238, 0x93B1,
            0x6B46, 0x7ACF, 0x4854, 0x59DD, 0x2D62, 0x3CEB, 0x0E70, 0x1FF9,
            0xF78F, 0xE606, 0xD49D, 0xC514, 0xB1AB, 0xA022, 0x92B9, 0x8330,
            0x7BC7, 0x6A4E, 0x58D5, 0x495C, 0x3DE3, 0x2C6A, 0x1EF1, 0x0F78]

        crcsum = 0xffff
        for byte in buffer:
            crcsum = crc16_x25_table[(byte ^ crcsum) & 0xff] ^ (crcsum >> 8 & 0xff)
        crcsum ^= 0xffff
        return crcsum

    def format_hex(self, data):
        """
        Format bytes to HEX String

        :param data: bytes
        :return: String
        """
        return " ".join(["{:02X}".format(b) for b in data])

    def get_frame(self, buffer):
        """
        Get SML frame from buffer. Function returns the buffer and if found the frame.
        get_frame can be called multiple times on a buffer.

        :param buffer: bytes
        :return: buffer, frame
        """

        if len(buffer) <= 16:
            return buffer, None  # return unmodified buffer (wait for complete rx in next read)

        p = buffer.find(b'\x1B\x1B\x1B\x1B\x01\x01\x01\x01')  # search for start sequence

        if p < 0:
            return bytes(), None  # without start flush entire receive buffer

        buffer = buffer[p:]  # strip bytes infront of start

        p = buffer.find(b'\x1B\x1B\x1B\x1B\x1A')  # search for end sequence

        if p >= 0 and len(buffer) >= p + 8:  # with end ans checksum
            frame = buffer[0: p + 8]
            return buffer[p + 8:], frame
        else:
            return buffer, None  # return unmodified buffer (wait for complete rx in next read)

    def decode_frame(self, frame):
        """
        Decode SML Frame

        :param frame: bytes
        :return: dictionary
        """
        crc_calc = self.calc_crc(frame[0:-2])
        crc_frame, = struct.unpack('<H', frame[-2:])
        # print("crc_calc={} crc_frame={}".format(crc_calc, crc_frame))
        if crc_calc == crc_frame:
            p = self.get_obis(frame, b'\x77\x07\x01\x00\x10\x07\x00\xff')   # 77 07 01 00 10 07 00 ff
            if p is None:
                p = self.get_obis(frame, b'\x77\x07\x01\x00\x0F\x07\x00\xff')  # 77 07 01 00 0F 07 00 ff alternativ wegen EMH eHZ
            return {'e_import': self.get_obis(frame, b'\x77\x07\x01\x00\x01\x08\x00\xff'),
                    'e_export': self.get_obis(frame, b'\x77\x07\x01\x00\x02\x08\x00\xff'),
                    'p': p}
        return None

    def get_obis(self, frame, obis):
        """
        Parse single OBIS entry

        :param frame: bytes
        :param obis: key (bytes)
        :return: value
        """
        try:
            pos = frame.find(obis)  # find obis key
            if pos < 0:
                return None
            pos += len(obis)
            if frame[pos] == 0x64:  # different status length
                pos += 4
            elif frame[pos] == 0x65:  # different status length
                pos += 5
            else:
                pos += 1
            pos += 4
            factor = 10 ** struct.unpack("@b", frame[pos:pos + 1])[0]

            pos += 1
            typ = frame[pos]
            pos += 1
            # print("{:02X} | {}".format(typ, " ".join("{:02X}".format(b) for b in frame[pos: pos + 4])))

            if typ == 0x52:  # int8
                return round(struct.unpack(">b", frame[pos: pos+1])[0] * factor)
            elif typ == 0x53:  # int16
                return round(struct.unpack(">h", frame[pos: pos+2])[0] * factor)
            elif typ == 0x55:  # int32
                return round(struct.unpack(">i", frame[pos: pos+4])[0] * factor)
            elif typ == 0x59:  # int64
                return round(struct.unpack(">q", frame[pos: pos+8])[0] * factor)

            elif typ == 0x62:  # uint8
                return round(struct.unpack(">B", frame[pos: pos+1])[0] * factor)
            elif typ == 0x63:  # uint16
                return round(struct.unpack(">H", frame[pos: pos+2])[0] * factor)
            elif typ == 0x65:  # uint32
                return round(struct.unpack(">I", frame[pos: pos+4])[0] * factor)
            elif typ == 0x69:  # uint64
                return round(struct.unpack(">Q", frame[pos: pos+8])[0] * factor)

            elif typ == 0x56:  # int64 5BYTE, EMH eHZ only 5Byte !!!
                return round(struct.unpack(">q", b'\x00\x00\x00' + frame[pos: pos+5])[0] * factor)
        except:
            return None

    def decode(self, buffer):
        """
        Decode SML Data

        :param buffer:
        :return:
        """
        buffer, frame = self.get_frame(buffer)

        # print("frame", len(frame), self.format_hex(frame))

        if frame:
            dataset = self.decode_frame(frame)
            return buffer, dataset
        else:
            return buffer, None

    def read(self):
        """
        Return latest data from buffer.
        self.data provides the same data but is valid between read() and has a lifetime in seconds

        :return: None / Dictionary
        """

        try:
            if self.com is None:
                self.com = serial.Serial(self.port, baudrate=9600, timeout=0)  # non blocking
            rx = self.com.read(8192)
            self.rx_buf += rx
        except:
            self.com = None
            self.rx_buf = bytes()
        data = None

        while True:
            self.rx_buf, frame = self.get_frame(self.rx_buf)
            if frame:
                self.log.debug("found frame len={}".format(len(frame)))
                data = self.decode_frame(frame)
                if data:
                    self.log.debug("valid sml data {}".format(data))
                    self.data = data
                    self.lifetime_timeout = time.perf_counter() + self.lifetime if self.lifetime else None  # set new lifetime timeout
            else:
                break

        if self.lifetime:
            if self.lifetime_timeout and time.perf_counter() > self.lifetime_timeout:
                self.log.error("data lifetime expired")
                self.lifetime_timeout = None  # disable timeout, restart with next valid receive
                self.data = None  # clear data
        else:
            self.data = None  # without lifetime set self.data instantly to read result

        return True if data else False

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
