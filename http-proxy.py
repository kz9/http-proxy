#!/usr/bin/env python3

import re
import socket
import sys
import datetime
from enum import Enum, auto
from urllib.parse import urlparse


class MessageType(Enum):
    REQUEST = auto()
    RESPONSE = auto()


def main():
    HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
    PORT = int(sys.argv[1])  # Port to listen on

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        print('Listening on the {}'.format(PORT))
        while True:
            conn, addr = s.accept()
            buffer = b''
            # Listen for HTTP requests
            with conn:
                while True:
                    data = conn.recv(65536)
                    if not data:
                        break
                    buffer += data
                    msg = parse_message(buffer)
                    if msg is not None:
                        now = datetime.datetime.now()
                        log = {}
                        log['addr'] = addr[0]
                        log['time'] = '[' +\
                                      now.strftime('%d/%b/%Y:%H:%M:%S') + ']'
                        log['request'] = '"' + ' '.join([msg['field1'],
                                                        msg['field2'],
                                                        msg['field3']]) + '"'
                        log['agent'] = '"' + msg['user-agent'] + '"'
                        server_ip, server_port = parse_uri(msg['field2'])
                        with socket.socket(socket.AF_INET,
                                           socket.SOCK_STREAM) as so:
                            so.connect((server_ip, server_port))
                            so.sendall(msg['data'])
                            buf = b''
                            while True:
                                data = so.recv(65536)
                                if not data:
                                    break
                                buf += data
                                msg = parse_message(buf)
                                if msg is not None:
                                    if 'referer' not in msg.keys():
                                        msg['referer'] = '-'
                                    if 'content-length' not in msg.keys():
                                        msg['content-length'] = 0
                                    print(log['addr'], log['time'],
                                          log['request'],
                                          msg['field2'], msg['content-length'],
                                          '"' + msg['referer'] + '"',
                                          log['agent'])
                                    conn.send(msg['data'])
                                    break
                        break


def parse_message(buf):
    try:
        message = {}
        line, data = parse_line(buf)
        count = 0
        first = line.split(' ', 2)
        if len(first) == 3:
            if re.match(r'^\d+$', first[1]) is not None:
                message['type'] = MessageType.RESPONSE
            else:
                message['type'] = MessageType.REQUEST
            message['field1'] = first[0]
            message['field2'] = first[1]
            message['field3'] = first[2]
        line, data = parse_line(data)
        while line and count == 0:
            header = line.split(':', 1)
            message[header[0].lower()] = header[1].strip()
            line, data = parse_line(data)
            if line is not None and len(line) == 0:
                count += 1
        if message['type'] is MessageType.REQUEST and count != 0:
            if 'content-length' in message.keys():
                if len(data) >= int(message['content-length']):
                    message['content'] = data
            message = make_forward(message)
        elif message['type'] is MessageType.RESPONSE and count != 0:
            if 'content-length' not in message.keys():
                if data is not None:
                    message['content'] = data
                message = make_forward(message)
            elif int(message['content-length']) == 0 and data is None:
                message['content'] = ''.encode('iso-8859-1')
                message = make_forward(message)
            elif data is not None and int(message['content-length']) <=\
                    len(data):
                message['content'] = data
                message = make_forward(message)
            else:
                message = None
        else:
            message = None
        return message
    except Exception as e:
        return e


def parse_line(data, encoding='iso-8859-1'):
    if data:
        loc = data.find(b'\n')
    else:
        loc = -1

    # I only want to read a line if I can see the \n terminator
    if loc >= 0:
        line = data[0:loc+1].decode(encoding)
        line = line.strip('\r\n')

        # If there are more characters, "tail" the stream
        if len(data) > loc + 1:
            return line, data[loc+1:]
        else:
            return line, None

    # If I can't see the termination, we expect more data
    else:
        return None, data


def make_forward(msg, encoding='iso-8859-1'):
    msg['data'] = b''
    if msg['type'] is MessageType.REQUEST:
        msg['field3'] = 'HTTP/1.0'
    else:
        msg['field1'] = 'HTTP/1.0'
    msg['data'] += '{} {} {}\r\n'.format(msg['field1'], msg['field2'],
                                         msg['field3']).encode(encoding)
    for i in msg.keys():
        if i not in ['type', 'field1', 'field2', 'field3', 'data']:
            if i == 'content':
                msg['data'] += '\r\n'.encode(encoding) + msg['content']
            else:
                msg['data'] += '{}: {}\r\n'.format(i, msg[i]).encode(encoding)
    if 'content-type' in msg.keys():
        if msg['content-type'] == 'text/html':
            msg['data'] += '\r\n'.encode(encoding)
    else:
        msg['data'] += '\r\n'.encode(encoding)
    return msg


def parse_uri(uri):
    uri = urlparse(uri)
    scheme = uri.scheme
    host = uri.hostname

    # urlparse can't deal with partial URI's that don't include the
    # protocol, e.g., push.services.mozilla.com:443

    if host:  # correctly parsed
        if uri.port:
            port = uri.port
        else:
            port = socket.getservbyname(scheme)
    else:  # incorrectly parsed
        uri = uri.path.split(':')
        host = uri[0]
        if len(uri) > 1:
            port = int(uri[1])
        else:
            port = 80

    return host,  port


if __name__ == "__main__":
    main()
