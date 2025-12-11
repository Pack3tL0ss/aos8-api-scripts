#!/usr/bin/env python3
#
# Author: Wade Wells github/Pack3tL0ss
#
# Version 2020-1.0


import socket
import threading
import time
from datetime import datetime, timezone
from pathlib import Path, PurePath
from common.arubaos_ssh import Cli

import requests
# from OpenSSL import crypto  # type: ignore
# from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.extensions import SubjectAlternativeName
# from cryptography import x509

from common import AosConnect, config, log, parse

LOCK = threading.Lock()
COUNT = 3
controllers = ''
port = ''


class Certificate:
    def __init__(self, data: dict):
        self.expired = None
        self.update_data(data)

    def update_data(self, data):
        self.name = data.get("cert_cn")
        self.ca_issuers_uri = data.get("cert_ca_issuers_uri")
        self.expire_date = data.get("cert_exp_date")
        if self.expire_date:
            self.expired = datetime.now(timezone.utc) > self.expire_date
            # try:
            # except TypeError:
            #     self.expired = datetime.now() > self.expire_date
        self.san = data.get("cert_san")


def verify_get_new_cert():
    if not config.cert.ok:
        raise Exception("Configuration data missing, verify contents of config.yaml")

    p = Path(PurePath(config.cert.dir, config.cert.p12_name))

    if not p.exists():
        log.fatal(f"{p.name} Not Found Exiting...")
        exit(1)

    le_p12 = pkcs12.load_key_and_certificates(p.read_bytes(), config.cert.p12_pass.encode("UTF-8"))
    le_key, cert, other_certs_in_chain = le_p12
    # le_cert=cert.public_bytes(serialization.Encoding.PEM)
    le_exp = cert.not_valid_after_utc
    # le_key=le_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption())

    sub = cert.subject.rfc4514_string()
    cn = sub.split("=")[-1]

    data = {}
    data["cert_cn"] = None if not cn else cn
    data["cert_exp_date"] = le_exp
    _san = cert.extensions.get_extension_for_class(SubjectAlternativeName)
    data["cert-san"] = _san.value

    return Certificate(data)


