#!/usr/bin/python
from __future__ import print_function
import time, datetime
from timeit import default_timer as timer
#import bluepy.btle as btle
import threading
import sys
import socket
import websockets
import json
import asyncio
import random
import pymysql
from time import gmtime, strftime, sleep
from bluepy.btle import Scanner, DefaultDelegate, BTLEException, Peripheral
import sys
import json
import numpy as np
import subprocess
from pykalman import KalmanFilter

drop_value = 80
trigger_value = 62 #50
trigger_floor = 58 #47 


logreader = False
runthegame = False
stopmeplease = False
pmdata=[[0,[[],[],0,0,0,[]]],
        [1,[[],[],0,0,0,[]]],
        [2,[[],[],0,0,0,[]]],
        [3,[[],[],0,0,0,[]]],
        [4,[[],[],0,0,0,[]]],
       ]

forgettime = 3

loop = asyncio.new_event_loop()
WSCONTROL = False
sendMsgToControl = []

def log(message):
     global lastlog
     global logreader
     global sendMsgToLog
     
     if message is not None:
          message = str(message)
          t = time.strftime("%Y %m %d %H:%M:%S")
          print('['+t+'] : ' + message)
          lastlog = ('['+t+'] : ' + message)
          #print(len(sendMsgToLog))
          if logreader == True and len(sendMsgToLog)<5:
               sendMsgToLog.append(lastlog)

def is_json(myjson):
  try:
    json_object = json.loads(myjson)
  except ValueError:
    return False
  return True

def getip ():
    cmd = "hostname -I | cut -d\' \' -f1"
    IP = subprocess.check_output(cmd, shell = True )
    IP=str(IP)
    IP=IP.replace("b'","")
    stat_IP=IP.replace("\\n'","")
    return(stat_IP)

def parab (ts1,ts2,ts3,rssi1,rssi2,rssi3):

    #ts1 = 11.9650
    #ts2 = 12.1357
    #ts3 = 12.3101

    #rssi1 = 75
    #rssi2 = 49
    #rssi3 = 55

    #print(ts1)
    #print(ts2)
    #print(ts3)

    #print(rssi1)
    #print(rssi2)
    #print(rssi3)
    
    A = np.array([(ts1*ts1,ts1,1),(ts2*ts2,ts2,1),(ts3*ts3,ts3,1)],dtype='float64')
    B = np.array([rssi1,rssi2,rssi3])


    z = np.linalg.solve(A,B)
    print(z)
    ret=round(abs((z[1]*2)/(z[0]*4)),4)
    return (ret)
class KalmanFilter(object):

    def __init__(self, process_variance, estimated_measurement_variance, posteri_estimate):
        self.process_variance = process_variance
        self.estimated_measurement_variance = estimated_measurement_variance
        self.posteri_estimate = posteri_estimate
        self.posteri_error_estimate = 10.0

    def input_latest_noisy_measurement(self, measurement):
        priori_estimate = self.posteri_estimate
        priori_error_estimate = self.posteri_error_estimate + self.process_variance

        blending_factor = priori_error_estimate / (priori_error_estimate + self.estimated_measurement_variance)
        self.posteri_estimate = priori_estimate + blending_factor * (measurement - priori_estimate)
        self.posteri_error_estimate = (1 - blending_factor) * priori_error_estimate

    def get_latest_estimated_measurement(self):
        return self.posteri_estimate

     
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
        global stopmeplease
        global command
        global commandlist
        global logreaderip
        global logreader
        global mainlooptime
        global maxroundtime
        global eventid
        global roundid
        global heatid
        global stopmeplease
        global command
        global soundtobeplayed
        global runthegame
        global readerpresent
        global audiopresent
        global rcpresent
        global ledpresent
        global lastlog
        global fieldtest
        global sendMsgToRc
        global killthedaemon
        global logreader
        global logreaderip
        global getasingleread
        global readstatus
        
        size = 1024
        exitthread = False
        while exitthread == False:
            try:
                rdata = client.recv(size)
                
                if rdata:
                    # Set the response to echo back the recieved data 
                    recmsg = rdata.decode("utf-8")
                    #print(recmsg)

                    if is_json(recmsg) == False:
                        print('ez nem json')
                        exitthread=True;
                    if is_json(recmsg) == True:
                        
                        data = json.loads(recmsg)
                        #print(data)
                        if (data['descriptor']) == 'command':
                                rcommand = data['command']
                                #print(rcommand)
                                device_id=data['deviceid']
                                 
                                    
                                    
                                if rcommand == "start":
                                    if runthegame == False:
                                         runthegame = True

                                         log("Fogadott socket adat(RiD:"+ str(roundid) +" EiD:"+ str(eventid)+" HiD:" + str(heatid))
                                         #exitthread=True; 
                                              
                                if rcommand == "stop":
                                    #runthegame = False
                                    stopmeplease = True
                                    log("Round is over!")            
                        exitthread=True;
                    else:
                       raise error('Client disconnected')
            except:
                client.close()
                return False

