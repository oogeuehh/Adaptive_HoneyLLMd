import paramiko
import socket

class MySSHServer(paramiko.ServerInterface):
    def __init__(self):
        self.event = paramiko.Event()

    def check_auth_password(self, username, password):
        if username == "root" and password == "password":
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password'

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_exec_request(self, channel, command):
        channel.send("Command executed: {}\n".format(command))
        return True
