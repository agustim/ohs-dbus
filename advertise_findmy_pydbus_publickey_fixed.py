#!/usr/bin/env python3
import time
from pathlib import Path
from gi.repository import GLib
from pydbus import SystemBus
from threading import Thread

KEY_FILE = "/home/agusti/Escriptori/Personal/myhaystack/mykeys/esp32/3XB36C_keyfile"
BUS_NAME = 'org.bluez'
ADAPTER_PATH = '/org/bluez/hci0'
ADVERTISING_INTERFACE = 'org.bluez.LEAdvertisingManager1'
ADVERTISING_PATH_TEMPLATE = '/org/bluez/example/advertisement{}'
INTERVAL = 600  # Segons entre rotacions

# Header seguint l'ESP32: Type (0x12), Length (0x19), State (0x00)
MYFIND = b'\x12\x19\x00'
# L'ESP32 fa padding final amb dos zeros

class Advertisement:
    def __init__(self, rpi_data):
        self.Type = 'broadcast'
        self.ServiceUUIDs = []
        self.SolicitUUIDs = []
        self.ManufacturerData = {0x004C: GLib.Variant('ay', MYFIND + rpi_data + b'\x00\x00')}
        self.ServiceData = {}
        self.LocalName = ''
        self.Includes = ['tx-power']
        self.TxPower = 0
        self.Appearance = 0
        self.Duration = 0
        self.Timeout = 0
        self.SecondaryChannel = '1M'

    def Release(self):
        print("🔌 Released advertisement")

    def get_path(self, timestamp):
        return ADVERTISING_PATH_TEMPLATE.format(timestamp)

    def Introspect(self):
        return f'''
        <node>
          <interface name="org.bluez.LEAdvertisement1">
            <method name="Release"/>
            <property name="Type" type="s" access="read"/>
            <property name="ServiceUUIDs" type="as" access="read"/>
            <property name="SolicitUUIDs" type="as" access="read"/>
            <property name="ManufacturerData" type="a{{qv}}" access="read"/>
            <property name="ServiceData" type="a{{sv}}" access="read"/>
            <property name="LocalName" type="s" access="read"/>
            <property name="Includes" type="as" access="read"/>
            <property name="TxPower" type="n" access="read"/>
            <property name="Appearance" type="q" access="read"/>
            <property name="Duration" type="q" access="read"/>
            <property name="Timeout" type="q" access="read"/>
            <property name="SecondaryChannel" type="s" access="read"/>
          </interface>
        </node>
        '''


def read_public_key(path):
    data = Path(path).read_bytes()
    # data[0]=versió, data[1:29]=public_key de 28 bytes
    return data[7:29]  # l'ESP32 copia public_key[6:28]


def run_loop():
    loop = GLib.MainLoop()
    loop.run()


def main():
    bus = SystemBus()
    adapter = bus.get(BUS_NAME, ADAPTER_PATH)
    adv_mgr = adapter

    rpi_data = read_public_key(KEY_FILE)
    print(f"Clau pública extreta RPI_data (22B): {rpi_data.hex()}")

    Thread(target=run_loop, daemon=True).start()

    while True:
        ts = int(time.time())
        payload = MYFIND + rpi_data + b'\x00\x00'
        print(f"📡 Emetent payload a {time.strftime('%H:%M:%S')}: {payload.hex()}")
        ad = Advertisement(rpi_data)
        path = ad.get_path(ts)

        try:
            bus.unregister_object(path)
        except:
            pass

        bus.register_object(path, ad, ad.Introspect())
        try:
            adv_mgr.RegisterAdvertisement(path, {})
        except Exception as e:
            print("Register error:", e)

        time.sleep(INTERVAL)

        try:
            adv_mgr.UnregisterAdvertisement(path)
            bus.unregister_object(path)
        except:
            pass

if __name__ == '__main__':
    main()
