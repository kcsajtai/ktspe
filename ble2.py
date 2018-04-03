#!/usr/bin/python
from __future__ import print_function
import time, datetime
from timeit import default_timer as timer
import bluepy.btle as btle
import threading
import sys
import socket
import websockets
import json
import asyncio
import random

from time import gmtime, strftime, sleep
from bluepy.btle import Scanner, DefaultDelegate, BTLEException, Peripheral
import sys
import json

loop = asyncio.new_event_loop()
WSCONTROL = False

resultlist = {}


resultlist['player0']=[]
resultlist['player1']=[]
resultlist['player2']=[]
resultlist['player3']=[]
ret=['',False]


player0_rssi=[]
player0_timestamp=[]
player0_starttime=0

player1_rssi=[]
player1_timestamp=[]
player1_starttime=0

player2_rssi=[]
player2_timestamp=[]
player2_starttime=0

player3_rssi=[]
player3_timestamp=[]
player3_starttime=0

player4_rssi=[]
player4_timestamp=[]
player4_starttime=0

trigger_value=65
trigger_floor=55
laptime = 0
skiptime = 3

sendMsgToLog=[]
sendMsgToMain = []
sendMsgToLed=[]
sendMsgToSound=[]
sendMsgToRc=[]
sendMsgToLog=[]
commandlist=['start','stop','logrequest']
command = []
ledconfigsent = False
killthedaemon = False
monitor_interval=1
#todo='idle'
todo='idle'
logreaderip=''
logreaderip = ''
getasingleread = False
readstatus = []
scanner_running = False
logreader=False
runthegame = False
runthegame = False
readerpresent = False
audiopresent = False
ledpresent = False
rcpresent = False

def is_json(myjson):
  try:
    json_object = json.loads(myjson)
  except ValueError:
    return False
  return True

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

def getconfig(eventid):
    db = pymysql.connect(host="localhost",    # your host, usually localhost
                         user="ktspe",         # your username
                         passwd="macilaci88",  # your password
                         db="ktspe")        # name of the data base

    # you must create a Cursor object. It will let
    #  you execute all the queries you need
    cur = db.cursor()

    # Use all the SQL you like
    
    sql = "SELECT * from event where eventid=%s"
    cur.execute(sql,(eventid))
    
    # print all the first cell of all the rows
   
    ret = cur.fetchone()
    
    db.close()
    if ret is not None: 
        return ret

def sendconfig (target):
     db = pymysql.connect(host="localhost",    
                         user="ktspe",         
                         passwd="macilaci88",  
                         db="ktspe")        

     cur = db.cursor()
     sql = "select * from event where active = '1'"
     cur.execute(sql)
     baseline = cur.fetchone()
     
     config={'descriptor':'config'}
     config['eventname'] = baseline[0].upper()
     config['bestpilot'] = getobestconfig(baseline[1])
     message = json.dumps(config)
     sendMsgToLed.append((message))
     db.close()



def timecheck(value,minlaptime,maxlaptime,skiptime,locktime):
    #retdef [behav code, message, next lap start, next round start]

    if ((((value < minlaptime) and (value > locktime)) or (value < skiptime))):
        ret = [0,"RESULT BELOW MINLAP",False,False];
    if ((value > minlaptime) and (value > locktime)):
        ret = [value,"SEEMS OK",True,False];
    if ((value > skiptime) and (value < locktime)):
        ret = [value,"Correction:",False,True];
    if (value > maxlaptime):
        ret = [1,"RESULT OVER MAXLAP",False,False];

    return ret

