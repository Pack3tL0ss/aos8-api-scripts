import os
import paramiko
import time
import re
import socket
import typer
from . import log
# def log(msg):
#     print(msg)


class Cli:
    """Class to execute CLI commands on device after configuration has been sent.

    Adapted from the Aruba Networks Automation Teams work on
    https://github.com/aruba/aruba-switch-ansible
    """
    def __init__(self, ip: str = None, cli_user: str = None, cli_pass: str = None,
                 cli_timeout: int = 5, cmd_list: list = None, **kwargs):

        self.fail_msg = ''
        self.ip = ip
        self.cmd_list = cmd_list
        if not cli_user or cli_pass is None or not cmd_list:
            log.info(f"No CLI Operations Performed on {ip} Missing/incomplete cli configuration")
        else:
            paramiko_ssh_connection_args = {'hostname': ip, 'port': 22, 'look_for_keys': False,
                                            'username': cli_user, 'password': cli_pass,
                                            'timeout': cli_timeout, **kwargs}

            # Login
            self.ssh_client = paramiko.SSHClient()
            # Default AutoAdd as Policy
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.run(paramiko_ssh_connection_args)

    def fail_json(self, **kwargs):
        self.fail_msg = {k: v for k, v in kwargs.items()}

    def execute_command(self, command_list: list):
        """
        Execute command and returns output
        :param command_list: list of commands
        :return: output of show command
        """
        if command_list.count("edomtset") >= 2:
            prompt = re.compile(re.escape(self.prompt.replace('#', '').replace(')[', ') [')) + '.*[#\$]')
        else:
            prompt = re.compile(re.escape(self.prompt.replace('#', '').replace(')[', ') [')) + '.*#')

        # Clear Buffer
        self.out_channel()

        # disable paging
        if command_list and not command_list[0].startswith("no pag"):
            command_list.insert(0, "no pag")

        cli_output = []
        for command in command_list:
            if command.startswith('SLEEP'):
                _ = os.system(command.lower())
            else:
                self.in_channel(command)
                count = 0
                text = ''
                fail = True
                while count < 45:
                    time.sleep(2)
                    curr_text = self.out_channel(command)
                    text += curr_text
                    if prompt.search(curr_text):
                        fail = False
                        break
                    count += 1
                if fail:
                    self.fail_json(msg='Unable to read CLI Output in given Time')
                # Reformat text
                text = text.replace('\r', '').rstrip('\n')
                # Delete command and end prompt from output
                # text_lines = text.split('\n')[1:-1]
                # cli_output.append('\n'.join(text))
                cli_output += [text]

        return cli_output

    def get_prompt(self):
        """
        Additional needed Setup for Connection
        """
        # Set prompt
        count = 0
        fail = True
        self.in_channel("")
        while count < 45:
            time.sleep(2)
            curr_text = self.out_channel()
            if '#' in curr_text:
                fail = False
                break
            count += 1
        if fail:
            self.fail_json(msg='Unable to read CLI Output in given Time')

        # Set prompt
        count = 0
        self.in_channel("")
        # Regex for ANSI escape chars and prompt
        text = ''
        fail = True
        while count < 45:
            time.sleep(2)
            curr_text = self.out_channel()
            text += curr_text.replace('\r', '')
            if '#' in curr_text:
                fail = False
                break
            count += 1

        if fail:
            self.fail_json(msg='Unable to read CLI Output in given Time for prompt')

        # typer.unstyle removes all ANSI escape chars
        self.prompt = typer.unstyle(text).strip('\n').replace(' ', '')

    def out_channel(self, command: str = ""):
        """
        Clear Buffer/Read from Shell
        :return: Read lines
        """
        recv = ""
        # Loop while shell is able to recv data
        while self.shell_chanel.recv_ready():
            recv = self.shell_chanel.recv(65535)
            if not recv:
                self.fail_json(msg='Chanel gives no data. Chanel is closed by Switch.')
            recv = recv.decode('utf-8', 'ignore')
            # remove all ANSI escape characters
            recv = typer.unstyle(recv)
            # normalize output (make all line endings consistent with \n and strip echo of provided cmd)
            recv = "\n".join([line.rstrip() if not command or not line.startswith(command) else line[len(command):].rstrip() for line in recv.splitlines()])
        return recv

    def in_channel(self, cmd):
        """
        Sends cli command to Shell
        :param cmd: the command itself
        """
        cmd = cmd.rstrip()
        cmd += '\n'
        cmd = cmd.encode('ascii', 'ignore')
        self.shell_chanel.sendall(cmd)

    def logout(self):
        """
        Logout from Switch
        :return:
        """
        self.in_channel('end')
        self.in_channel('exit')
        self.shell_chanel.close()
        self.ssh_client.close()

    def run(self, connection_args):
        '''Establish Connection to device and run CLI commands provided via ztp config

        Args:
            connection_args (dict): Arguments passed to paramiko to establish connection
        '''
        result = dict(
            changed=False,
            cli_output=[],
            message=''
        )
        _start_time = time.time()
        while True:
            try:
                go = False
                # Connect to Switch via SSH
                self.ssh_client.connect(**connection_args)
                self.prompt = ''
                # SSH Command execution not allowed, therefore using the following paramiko functionality
                self.shell_chanel = self.ssh_client.invoke_shell()
                self.shell_chanel.settimeout(8)
                # AOS-CX specific
                self.get_prompt()
                go = True
                break
            except socket.timeout:
                log.error(f'ZTP CLI Operations Failed, TimeOut Connecting to {self.ip}')
            except paramiko.ssh_exception.NoValidConnectionsError as e:
                log.error(f'ZTP CLI Operations Failed, {e}')
            except paramiko.ssh_exception.AuthenticationException:
                log.error('ZTP CLI Operations Failed, CLI Authentication Failed verify creds in config')

            if time.time() - _start_time >= 30:
                break  # Give Up
            else:
                time.sleep(10)

        if go:
            try:
                result['cli_output'] = self.execute_command(self.cmd_list)
                result['changed'] = True
                if self.fail_msg:
                    result['message'] += self.fail_msg.get('msg')
            finally:
                self.logout()

            # Format log entries and exit
            _res = " -- // Command Results \\ -- \n"
            _cmds = [c for c in self.cmd_list if 'SLEEP' not in c]
            for cmd, out in zip(_cmds, result['cli_output']):
                if "progress:" in out and f"progress: {out.count('progress:')}/{out.count('progress:')}" in out:
                    out = out.split("progress:")[0] + f"progress: {out.count('progress:')}/{out.count('progress:')}"
                _res += "{}:{} {}\n".format(cmd, '\n' if '\n' in out else '', out)
            _res += " --------------------------- \n"
            _res += ''.join([f"{k}: {v}\n" for k, v in result.items() if k != "cli_output" and v])
            print(_res)
            # log.info(f"Post ZTP CLI Operational Result for {ip}:\n{_res}")


# if __name__ == "__main__":
#     def __init__(self, ip: str = None, cli_method: str = 'ssh', cli_user: str = None, cli_pass: str = None,
#                  cli_timeout: int = 5, cmd_list: list = None, **kwargs):
#         cfg_dict = {
#             "ip": "mm.kabrew.com",
#             "cli_user": "wade",
#             "cli_pass": "hpIMC!!!",
#             "cmd_list": [
#                 "copy tftp: 10.0.30.31 securelogin.kabrew.com.pfx flash securelogin.kabrew.com.p12",
#                 "cd /mynode", "conf t",
#                 "crypto pki-import pkcs12 ServerCert securelogin.kabrew.com.pfx securelogin.kabrew.com.p12 hpIMC!!!",
#                 "cd /md/WadeLab/Cluster", "conf t", "crypto-local pki ServerCert securelogin_kabrew.com.pfx securelogin.kabrew.com.p12",
#                 "web-server profile", "switch-cert default", "process restart httpd", "y"
#             ]
#         }
#         cli = Cli(**cfg_dict)
#         print(cli)
