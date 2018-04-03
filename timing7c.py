#!/usr/bin/env python3
from __future__ import print_function
import socket
import sys
import tty, termios
import time
from timeit import default_timer as timer
import pymysql
import mercury
from usb.core import find as finddev
import threading
import json
from subprocess import call
#import atexit
#from playsound import playsound



#log_file = open("/home/pi/message.log","a")
#sys.stdout = log_file
#log_file.close()

#def closeOnExit(log_file):
	#log_file.close()

#atexit.register(closeOnExit(log_file))

lastlog=''




runthegame = False
readerpresent = False
audiopresent = False
ledpresent = False
rcpresent = False
sendMsgToLed=[]
sendMsgToSound=[]
sendMsgToRc=[]
sendMsgToLog=[]
usb_error_counter = 0
debugmode= False
fieldtest = False
fieldtestreadrate_a = 0
fieldtestreadrate_b = 0
fieldtesttimeout = 60 # másodperc
forcedrestart = False
ledconfigsent = False
killthedaemon = False
dualread = False
logreader = False
logreaderip = ''
getasingleread = False
readstatus = []

#print(reader.get_supported_regions())

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
                         user="kts",         # your username
                         passwd="DQYVRi1XbV21So90",  # your password
                         db="kts")        # name of the data base

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



#mainbasz


def sendconfig (target):
     db = pymysql.connect(host="localhost",    
                         user="kts",         
                         passwd="DQYVRi1XbV21So90",  
                         db="kts")        

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

        
def mainloop():
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
            q_end = timer()
            log("RACER "+ str(q_pilotid)+" LAPTIME:")
            q_res = q_end - q_start
            q_res = timecheck(q_res,minlaptime,maxlaptime,skiptime,locktime) #valtozott
            log(str(q_res[0]))
            log(str(q_res[1]))
            if q_res[2] == True:

                q_start = timer()
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
                q_start = timer()
                
            if q_res[2] == False:
                if q_res[0] == 1:
                    q_is_running = False
                    #print ("RACER POSSIBLY OUT, NEXT ROUND MARKER ASSIGNED:", q_pilotid, "")
                    

        # ha meg nem megy de vagy autonextround 
        if q_is_running == False:
            q_start = timer()
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
            w_end = timer()
            log("RACER "+ str(w_pilotid)+" LAPTIME:")
            w_res = w_end - w_start
            w_res = timecheck(w_res,minlaptime,maxlaptime,skiptime,locktime)
            log(str(w_res[0]))
            log(str(w_res[1]))
            if w_res[2] == True:

                w_start = timer()
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
                w_start = timer()
               
            if w_res[2] == False:
                if w_res[0] == 1:
                    w_is_running = False
                    #print ("RACER POSSIBLY OUT, NEXT ROUND MARKER ASSIGNED:", w_pilotid, "")
         
        if w_is_running == False:
            w_start = timer()
            w_pilotid = getpilotdata(players[1])
            w_best = getbest(w_pilotid,eventid)
            startmebitch('0',w_pilotid,eventid,roundid,heatid)
            log ("STARTING RACER, KEY:"+ str(w_pilotid))
            w_is_running = True
            w_laps = 0

        playerslot1 = False;

    if playerslot2:
      
        if e_is_running == True:
            e_end = timer()
            print("RACER ", e_pilotid,"LAPTIME:")
            e_res = e_end - e_start
            e_res = timecheck(e_res,minlaptime,maxlaptime,skiptime,locktime)
            log(str(e_res[0]))
            log(str(e_res[1]))
            if e_res[2] == True:

                e_start = timer()
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
                e_start = timer()

            if e_res[2] == False:
                if e_res[0] == 1:
                    e_is_running = False
                    #print ("RACER POSSIBLY OUT, NEXT ROUND MARKER ASSIGNED:", e_pilotid, "")
         
        if e_is_running == False:
            e_start = timer()
            e_pilotid = getpilotdata(players[2])
            e_best = getbest(e_pilotid,eventid)
            startmebitch('0',e_pilotid,eventid,roundid,heatid)
            log ("STARTING RACER, KEY:"+ str(e_pilotid))
            e_is_running = True
            e_laps = 0

        playerslot2 = False;
         
    if playerslot3:
      
        if r_is_running == True:
            r_end = timer()
            log("RACER "+ str(r_pilotid) + "LAPTIME:")
            r_res = r_end - r_start
            r_res = timecheck(r_res,minlaptime,maxlaptime,skiptime,locktime)
            log(str(r_res[0]))
            log(str(r_res[1]))
            if r_res[2] == True:

                r_start = timer()
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
                r_start = timer()

            if r_res[2] == False:
                if r_res[0] == 1:
                    r_is_running = False
                    #print ("RACER POSSIBLY OUT, NEXT ROUND MARKER ASSIGNED:", r_pilotid, "")
         
        if r_is_running == False:
            r_start = timer()
            r_pilotid = getpilotdata(players[3])
            r_best = getbest(r_pilotid,eventid)
            startmebitch('0',r_pilotid,eventid,roundid,heatid)
            log ("STARTING RACER, KEY:"+ str(r_pilotid))
            r_is_running = True
            r_laps = 0

        playerslot3 = False;

    if playerslot4:
      
        if t_is_running == True:
            t_end = timer()
            log("RACER "+ str(t_pilotid)+"LAPTIME:")
            t_res = t_end - t_start
            t_res = timecheck(t_res,minlaptime,maxlaptime,skiptime,locktime)
            log(str(t_res[0]))
            log(str(t_res[1]))
            if t_res[2] == True:

                t_start = timer()
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
                t_start = timer()

            if t_res[2] == False:
                if t_res[0] == 1:
                    t_is_running = False
                    #print ("RACER POSSIBLY OUT, NEXT ROUND MARKER ASSIGNED:", t_pilotid, "")
         
        if t_is_running == False:
            t_start = timer()
            t_pilotid = getpilotdata(players[4])
            t_best = getbest(t_pilotid,eventid)
            startmebitch('0',t_pilotid,eventid,roundid,heatid)
            log ("STARTING RACER, KEY:"+ str(t_pilotid))
            t_is_running = True
            t_laps = 0

        playerslot4 = False;
        