class websocketThread (threading.Thread):
   def __init__(self, threadID, name, timeout,loop):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
      self.loop = loop
   def run(self):
       WSSERVER(self.timeout,self.loop)
       print("Exiting " + self.name)

wsconnected = set()

def WSSERVER(timeout,loop):

    #global sendMsgToSound
     asyncio.set_event_loop(loop)
     
     def producer():
        global resultlist
        global WSCONTROL
        global sendMsgToControl 

        ret = ['x',False];
        if len(sendMsgToControl)>0:
            MsgToControl=sendMsgToControl.pop(0)
            if MsgToControl!="status":
                ret=[MsgToControl,True]
        return(ret)

     async def producer_handler(websocket, path):
         global WSCONTROL
         global wsconnected
         wskeepalive=timer()
         wsconnected.add(websocket)
         while True:
              message = producer()
              wslooptime=timer()

              if (wslooptime-wskeepalive)>10:
                try:
                    await websocket.send("KAL")
                    wskeepalive=timer()
                except:
                    log('WS Client Gone! [KAL] missed]')
                    break
              if message[1] == True:
                try:
                    await websocket.send(message[0])
                except:
                    log('WS Client Gone! ['+ message[0] +' missed]')
                    break
                    
                #WSCONTROL = False
              await asyncio.sleep(0.1)
          

     start_server = websockets.serve(producer_handler, getip(), 5678)
     loop.run_until_complete(start_server)
     loop.run_forever()


class collectorThread (threading.Thread):
    def __init__(self, threadID, name, timeout):
       threading.Thread.__init__(self)
       self.threadID = threadID
       self.name = name
       self.timeout = timeout
       self.loop = loop
    def run(self):
        COLLECTOR(self.timeout)
        print("Exiting " + self.name)

class ScanDelegate(DefaultDelegate):

    def handleDiscovery(self, dev, isNewDev, isNewData):
        global readcount
        #print(strftime("%Y-%m-%d %H:%M:%S", gmtime()), dev.addr, dev.getScanData(), dev.rssi)
        scandata=(dev.getValueText(9))
        monitor(dev.addr,dev.rssi,scandata)
        #print(scandata)
        #print(dev) 
        sys.stdout.flush()

def monitor(addr,rssi,scandata):

    global playermonitor
    global skiptime
    global pmdata 
    global trigger_value
    global drop_value
    global WSCONTROL
    global resultlist
    global laptime
    global forgettime
    global sendMsgToControl
    skipforget = False

    if scandata is not None:
        control = scandata
    else:
        control = "XXXX"
        
    if control[0:4] == "KTS0" :
        if addr not in playermonitor and len(playermonitor)<6:
            playermonitor.append(addr)
            skipforget = True #most látjuk a gépet először
        if addr in playermonitor:
            ddistribute = playermonitor.index(addr)
          
            if (timer()-pmdata[ddistribute][1][3]>forgettime) and not skipforget: # a távolodó gép adatait töröljük az előző körből
                pmdata[ddistribute][1][0] = []
                pmdata[ddistribute][1][1] = []
                log("GARBAGE OUT CLEAN SLATE IN")
            if (abs(rssi))<drop_value:   
                 pmdata[ddistribute][1][0].append(abs(rssi))
                 pmdata[ddistribute][1][1].append(timer())
                 pmdata[ddistribute][1][3]=timer() # itt láttuk utoljára 

                 message=str(rssi) +" "+ str(addr) +" "+ str(timer())
                 #log(message)
                 t = time.strftime("%Y %m %d %H:%M:%S")
                 message = ('['+t+'] : ' + message)
                 #sendMsgToControl.append(message)