def clockmebitch(result,pilotid,eventid,roundid,heatid):
    db = pymysql.connect(host="localhost",    # your host, usually localhost
                         user="ktspe",         # your username
                         passwd="macilaci88",  # your password
                         db="ktspe")        # name of the data base

    # you must create a Cursor object. It will let
    #  you execute all the queries you need
    cur = db.cursor()

    # Use all the SQL you like
    
    sql = "INSERT INTO results set pilotid=%s, result=%s, eventid=%s, roundid=%s, heatid=%s"
    cur.execute(sql, (pilotid, result, eventid, roundid,heatid))
    db.commit();
    # print all the first cell of all the rows
   

    db.close()
    sendMsgToSound.append("pass_snd")
    pilotname=getpilotname(pilotid)
    pilotname=pilotname.upper()
    resulttoled = str(result)
    resulttoled = resulttoled[0:7]
    print('display|'+resulttoled+'|'+pilotname+'|')
    sendMsgToLed.append('display|'+resulttoled+'|'+pilotname+'|')
    sendMsgToRc.append('display|'+resulttoled+'|'+pilotname+'|')

def correctmebitch(result,pilotid,eventid,roundid,heatid):
    db = pymysql.connect(host="localhost",    # your host, usually localhost
                         user="ktspe",         # your username
                         passwd="macilaci88",  # your password
                         db="ktspe")        # name of the data base

    cur = db.cursor()
    # you must create a Cursor object. It will let
    #  you execute all the queries you need
    sql = "SELECT * from results where pilotid=%s and eventid=%s and heatid=%s and roundid=%s order by resultid DESC limit 1"
    cur.execute(sql,(pilotid,eventid,heatid,roundid))
    
    # print all the first cell of all the rows
   
    ret = cur.fetchone()

    resultid=ret[0]
    prevresult=float(ret[1])
    log("Korrekcio: elozo eredmeny: "+ str(prevresult))
    #print(result)
    result=prevresult+result;
    #print(result)
   
    if prevresult != 0:
        # Use all the SQL you like
        
        sql = "update results set result=%s where resultid=%s"
        cur.execute(sql, (result, resultid))
        db.commit();
        # print all the first cell of all the rows
        sql = "insert into corrections set result=%s, resultid=%s"
        cur.execute(sql, (prevresult, resultid))
        db.commit();

        db.close()
        sendMsgToSound.append("pass_snd")
        
        pilotname=getpilotname(pilotid)
        pilotname=pilotname.upper()
        resulttoled = str(result)
        resulttoled = resulttoled[0:7]
        #print('correct|'+resulttoled+'|'+pilotname+'|')
        sendMsgToLed.append('correct|'+resulttoled+'|'+pilotname+'|')
        sendMsgToRc.append('correct|'+resulttoled+'|'+pilotname+'|')
def startmebitch(result,pilotid,eventid,roundid,heatid):
    result = 0
    db = pymysql.connect(host="localhost",    # your host, usually localhost
                         user="ktspe",         # your username
                         passwd="macilaci88",  # your password
                         db="ktspe")        # name of the data base

    # you must create a Cursor object. It will let
    #  you execute all the queries you need
    cur = db.cursor()

    # Use all the SQL you like
    
    sql = "INSERT INTO results set pilotid=%s, result=%s, eventid=%s, roundid=%s, heatid=%s"
    cur.execute(sql, (pilotid, result, eventid, roundid, heatid))
    db.commit();
    # print all the first cell of all the rows
   

    db.close()
    sendMsgToSound.append("pass_snd")
    pilotname=getpilotname(pilotid)
    pilotname=pilotname.upper()
    sendMsgToLed.append('display| |'+pilotname+'|')
    sendMsgToRc.append('display| |'+pilotname+'|') 
def getpilotname(pilotid):
    db = pymysql.connect(host="localhost",    
                         user="ktspe",         
                         passwd="macilaci88",  
                         db="ktspe")        

    cur = db.cursor()

  
    
    sql = "select * from pilots where pilotid=%s"
    cur.execute(sql, (pilotid))
    
    # print all the first cell of all the rows
   
    ret = cur.fetchone()
    db.close()

    
    
    if ret is not None:
         log("Func getpilotname:" +str(ret))
         return ret[0]
    
