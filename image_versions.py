#!/etc/ConsolePi/venv/bin python3
#
# Author: Wade Wells github/Pack3tL0ss
#
# Version 2020-1.1
#
# portions of this script based on the work already done by https://github.com/aruba/arubaos8-example-scripts


import socket
import threading
import time

import requests

from common import AosConnect, config, log, parse

LOCK = threading.Lock()
COUNT = 3
controllers = ''
port = ''
outfile = 'results.csv'
outfile2 = 'results.txt'
config = config.config


class ManagedDevice:
    def __init__(self, data: dict = None, connection=None):
        if connection:
            self.connection = connection
        if data:
            self.update_data(data)

    def update_data(self, data):
        self.name = data.get('Name')
        self.cfg_id = data.get('Config ID')
        self.sync_time = data.get('Config Sync Time (sec)')
        self.cfg_state = data.get('Configuration State')
        self.ip = data.get('IP Address')
        self.location = data.get('Location')
        self.model = data.get('Model')
        self.status = data.get('Status')
        self.type = data.get('Type')
        self.version = data.get('Version')

    def __repr__(self):
        ret = f" ---- {self.name} ----\n"
        for k, v in self.__dict__.items():
            if isinstance(v, (str, int)):
                ret += f" {k}: {v}\n"
        return ret

    def _repr_csv_(self):
        """csv representation

        Returns:
            tuple: commas seperated values of class attributes: (keys, values)
        """
        head = ""
        ret = ""
        for k, v in self.__dict__.items():
            if isinstance(v, (str, int)):
                head += f"{k},"
                ret += f"{v},"
        return head.rstrip(','), ret.rstrip(',')


class Controllers():
    def __init__(self, conductors):
        self.conductors = conductors
        self.data = {}
        self.run()

    def run(self):
        ''' Start parallel threads to establish session with Mobility Conductors

        updates data attribute
        '''
        self.start_controller_threads(self.conductors)
        start = len(self.data)
        if self.data:
            self.exec_api()
        if len(self.data) > start:
            md_list = [dev for dev in self.data if not hasattr(self.data[dev], 'connection')]
            self.start_controller_threads(md_list)
            self.exec_api(conductor=False)

        with open(outfile, "w") as out:
            for dev in self.data:
                out.write(self.data[dev]._repr_csv_()[0] + "\n")
                break
            for dev in self.data:
                out.write(self.data[dev]._repr_csv_()[1] + "\n")

        by_version = {}
        for dev in self.data:
            ver0 = self.data[dev].__dict__.get("version 0:0")
            ver1 = self.data[dev].__dict__.get("version 0:1")
            if ver0 not in by_version:
                by_version[ver0] = []
            if ver1 not in by_version:
                by_version[ver1] = []
            _this0 = {'name': self.data[dev].name, 'ip': self.data[dev].ip, 'type': self.data[dev].type}
            _this1 = {'name': self.data[dev].name, 'ip': self.data[dev].ip, 'type': self.data[dev].type}
            _this0['default_boot'] = True if '0:0' in self.data[dev].default_boot else False
            _this1['default_boot'] = True if '0:1' in self.data[dev].default_boot else False
            _this0['partition'] = '0:0'
            _this1['partition'] = '0:1'
            by_version[ver0] += [_this0]
            by_version[ver1] += [_this1]

        with open(outfile2, "w") as out:
            rel6 = False
            for rel in by_version:
                if rel.startswith('6'):
                    rel6 = True
                out.write(f"Partitions Containing {rel}\n")
                for dev in by_version[rel]:
                    out.write(f"  {dev['type']}: {dev['name']}({dev['ip']}) Partition: {dev['partition']} "
                              f"{'' if not dev['default_boot'] else '**default boot**'}\n")
                out.write('\n')
            if rel6:
                out.write(" ** Partitions exist with 6.x **\n")
            else:
                out.write(" ** NO partitions exist with 6.x **\n")

    def start_controller_threads(self, devices):
        """Login/establish session for each controller
        """
        thread_array = []
        t = [None] * len(devices)

        for i, dev in enumerate(devices):
            _this = [dev, config['user'], config['pass']]
            thread_array.append(_this)
            t[i] = threading.Thread(target=self.get_session, args=(_this))

            t[i].daemon = True
            t[i].start()

            time.sleep(0.5)

        for thread in t:
            thread.join()

    def get_session(self, dev, username, password):
        try:
            ip = socket.gethostbyname(dev)
            con = AosConnect(ip, user=username, password=password)
            r = con.api_login()
            if r.ok:
                log.info(f"{ip}: Session Estabished", show=True)
                if ip not in self.data:
                    self.data[ip] = ManagedDevice(connection=con)
                else:
                    setattr(self.data[ip], 'connection', con)
            else:
                log.error(f"{dev}: Failure Establishing Session: {r.error}", show=True)
                # raise r.error.__name__
        except socket.gaierror:
            log.critical(f"{dev}: Unable to resolve host.")
        except ConnectionRefusedError as e:
            log.critical(f"{dev}: Unable to connect to Controller. Login Failed.\n{e}")
        except requests.RequestException as e:
            log.critical(f"{dev}: Requests Exception {e}")
        except Exception as e:
            log.critical(f"{dev}: Exception Occured {e}")

    def exec_api(self, conductor=True):
        if conductor:
            ''' get all the MDs connect to the Mobility Conductor'''
            for dev in self.data.copy():
                if self.data[dev].connection.handle:
                    con = self.data[dev].connection
                    res = con.execute_command("show switches")
                    if res.ok:
                        switch_dict = parse.show_switches(res.json)
                        for ip in switch_dict:
                            if switch_dict[ip]['Type'] in ["MD", "master"]:
                                self.data[ip] = ManagedDevice(data=switch_dict[ip])
                        # Determine if this is VRRP address for MM
                        try:
                            res = con.execute_command("show vrrp")
                            if res.json.get('_data'):
                                if dev in '\n'.join(res.json['_data']):
                                    log.info(f'{dev}: Removing MM VRRP addrress from data - data will include physical addresses')
                                    con.handle.close()
                                    log.info(f"{dev}: Session Closed", show=True)
                                    del self.data[dev]
                        except Exception as e:
                            log.error(f"{dev}: Exception occured 'show vrrp' {e}")
        else:
            for dev in self.data:
                if hasattr(self.data[dev], "connection"):
                    con = self.data[dev].connection
                    res = con.execute_command("show image version")
                    if res.ok:
                        img_dict = parse.show_image_version(res.json)
                        for k, v in img_dict.items():
                            setattr(self.data[dev], k, v)
                    else:
                        log.error(f"{dev}: error: ({res.status_code}) {res.error}", show=True)

                    # Done with API calls close session with Controller
                    try:
                        con.handle.close()
                        log.info(f"{dev}: Session Closed", show=True)
                    except Exception as e:
                        log.error(f"{dev}: Error on session close {e}")


if __name__ == "__main__":
    log.info(f" {'-' * 10 } Script Startup {'-' * 20 }")
    mcds = config.get('conductors', [])
    if mcds:
        Controllers(mcds)
    else:
        print('No Data, Check config.yaml')
