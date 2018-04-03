#!/usr/bin/env python3
from __future__ import print_function
import socket
import sys
import time
from timeit import default_timer as timer
import threading
import json
from subprocess import call

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("172.24.1.1", 80))
print(s.getsockname()[0])
selfIP = (s.getsockname()[0])
s.close()

def log(message):
     global lastlog
     global logreader
     if message is not None:
          message = str(message)
          t = time.strftime("%Y %m %d %H:%M:%S")
          print('['+t+'] : ' + message)
          lastlog = ('['+t+'] : ' + message)
          



class myThread (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
        ThreadedServer('',int(2000)).listen()
        print("Exiting " + self.name)

class ThreadedServer(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

    def listen(self):
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(60)
            threading.Thread(target = self.listenToClient,args = (client,address)).start()

    def listenToClient(self, client, address):
        
        size = 1024
        exitthread = False
        while exitthread == False:
            try:
                rdata = client.recv(size)
                
                if rdata:
                   recmsg = rdata.decode("utf-8")
                   print(recmsg)
                else:
                       raise error('Client disconnected')
            except:
                client.close()
                return False

thread1 = myThread(1, "socketserver", 0)
thread1.daemon = True
thread1.start() 


ss=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
host= '172.24.1.1'
port=int(2000)

message = "LOGREADER|logrequest|"+selfIP+"|"

try:
    ss.connect((host,port))
    ss.sendall((message.encode()))
    ss.close()
    
except socket.error:
    logreader = False;
    log('Nincs MAINUNIT / Nem válaszol')

while True:
    time.sleep(1)
    