def COLLECTOR(timeout):
    global runthegame
    global pmdata
    global playermonitor
    global stopmeplease
    scanner = Scanner().withDelegate(ScanDelegate())

    while True:
        if runthegame: # 0: rawrssi 1:timestamp 2:lastresult 3: ? 4: item counter 5: KalmanRssi 6:KalmanTime
            pmdata=[[0,[[],[],0,0,0,[],[]]],
                    [1,[[],[],0,0,0,[],[]]],
                    [2,[[],[],0,0,0,[],[]]],
                    [3,[[],[],0,0,0,[],[]]],
                    [4,[[],[],0,0,0,[],[]]],

                   ]
            playermonitor = []
            scanner.clear()
            scanner.start(passive = True)

            while runthegame:
                most = timer() 
                scanner.process(0.1)
                
                if stopmeplease == True:
                    runthegame = False
                    scanner.stop()
        time.sleep(0.01)           
                    

class evaluateThread (threading.Thread):
    def __init__(self, threadID, name, timeout):
       threading.Thread.__init__(self)
       self.threadID = threadID
       self.name = name
       self.timeout = timeout
       self.loop = loop
    def run(self):
        EVALUATE(self.timeout)
        print("Exiting " + self.name)

def EVALUATE(timeout):
    global runthegame
    global pmdata
    global trigger_value
    global trigger_floor
    while True:
        loopstart=timer()
        websocket_updater=timer()
        while runthegame:
            checkup = pmdata
            most=timer()
            data3 = 0
            data4 = 0
            for i in range (0,4):
                if len(pmdata[i][1][1])>2:
                    #if (most-checkup[i][1][1][-1])>0.1:
                   #log('checkup' + str(most-checkup[i][1][1][-1]))

                   iteration_count=len(checkup[i][1][0])      
                   
                   measurement_standard_deviation = np.std(checkup[i][1][0])
                   posteri_estimate = np.average(checkup[i][1][0])
                   
                   #print(posteri_estimate)  
                   #print(measurement_standard_deviation)
                   #print(posteri_estimate)
                   # The smaller this number, the fewer fluctuations, but can also venture off
                   # course...
                   #process_variance = 1e-3
                   process_variance = 1
                   estimated_measurement_variance = measurement_standard_deviation ** 2  # 0.05 ** 2
                   kalman_filter = KalmanFilter(process_variance, estimated_measurement_variance, posteri_estimate)
                   posteri_estimate_graph = []

                   for iteration in range(0, iteration_count):
                       kalman_filter.input_latest_noisy_measurement(checkup[i][1][0][iteration])
                       #posteri_estimate_graph.append(kalman_filter.get_latest_estimated_measurement())
                       pmdata[i][1][5].append(kalman_filter.get_latest_estimated_measurement())
                       pmdata[i][1][6].append(timer())
                       if (most-checkup[i][1][6][0]>0.3):
                           pmdata[i][1][5].pop(0)
                           pmdata[i][1][6].pop(0)
                       #print(pmdata[i][1][5][-1])
                       #print(len(pmdata[i][1][5]))
                   #print(checkup[i][1][0][k] )

                   if len(checkup[i][1][6])>4:
                        trigger_estimate = np.average(pmdata[i][1][5]) 
                        if (trigger_estimate<trigger_value) and (len(checkup[i][1][6])>0):
                            min_rssi=checkup[i][1][5][-1]
                            for cic in range (1,len(checkup[i][1][5])):
                                if checkup[i][1][5][-cic]<min_rssi:
                                    min_rssi=checkup[i][1][5][-cic]
                            if min_rssi==checkup[i][1][5][-1]:
                                log("Failed: uccsó a kicsike")
                            if min_rssi==checkup[i][1][5][-2]:
                                log("Failed: uccsóelőtti a kicsike")
                            if checkup[i][1][5].index(min_rssi)==0:
                                log("Failed: első a kicsike")
                            if min_rssi>trigger_floor:
                                log("Failed: nem érte el a floort")
                                
                            if min_rssi!=checkup[i][1][5][-1] and min_rssi!=checkup[i][1][5][-2] and checkup[i][1][5].index(min_rssi)!=0 and min_rssi<trigger_floor:
                                #print(len(checkup[i][1][1]))
                                   
                                min_timestamp=checkup[i][1][6][checkup[i][1][5].index(min_rssi)]
                                #print(min_timestamp)
                                lowest_key=checkup[i][1][5].index(min_rssi)
                                #print(lowest_key)
                                result = parab(pmdata[i][1][6][(lowest_key-2)],pmdata[i][1][6][(lowest_key)],pmdata[i][1][6][(lowest_key+2)],pmdata[i][1][5][lowest_key-2],pmdata[i][1][5][lowest_key],pmdata[i][1][5][lowest_key+2])      

                                if checkup[i][1][2]  != 0:
                                    
                                     #print(pmdata[i][1][5])
                                     #print(pmdata[i][1][1])
                                     print("TRIGGERED: ["+str(i)+"]" + str(result-pmdata[i][1][2]))   
                                     if i == 0:   
                                          data3 = result-pmdata[i][1][2]
                                     if i == 1:
                                          data4 = result-pmdata[i][1][2]
                                     pmdata[i][1][2] = result
                                     data1=pmdata[i][1][5][-1]
                                     data2=pmdata[i][1][0][-1]   
                                     message ={}
                                     message['data1']=round(data1)
                                     message['data2']=data2
                                     message['data3']=data3
                                     message['data4']=data4
                                     message = json.dumps(message)
                                     sendMsgToControl.append(message)    
                                     pmdata[i][1][0] = []
                                     pmdata[i][1][1] = []
                                     pmdata[i][1][5] = []
                                     pmdata[i][1][6] = []
                                     
                                if checkup[i][1][2]  == 0:
                                     oresult = 0
                                     pmdata[i][1][2] = most
                                     print("TRIGGERED ZERO: " + str(oresult))
                                     pmdata[i][1][0] = []
                                     pmdata[i][1][1] = []
                                     pmdata[i][1][5] = []
                                     pmdata[i][1][6] = []
                                     data3 = 'Start'
                           
                                
                   if most-websocket_updater>0.2: 
                       try:  
                            data1=pmdata[i][1][5][-1]
                            data2=pmdata[i][1][0][-1]   
                            message ={}
                            message['data1']=round(data1)
                            message['data2']=data2
                            message['data3']=data3
                            message['data4']=data4  
                            message = json.dumps(message)
                            sendMsgToControl.append(message) 
                            websocket_updater = timer()
                       except:
                            pass
                         
                   for i in range (0,4):
                        if len(checkup[i][1][1])>0:
                           if (most-pmdata[i][1][1][0]>2):
                                   
                                   pmdata[i][1][0].pop(0)
                                   pmdata[i][1][1].pop(0)
                                   
                   pmdata[i][1][4]=len(checkup[i][1][0])
            time.sleep(0.01)
        time.sleep(0.1)

