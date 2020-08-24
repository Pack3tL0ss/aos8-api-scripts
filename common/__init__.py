#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import urllib3
import requests


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# PROMPT = re.compile(r"([a-zA-Z0-9\-.\s]*#)")

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
            self.json = None


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
                return Response(ok=False, error=err)
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
                # self.handle = r
                return Response(ok=True, output=r.text, status_code=r.status_code, json=r.json())
            else:
                return Response(ok=False, error=r.reason, status_code=r.status_code)
        except Exception as err:
            return Response(ok=False, error=err)


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
        return logging.getLogger(__name__)

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


# DEBUG = os.getenv('DEBUG', False)
# log = MyLogger(os.path.join(os.path.abspath(".."), 'logs', f"{__name__}.log"), debug=DEBUG)
