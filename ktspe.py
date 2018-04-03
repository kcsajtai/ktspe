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

loop = asyncio.new_event_loop()
WSCONTROL = False


def getsystemconfig():
    db = pymysql.connect(host="localhost",    # your host, usually localhost
                         user="ktspe",         # your username
                         passwd="macilaci88",  # your password
                         db="ktspe")        # name of the data base

    # you must create a Cursor object. It will let
    #  you execute all the queries you need
    cur = db.cursor()

    # Use all the SQL you like
    
    sql = "SELECT * from conf where confid='1'"
    cur.execute(sql)
    
    # print all the first cell of all the rows
   
    ret = cur.fetchone()
    
    db.close()
    if ret is not None: 
        return ret

## DEFAULT AND STARTUP PARAMETERS
resultlist = {}


resultlist['player0']=[]
resultlist['player1']=[]
resultlist['player2']=[]
resultlist['player3']=[]
resultlist['player4']=[]
ret=['',False]

sysconfig=getsystemconfig()
trigger_value=sysconfig[0]
trigger_floor=sysconfig[1]


locktime = 8
skiptime = 1
forgettime = 3

sendMsgToLog=[]
sendMsgToMain = []
sendMsgToLed=[]
sendMsgToSound=[]
sendMsgToRc=[]
sendMsgToLog=[]
sendMsgToOledGui=[]
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
forcedrestart = False
ledconfigsent = False
logreader=False
runthegame = False
readerpresent = False
audiopresent = False
ledpresent = False
rcpresent = False


### BASIC FUNCS

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

def getip ():
    cmd = "hostname -I | cut -d\' \' -f1"
    IP = subprocess.check_output(cmd, shell = True )
    IP=str(IP)
    IP=IP.replace("b'","")
    stat_IP=IP.replace("\\n'","")
    return(stat_IP)

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

def cdsound(laps,controller):
    global minlaps

    
    if controller == 1:
        sendMsgToSound.append("egyeni_snd")
        
    if controller == 2:
        sendMsgToSound.append("osszetett_snd")     
    if (minlaps-laps) == 3:
        sendMsgToSound.append("haromkor_snd")
    if (minlaps-laps) == 2:
        sendMsgToSound.append("ketkor_snd")
    if (minlaps-laps) == 1:
        sendMsgToSound.append("egykor_snd")
    if (minlaps-laps) == 0:
        sendMsgToSound.append("complete_snd")

def timecheck(value,minlaptime,maxlaptime,skiptime,locktime):
    #retdef [behav code, message, next lap start, next round start]
    print(value)
    if ((((value < minlaptime) and (value > locktime)) or (value < skiptime))):
        ret = [0,"RESULT BELOW MINLAP",False,False];
    if ((value > minlaptime) and (value > locktime)):
        ret = [value,"SEEMS OK",True,False];
    if ((value > skiptime) and (value < locktime)):
        ret = [value,"Correction:",False,True];
    if (value > maxlaptime):
        ret = [1,"RESULT OVER MAXLAP" ,False,False];

    return ret

def clockmebitch(result,pilotid,eventid,roundid,heatid):
    global WSCONTROL
    db = pymysql.connect(host="localhost",    # your host, usually localhost
                         user="ktspe",         # your username
                         passwd="macilaci88",  # your password
                         db="ktspe")        # name of the data base

    # you must create a Cursor object. It will let
    #  you execute all the queries you need
    cur = db.cursor()

    # Use all the SQL you like
    result = float(result)
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
    WSCONTROL = True

def correctmebitch(result,pilotid,eventid,roundid,heatid):
    global WSCONTROL
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
    result=prevresult+float(result);
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
        WSCONTROL = True
def startmebitch(result,pilotid,eventid,roundid,heatid):
    global WSCONTROL
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
    WSCONTROL = True
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

  
    
    sql = "select * from pilots where (transponderid=%s) or (transponderid2=%s)"
    cur.execute(sql, (transponderid,transponderid))
    
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

  
    
    sql = "select * from pilots where (transponderid=%s) or transponderid2=%s"
    cur.execute(sql, (transponderid,transponderid))
    
    # print all the first cell of all the rows
   
    ret = cur.fetchone()
    db.close()
    #print(ret) 
    duplicate = []
    
    if ret is not None:
         duplicate.append(1) 
         duplicate.append("[DUPLICATE]:" + ret[0])
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