def timing(data):
    passid = data.epc
    rssi = data.rssi
    log("Timing / PassID: " +str(passid) +" RSSI: "+ str(rssi))
    
    
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
            mainloop()
        if players.index(passid) == 1:
            playerslot1 = True;
            mainloop()
        if players.index(passid) == 2:
            playerslot2 = True;
            mainloop()
        if players.index(passid) == 3:
            playerslot3 = True;
            mainloop()
        if players.index(passid) == 4:
            playerslot4 = True;
            mainloop()

    if passid not in players:
        if (len(players)<5):
            players.append(passid)
            newplayer = True

            if players.index(passid) == 0:
                playerslot0 = True;
                mainloop()
            if players.index(passid) == 1:
                playerslot1 = True;
                mainloop()
            if players.index(passid) == 2:
                playerslot2 = True;
                mainloop()
            if players.index(passid) == 3:
                playerslot3 = True;
                mainloop()
            if players.index(passid) == 4:
                playerslot4 = True;
                mainloop()

def playsound (wave_obj):
    
    play_obj = wave_obj.play()

def playsoundcounter (wave_obj):
    
    play_obj = wave_obj.play()
   
            
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
                         user="kts",         # your username
                         passwd="DQYVRi1XbV21So90",  # your password
                         db="kts")        # name of the data base

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
                         user="kts",         # your username
                         passwd="DQYVRi1XbV21So90",  # your password
                         db="kts")        # name of the data base

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
                         user="kts",         # your username
                         passwd="DQYVRi1XbV21So90",  # your password
                         db="kts")        # name of the data base

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
                         user="kts",         
                         passwd="DQYVRi1XbV21So90",  
                         db="kts")        

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
                         user="kts",         
                         passwd="DQYVRi1XbV21So90",  
                         db="kts")        

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
                         user="kts",         
                         passwd="DQYVRi1XbV21So90",  
                         db="kts")        

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
                         user="kts",         
                         passwd="DQYVRi1XbV21So90",  
                         db="kts")        

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
                         user="kts",         
                         passwd="DQYVRi1XbV21So90",  
                         db="kts")        

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
                         user="kts",         
                         passwd="DQYVRi1XbV21So90",  
                         db="kts")        

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
                         user="kts",         
                         passwd="DQYVRi1XbV21So90",  
                         db="kts")        

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
                         user="kts",         
                         passwd="DQYVRi1XbV21So90",  
                         db="kts")        

    cur = db.cursor()
    sql = "update lck set device_id=%s"
    cur.execute(sql, (device_id))
    db.commit()
    db.close()   
    log("Func setlockstatus:" + str(device_id))
         

