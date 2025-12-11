#!/etc/ConsolePi/venv/bin python3
#
# Author: Wade Wells github/Pack3tL0ss
#
# Version 0.1
#
from typing import Union, Any, List

import socket
import threading
import time
from rich.console import Console

import aiohttp
import asyncio
from netmiko.aruba import ArubaOsSSH
from netmiko.exceptions import NetmikoTimeoutException

from common import config, log, Response
from common.models import APDBModel

LOCK = threading.Lock()
COUNT = 3
controllers = ''
port = ''
outfile = 'results.csv'
outfile2 = 'results.txt'
config = config.config

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}


class SSHResponse:
    def __init__(self, stdout: str, stderr: str = None, *, cmd: str = ""):
        self.cmd = cmd
        self.response = stdout if stdout is not None else stderr
        self.error = stderr


class BatchRequest:
    def __init__(self, func: callable, args: Any = (), **kwargs: dict) -> None:
        """Constructor object for for api requests.

        Used to pass multiple requests into CentralApi batch_request method for parallel
        execution.

        Args:
            func (callable): The CentralApi method to execute.
            args (Any, optional): args passed on to method. Defaults to ().
            kwargs (dict, optional): kwargs passed on to method. Defaults to {}.
        """
        self.func = func
        self.args: Union[list, tuple] = args if isinstance(args, (list, tuple)) else (args, )
        self.kwargs = kwargs

    def __repr__(self):
        return f"<{self.__module__}.{type(self).__name__} ({self.func.__name__}) object at {hex(id(self))}>"


async def is_reachable(host: str, port: Union[str, list], timeout: int = 2, silent: bool = True):
    s = socket.socket()
    try:
        s.settimeout(timeout)
        s.connect((host, port))
        _reachable = True
    except Exception as e:
        if not silent:
            print("something's wrong with %s:%d. Exception is %s" % (host, port, e))
        _reachable = False
    finally:
        s.close()
    return _reachable


class AP:
    def __init__(self, name: str, ip: str, reachable: bool = None):
        self.name = name
        self.ip = ip
        self.reachable = reachable
        self.cmd: str = None
        self.response: str = None

    def __repr__(self):
        return f"<AP ({self.name}) object at {hex(id(self))}>"

    def __str__(self):
        return self.response if self.response else f"{self.name}|{self.ip}: No Response"


class AosConnect(Response):

    def __init__(self, port: int = 4343):
        self.port = port
        self.user = config["user"]
        self.password = config["pass"]
        self.handle = None
        self.output = ''
        self.ip = config["conductors"][-1]  # script built to only expect a single conductor currently

    def down_aps(self) -> List[AP]:
        return asyncio.run(self.get_down_aps())

    async def get_down_aps(self) -> object:
        """
        This function will login into the controller using API.
        :return: connection handle for the device.
        """

        base_url = f"https://{self.ip}:{self.port}"
        payload = {'username': self.user, 'password': self.password}

        if self.ip:
            async with aiohttp.ClientSession(base_url=base_url, ) as session:
                con = await session.post("/v1/api/login", data=payload, headers=headers, ssl=False)
                uuid = con.headers["Set-Cookie"].split(';')[0].split('=')[1]

                res = await session.get("/v1/configuration/showcommand", headers=headers, params={"UIDARUBA": uuid, "command": "show ap database status down"}, ssl=False)

                try:
                    res_data = await res.json()
                    res_data = APDBModel(**res_data)
                    r = [AP(name=ap.name, ip=ap.ip) for ap in res_data.ap_database]
                    return r
                except Exception:
                    res_data = await res.text()
                    return res_data

    async def ssh_run_command(self, host: str, user: str, psswd: str, cmd: Union[str, List[str]], expect_string: str = None) -> SSHResponse:
        cmd = cmd if isinstance(cmd, list) else [cmd]
        cmd = [c.strip() for c in cmd]
        try:
            ssh = ArubaOsSSH(host=host, username=user, password=psswd, timeout=3,)
            cmd_res = ssh.send_command("\n".join(cmd), expect_string=expect_string)
            cmd_res.replace(expect_string, f"[bright_green]{expect_string}[/]")
        except NetmikoTimeoutException:
            cmd_res = f"[bright_red]Unable to connect to {host}[/]"

        confirm_strings = ["yes", "y"]
        cmd = [c.rstrip("\ny").rstrip("\nY").rstrip("\nyes").rstrip("\nYES") for c in cmd if c.lower() not in confirm_strings]
        console = Console(emoji=False)
        console.print(f"{host}: {cmd} -> {cmd_res.splitlines()[-1]}")
        return SSHResponse(cmd_res.splitlines()[-1], cmd="; ".join(cmd))

    async def _batch_request(self, api_calls: List[BatchRequest]) -> List[Response]:
        # self.silent = True
        _start = time.perf_counter()
        _api_calls = [call.func(*call.args, **call.kwargs) for call in api_calls]

        m_resp = await asyncio.gather(*_api_calls)
        _elapsed = time.perf_counter() - _start
        log.debug(f"batch of {len(api_calls)} took {_elapsed:.2f}.")

        return m_resp

    # TODO return a BatchResponse object (subclass Response) where OK indicates all OK
    # and method that returns merged output from all resp...
    def batch_request(self, api_calls: List[BatchRequest], progress_msg: str = None) -> List[Response]:
        """non async to async wrapper for multiple parallel API calls

        First entry is ran alone, if successful the remaining calls
        are made in parallel.

        Args:
            api_calls (List[BatchRequest]): List of BatchRequest objects.
            progress_msg (Optional str): message to display with progress spinner.

        Returns:
            List[Response]: List of aosapi.response.Response objects.
        """
        if progress_msg:
            console = Console(emoji=False)
            with console.status(progress_msg):
                return asyncio.run(self._batch_request(api_calls))
        else:
            return asyncio.run(self._batch_request(api_calls))


if __name__ == "__main__":
    log.info(f" {'-' * 10 } Script Startup {'-' * 20 }")
    x = AosConnect()
    br = BatchRequest
    console = Console(emoji=False)
    down_aps = asyncio.run(x.get_down_aps())
    if down_aps:
        # reachable_reqs = [br(is_reachable, (ap.ip, 22)) for ap in down_aps]
        # reachable_resp = x.batch_request(reachable_reqs, progress_msg=f"Checking reachability for {len(down_aps)} APs")
        # _ = [setattr(ap, "reachable", reachable) for ap, reachable in zip(down_aps, reachable_resp)]

        # reboot_calls = [br(x.ssh_run_command, (ap.ip,), user="wade", psswd="hpIMC!!!", cmd="reload\ny\n", expect_string="Reloading") for ap in down_aps if ap.reachable]
        reboot_calls = [br(x.ssh_run_command, (ap.ip,), user=config["user"], psswd=config["pass"], cmd="reload\ny\n", expect_string="Reloading") for ap in down_aps]
        reboot_res = x.batch_request(reboot_calls, progress_msg=f"rebooting {len(down_aps)} APs")
        pass
        # reboot_res = x.batch_request(reboot_calls, progress_msg=f"rebooting {len([ap for ap in down_aps if ap.reachable])} reachable APs")

        # skipped_calls = [SSHResponse(f"Device {ap.name} @ {ap.ip} is not reachable", cmd="reload") for ap, reachable in zip(down_aps, reachable_resp) if not reachable]
        # total_res = [*skipped_calls, *reboot_res]

        # console.print(total_res)
    else:
        console.print("No down APs")