def MsgToOledGui(message):
     global oledpresent

     log("Transport To OLEDGUI: " + message)
     ss=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
     
     host= 'localhost'
     port=int(2001)
     try:
         json_message = {}
         json_message['descriptor']='command'
         json_message['command']=message
         json_message['deviceid']='DAEMON'
         message = json.dumps(json_message)
         ss.connect((host,port))
         ss.sendall(message.encode())
         ss.close()
         oledpresent = True;
     except socket.error:
         oledpresent = False;
         log('Nincs OLEDGUI controller / Nem válaszol')

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
                                if rcommand == "readtag":
                                    if runthegame == False:
                                         readstatus = []
                                         getasingleread = True
                                        
                                         time.sleep(2)
                                    else:
                                         readstatus = ['NOK','Timing still running!']
                                    message = readstatus
                                    message = json.dumps(message) 
                                    client.send(message.encode())
                                    #print(recmsg)
                                if rcommand=='auxcheck':
                                    rmessage = [ledpresent,audiopresent,rcpresent]
                                    message = json.dumps(rmessage) 
                                    client.send(message.encode())

                                if rcommand=='status':
                                    rmessage = ['OK',str(timer()),lastlog]
                                    message = json.dumps(rmessage) 
                                    client.send(message.encode())

                                if rcommand=='daemonrestart':
                                    
                                    killthedaemon=True
                                    
                                
                                if rcommand=='logrequest':
                                    
                                    logreaderip=data['ip']
                                    logreader = True;
                                if rcommand == 'nextround':
                                    last_device_id = getlockstatus()
                                    if last_device_id == device_id:                                   
                                         if runthegame == False:
                                              eventdata=eventcontrol('nextround')
                                         else:
                                              eventdata=['','','','','','TSR']
                                    else:
                                         setlockstatus(device_id)
                                         eventdata=['','','','','','ODR']
                                         if device_id == 'RC':
                                              sendMsgToRc.append(str(eventdata))
                                     
                                    message = json.dumps(eventdata) 
                                    client.send(message.encode())

                                if rcommand == "prevround":
                                    print(rcommand)
                                    last_device_id = getlockstatus()
                                    if last_device_id == device_id:                                   
                                         if runthegame == False:
                                              eventdata=eventcontrol('prevround')
                                         else:
                                              eventdata=['','','','','','TSR']
                                    else:
                                         setlockstatus(device_id)
                                         eventdata=['','','','','','ODR']
                                         if device_id == 'RC':
                                              sendMsgToRc.append(str(eventdata))
                                    message = json.dumps(eventdata)
                                    client.send(message.encode())

                                if rcommand == "getposition":
                                    eventdata=eventcontrol('x')                                
                                    message = json.dumps(eventdata) 
                                    client.send(message.encode())

                                if rcommand == "getrounddetails":
                                    rounddetails()                                

                                if rcommand == 'isrunning':
                                    if runthegame == True:
                                        cd =   str(maxroundtime -mainlooptime)
                                        message=['1',cd]
                                        message = json.dumps(message);
                                    if runthegame == False:
                                        message=['0','0']
                                        message = json.dumps(message);
                                    
                                    client.send(message.encode())    
                                    
                                    
                                if rcommand == "start":
                                    eventdata=eventcontrol('')
                                    #print(eventdata)
                                    if runthegame == False:
                                         roundid = eventdata[0]
                                         eventid = eventdata[1]
                                         heatid = eventdata[2]
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

wsconnected = set()

def WSSERVER(timeout,loop):

    #global sendMsgToSound
     asyncio.set_event_loop(loop)
     
     def producer():
        global resultlist
        global WSCONTROL
        global sendMsgToSound 

        ret = ['x',False];
        if len(sendMsgToSound)>0:
            MsgToSound=sendMsgToSound.pop(0)
            if MsgToSound!="status":
                ret=[MsgToSound,True]
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
     