#Original
##def EVALUATE(timeout):
##    global runthegame
##    global pmdata
##    while True:
##        
##        while runthegame:
##            checkup=pmdata
##            most=timer()    
##            for i in range (0,4):
##                if len(checkup[i][1][1])>0:
##                    if (most-checkup[i][1][1][-1])>0.6:
##                        log('checkup' + str(most-checkup[i][1][1][-1]))
##
##                        iteration_count=len(checkup[i][1][0])      
##                        
##                        measurement_standard_deviation = np.std(checkup[i][1][0])
##                        posteri_estimate = np.average(checkup[i][1][0]) 
##                        print(posteri_estimate)  
##                        print(measurement_standard_deviation) 
##                        # The smaller this number, the fewer fluctuations, but can also venture off
##                        # course...
##                        process_variance = 1
##                        estimated_measurement_variance = measurement_standard_deviation ** 2  # 0.05 ** 2
##                        kalman_filter = KalmanFilter(process_variance, estimated_measurement_variance, posteri_estimate)
##                        posteri_estimate_graph = []
##
##                        for iteration in range(0, iteration_count-1):
##                            kalman_filter.input_latest_noisy_measurement(checkup[i][1][0][iteration])
##                            posteri_estimate_graph.append(kalman_filter.get_latest_estimated_measurement())
##
##                        #print(checkup[i][1][0][k] )
##                        print(posteri_estimate_graph)
##                        #print(states_pred)
##                        message = str(pmdata[i][1][1])
##                        t = time.strftime("%Y %m %d %H:%M:%S")
##                        message = ('['+t+'] : ' + message)
##                        sendMsgToControl.append(message)    
##                        pmdata[i][1][0] = []
##                        pmdata[i][1][1] = []
##                        log("DATA OUT CLEAN SLATE IN")
##            time.sleep(0.01)
##        time.sleep(0.01)
##                
thread1 = myThread(1, "socketserver", 0)
thread1.daemon = True
thread1.start()

