#!/usr/bin/env python3
import asyncio
from bleak import BleakScanner
from datetime import datetime
import logging
import csv
import os
import warnings

# Silenciar warnings coneguts de Bleak
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Configura log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("findmy_scanner")

# Arxiu de sortida
OUTPUT_FILE = "findmy_scan_log.csv"

# Escrivim capçalera si no existeix
if not os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "rpi", "device_name", "mac_address", "rssi"])

APPLE_COMPANY_ID = 0x004C
FINDMY_HEADER = b'\x12'

def parse_findmy_rpi(manufacturer_data):
    if manufacturer_data.startswith(FINDMY_HEADER):
        rpi = manufacturer_data[1:17]
        return rpi.hex()
    return None

async def scan():
    print("🔍 Escanejant dispositius BLE... (Ctrl+C per sortir)\n")

    def detection_callback(device, advertisement_data):
        md = advertisement_data.manufacturer_data
        for k, v in md.items():
            if k == APPLE_COMPANY_ID and isinstance(v, bytes):
                rpi = parse_findmy_rpi(v)
                if rpi:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    print(f"📡 Beacon Apple: {rpi} {device.name} {device.address} {advertisement_data.rssi} dBm {datetime.now().strftime('%H:%M:%S')}")

                    # Escriu al CSV
                    with open(OUTPUT_FILE, "a", newline="") as f:
                        writer = csv.writer(f)
                        writer.writerow([timestamp, rpi, device.name, device.address, advertisement_data.rssi])

    scanner = BleakScanner(detection_callback)
    await scanner.start()
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await scanner.stop()
        print("\n⏹ Escaneig aturat.")

if __name__ == "__main__":
    asyncio.run(scan())
