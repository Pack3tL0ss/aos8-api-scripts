#!/etc/ConsolePi/venv/bin python3
#
# Author: Wade Wells github/Pack3tL0ss
# portions of this script based on the work already done by https://github.com/aruba/arubaos8-example-scripts


import threading
import datetime
import utils
import requests
import argparse
import socket
# import log
# import yaml
# from tabulate import tabulate
# import argparse
import os
import time

path = os.path
LOCK = threading.Lock()
COUNT = 3
controllers = ''
final_result = []
port = ''
localtime = datetime.datetime.now().strftime("%m%d%Y_%H%M%S")
outfile = 'results.log'
log_file = 'image_versions.log'
yaml_config = 'config.yaml'
DEBUG = os.environ.get('DEBUG', False)


# setting the log level
log = utils.MyLogger(log_file, debug=DEBUG)
log.info(f" {'-' * 10 } Script Startup {'-' * 20 }")

# -- // Get Config from config.yaml \\ --
config = utils.get_yaml_file(yaml_config)


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


class Controllers():
    def __init__(self, conductors):
        self.conductors = conductors
        self.data = {}
        self.run()

    def run(self):
        # Start parallel threads to establish session with Mobility Conductors
        # updates data attribute
        self.start_controller_threads(self.conductors)
        start = len(self.data)
        if self.data:
            self.exec_api()
        if len(self.data) > start:
            md_list = [dev for dev in self.data if not hasattr(self.data[dev], 'connection')]
            self.start_controller_threads(md_list)
            self.exec_api(conductor=False)

    def start_controller_threads(self, devices):
        """Get Session for each
        """
        thread_array = []
        t = [None] * len(devices)

        for i, dev in enumerate(devices):
            '''------------Initiating a thread for API session to each controller IP----------------'''
            _this = [dev, config['user'], config['pass']]
            thread_array.append(_this)
            t[i] = threading.Thread(target=self.get_session, args=(_this))

            t[i].daemon = True
            t[i].start()

            time.sleep(0.5)

        for idx, thread in enumerate(t):
            thread.join()
            log.info(f"Thread with ip - {thread_array[idx][0]} completed", show=True)

    def get_session(self, dev, username, password):
        try:
            ip = socket.gethostbyname(dev)
            con = utils.AosConnect(ip, user=username, password=password)
            r = con.api_login()
            if r.ok:
                if ip not in self.data:
                    self.data[ip] = ManagedDevice(connection=con)
                else:
                    setattr(self.data[ip], 'connection',con)
            else:
                log.error(r.err)
                raise r.error.__name__
        except socket.gaierror:
            log.critical(f"[{dev}] Unable to resolve host.")
        except ConnectionRefusedError as e:
            log.critical(f"[{dev}] Unable to connect to Controller. Login Failed.\n{e}")
        except requests.RequestException as e:
            log.critical(f"[{dev}] Requests Exception {e}")
        except Exception as e:
            log.critical(f"[{dev}] Exception Occured {e}")

    def exec_api(self, conductor=True):
        """
        This function will login into the controller via API and execute all the commands sequentially for all the IPs.
        :param ip_address: IP address of the controller
        :param username: Username of the controller
        :param password: password of the controller
        :param model_type: if the controller is MM/MD
        """
        if conductor:
            ''' get all the MDs connect to the Mobility Conductor'''
            for dev in self.data.copy():
                if self.data[dev].connection.handle:
                    con = self.data[dev].connection
                    res = con.execute_command("show switches")
                    if res.ok:
                        switch_dict = utils.parse_show_switches(res.json)
                        for ip in switch_dict:
                            self.data[ip] = ManagedDevice(data=switch_dict[ip])
        else:
            for dev in self.data:
                if hasattr(self.data[dev], "connection"):
                    con = self.data[dev].connection
                    res = con.execute_command("show image version")
                    if res.ok:
                        img_dict = utils.parse_show_image_version(res.json)
                        for k, v in img_dict.items():
                            setattr(self.data[dev], k, v)

        print(self.data)


            # con.execute_command("show switches")
            # md_dict = con.ps.parse_show_switches()

            # # md_list = find_up_mds(controller_ids)
            # ''' execute show configuration committed on all MDs'''
            # if md_dict:
            #     print('validating configuration on MDs connected to MM {}\n'.format(ip_address))

            #     for md in md_dict:
            #         print(md)

                        # tun_conf = con.ps.parse_show_config_tunnel(cntr)

                        # ''' validate for overlapping src/dst IP'''
                        # result1 = validate_tunnel_ip(tun_conf)
                        # # final_result.append(result1)
                        # '''parse the tunnel group configuration from show config'''
                        # tun_grp = con.ps.parse_tunnel_group(cntr)
                        # '''validate tunnel grp assigned to the tunnels on the node'''
                        # result2 = validate_tunnel_grp(tun_conf, tun_grp)
                        # #  final_result.append(result2)
                        # ''' write results to the result file'''
                        # fd = open(outfile, "a")
                        # fd.write('\noverlapping ip tunnel validation result for node {} connected to MM {},\n'
                        #          .format(cntr, ip_address))
                        # fd.write('+++++++++++++++++++++++++++++++++++++++++++++++++\n')
                        # if (len(result1) > 1):
                        #     fd.write(tabulate(result1, headers="firstrow"))
                        #     fd.write('\n')
                        # else:
                        #     fd.write('No tunnels found for node {}'.format(cntr))
                        #     fd.write('\n')

                        # fd.write(
                        #     '\ntunnel group validation result for node {} connected to MM {} ,\n'.format(cntr, ip_address))
                        # fd.write('+++++++++++++++++++++++++++++++++++++++++++++++++\n')

                        # if (len(result2) > 1):
                        #     fd.write(tabulate(result2, headers='firstrow'))
                        #     fd.write('\n')
                        # else:
                        #     fd.write('No tunnels found for node {}'.format(cntr))
                        #     fd.write('\n')

                        # fd.close()

                        # '''print results on the terminal'''
                        # if verbose and len(result1) > 1 and len(result2) > 1:
                        #     print('overlapping ip tunnel validation result for node {} connected to MM {},\n'
                        #           .format(cntr, ip_address))
                        #     print(tabulate(result1, headers='firstrow', tablefmt="fancy_grid"))
                        #     print('\ntunnel group validation result for node {} connected to MM {} ,\n'.format(cntr,
                        #                                                                                        ip_address))
                        #     print(tabulate(result2, headers='firstrow', tablefmt="fancy_grid"))

            # if model_type == 'MD':
            #     ## check tunnel status
            #     print('validating tunnel status on MD {}\n'.format(ip_address))
            #     cmd = 'show ip interface brief'
                # con.execute_command(cmd)

                # '''parse tunnel UP / down status from each of the MD'''
                # intf_state = con.ps.parse_show_ip_interface(ip_address)

                # ''' validate if tunnel status is UP or DOWN'''
                # result3 = validate_tunnel_status(intf_state)
                # fd = open(outfile, "a")
                # '''write to file the results'''
                # fd.write('\ntunnel status validation result for MD node {},\n'.format(ip_address))
                # fd.write('+++++++++++++++++++++++++++++++++++++++++++++++++\n')
                # if len(result3) == 1:
                #     log.critical('NO Tunnels Found for MD node {}'.format(ip_address))
                #     fd.write('No Tunnels found for node {}\n'.format(ip_address))
                #     if verbose:
                #         print('No Tunnels found for node {}.\n'.format(ip_address))
                # else:
                #     ''' write results to the result file'''
                #     fd.write(tabulate(result3, headers="firstrow"))
                #     final_result.append(result3)
                #     fd.write('\n')
                #     '''print results on the terminal'''
                #     if verbose:
                #         print('\ntunnel status validation result for MD node {},\n'.format(ip_address))
                #         print(tabulate(result3, headers="firstrow", tablefmt="fancy_grid"))
                # fd.close()
            # con.handle.close()




if __name__ == "__main__":
    parser = argparse.ArgumentParser('Run Tunnel Validation  tool.\n'
                                     'Example: mainFile.py  --controller controllers.txt --port 4343 --verbose\n')

    parser.add_argument('--controllers', help='list of controllers and username/password, \n'
                                              'Default file is included with distribution, \n'
                                              'Example - 10.1.1.1,viewonly,viewonly,MD')
    parser.add_argument('--port', default=4343, help='provide custom REST API https port, default port used is 4343')
    parser.add_argument('--verbose', dest='verbose', action='store_true', help='set this option to print results on '
                                                                               'terminal\n')
    parser.set_defaults(verbose=False)

    args = parser.parse_args()
    if args.controllers is None:
        pass

    else:
        controllers = args.controllers

    port = args.port
    verbose = args.verbose

    mcds = config.get('conductors', [])
    if mcds:
        Controllers(mcds)
    else:
        print('No Data, Check config.yaml')