thread10 = collectorThread(10, "collector", 0)
thread10.daemon = True
thread10.start()

thread10 = evaluateThread(11, "evalaute", 0)
thread10.daemon = True
thread10.start()

thread4 = websocketThread(4, "websocket", 0, loop)
thread4.daemon = True
thread4.start()




#            if len(pmdata[ddistribute][1][0])>2:
#                if pmdata[ddistribute][1][0][-3]<trigger_value and pmdata[ddistribute][1][0][-2]<trigger_floor and pmdata[ddistribute][1][0][-1]<trigger_value:
#                    min_rssi=pmdata[ddistribute][1][0][-1]
#                    for i in range (1,3):
#                        if pmdata[ddistribute][1][0][-i]<min_rssi:
#                            min_rssi=pmdata[ddistribute][1][0][-i]
#
#                    if min_rssi!=pmdata[ddistribute][1][0][-1] and pmdata[ddistribute][1][0].index(min_rssi)!=0 and min_rssi<trigger_floor:        
#                        min_timestamp=pmdata[ddistribute][1][1][pmdata[ddistribute][1][0].index(min_rssi)]
#                        #print(min_timestamp)
#                        lowest_key=pmdata[ddistribute][1][0].index(min_rssi)
#                        #print(lowest_key)
#                        result = parab(pmdata[ddistribute][1][1][(lowest_key-1)],pmdata[ddistribute][1][1][(lowest_key)],pmdata[ddistribute][1][1][(lowest_key+1)],pmdata[ddistribute][1][0][lowest_key-1],pmdata[ddistribute][1][0][lowest_key],pmdata[ddistribute][1][0][lowest_key+1])
#
#                        if pmdata[ddistribute][1][2] == 0: #első nekifutás
#                           pmdata[ddistribute][1][2] = result
#                           log("KORSTART 1: " + str(pmdata[ddistribute][1][2]))
#                           triggerdata=[addr,(result-pmdata[ddistribute][1][2])] 
#                           timing(triggerdata)
#                           pmdata[ddistribute][1][0] = []
#                           pmdata[ddistribute][1][1] = []
                           
#                        if ((pmdata[ddistribute][1][2]!=result) and (result-pmdata[ddistribute][1][2]>skiptime)): #összes többi
#                           log("SKIP CHECK: " + str(timer()-pmdata[ddistribute][1][2]))
#                           log("KORSTART X: " + str(pmdata[ddistribute][1][2]))
#                           triggerdata=[addr,(result-pmdata[ddistribute][1][2])] 
#                           timing(triggerdata)
#                           pmdata[ddistribute][1][0] = []
#                           pmdata[ddistribute][1][1] = []
#                           pmdata[ddistribute][1][2] = result 
                        
                        
                        
                        #print(pmdata[ddistribute][1][2])       
                        
                       
                        
                        #sendMsgToMain.append('BLE_READER_001|timing|startgate|'+control+'|'+result+'|')







log('running')
while True:
    
    #print(pmdata)
    time.sleep(0.1) 
