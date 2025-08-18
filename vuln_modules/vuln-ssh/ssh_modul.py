try:
    import psyco
    psyco.full()
    from psyco.classes import *
except ImportError:
    pass


import struct
import random
import hashlib
import os
import amun_logging
import traceback
import StringIO
import sys
from ssh_server import *
import paramiko
import socket

class vuln:

    def __init__(self):
        try:
            self.vuln_name = "SSH CHECK Vulnerability"
            self.stage = "SSH_STAGE1"
            self.welcome_message = "SSH-2.0-OpenSSH_7.4\n"
            self.shellcode = []

            # Automatically generate RSA key if it doesn't exist
            self.key_filename = './test_rsa.key'
            if not os.path.exists(self.key_filename):
                self.host_key = paramiko.RSAKey.generate(2048)
                self.host_key.write_private_key_file(self.key_filename)
                print ".::[Amun - SSH] Generated new RSA key and saved to {}".format(self.key_filename)
            else:
                self.host_key = paramiko.RSAKey(filename=self.key_filename)

        except KeyboardInterrupt:
            raise

    def write_hexdump(self, shellcode=None, extension=None):
        if not shellcode:
            hash = hashlib.sha("".join(self.shellcode))
        else:
            hash = hashlib.sha("".join(shellcode))
        if extension is not None:
            filename = "hexdumps/%s-%s.bin" % (extension, hash.hexdigest())
        else:
            filename = "hexdumps/%s.bin" % (hash.hexdigest())
        if not os.path.exists(filename):
            with open(filename, 'a+') as fp:
                if not shellcode:
                    fp.write("".join(self.shellcode))
                else:
                    fp.write("".join(shellcode))
            print ".::[Amun - SSH] no match found, writing hexdump ::."
        return

    def getVulnName(self):
        return self.vuln_name

    def getCurrentStage(self):
        return self.stage

    def getWelcomeMessage(self):
        return self.welcome_message

    def incoming(self, message, bytes, ip, vuLogger, random_reply, ownIP):
        try:
            # Set up the socket and bind it to listen for incoming SSH connections
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((ownIP, 0))
            sock.listen(100)

            # Accept an incoming connection
            client, addr = sock.accept()

            # Create a new Paramiko transport for this connection
            transport = paramiko.Transport(client)
            transport.add_server_key(self.host_key)

            # Start the SSH session
            server = MySSHServer()
            transport.start_server(server=server)

            # Wait for authentication
            chan = transport.accept(20)
            if chan is None:
                print "No channel."
                return

            # If a session is opened, interact with the attacker
            chan.send("Welcome to the SSH Honeypot\n")
            while True:
                command = chan.recv(1024).decode('utf-8')
                if command.strip() in ('quit', 'exit'):
                    chan.send("Goodbye\n")
                    break
                chan.send("Command not found: {}\n".format(command))

        except Exception, e:
            print "Exception: ", e
            traceback.print_exc()
        finally:
            if 'client' in locals():
                client.close()
            sock.close()
