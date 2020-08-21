#!/etc/ConsolePi/venv/bin python3
#
# Author: Wade Wells github/Pack3tL0ss
# portions of this script based on the work already done by https://github.com/aruba/arubaos8-example-scripts


import threading
import datetime
import utils
import requests
import argparse
import logging
# import yaml
# from tabulate import tabulate
# import argparse
import os.path
import time
import utils

LOCK = threading.Lock()
COUNT = 3
controllers = ''
final_result = []
port = ''
localtime = datetime.datetime.now().strftime("%m%d%Y_%H%M%S")
outfile = 'results.log'
logfile = 'image_versions.log'
yaml_config = 'config.yaml'

# setting the logging level
logging.basicConfig(filename=logfile, level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger(__name__)


def connect():
    """
    This function is utilized to read controllers information from config file and start the Multi-threaded session
    """

    # -- // Get Config from config.yaml \\ --
    config = utils.get_yaml_file(yaml_config)

    i = 0
    thread_array = []
    mcds = config.get('conductors', [])
    t = [None] * len(mcds)

    for mcd in mcds:
        '''------------Initiating a thread for API session to each controller IP----------------'''
        _this = [mcd, config['user'], config['pass'], 'MM']
        thread_array.append(_this)
        t[i] = threading.Thread(target=exec_api, args=(_this))

        t[i].daemon = True
        t[i].start()

        time.sleep(0.5)
        i += 1

    count = 0
    for thread in t:
        thread.join()
        logging.info(f"Thread with ip - {thread_array[count]} completed")
        count += 1

def find_up_mds(data):
    """ checks for all the UP state MDs and returns a list of MDs"""
    val = []
    for k in data.keys():
        if data[k][3] == 'up':
            val.append(k)
    return (val)

def exec_api(ip_address, username, password, model_type=""):
    """
    This function will login into the controller via API and execute all the commands sequentially for all the IPs.
    :param ip_address: IP address of the controller
    :param username: Username of the controller
    :param password: password of the controller
    :param model_type: if the controller is MM/MD
    """

    try:

        if not os.path.isfile(outfile):
            # create result file
            fd = open(outfile, 'w')
            fd.close()
        con = utils.ConnectUtil(ip_address, username, password, port)
        if not con.api_login():
            raise ConnectionRefusedError

        if model_type == 'MM':
            ''' get all the MDs connect to the particular MM'''
            con.execute_command("show switches")
            controller_ids = con.ps.parse_show_switches()
            md_list = find_up_mds(controller_ids)
            ''' execute show configuration committed on all MDs'''
            if len(md_list) > 0:
                print('validating configuration on MDs connected to MM {}\n'.format(ip_address))

                for cntr in md_list:
                    cntr = cntr.strip('\r\n')
                    print(cntr)
                    # cmd = 'show configuration committed ' + cntr
                    # con.execute_command(cmd)
                    # ''' parse the tunnel configuration tunnel source and tunnel destination'''
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

                    '''print results on the terminal'''
                    # if verbose and len(result1) > 1 and len(result2) > 1:
                    #     print('overlapping ip tunnel validation result for node {} connected to MM {},\n'
                    #           .format(cntr, ip_address))
                    #     print(tabulate(result1, headers='firstrow', tablefmt="fancy_grid"))
                    #     print('\ntunnel group validation result for node {} connected to MM {} ,\n'.format(cntr,
                    #                                                                                        ip_address))
                    #     print(tabulate(result2, headers='firstrow', tablefmt="fancy_grid"))

        if model_type == 'MD':
            ## check tunnel status
            print('validating tunnel status on MD {}\n'.format(ip_address))
            cmd = 'show ip interface brief'
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
            #     logging.critical('NO Tunnels Found for MD node {}'.format(ip_address))
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
    except ConnectionRefusedError as e:
        logging.critical("Unable to connect to Controller. Login Failed. {}".format(ip_address))
    except requests.RequestException as e:
        logging.critical("New Connection error. Network Failure {}".format(ip_address))
    except Exception as e:
        logging.critical("session timeout/ controller crashed {}".format(ip_address))

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
    connect()