class ManagedDevice():
    def __init__(self, data: dict = None, connection=None):
        if connection:
            self.connection = connection
        if data:
            self.update_data(data)

    def update_data(self, data):
        if "cert_cn" in data.keys():
            self.portal = Certificate(data)
        else:
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
        self.new_cert = verify_get_new_cert()
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

    def push_new_cert(self, md: ManagedDevice) -> None:
        new_cert = self.new_cert
        diff = new_cert.expire_date - md.portal.expire_date
        # if diff.days > 0:
        d = datetime.now()
        time_stamp = d.strftime("%h%d_%Y")  # Dec25_2020  Unique enough to ensure no conflicts with previous cert
        new_cert_name = f"LE_{time_stamp}_2"
        # TODO would need to determine this md is associated with this conductor in the event they put multiple in the config.  For now we just use the first one.
        # might already be handled using self vs config
        if diff.days != 0:
            cfg_dict = {
                "ip": self.conductors[0],
                "cli_user": config.user,
                "cli_pass": f"{config.password}",
                "cmd_list": [
                    f"copy tftp: {config.cert.tftp_svr} {config.cert.p12_name} flash {new_cert.name}.p12",  # File copied successfully
                    "conf t",
                    f"crypto pki-import pkcs12 ServerCert {new_cert_name} {new_cert.name}.p12 {config.cert.p12_pass}",  # Certificate is uploaded. Please execute "crypto-local pki SERVERCERT securelogin.kabrew.com_0412.p12 securelogin.kabrew.com.p12" from a config node
                    f"cd {config.cert.md_path}",
                    f"crypto-local pki ServerCert {new_cert_name} {new_cert.name}.p12",
                    "write mem",  # Configuration Saved
                    "web-server profile",
                    f"captive-portal-cert {new_cert_name}"
                ]
            }
            cli = Cli(**cfg_dict)
            print(cli)
            log.info("If the Script was done the Cert would be pushed here")
            # TODO login to mds and # "process restart httpd", "y"
        else:
            log.info(f"{md.name}: No Certificate Update necessary Expiration is the same.")

    def start_controller_threads(self, devices):
        """Login/establish session for each controller
        """
        thread_array = []
        t = [None] * len(devices)

        for i, dev in enumerate(devices):
            _this = (dev, config.user, config.password)
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
                log.info(f"{ip}: Session Estabished")
                if ip not in self.data:
                    self.data[ip] = ManagedDevice(connection=con)
                else:
                    setattr(self.data[ip], 'connection', con)
            else:
                log.error(f"{dev}: Failure Establishing Session: {r.error}")

        except socket.gaierror:
            log.critical(f"{dev}: Unable to resolve host.")
        except ConnectionRefusedError as e:
            log.critical(f"{dev}: Unable to connect to Controller. Login Failed.\n{e}")
        except requests.RequestException as e:
            log.critical(f"{dev}: Requests Exception {e}")
        except Exception as e:
            log.critical(f"{dev}: Exception Occured {e}")

    def exec_api_md(self):
        for dev in self.data:
            if hasattr(self.data[dev], "connection"):
                con = self.data[dev].connection
                res = con.execute_command("show web-server profile")
                pretty_name = f"{self.data[dev].name}:({dev})"
                if res.ok:
                    web_svr_data = parse.show_web_server_profile(res)
                    cert_name = web_svr_data.get("Captive Portal Certificate")
                    if not cert_name:
                        log.error(f"{pretty_name}: No Captive Portal Certificate Returned")
                        self.data[dev].portal = None
                    elif cert_name == "default":
                        log.info(f"{pretty_name} is using the default certificate... data retrieval skipped")
                        self.data[dev].portal = None
                    else:
                        cert_data = con.execute_command(f"show crypto pki ServerCert {cert_name}")
                        cert_data = parse.show_crypto_pki_servercert(cert_data)
                        if not cert_data:
                            log.error(
                                f"{pretty_name}: "
                                f"No cert data retunred from output of show crypto pki ServerCert {cert_name}"
                                )
                        else:
                            self.data[dev].update_data(cert_data)
                            yield self.data[dev]

    def exec_api(self, conductor=True):
        if conductor:
            ''' get all the MDs connect to the Mobility Conductor'''
            for dev in self.data.copy():
                if self.data[dev].connection.handle:
                    con = self.data[dev].connection
                    res = con.execute_command("show switches")
                    if res.ok:
                        switch_dict = parse.show_switches(res.json())
                        for ip in switch_dict:
                            if switch_dict[ip]['Type'] in ["MD", "master", "conductor"]:
                                self.data[ip] = ManagedDevice(data=switch_dict[ip])
                        # Determine if this is VRRP address for MM
                        try:
                            res = con.execute_command("show vrrp")
                            if res.json().get('_data'):
                                if dev in '\n'.join(res.json()['_data']):
                                    log.info(
                                        f'Removing MM VRRP addrress ({dev}) from data '
                                        f'- data will include physical addresses'
                                             )
                                    con.handle.close()
                                    log.info(f"{dev}: Session Closed")
                                    del self.data[dev]
                        except Exception as e:
                            log.error(f"{dev}: Exception occured 'show vrrp' {e}")
        else:
            for dev in self.exec_api_md():
                self.push_new_cert(dev)
                con = dev.connection
                pretty_name = f"{dev.name}:({dev.ip})"
                # Done with API calls close session with Controller
                try:
                    con.handle.close()
                    log.info(f"{pretty_name}: Session Closed")
                except Exception as e:
                    log.error(f"{pretty_name}: Error on session close {e}")


if __name__ == "__main__":
    log.info(f" {'-' * 10 } Script Startup {'-' * 20 }")
    mcds = config.conductors
    if mcds:
        aruba = Controllers(mcds)
        log.info(f" {'-' * 10 } Script Complete {'-' * 20 }")
    else:
        print('No Data, Check config.yaml')
