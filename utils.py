#!/usr/bin/env python3
#
# Author: Wade Wells github/Pack3tL0ss
# portions of this script based on the work already done by https://github.com/aruba/arubaos8-example-scripts


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


class ConnectUtil:

    def __init__(self, ip, user='', password='', port=4343):
        self.ip = ip
        self.port = port
        self.user = user
        self.password = password
        self.handle = None
        self.ps = ParseCommand()
        self.output = ''

    def api_login(self) -> object:
        """
        This function will login into the controller using API.
        :return: connection handle for the device.
        """

        url = f"https://{self.ip}:{self.port}/v1/api/login"
        payload = {'username': self.user, 'password': self.password}

        try:
            if self.ip:
                r = requests.post(url, data=payload, verify=False)
                self.handle = r
                print(r.text)
                return True
            else:
                raise Exception("No IP")
        except Exception as err:
            return False

    def execute_command(self, cmd: str) -> object:
        """
        This function will execute commands on controller and returns the output
        :param cmd: command to be executed on device
        :return: data containing output of the command
        """
        parameters = {"UIDARUBA": self.handle.headers['Set-Cookie'].split(';')[0].split('=')[1], "command": cmd}
        self.handle = requests.get(f"https://{self.ip}:{self.port}/v1/configuration/showcommand",
                                   verify=False,
                                   headers=headers,
                                   params=parameters, cookies=self.handle.cookies)
        data = self.handle.content.decode('utf-8')
        self.ps.value = data
        self.output = data


class ParseCommand:

    def __init__(self, value='', sc_model=''):
        self.value = value
        self.sc_model = sc_model

    def parse_show_switches(self):
        """
        Parses show switches output
        :returns dictionary with Node Name , IP address, Configuration Status and Status of MD
        """
        localtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = json.loads(self.value)
        new_values = {}
        for var in data['All Switches']:
            if var['Type'] == 'MD':
                attribute_name = var['Name']
                tupple = (localtime, var['IP Address'], var['Configuration State'], var['Status'])
                new_values.update({attribute_name.rstrip(): tupple})
        return new_values

def get_yaml_file(yaml_file):
    '''Return dict from yaml file.'''
    if os.path.isfile(yaml_file) and os.stat(yaml_file).st_size > 0:
        with open(yaml_file) as f:
            try:
                # return yaml.load(f, Loader=yaml.BaseLoader)
                return yaml.load(f, Loader=yaml.FullLoader)
            except ValueError as e:
                print(f'Unable to load configuration from {yaml_file}\n\t{e}', show=True)