class transportaudioThread (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
       transportaudio(self.timeout)
       print("Exiting " + self.name)

def transportaudio(timeout):
     global sendMsgToSound
     while True:
          time.sleep(0.01)
          while len(sendMsgToSound)>0:
                    message = sendMsgToSound[0]
                    MsgToSound(message)
                    sendMsgToSound.pop(0)

class transportledThread (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
       transportled(self.timeout)
       print("Exiting " + self.name)
       
def transportled(timeout): 
     global sendMsgToLed
     while True:
          time.sleep(0.01)
          while len(sendMsgToLed)>0:
                    
                    message = sendMsgToLed[0]
                    MsgToLed(message)
                    sendMsgToLed.pop(0)

class transportrcThread (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
       transportrc(self.timeout)
       print("Exiting " + self.name)
       
def transportrc(timeout):
     global sendMsgToRc
     while True:
          time.sleep(0.01)
          while len(sendMsgToRc)>0:
                    
                    message = sendMsgToRc[0]
                    MsgToRc(message)
                    sendMsgToRc.pop(0)

class transportoledguiThread (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
       transportoledgui(self.timeout)
       print("Exiting " + self.name)
       
def transportoledgui(timeout):
     global sendMsgToOledGui
     while True:
          time.sleep(0.01)
          while len(sendMsgToOledGui)>0:
                    
                    message = sendMsgToOledGui[0]
                    MsgToOledGui(message)
                    sendMsgToOledGui.pop(0)
             

thread1 = myThread(1, "socketserver", 0)
thread1.daemon = True
thread1.start()

#thread2 = transportmainThread(2, "transportmain", 0)
#thread2.daemon = True
#thread2.start()

thread3 = transportlogThread(3, "transportlog", 0)
thread3.daemon = True
thread3.start()

if sysconfig[6]==1:
    thread4 = websocketThread(4, "websocket", 0, loop)
    thread4.daemon = True
    thread4.start()

if sysconfig[2]==1:
 
  thread5 = transportaudioThread(5, "transportaudio", 0)
  thread5.daemon = True
  thread5.start()


if sysconfig[3]==1:
  thread6 = transportledThread(6, "transportled", 0)
  thread6.daemon = True
  thread6.start()

if sysconfig[4]==1:
  thread7 = transportrcThread(7, "transportrc", 0)
  thread7.daemon = True
  thread7.start()

thread8 = transportoledguiThread(1, "transportoledgui", 0)
thread8.daemon = True
thread8.start()

################ Kommunikáció vége
#### timing code

def mainloop(time):
    global newplayer
    global obest
    global skiptime
    global locktime
    global playerslot0
    global playerslot1
    global playerslot2
    global playerslot3
    global playerslot4

    global q_is_running
    global w_is_running
    global e_is_running
    global r_is_running
    global t_is_running

    global q_laps
    global w_laps
    global e_laps
    global r_laps
    global t_laps

    global q_best
    global w_best
    global e_best
    global r_best
    global t_best

    global q_start
    global q_end
    global w_start
    global w_end
    global e_start
    global e_end
    global r_start
    global r_end
    global t_start
    global t_end

    global q_pilotid
    global w_pilotid
    global e_pilotid
    global r_pilotid
    global t_pilotid
    global minlaps
    global eventid
    
    if playerslot0:
              
        if q_is_running == True:
            q_res=time
            log("RACER "+ str(q_pilotid)+" LAPTIME:")
            q_res = timecheck(q_res,minlaptime,maxlaptime,skiptime,locktime) #valtozott
            log(str(q_res[0]))
            log(str(q_res[1]))
            if q_res[2] == True:

                q_start = time
                q_is_running = True
                clockmebitch(q_res[0],q_pilotid,eventid,roundid,heatid)
                q_laps += 1

                controller = 0 # 0 = csak visszaszámol 1 = legjobb egyéni 2 = legjobb total
                if (obest is not None) and (q_res[0] is not None) and (q_best is not None):
                    if (q_res[0]<q_best):
                        controller = 1
                        q_best = q_res[0]
                    if (q_res[0]<obest):
                        controller = 2  
                        obest = q_res[0]
                        
                cdsound(q_laps,controller)

            if q_res[3] == True:
                correctmebitch(q_res[0],q_pilotid,eventid,roundid,heatid)
                q_start = time
                
            if q_res[2] == False:
                if q_res[0] == 1:
                    q_is_running = False
                    #print ("RACER POSSIBLY OUT, NEXT ROUND MARKER ASSIGNED:", q_pilotid, "")
                    

        # ha meg nem megy de vagy autonextround 
        if q_is_running == False:
            q_start = time
            q_pilotid = getpilotdata(players[0])
            q_best = getbest(q_pilotid,eventid)
            log(str(q_best))
            startmebitch('0',q_pilotid,eventid,roundid,heatid)
            log("STARTING RACER, KEY:"+ str(q_pilotid))
            q_is_running = True
            q_laps = 0

        playerslot0 = False;

    if playerslot1:
      
        if w_is_running == True:
            w_res = time
            log("RACER "+ str(w_pilotid)+" LAPTIME:")
            w_res = timecheck(w_res,minlaptime,maxlaptime,skiptime,locktime)
            log(str(w_res[0]))
            log(str(w_res[1]))
            if w_res[2] == True:

                w_start = time
                w_is_running = True
                clockmebitch(w_res[0],w_pilotid,eventid,roundid,heatid)
                w_laps += 1

                controller = 0 # 0 = csak visszaszámol 1 = legjobb egyéni 2 = legjobb total
                if (obest is not None) and (w_res[0] is not None):
                    if (w_res[0]<w_best):
                        controller = 1
                        w_best = w_res[0]
                    if (w_res[0]<obest):
                        controller = 2  
                        obest = w_res[0]
                cdsound(w_laps,controller)

            if w_res[3] == True:
                correctmebitch(w_res[0],w_pilotid,eventid,roundid,heatid)
                w_start = time
               
            if w_res[2] == False:
                if w_res[0] == 1:
                    w_is_running = False
                    #print ("RACER POSSIBLY OUT, NEXT ROUND MARKER ASSIGNED:", w_pilotid, "")
         
        if w_is_running == False:
            w_start = time
            w_pilotid = getpilotdata(players[1])
            w_best = getbest(w_pilotid,eventid)
            startmebitch('0',w_pilotid,eventid,roundid,heatid)
            log ("STARTING RACER, KEY:"+ str(w_pilotid))
            w_is_running = True
            w_laps = 0

        playerslot1 = False;

    if playerslot2:
      
        if e_is_running == True:
            e_res = time
            print("RACER ", e_pilotid,"LAPTIME:")
            e_res = timecheck(e_res,minlaptime,maxlaptime,skiptime,locktime)
            log(str(e_res[0]))
            log(str(e_res[1]))
            if e_res[2] == True:

                e_start = time
                e_is_running = True
                clockmebitch(e_res[0],e_pilotid,eventid,roundid,heatid)
                e_laps += 1

                controller = 0 # 0 = csak visszaszámol 1 = legjobb egyéni 2 = legjobb total
                if (obest is not None) and (e_res[0] is not None):
                    if (e_res[0]<e_best):
                        controller = 1
                        e_best = e_res[0]
                    if (e_res[0]<obest):
                        controller = 2  
                        obest = e_res[0]
                cdsound(e_laps,controller)

            if e_res[3] == True:
                correctmebitch(e_res[0],e_pilotid,eventid,roundid,heatid)
                e_start = time

            if e_res[2] == False:
                if e_res[0] == 1:
                    e_is_running = False
                    #print ("RACER POSSIBLY OUT, NEXT ROUND MARKER ASSIGNED:", e_pilotid, "")
         
        if e_is_running == False:
            e_start = time
            e_pilotid = getpilotdata(players[2])
            e_best = getbest(e_pilotid,eventid)
            startmebitch('0',e_pilotid,eventid,roundid,heatid)
            log ("STARTING RACER, KEY:"+ str(e_pilotid))
            e_is_running = True
            e_laps = 0

        playerslot2 = False;
         
    if playerslot3:
      
        if r_is_running == True:
            r_res = time
            log("RACER "+ str(r_pilotid) + "LAPTIME:")
            r_res = timecheck(r_res,minlaptime,maxlaptime,skiptime,locktime)
            log(str(r_res[0]))
            log(str(r_res[1]))
            if r_res[2] == True:

                r_start = time
                r_is_running = True
                clockmebitch(r_res[0],r_pilotid,eventid,roundid,heatid)
                r_laps += 1

                controller = 0 # 0 = csak visszaszámol 1 = legjobb egyéni 2 = legjobb total
                if (obest is not None) and (r_res[0] is not None):
                    if (r_res[0]<r_best):
                        controller = 1
                        r_best = r_res[0]
                    if (r_res[0]<obest):
                        controller = 2  
                        obest = r_res[0]
                cdsound(r_laps,controller)

            if r_res[3] == True:
                correctmebitch(r_res[0],r_pilotid,eventid,roundid,heatid)
                r_start = time

            if r_res[2] == False:
                if r_res[0] == 1:
                    r_is_running = False
                    #print ("RACER POSSIBLY OUT, NEXT ROUND MARKER ASSIGNED:", r_pilotid, "")
         
        if r_is_running == False:
            r_start = time
            r_pilotid = getpilotdata(players[3])
            r_best = getbest(r_pilotid,eventid)
            startmebitch('0',r_pilotid,eventid,roundid,heatid)
            log ("STARTING RACER, KEY:"+ str(r_pilotid))
            r_is_running = True
            r_laps = 0

        playerslot3 = False;

    if playerslot4:
      
        if t_is_running == True:
            t_res = time
            log("RACER "+ str(t_pilotid)+"LAPTIME:")
            t_res = timecheck(t_res,minlaptime,maxlaptime,skiptime,locktime)
            log(str(t_res[0]))
            log(str(t_res[1]))
            if t_res[2] == True:

                t_start = time
                t_is_running = True
                clockmebitch(t_res[0],t_pilotid,eventid,roundid,heatid)
                t_laps += 1

                controller = 0 # 0 = csak visszaszámol 1 = legjobb egyéni 2 = legjobb total
                if (t_best is not None) and (t_res[0] is not None):
                    if (t_res[0]<t_best):
                        controller = 1
                        t_best = t_res[0]
                    if (t_res[0]<obest):
                        controller = 2  
                        obest = t_res[0]
                cdsound(t_laps,controller)
            if t_res[3] == True:
                correctmebitch(t_res[0],t_pilotid,eventid,roundid,heatid)
                t_start = time

            if t_res[2] == False:
                if t_res[0] == 1:
                    t_is_running = False
                    #print ("RACER POSSIBLY OUT, NEXT ROUND MARKER ASSIGNED:", t_pilotid, "")
         
        if t_is_running == False:
            t_start = time
            t_pilotid = getpilotdata(players[4])
            t_best = getbest(t_pilotid,eventid)
            startmebitch('0',t_pilotid,eventid,roundid,heatid)
            log ("STARTING RACER, KEY:"+ str(t_pilotid))
            t_is_running = True
            t_laps = 0

        playerslot4 = False;
        
def timing(data):
    passid = data[0]
    time=data[1]
    log("Timing / PassID: " +str(passid))
    
    
    global players
    global newplayer
    global playerslot0
    global playerslot1
    global playerslot2
    global playerslot3
    global playerslot4
    
    
    if passid in players:
        if players.index(passid) == 0:
            playerslot0 = True;
            mainloop(time)
        if players.index(passid) == 1:
            playerslot1 = True;
            mainloop(time)
        if players.index(passid) == 2:
            playerslot2 = True;
            mainloop(time)
        if players.index(passid) == 3:
            playerslot3 = True;
            mainloop(time)
        if players.index(passid) == 4:
            playerslot4 = True;
            mainloop(time)

    if passid not in players:
        if (len(players)<5):
            players.append(passid)
            newplayer = True

            if players.index(passid) == 0:
                playerslot0 = True;
                mainloop(time)
            if players.index(passid) == 1:
                playerslot1 = True;
                mainloop(time)
            if players.index(passid) == 2:
                playerslot2 = True;
                mainloop(time)
            if players.index(passid) == 3:
                playerslot3 = True;
                mainloop(time)
            if players.index(passid) == 4:
                playerslot4 = True;
                mainloop(time)


#### scanner code

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

def monitor(addr,rssi,scandata):

    global playermonitor
    global skiptime
    global pmdata 
    global trigger_value
    global WSCONTROL
    global resultlist
    global laptime
    global forgettime
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
                
            pmdata[ddistribute][1][0].append(abs(rssi))
            pmdata[ddistribute][1][1].append(timer())
            pmdata[ddistribute][1][3]=timer() # itt láttuk utoljára 

            
            log(str(rssi) +" "+ str(addr) +" "+ str(timer()))
            if len(pmdata[ddistribute][1][0])>2:
                if pmdata[ddistribute][1][0][-3]<trigger_value and pmdata[ddistribute][1][0][-2]<trigger_floor and pmdata[ddistribute][1][0][-1]<trigger_value:
                    min_rssi=pmdata[ddistribute][1][0][-1]
                    for i in range (1,3):
                        if pmdata[ddistribute][1][0][-i]<min_rssi:
                            min_rssi=pmdata[ddistribute][1][0][-i]

                    if min_rssi!=pmdata[ddistribute][1][0][-1] and pmdata[ddistribute][1][0].index(min_rssi)!=0 and min_rssi<trigger_floor:        
                        min_timestamp=pmdata[ddistribute][1][1][pmdata[ddistribute][1][0].index(min_rssi)]
                        #print(min_timestamp)
                        lowest_key=pmdata[ddistribute][1][0].index(min_rssi)
                        #print(lowest_key)
                        result = parab(pmdata[ddistribute][1][1][(lowest_key-1)],pmdata[ddistribute][1][1][(lowest_key)],pmdata[ddistribute][1][1][(lowest_key+1)],pmdata[ddistribute][1][0][lowest_key-1],pmdata[ddistribute][1][0][lowest_key],pmdata[ddistribute][1][0][lowest_key+1])

                        if pmdata[ddistribute][1][2] == 0: #első nekifutás
                           pmdata[ddistribute][1][2] = result
                           log("KORSTART 1: " + str(pmdata[ddistribute][1][2]))
                           triggerdata=[addr,(result-pmdata[ddistribute][1][2])] 
                           timing(triggerdata)
                           pmdata[ddistribute][1][0] = []
                           pmdata[ddistribute][1][1] = []
                           
                        if ((pmdata[ddistribute][1][2]!=result) and (result-pmdata[ddistribute][1][2]>skiptime)): #összes többi
                           log("SKIP CHECK: " + str(timer()-pmdata[ddistribute][1][2]))
                           log("KORSTART X: " + str(pmdata[ddistribute][1][2]))
                           triggerdata=[addr,(result-pmdata[ddistribute][1][2])] 
                           timing(triggerdata)
                           pmdata[ddistribute][1][0] = []
                           pmdata[ddistribute][1][1] = []
                           pmdata[ddistribute][1][2] = result 
                        
                        
                        
                        #print(pmdata[ddistribute][1][2])       
                        
                       
                        
                        #sendMsgToMain.append('BLE_READER_001|timing|startgate|'+control+'|'+result+'|')
                        
                        
                       
readcount=0    
class ScanDelegate(DefaultDelegate):

    def handleDiscovery(self, dev, isNewDev, isNewData):
        global readcount
        #print(strftime("%Y-%m-%d %H:%M:%S", gmtime()), dev.addr, dev.getScanData(), dev.rssi)
        scandata=(dev.getValueText(9))
        monitor(dev.addr,dev.rssi,scandata)
        readcount=readcount+1
        #print(scandata)
        #print(dev) 
        sys.stdout.flush()

class ScanDelegateForSingle(DefaultDelegate):

    def handleDiscovery(self, dev, isNewDev, isNewData):
        global readstatus
        #print(strftime("%Y-%m-%d %H:%M:%S", gmtime()), dev.addr, dev.getScanData(), dev.rssi)
        scandata=(dev.getValueText(9))  
        if scandata is not None:
            
            if scandata[0:4]=="KTS0" and dev.rssi>-80:
                srcheckup = checkduplicate(dev.addr)
                if srcheckup[0] == 0:
                    readstatus = ['OK',dev.addr]
                if srcheckup[0] == 1:
                    readstatus = ['NOK',srcheckup[1]]
            log("SINGLEREAD: " + str(readstatus))       
            #print(scandata)
            #print(dev) 
            sys.stdout.flush()
        if scandata is None:
            #readstatus = ['NOK','No Tag detected']    
            log("SINGLEREAD: " + str(readstatus))

        
scanner = Scanner().withDelegate(ScanDelegate())
singlescanner = Scanner().withDelegate(ScanDelegateForSingle())


##### MAINLOOP
networkcheck_start = timer()
devicecheck_start = timer()
sendconfig('led')



while True:
   
    time.sleep(0.01)
    if killthedaemon == True:
         sys.exit("Killing Daemon now...")
         
    if forcedrestart == True:
          runthegame= True

    devicecheck_iv = timer()

    if devicecheck_iv-devicecheck_start > 10: 
          
         pass
    
    networkcheck_iv = timer()

    if networkcheck_iv-networkcheck_start > 10: 
         sendMsgToSound.append("status")
         sendMsgToLed.append("status")
         sendMsgToRc.append("status")
         networkcheck_start = timer()
         #sendconfig('led')

    if getasingleread == True:
                          
         #try:
         singlescanner.scan(1,passive=False)
         #singlescanner.process()
         #time.sleep(1) 
         #singlescanner.stop()
         #singlescanner.clear()
                       
         #except:
             #readstatus = ['NOK','No TAG detected!']
             #print(readstatus)
           
           
         getasingleread = False    
            

    if runthegame:
           q_is_running = False
           w_is_running = False
           e_is_running = False
           r_is_running = False
           t_is_running = False

           playerslot0 = False
           playerslot1 = False
           playerslot2 = False
           playerslot3 = False
           playerslot4 = False

           
           pmdata=[[0,[[],[],0,0]],
                   [1,[[],[],0,0]],
                   [2,[[],[],0,0]],
                   [3,[[],[],0,0]],
                   [4,[[],[],0,0]],

                  ]
                   
           

           
           playermonitor = []
                     
           config = getconfig(eventid)

           minlaptime = config[4]
           maxlaptime = config[5]
           maxroundtime = config[6]+3
           readpower = config[9]
           

           socketcommand=''
           stopmeplease = False
           stopnodeserver = False

           #all values pcs
           maxlaps = config[7]
           maxrounds = config[8]
           minlaps = config [11]
           players = list()
           newplayer = False
           
           
                                               
           #if readerpresent == True:   
           log("Futam indul!")    
           sendMsgToSound.append("start_snd")
           sendMsgToLed.append('countdown')
           sendMsgToRc.append('countdown|'+ str(maxroundtime) + "|")
                
           mainlooptime_start = timer()
           hasbeenclosed = False
           hasbeenthirty = False
           hasbeenten = False
           obest = getobest(eventid)  

           scanner.clear()
           log('ML start:' + str(mainlooptime_start))
                
           scanner.start(passive=True)
           scanner_running = True; 
           sendMsgToOledGui.append('start')   
           

           while runthegame:
                   
                   
                   scanner.process(0.001) 
                    
                   #time.sleep(0.5)
                   
                   if killthedaemon == True:
                        sys.exit("Killing Daemon now...")
                   #print(nodecommand)
                   #print(socketcommand)
                   #print(stopmeplease)
                   
                   mainlooptime_current = timer()
                     
                   mainlooptime = mainlooptime_current-mainlooptime_start

                   if ((mainlooptime > maxroundtime-2) and (hasbeenclosed == False)):
                       #sendMsgToSound.append("finish_snd")
                       hasbeenclosed = True

                   if ((mainlooptime > maxroundtime-30) and (hasbeenthirty == False)):
                       sendMsgToSound.append("thirty_snd")
                       hasbeenthirty = True
                       
                   if ((mainlooptime > maxroundtime-10) and (hasbeenten == False)):
                       sendMsgToSound.append("ten_snd")
                       hasbeenten = True
                   
                   if (mainlooptime > maxroundtime) or (stopmeplease == True):

                       #if (stopmeplease == True):
                       #    sendMsgToSound.append("finish_snd")

                       sendMsgToOledGui.append('finish')
                       scanner.stop()
                       
                       scanner_running = False                     
                           
                       mainlooptime_current = timer()
                       mainlooptime = mainlooptime_current-mainlooptime_start
                       log('ML end: '+str(mainlooptime))
                       runthegame = False
                       
                       
                       
                       sendMsgToLed.append('waitone')
                       #sendconfig('led')
                       sendMsgToRc.append('waitone')
                       
                       sendMsgToSound.append("finish_snd")
                       #sys.exit("Itt a vége")
                       log("Itt a vége. RC: " + str(readcount))  


