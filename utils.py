#!/usr/bin/env python3
#
# Author: Wade Wells github/Pack3tL0ss
# portions of this script based on the work already done by https://github.com/aruba/arubaos8-example-scripts


import logging
import re
import requests
import urllib3
import json
import datetime
import yaml
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PROMPT = re.compile(r"([a-zA-Z0-9\-.\s]*#)")

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}


class Response():
    def __init__(self, ok: bool, output=None, error=None, status_code=None, state=None, do_json=False,  **kwargs):
        self.ok = ok
        self.text = output
        self.error = error
        self.state = state
        self.status_code = status_code
        if 'json' in kwargs:
            self.json = kwargs['json']
        else:
            self.json = None if not do_json else json.dumps(output)


class MyLogger:
    def __init__(self, log_file, debug=False):
        self.log_msgs = []
        self.DEBUG = debug
        self.verbose = False
        self.log_file = log_file
        self._log = self.get_logger()
        self.name = self._log.name

    def get_logger(self):
        '''Return custom log object.'''
        fmtStr = "%(asctime)s [%(process)d][%(levelname)s]: %(message)s"
        dateStr = "%m/%d/%Y %I:%M:%S %p"
        logging.basicConfig(filename=self.log_file,
                            level=logging.DEBUG if self.DEBUG else logging.INFO,
                            format=fmtStr,
                            datefmt=dateStr)
        return logging.getLogger('ConsolePi')

    def log_print(self, msgs, log=False, show=True, level='info', *args, **kwargs):
        msgs = [msgs] if not isinstance(msgs, list) else msgs
        _msgs = []
        _logged = []
        for i in msgs:
            if log and i not in _logged:
                getattr(self._log, level)(i)
                _logged.append(i)
            if '\n' in i:
                _msgs += i.replace('\t', '').replace('\r', '').split('\n')
            elif i.startswith('[') and ']' in i:
                _msgs.append(i.split(']', 1)[1].replace('\t', '').replace('\r', ''))
            else:
                _msgs.append(i.replace('\t', '').replace('\r', '').strip())

        msgs = []
        [msgs.append(i) for i in _msgs
            if i and i not in msgs and i not in self.log_msgs]

        if show:
            self.log_msgs += msgs
            for m in self.log_msgs:
                print(m)
            self.log_msgs = []

    def show(self, msgs, log=False, show=True, *args, **kwargs):
        self.log_print(msgs, show=show, log=log, *args, **kwargs)

    def debug(self, msgs, log=True, show=False, *args, **kwargs):
        self.log_print(msgs, log=log, show=show, level='debug', *args, **kwargs)

    # -- more verbose debugging - primarily to get json dumps
    def debugv(self, msgs, log=True, show=False, *args, **kwargs):
        if self.DEBUG and self.verbose:
            self.log_print(msgs, log=log, show=show, level='debug', *args, **kwargs)

    def info(self, msgs, log=True, show=False, *args, **kwargs):
        self.log_print(msgs, log=log, show=show, *args, **kwargs)

    def warning(self, msgs, log=True, show=False, *args, **kwargs):
        self.log_print(msgs, log=log, show=show, level='warning', *args, **kwargs)

    def error(self, msgs, log=True, show=False, *args, **kwargs):
        self.log_print(msgs, log=log, show=show, level='error', *args, **kwargs)

    def exception(self, msgs, log=True, show=False, *args, **kwargs):
        self.log_print(msgs, log=log, show=show, level='exception', *args, **kwargs)

    def critical(self, msgs, log=True, show=False, *args, **kwargs):
        self.log_print(msgs, log=log, show=show, level='critical', *args, **kwargs)

    def fatal(self, msgs, log=True, show=False, *args, **kwargs):
        self.log_print(msgs, log=log, show=show, level='fatal', *args, **kwargs)

    def setLevel(self, level):
        getattr(self._log, 'setLevel')(level)


class AosConnect(Response):

    def __init__(self, ip, user='', password='', port=4343):
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        self.handle = None
        self.output = ''

    def api_login(self) -> object:
        """
        This function will login into the controller using API.
        :return: connection handle for the device.
        """

        url = f"https://{self.ip}:{self.port}/v1/api/login"
        payload = {'username': self.user, 'password': self.password}

        if self.ip:
            try:
                r = requests.post(url, data=payload, headers=headers, verify=False)
                self.handle = r
                return Response(ok=True, output=r.text, json=r.json(), status_code=r.status_code)
            except Exception as err:
                return Response(ok=False, error=err, status_code=r.status_code)
        else:
            return Response(ok=False, error="No IP address")

    def execute_command(self, cmd: str) -> object:
        """
        This function will execute commands on controller and returns the output
        :param cmd: command to be executed on device
        :return: data containing output of the command
        """
        try:
            parameters = {"UIDARUBA": self.handle.headers['Set-Cookie'].split(';')[0].split('=')[1], "command": cmd}
            r = requests.get(f"https://{self.ip}:{self.port}/v1/configuration/showcommand",
                             verify=False,
                             headers=headers,
                             params=parameters, cookies=self.handle.cookies
                             )
            if r.ok:
                self.handle = r
                return Response(ok=True, output=r.text, status_code=r.status_code, json=r.json())
            else:
                return Response(ok=False, error=r.reason, status_code=r.status_code)
        except Exception as err:
            return Response(ok=False, error=err)


def parse_show_switches(data: dict):
    """
    Parses show switches output
    :returns dictionary of ManagedDevice objects by switch IP
    """
    # data = json.loads(data)
    switch_dict = {}
    for dev in data.get('All Switches', {}):
        switch_dict[dev['IP Address']] = dev

    return switch_dict


def parse_show_image_version(data):
    """Parse return from show image version command
    """
    # data = json.loads(data)
    data = data.get('_data', [])[0].split('\n')
    img_dict = {}
    _part = 'err'
    for line in data:
        if line.startswith("Partition"):
            if '0:0' in line:
                _part = '0:0'
            elif '0:1' in line:
                _part = '0:1'
            if 'Default boot' in line:
                img_dict['default_boot'] = f"0:{line.split(':')[2].replace(' **Default boot**', '')}"
            continue
        if line.startswith('Software Version'):
            img_dict[f"version {_part}"] = line.split(':')[1].strip()
        if line.startswith('Build num'):
            img_dict[f"version {_part}"] += f" Build: {line.split(':')[1].strip()}"

    return img_dict


def get_yaml_file(yaml_file):
    '''Return dict from yaml file.'''
    if os.path.isfile(yaml_file) and os.stat(yaml_file).st_size > 0:
        with open(yaml_file) as f:
            try:
                # return yaml.load(f, Loader=yaml.BaseLoader)
                return yaml.load(f, Loader=yaml.FullLoader)
            except ValueError as e:
                print(f'Unable to load configuration from {yaml_file}\n\t{e}', show=True)