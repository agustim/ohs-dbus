#!/usr/bin/env python3
import time
import base64
import asyncio

from gi.repository import GLib
from pydbus import SystemBus
from threading import Thread

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256

KEY_FILE = "/home/agusti/Escriptori/Personal/myhaystack/mykeys/esp32/3XB36C.keys"
BUS_NAME = 'org.bluez'
ADAPTER_PATH = '/org/bluez/hci0'
ADVERTISING_INTERFACE = 'org.bluez.LEAdvertisingManager1'

ADVERTISING_PATH_TEMPLATE = '/org/bluez/example/advertisement{}'

LOOP_TIME = 30  # seconds

class Advertisement:
    def __init__(self, rpi_data):
        self.Type = 'broadcast'
        self.ManufacturerData = {0x004C: GLib.Variant('ay', bytes([0x12]) + rpi_data)}
        self.Includes = ['tx-power']
        self.TxPower = 0
        self.LocalName = 'MyFindTag'
        self.Appearance = 0

    def Release(self):
        print("🔌 Released advertisement")

    def get_properties(self):
        return {
            'org.bluez.LEAdvertisement1': {
                'Type': GLib.Variant('s', self.Type),
                'ManufacturerData': GLib.Variant('a{qv}', self.ManufacturerData),
                'Includes': GLib.Variant('as', self.Includes),
                'TxPower': GLib.Variant('n', self.TxPower),
            }
        }

    def get_path(self, timestamp):
        return ADVERTISING_PATH_TEMPLATE.format(timestamp)

    def get_interfaces(self):
        return ['org.bluez.LEAdvertisement1']

    def Introspect(self):
        return f'''
        <node>
          <interface name="org.bluez.LEAdvertisement1">
            <method name="Release"/>
            <property name="Type" type="s" access="read"/>
            <property name="ManufacturerData" type="a{{qv}}" access="read"/>
            <property name="Includes" type="as" access="read"/>
            <property name="TxPower" type="n" access="read"/>
          </interface>
        </node>
        '''

def read_private_key(path):
    with open(path, "r") as f:
        for line in f:
            if line.startswith("Private key:"):
                return base64.b64decode(line.split(":", 1)[1].strip())
    raise ValueError("Private key not found.")

def generate_rpi(private_key, timestamp):
    interval = timestamp // LOOP_TIME  # For testing purposes
    salt = interval.to_bytes(4, 'big')
    rpi_key = HKDF(private_key, 16, salt, SHA256, 1, context=b'OpenHaystack')
    cipher = AES.new(rpi_key, AES.MODE_ECB)
    return cipher.encrypt(bytes(16))[:16]

def run_loop():
    loop = GLib.MainLoop()
    loop.run()

def main():
    bus = SystemBus()
    adapter = bus.get(BUS_NAME, ADAPTER_PATH)
    adv_mgr = adapter[ADVERTISING_INTERFACE]

    private_key = read_private_key(KEY_FILE)

    #GLib.threads_init()
    Thread(target=run_loop, daemon=True).start()

    while True:
        timestamp = int(time.time())
        rpi = generate_rpi(private_key, timestamp)
        print(f"📡 Emetent RPI a {time.strftime('%H:%M:%S')}: {rpi.hex()}")
        ad = Advertisement(rpi)
        path = ad.get_path(timestamp)

        try:
            bus.unregister_object(path)
        except Exception:
            pass

        bus.register_object(path, ad, ad.Introspect())
        try:
            adv_mgr.RegisterAdvertisement(path, {})
        except Exception:
            pass

        time.sleep(LOOP_TIME)

        try:
            adv_mgr.UnregisterAdvertisement(path)
            bus.unregister_object(path)
        except Exception:
            pass

if __name__ == "__main__":
    main()