def getpilotdata(transponderid):
    db = pymysql.connect(host="localhost",    
                         user="ktspe",         
                         passwd="macilaci88",  
                         db="ktspe")        

    cur = db.cursor()

  
    
    sql = "select * from pilots where transponderid=%s"
    cur.execute(sql, (transponderid))
    
    # print all the first cell of all the rows
   
    ret = cur.fetchone()
    

    if ret is None:

         sql = "insert into pilots set transponderid=%s, nick=%s"
         cur.execute(sql, (transponderid,transponderid))     
         db.commit() 

         sql = "select * from pilots where transponderid=%s"
         cur.execute(sql, (transponderid)) 

         ret = cur.fetchone()
         
    db.close()     

    if ret is not None:
         log("Func getpilotdata:" +str(ret))
         return ret[1]

def checkduplicate(transponderid):
    db = pymysql.connect(host="localhost",    
                         user="ktspe",         
                         passwd="macilaci88",  
                         db="ktspe")        

    cur = db.cursor()

  
    
    sql = "select * from pilots where transponderid=%s"
    cur.execute(sql, (transponderid))
    
    # print all the first cell of all the rows
   
    ret = cur.fetchone()
    db.close()
    #print(ret) 
    duplicate = []
    
    if ret is not None:
         duplicate.append(1) 
         duplicate.append(ret[0])
    if ret is None:
         duplicate.append(0) 
    #print(duplicate) 
    log("Func checkduplicate:" +str(duplicate))
    return duplicate
     
def getbest(pilotid,eventid):
    db = pymysql.connect(host="localhost",    
                         user="ktspe",         
                         passwd="macilaci88",  
                         db="ktspe")        

    cur = db.cursor()

  
    
    sql = "select result from results where pilotid=%s and eventid=%s and result!='0' and invalid!='1' order by result ASC limit 1"
    cur.execute(sql, (pilotid,eventid))
    
    # print all the first cell of all the rows
   
    ret = cur.fetchone()
    db.close()

    
   
    if ret is not None:
         log("Func getbest:" +str(ret))
         return ret[0]

def getobestconfig(eventid):
    db = pymysql.connect(host="localhost",    
                         user="ktspe",         
                         passwd="macilaci88",  
                         db="ktspe")        

    cur = db.cursor()

  
    
    sql = "select * from results where  eventid=%s and result!='0' and invalid!='1' order by result ASC limit 1"
    cur.execute(sql, (eventid))
    
    # print all the first cell of all the rows
   
    ret = cur.fetchone()
    db.close()
    if ret is not None:
         result = ret[1]
         pilotid = ret[2]
         pilotname = getpilotname(pilotid)
         ret = [pilotname,result]  
         log("Func getobestforconfig:" + str(ret))
         return ret
    else:
         log("Func getobestforconfig: NO DATA YET")
         ret = 0
         return ret
def getobest(eventid):
    db = pymysql.connect(host="localhost",    
                         user="ktspe",         
                         passwd="macilaci88",  
                         db="ktspe")        

    cur = db.cursor()

  
    
    sql = "select result from results where  eventid=%s and result!='0' and invalid!='1' order by result ASC limit 1"
    cur.execute(sql, (eventid))
    
    # print all the first cell of all the rows
   
    ret = cur.fetchone()
    db.close()

    
    
    if ret is not None:
         log("Func getobest:" + str(ret))
         return ret[0]
def getlockstatus():
    db = pymysql.connect(host="localhost",    
                         user="ktspe",         
                         passwd="macilaci88",  
                         db="ktspe")        

    cur = db.cursor()
    sql = "select device_id from lck"
    cur.execute(sql)
    ret = cur.fetchone()
    db.close()   
    if ret is not None:
         log("Func getlockstatus:" + str(ret))
         return ret[0]
     
def setlockstatus(device_id):
    db = pymysql.connect(host="localhost",    
                         user="ktspe",         
                         passwd="macilaci88",  
                         db="ktspe")        

    cur = db.cursor()
    sql = "update lck set device_id=%s"
    cur.execute(sql, (device_id))
    db.commit()
    db.close()   
    log("Func setlockstatus:" + str(device_id))
         

