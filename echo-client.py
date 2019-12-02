#!/usr/bin/env python3

import socket
import sys

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65432        # The port used by the server
message = sys.argv[1]

if message:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(bytes(message, 'utf-8'))
        data = s.recv(1024)

    print('Received', repr(data.decode('UTF-8')))
else:
    print('Don\'t use a empty string as the parameter')
