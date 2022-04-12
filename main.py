import csv
import datetime
import json
import os
from time import perf_counter, sleep
from urllib.request import Request, urlopen
from threading import Thread, Lock, Semaphore

try:
    from dotenv import load_dotenv
except ImportError as e:
    API_KEY = input("Enter your Meraki's API key: ")
    ORG_ID = input("Enter your Meraki's Organization ID: ")
else:
    load_dotenv()
    API_KEY = os.getenv("API_KEY")
    ORG_ID = os.getenv("ORG_ID")

HEADERS = {'X-Cisco-Meraki-API-Key': API_KEY, 'Content-Type': 'application/json'}
LOCK = Lock()
SEMA = Semaphore(value=10)


def get_network_name(network_id, networks_):
    return [element for element in networks_ if network_id == element['id']][0]['name']


def exec_request(url):
    request = Request(url, headers=HEADERS or {})
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read())
    except Exception as e:
        print(f"[ERROR] {e}")
        result = {}
    return result


def get_device_information(i, device, networks, writer):
    # Using a Semaphore to limit threads to 10 at the same time
    SEMA.acquire()
    network_name = get_network_name(device['networkId'], networks)
    print(f'{i} Looking into network {network_name}')

    try:
        device_name = exec_request(f"https://api.meraki.com/api/v1/networks/{device['networkId']}"
                                   f"/devices/{device['serial']}")['name']
    except Exception as e:
        print(e.args)
        device_name = "Couldn't get device name"

    uplink = exec_request(f"https://api.meraki.com/api/v0/networks/{device['networkId']}"
                          f"/devices/{device['serial']}/uplink")

    usage = exec_request(f"https://api.meraki.com/api/v1/networks/{device['networkId']}/wireless/usageHistory?"
                         f"timespan=86400&deviceSerial={device['serial']}")

    if not usage:
        usage = [{'sentKbps': "error getting information", 'receivedKbps': "error getting information"}]

    # Blank uplink for devices that are down or meshed APs
    if uplink:
        uplink_info = dict.fromkeys(['interface', 'status', 'ip', 'gateway', 'publicIp', 'dns'])
        # All other devices have single uplink
        uplink = uplink[0]
        for key in uplink.keys():
            uplink_info[key] = uplink[key]

        write_to_file(writer, [network_name, device_name, device['serial'], device['model'],
                      uplink_info['status'], uplink_info['ip'], uplink_info['gateway'],
                      uplink_info['publicIp'], uplink_info['dns'],
                      usage[0]['sentKbps'], usage[0]['receivedKbps']])
    SEMA.release()


def write_to_file(writer_, data):
    LOCK.acquire()
    writer_.writerow(data)
    LOCK.release()


def main():
    today = datetime.date.today()

    # Find all appliance networks (MX, Z1, Z3, vMX100)
    name = exec_request(f"https://api.meraki.com/api/v0/organizations/{ORG_ID}")["name"]
    networks = exec_request(f"https://api.meraki.com/api/v0/organizations/{ORG_ID}/networks")
    inventory = exec_request(f"https://api.meraki.com/api/v0/organizations/{ORG_ID}/inventory")

    appliances = [device for device in inventory if
                  device['model'][:2] in ('MX', 'Z1', 'Z3', 'vM') and device['networkId'] is not None]
    devices = [device for device in inventory if device not in appliances and device['networkId'] is not None]
    devices = sorted(devices, key=lambda d: d['networkId'])

    # Output CSV of all 'other devices' info
    with open(name + ' other devices - ' + str(today) + '.csv', 'w', encoding='utf-8', newline='') as csv_file:
        fieldnames = ['Network', 'Device', 'Serial', 'Model', 'Status', 'IP', 'Gateway', 'Public IP', 'DNS',
                      'Usage sentKbps last day', 'Usage receivedKbps last day']
        writer = csv.writer(csv_file, dialect='excel')
        writer.writerow(fieldnames)

        # Iterate through all 'other devices'
        for i, device in enumerate(devices):
            if i % 10 == 0:
                sleep(2)
            thread = Thread(target=get_device_information, args=[i, device, networks, writer], daemon=True)
            thread.start()

        thread.join()


if __name__ == '__main__':
    main()
    print(f"Elapsed time was: {perf_counter()}")