def rounddetails():
     global sendMsgToRc
     db = pymysql.connect(host="localhost",user="ktspe",passwd="macilaci88",db="ktspe")        
     cur = db.cursor()

     sql = "SELECT * from event where active=1"
     cur.execute(sql)
     res = cur.fetchone()
     eventid = res[1]
     
     sql = "SELECT id from round where active=1 and eventid=%s"
     cur.execute(sql,eventid)
     res = cur.fetchone()
     roundid = res[0]
     
     sql = "SELECT pilotid from results where roundid=%s"
     cur.execute(sql,roundid)
     res = cur.fetchall()
     res=list(set(res))
     #print(res)
     ret = {'descriptor':'rounddetails'} 
     
     for n in range(len(res)):
         sql = "SELECT * from results where pilotid = %s and roundid=%s"
         nor = cur.execute(sql,(res[n],roundid))

         ret[getpilotname(res[n])] = nor 
     
    

     message = json.dumps(ret) 
     sendMsgToRc.append(str(message))
     
 
def eventcontrol(command):
     db = pymysql.connect(host="localhost",user="ktspe", passwd="macilaci88",db="ktspe")        
     cur = db.cursor()

     sql = "SELECT * from event where active=1"
     #cur.execute(sql,(eventid))
     nr_ae = cur.execute(sql)
     if nr_ae>0:
          res = cur.fetchone()
          active_event = res[1]
          number_of_heats = res[3]
          number_of_rounds = res[8]
          #print('Aktív esemény: ', active_event)
          #print('Futamok száma: ', number_of_heats)
          #print('Csoportok száma: ', number_of_rounds)

          ## mennyi Futam lett megkezdve
          sql="select * from heat where eventid=%s order by heatid DESC"
          noh_already = cur.execute(sql,active_event)
          #print('Eddigi futamok száma: ', noh_already)


          ##melyik az aktuális aktív Futam
          sql="select * from heat where eventid=%s and active='1'"
          cur.execute(sql,active_event)
          res = cur.fetchone()
          current_heatid = res[0] ##aktív futam

          ## mennyi Csoport lett megkezdve a futamban
          sql="select * from round where eventid=%s and heatid=%s order by id DESC"
          nor_already = cur.execute(sql,(active_event,current_heatid))
          #print('Eddigi csoportok száma a futamban: ', nor_already)

          sql="select * from round where eventid=%s and active='1'"
          cur.execute(sql,(active_event))
          res = cur.fetchone()
          current_roundid = res[0] ## aktív csoport
         
          #sql="select * from rounds where eventid=%s and heatid=%s"
          #cur.execute(sql,active_event,heatid)
          message = "OK"
          
          if command=='nextround':
               sql="select * from round where  eventid=%s and id>%s order by id ASC"
               cnor = cur.execute(sql,(active_event,current_roundid))
               #print(cnor)
               if cnor == 0:
                    
                    if nor_already<number_of_rounds: # ha nem  érte el a csoportszám a futamszámot
                         #print('megyek')
                         sql="update round set active='0' where eventid=%s" # töröljük az aktív csoport kijelölést
                         cur.execute(sql,(active_event))
                         db.commit();
                         sql="insert into round set eventid=%s, heatid=%s, active='1'"
                         cur.execute(sql,(active_event,current_heatid))
                         db.commit();
                         message = "OK"
                    if nor_already==number_of_rounds: # ha elérte a csoportszám a futamszámot
                         if noh_already<number_of_heats:
                              sql="update heat set active='0' where eventid=%s" # aktív futam kijelölés kiveszzük
                              db.commit();
                              cur.execute(sql,(active_event))                 
                              sql="insert into heat set eventid=%s, active='1'" # bedobunk egy új aktív futamot
                              cur.execute(sql,(active_event))
                              db.commit();
                              sql="select * from heat where eventid=%s order by heatid desc" # elkérjük az azonosítóját
                              cur.execute(sql,(active_event))
                              res = cur.fetchone()
                              current_heatid = res[0]
                              sql="update round set active='0' where eventid=%s" # töröljük az aktív csoport kijelölést
                              cur.execute(sql,(active_event))
                              db.commit();
                              sql="insert into round set eventid=%s, heatid=%s, active='1'" # beteszünk egy aktív csoportot 
                              cur.execute(sql,(active_event,current_heatid))
                              db.commit();
                              message = "OK"
                         else:
                              message = "EOF"
                         
               if cnor != 0:
                    sql="select * from round where eventid=%s and id>%s order by id ASC limit 1"
                    cur.execute(sql,(active_event,current_roundid))
                    res = cur.fetchone()
                    current_roundid = res[0]
                    sql="update round set active='0' where eventid=%s" # töröljük az aktív csoport kijelölést
                    cur.execute(sql,(active_event))
                    db.commit();
                    sql="update round set active='1' where id=%s" # beteszünk egy aktív csoportot 
                    cur.execute(sql,(current_roundid))
                    db.commit();
                    message = "OK"

          if command=='prevround':
               sql="select * from round where eventid=%s and id<%s order by id DESC"
               nr_to_start = cur.execute(sql,(active_event,current_roundid))
               res = cur.fetchone()
               current_roundid = res[0]
               if nr_to_start>0:
                    sql="update round set active='0' where eventid=%s" # töröljük az aktív csoport kijelölést
                    cur.execute(sql,(active_event))
                    db.commit();
                    sql="update round set active='1' where id=%s" # beteszünk egy aktív csoportot 
                    cur.execute(sql,(current_roundid))
                    db.commit();
                    message = "OK"
               else:
                    message = "EOS"
               
          ## ennek kell lennie a function végének, minden manipuláció előtte

          
          
          sql="select * from round where eventid=%s and active='1'"
          cur.execute(sql,(active_event))
          res = cur.fetchone()

          current_roundid = res[0] ## aktív csoport
          current_heatid = res[3] ##aktív futam

          sql="select * from round where eventid=%s and heatid=%s and id<=%s"
          nor = cur.execute(sql,(active_event,current_heatid,current_roundid))

          sql="select * from heat where eventid=%s and heatid<=%s"
          noh = cur.execute(sql,(active_event,current_heatid))
          #print('Aktív futam: ', current_heatid)     
          #print('Aktív csoport: ', current_roundid)
          db.close();
          ret=[current_roundid,active_event,current_heatid,noh,nor,message]
     else:
          message="NAE"
          ret=['','','','','',message]
     sendMsgToRc.append(str(ret))
     rounddetails()
     #print(ret)
     return ret
     