def rounddetails():
     global sendMsgToRc
     db = pymysql.connect(host="localhost",user="kts",passwd="DQYVRi1XbV21So90",db="kts")        
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
     db = pymysql.connect(host="localhost",user="kts",passwd="DQYVRi1XbV21So90",db="kts")        
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




################## socket szutyok


server_address = ('172.14.1.2', 2000)
log('init connection to LED CONTROL on %s port %s' % server_address)

server_address = ('172.14.1.3', 2000)
log('init connection to AUDIO CONTROL on %s port %s' % server_address)

server_address = ('172.14.1.4', 2000)
log('init connection to REMOTE CONTROL on %s port %s' % server_address)

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
#sendMsgToLed.append('countdown')

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

#sendMsgToSound('start_snd')

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
#sendMsgToSound('start_snd')


################ NODE server #########

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
                    #print(rdata)
                    
                    if 'terminate' in recmsg:
                        
                         stopmeplease = True
                         exitthread=True;
                    if 'syncmeup' in recmsg:
                         message = str(time.time());
                         message = message + '\r\n'
                         client.send(message.encode())
                         #exitthread=True;
                    if 'status' in recmsg:
                         message = str('Timing daemon fut');
                         message = message + '\r\n'
                         client.send(message.encode())
                         #exitthread=True;
                    if 'lastlog' in recmsg:
                         message = str(lastlog);
                         message = message + '\r\n'
                         client.send(message.encode())
                         #exitthread=True;

                    if 'daemonrestart' in recmsg:
                         message = "Killing Daemon now...";
                         message = message + '\r\n'
                         #client.send(message.encode())
                         #print(recmsg)
                         killthedaemon= True
                         #exitthread=True;
                         
                    if 'reader' in recmsg:
                         if readerpresent == True:
                              message = str('Up and running');
                         if readerpresent == False:
                              message = str('NOT OK!');
                         message = message + '\r\n'
                         client.send(message.encode())
                         #exitthread=True;
                    if 'isrunning' in recmsg:
                         if runthegame == True:
                              cd =   str(maxroundtime -mainlooptime)
                              message = str('1|'+ cd);
                         if runthegame == False:
                              message = str('0|');
                         message = message + '\r\n'
                         client.send(message.encode())
                         #exitthread=True;
                    if 'auxcheck' in recmsg:
                         if ledpresent == True:
                              message = str('1|');
                         else:
                              message = str('0|');
                         if audiopresent == True:
                              message = message+str('1|');
                         else:
                              message = message+str('0|');
                         if rcpresent == True:
                              message = message+str('1|');
                         else:
                              message = message+str('0|');
                        
                         message = message + '\r\n'
                         client.send(message.encode())
                         #exitthread=True;

                    if "|" in recmsg: 
                            
                         data = recmsg.split("|")
                         #print('command', data[0])
                         #print('toplay', data[1])
                         #print('pilot', data[2])    
                         command = data[1]
                         device_id = data[0]
                         #print(command)
                         log("Incoming query from: " + str(device_id) + " ::: "+ str(command))
                         if command == "readtag":
                              if runthegame == False:
                                   readstatus = []
                                   getasingleread = True
                                  
                                   time.sleep(2)
                              else:
                                   readstatus = ['NOK','Fut az időmérés!']
                              message = readstatus
                              message = json.dumps(message) 
                              client.send(message.encode())
                              #print(recmsg)
                         if command == "logrequest":
                              logreader = True
                              logreaderip = data[2]
                              #print(recmsg)
                         if command == "nextround":
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

                         if command == "prevround":
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

                         if command == "getposition":
                              eventdata=eventcontrol('x')                                
                              message = json.dumps(eventdata) 
                              client.send(message.encode())

                         if command == "getrounddetails":
                              rounddetails()                                
                              
                              
                              
                         if command == "start":
                              eventdata=eventcontrol('')
                              #print(eventdata)
                              if runthegame == False:
                                   roundid = eventdata[0]
                                   eventid = eventdata[1]
                                   heatid = eventdata[2]
                                   runthegame = True

                                   log("Fogadott socket adat(RiD:"+ str(roundid) +" EiD:"+ str(eventid)+" HiD:" + str(heatid))
                         if command == "fieldtest":
                              if runthegame == False:
                                   if fieldtest == False:
                                        eventdata=eventcontrol('')
                                        eventid = eventdata[1]
                                        fieldtest = True
                                   else:
                                        fieldtest = False
                                        
                         if command == "stop":
                              runthegame = False
                              stopmeplease = True
                              log("Round is over!")                                
                         exitthread=True;        
                    else:
                       raise error('Client disconnected')
            except:
                client.close()
                return False


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

