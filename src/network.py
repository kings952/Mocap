import json
import socket

class PoseSender:
    def __init__(self, host="127.0.0.1", port=8765):
        self.addr=(host,port)
        self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

    def send(self,payload):
        data=json.dumps(payload,separators=(",",":")).encode("utf-8")
        self.sock.sendto(data,self.addr)

    def close(self):
        self.sock.close()