########################## KOMMUNIKÁCIÓ ELEJE
def MsgToLed(message):
     global ledpresent

     log("Transport To LED: " + message)
     ss=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
     
     host= '172.24.1.2'
     port=int(2000)
     try:
         ss.connect((host,port))
         ss.sendall(message.encode())
         ss.close()
         ledpresent = True;
     except socket.error:
         ledpresent = False;
         log('Nincs LED controller / Nem válaszol')

def MsgToSound(message):

     global audiopresent
     log("Transport To AUDIO: " + message)
     if message != "status":
          message="play|" + message
     
          
     ss=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
     host= '172.24.1.3'
     port=int(2000)
     try:
         ss.connect((host,port))
         ss.sendall(message.encode())
         ss.close()
         audiopresent = True;
     except socket.error:
         audiopresent = False;
         log('Nincs Audio controller / Nem válaszol')
#sendMsgToSound('start_snd')

def MsgToRc(message):
     global rcpresent
     message=message
     log("Transport To Rc: " + message)
     global rcpresent
     ss=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
     host= '172.24.1.4'
     port=int(2000)
     try:
         ss.connect((host,port))
         ss.sendall(message.encode())
         ss.close()
         rcpresent = True;
     except socket.error:
         rcpresent = False;
         log('Nincs Remote controller / Nem válaszol')
         
def MsgToLog(message):

     global logreader
     global logreaderip
        
     #print ("fuck you")
       
     ss=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
     host = logreaderip
     #print(host)
     port=int(2000)
     try:
          ss.connect((host,port))
          ss.sendall(message.encode())
          ss.close()
          logreader = True
     except socket.error:
          logreader = False
          log('Nincs LOG reader / Nem válaszol')