thread1 = myThread(1, "socketserver", 0)
thread1.daemon = True
thread1.start() 

thread2 = transportaudioThread(2, "transportaudio", 0)
thread2.daemon = True
thread2.start()

thread3 = transportledThread(3, "transportled", 0)
thread3.daemon = True
thread3.start()

thread4 = transportrcThread(4, "transportrc", 0)
thread4.daemon = True
thread4.start()

thread5 = transportlogThread(5, "transportlog", 0)
thread5.daemon = True
thread5.start()

################## socket szutyok vége

def fieldteststream_a(data):
    global fieldtestreadrate_a
    passid = data.epc
    rssi = data.rssi
    fieldtestreadrate_a +=1
    sendMsgToRc.append('ftstream|0|RSSI|'+ str(rssi) + '|')


def fieldteststream_b(data):
    global fieldtestreadrate_b
    passid = data.epc
    rssi = data.rssi
    fieldtestreadrate_b +=1
    sendMsgToRc.append('ftstream|1|RSSI|'+ str(rssi) + '|')
    

# MAIN LOOP



networkcheck_start = timer()
devicecheck_start = timer()
sendconfig('led')

dev = finddev(idVendor=0x1a86, idProduct=0x7523)

while True:
   
    time.sleep(0.8)
    if killthedaemon == True:
         sys.exit("Killing Daemon now...")
         
    if forcedrestart == True:
          runthegame= True

    devicecheck_iv = timer()

    if devicecheck_iv-devicecheck_start > 10: 
          
         dev = finddev(idVendor=0x1a86, idProduct=0x7523)
         devicecheck_start=timer()
    
    networkcheck_iv = timer()

    if networkcheck_iv-networkcheck_start > 10: 
         sendMsgToSound.append("status")
         sendMsgToLed.append("status")
         sendMsgToRc.append("status")
         networkcheck_start = timer()
         sendconfig('led')
         
    

    if dev is None:
       dev = finddev(idVendor=0x1a86, idProduct=0x7523)
       readerpresent = False
    if readerpresent == False and debugmode == False:
         dev = finddev(idVendor=0x1a86, idProduct=0x7523)
         if usb_error_counter > 2:
              call("sudo nohup usb_modeswitch -v 0x1a86 -p 0x7523 --reset-usb", shell=True)
              usb_error_counter = 0
              time.sleep(10)
         try:
              #dev.reset()
              #log("USB Soft Reset")
              time.sleep(2)
              #usb_error_counter = 0
         except AttributeError:
              log("Nincs RFID olvaso!")
         time.sleep(0.2)
         try:
              reader_a = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=57600)
              log(reader_a.get_model())
              reader_a.set_region("EU3")
              readerpresent = True
         except TypeError:
              log(" (A)  Hardver nem valaszol! BP1")
              usb_error_counter += 1
              readerpresent = False
         if dualread == True:
              time.sleep(0.2)
              try:
                   reader_b = mercury.Reader("tmr:///dev/ttyUSB1", baudrate=115200)
                   log(reader_b.get_model())
                   reader_b.set_region("EU3")
                   b_readerpresent = True
              except TypeError:
                   log(" (B)  Hardver nem valaszol! BP1")
                   usb_error_counter += 1
                   b_readerpresent = False

         if dualread == True and b_readerpresent == False:
               readerpresent = False

    if readerpresent == True and getasingleread == True:
        
        try:
             #reader = mercury.Reader("tmr:///dev/ttyUSB0", baudrate=115200)
             reader_a.set_region("EU3")
             reader_a.set_read_plan([1], "GEN2", read_power=1500)
             read = reader_a.read(500)
             time.sleep(0.5)

             try:
                  readresult = str(read[0])
                  readresult = readresult[2:26]
                       #print(readresult)
                  srcheckup = checkduplicate(readresult)
                  
                  if srcheckup[0] == 0:
                        readstatus = ['OK',readresult]
                  if srcheckup[0] == 1:
                        readstatus = ['NOK',srcheckup[1]]
                  
                   
             except:
                  readstatus = ['NOK','Nem érzékelek TAG-et!']
                  #print(readstatus)
       
        except TypeError:
            log("Hardver nem valaszol! SINGLEREAD")
            readstatus = ['NOK','Hardver nem valaszol!']

        getasingleread = False    
        log("SINGLEREAD: " + str(readstatus))
        
                   
    if fieldtest == True and readerpresent == True:
           config = getconfig(eventid)
           readpower = config[9]
           reader_a.set_read_plan([1], "GEN2", read_power=readpower)
           reader_a.start_reading(fieldteststream_a)

           if dualread == True:
                time.sleep(0.2)
                reader_b.set_read_plan([1], "GEN2", read_power=readpower)
                reader_b.start_reading(fieldteststream_b)

           fieldteststart = timer()
           
           
           sendMsgToRc.append('fieldtest')

           while fieldtest == True:
               start_read_count_a =  fieldtestreadrate_a
               time.sleep(1)
               current_read_count_a = fieldtestreadrate_a
               readrate_a = current_read_count_a - start_read_count_a
               if readrate_a == 0:
                    sendMsgToRc.append('ftstream|0|RSSI|-135|')
               sendMsgToRc.append('ftstream|0|RR|'+ str(readrate_a) + '|')
               fieldtesttimer = timer()

               if dualread == True:
                    start_read_count_b =  fieldtestreadrate_b
                    time.sleep(1)
                    current_read_count_b = fieldtestreadrate_b
                    readrate_b = current_read_count_b - start_read_count_b
                    if readrate_b == 0:
                         sendMsgToRc.append('ftstream|1|RSSI|-135|')
                    sendMsgToRc.append('ftstream|1|RR|'+ str(readrate_b) + '|') 

               if fieldtesttimer-fieldteststart > fieldtesttimeout:
                    try:
                           reader_a.stop_reading()
                    except NameError:
                           log(" (A) hardver nem ment")

                    if dualread == True:
                           try:
                                  reader_b.stop_reading()
                           except NameError:
                                  log(" (B) hardver nem ment")
                               
                    sendMsgToRc.append('waitone')
                    fieldtest = False
                    
                     
    if runthegame:
           print(usb_error_counter)
           #defaults 
           #roundid = sys.argv[1]
           #eventid = sys.argv[2]
           #heatid = sys.argv[3]
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
           
           config = getconfig(eventid)

           minlaptime = config[4]
           maxlaptime = config[5]
           maxroundtime = config[6]+3
           readpower = config[9]
           locktime = 8
           skiptime = 1

           socketcommand=''
           stopmeplease = False
           stopnodeserver = False

           #all values pcs
           maxlaps = config[7]
           maxrounds = config[8]
           minlaps = config [11]
           players = list()
           newplayer = False
           
           log(readpower)
           #log_file = open("/home/pi/message.log","a")
           #sys.stdout = log_file
           if debugmode == False:
                try:
                    reader_a.set_read_plan([1], "GEN2", read_power=readpower)
                    reader_a.start_reading(timing)
                    usb_error_counter = 0
                except (NameError, TypeError):
                   log(" (A)  Hardver nem valaszol BP2!")
                   usb_error_counter += 1
                   readerpresent = False
                   forcedrestart = True
                   runthegame = False

                if dualread == True:
                    try:
                        reader_b.set_read_plan([1], "GEN2", read_power=readpower)
                        reader_b.start_reading(timing)
                        usb_error_counter = 0
                    except (NameError, TypeError):
                        log(" (B)  Hardver nem valaszol BP2!")
                        usb_error_counter += 1
                        readerpresent = False
                        forcedrestart = True
                        runthegame = False
                     
           if debugmode == True:
                readerpresent = True
                
           if readerpresent == True:   
                log("Futam indul!")    
                sendMsgToSound.append("start_snd")
                sendMsgToLed.append('countdown')
                sendMsgToRc.append('countdown|'+ str(maxroundtime) + "|")
                
                mainlooptime_start = timer()
                hasbeenclosed = False
                hasbeenthirty = False
                hasbeenten = False
                obest = getobest(eventid)  
                log('ML start:' + str(mainlooptime_start))
                #stopmeplease= False

              
           

           while runthegame:
                   time.sleep(0.5)                    
                   if killthedaemon == True:
                        sys.exit("Killing Daemon now...")
                   #print(nodecommand)
                   #print(socketcommand)
                   #print(stopmeplease)
                   
                   mainlooptime_current = timer()
                     
                   mainlooptime = mainlooptime_current-mainlooptime_start

                   if ((mainlooptime > maxroundtime-2) and (hasbeenclosed == False)):
                       sendMsgToSound.append("finish_snd")
                       hasbeenclosed = True

                   if ((mainlooptime > maxroundtime-30) and (hasbeenthirty == False)):
                       sendMsgToSound.append("thirty_snd")
                       hasbeenthirty = True
                       
                   if ((mainlooptime > maxroundtime-10) and (hasbeenten == False)):
                       sendMsgToSound.append("ten_snd")
                       hasbeenten = True
                   
                   if (mainlooptime > maxroundtime) or (stopmeplease == True):

                       if (stopmeplease == True):
                           sendMsgToSound.append("finish_snd")

                       
                       #print(mainlooptime)
                       try:
                           reader_a.stop_reading()
                       except NameError:
                           log(" (A) hardver nem ment")
                           usb_error_counter += 1
                       
                           
                       mainlooptime_current = timer()
                       mainlooptime = mainlooptime_current-mainlooptime_start
                       log('ML end: '+str(mainlooptime))
                       runthegame = False
                       
                       stopnodeserver = True
                       forcedrestart = False
                       sendMsgToLed.append('waitone')
                       sendconfig('led')
                       sendMsgToRc.append('waitone')
                       #sendMsgToSound.append("finish_snd")
                       #sys.exit("Itt a vége")
                       log("Itt a vége")
                       
                       
        