def MsgToMain(message):
     waitforresponse = False
     #message="play|" + message
     ss=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
     #ss.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
     host= '172.24.1.1'
     port=int(2000)
     try:
         ss.connect((host,port))
         ss.sendall(message.encode())
         ss.close()
         #time.sleep(1)
         #command.append('menu')
     except socket.error:
         pass   
         #command.append('comerror')
         
 
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
        size = 1024
        exitthread = False
        while exitthread == False:
            try:
                rdata = client.recv(size)
                
                if rdata:
                    # Set the response to echo back the recieved data 
                    recmsg = rdata.decode("utf-8")


                    if is_json(recmsg) == False:
                        print('ez nem json')
                        exitthread=True;
                    if is_json(recmsg) == True:
                        
                        data = json.loads(recmsg)
                        
                        if (data['descriptor']) == 'command':
                                rcommand = data['command']
                                if rcommand in commandlist:    
                                    command.append(rcommand)
                                if rcommand=='logrequest':
                                    logreaderip=data['ip']
                                    
                        exitthread=True;
                    else:
                       raise error('Client disconnected')
            except:
                client.close()
                return False


class transportmainThread (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
       transportmain(self.timeout)
       print("Exiting " + self.name)

def transportmain(timeout):
     global sendMsgToMain
     while True:
          time.sleep(0.01)
          while len(sendMsgToMain)>0:
                    message = sendMsgToMain[0]
                    MsgToMain(message)
                    sendMsgToMain.pop(0)
          
class transportlogThread (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
       transportlog(self.timeout)
       print("Exiting " + self.name)

def transportlog(timeout):
     global sendMsgToLog
     
     while True:
          time.sleep(0.01)
          #print(len(sendMsgToLog))
          while len(sendMsgToLog)>0:
                    #print('itt még jó')
                    message = sendMsgToLog[0]
                    MsgToLog(message)
                    sendMsgToLog.pop(0)

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

def WSSERVER(timeout,loop):
     global resultlist
     global todo
     global broadcastresult
     global WSCONTROL
     asyncio.set_event_loop(loop)
     
     def producer():
        global resultlist
        global WSCONTROL
         
        print(WSCONTROL)
        if WSCONTROL== True:
          #resultlist['player0'].append(random.random()*15)
           print('kéne küldeni')
           ret = [json.dumps(resultlist),True]
        else:
           ret = [json.dumps(resultlist),False]

        return(ret)

     async def producer_handler(websocket, path):
         global WSCONTROL
         while True:
              message = producer()
              if message[1] == True:
                await websocket.send(message[0])
                WSCONTROL = False
              await asyncio.sleep(0.1)
          

     start_server = websockets.serve(producer_handler, '172.24.1.10', 5678)
     loop.run_until_complete(start_server)
     loop.run_forever()
     
             

thread1 = myThread(1, "socketserver", 0)
thread1.daemon = True
thread1.start()

thread2 = transportmainThread(2, "transportmain", 0)
thread2.daemon = True
thread2.start()

thread3 = transportlogThread(3, "transportlog", 0)
thread3.daemon = True
thread3.start()

thread4 = websocketThread(3, "websocket", 0, loop)
thread4.daemon = True
thread4.start()
 


################ Kommunikáció vége
def monitor(addr,rssi,scandata):
       
    global trigger_value
    global player0_rssi
    global player0_timestamp
    global player0_starttime

    global player1_rssi
    global player1_timestamp
    global player1_starttime

    global player2_rssi
    global player2_timestamp
    global player2_starttime

    global player3_rssi
    global player3_timestamp
    global player3_starttime

    global player4_rssi
    global player4_timestamp
    global player4_starttime

    global WSCONTROL
    global resultlist
    global laptime
    #control='d9:0d:b2:30:3a:7e'
    #if addr==control:
    if scandata is not None:
        control = scandata
    else:
        control = "XXXX"
        
    if control[0:4] == "KTS0" :
        player0_rssi.append(abs(rssi))
        player0_timestamp.append(timer())
        log(str(rssi) +" "+ str(addr) +" "+ str(timer()))
        if len(player0_rssi)>2:
            if player0_rssi[-3]<trigger_value and player0_rssi[-2]<trigger_value and player0_rssi[-2]<trigger_value:
        #if len(player0_rssi)>3:
            #if player0_rssi[-4]<trigger_value and player0_rssi[-3]<trigger_value and player0_rssi[-2]<trigger_value and player0_rssi[-2]<trigger_value:
                min_rssi=player0_rssi[-1]
                for i in range (1,4):
                    if player0_rssi[-i]<min_rssi:
                        min_rssi=player0_rssi[-i]

                if min_rssi!=player0_rssi[-1] and player0_rssi.index(min_rssi)!=0 and min_rssi<trigger_floor:        
                    min_timestamp=player0_timestamp[player0_rssi.index(min_rssi)]
                    lowest_key=player0_rssi.index(min_rssi)
                    rssi_diff_a = player0_rssi[lowest_key-1]-player0_rssi[lowest_key]
                    rssi_diff_b = player0_rssi[lowest_key+1]-player0_rssi[lowest_key]

                    if rssi_diff_a == 0:
                        rssi_diff_a = 1
                        
                    if rssi_diff_b == 0:
                        rssi_diff_b = 1
                    
                    
                    timestamp_diff_a = player0_timestamp[lowest_key]-player0_timestamp[lowest_key-1]
                    timestamp_diff_b = player0_timestamp[lowest_key+1]-player0_timestamp[lowest_key]
                    
                        
                    result = player0_timestamp[lowest_key]-timestamp_diff_a/rssi_diff_a+timestamp_diff_b/rssi_diff_b
                    if result-player0_starttime>skiptime:
                      log("Triggered: "+ str(min_rssi)+" "+ str(min_timestamp)+" "+ str(result-player0_starttime))
                      resultlist['player0'].append((result-player0_starttime))
                      print(resultlist)
                      WSCONTROL= True
                    if player0_starttime != 0:
                        sendMsgToMain.append('BLE_READER_001|timing|startgate|'+addr+'|'+str(result-player0_starttime)+'|')
                        player0_starttime = timer()
                    
                    if player0_starttime == 0:
                        sendMsgToMain.append('BLE_READER_001|timing|startgate|'+addr+'|'+str(player0_starttime)+'|')
                        player0_starttime = timer()
                        
                    
                   
                    
                    #sendMsgToMain.append('BLE_READER_001|timing|startgate|'+control+'|'+result+'|')
                    
                    
                    player0_rssi=[]
                    player0_timestamp=[]
        
    
class ScanDelegate(DefaultDelegate):

    def handleDiscovery(self, dev, isNewDev, isNewData):
        #print(strftime("%Y-%m-%d %H:%M:%S", gmtime()), dev.addr, dev.getScanData(), dev.rssi)
        scandata=(dev.getValueText(9))
        monitor(dev.addr,dev.rssi,scandata)
        #print(scandata)
        #print(dev) 
        sys.stdout.flush()

scanner = Scanner().withDelegate(ScanDelegate())

# listen for ADV_IND packages for 10s, then exit
while True:
    time.sleep(0.001)
    #log('OK')
    if len(command)>0:
        todo = command.pop(-1)
        log(todo)
    if todo == 'logrequest':
        logreader = True;
        todo = 'idle'
    if todo == 'start':    
        scanner.start(passive=True)
        scanner_running = True;
        while todo =='start':        
            scanner.process()
            if len(command)>0:
                todo = command.pop(-1)
            #print(todo)
    if todo == 'stop' and scanner_running == True: 
        scanner.stop()
        scanner.clear()
        player0_starttime = 0
        scanner_running = False
        log('Timeout')
        todo='idle'
    if todo == 'idle':
      time.sleep(1)
    #print(todo)
#address ='C4:BE:84:25:2E:5A'

