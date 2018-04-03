import time
import threading
import atexit
import socket
import sys
import os
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
import RPi.GPIO as GPIO
import json

sys.path.append('../')
from obswebsocket import obsws, requests

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import subprocess

from timeit import default_timer as timer

# Input pins:
L_pin = 27 
R_pin = 23 
C_pin = 4 
U_pin = 17 
D_pin = 22 

A_pin = 5 
B_pin = 6 


GPIO.setmode(GPIO.BCM) 

GPIO.setup(A_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
GPIO.setup(B_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
GPIO.setup(L_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
GPIO.setup(R_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
GPIO.setup(U_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
GPIO.setup(D_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up
GPIO.setup(C_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Input with pull-up



# Raspberry Pi pin configuration:
RST = None     # on the PiOLED this pin isnt used
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

disp = Adafruit_SSD1306.SSD1306_128_64(rst=RST)
disp.begin()

# Clear display.
disp.clear()
disp.display()

menulist = ['START','STOP', 'KOV.FUTAM','ELO.FUTAM','RFID TESZT','STÁTUSZ','ÚJRAINDÍT','LEÁLLÍT']
commandlist = ['start','stop','nextround','prevround','fieldtest','status','reboot','shutdown']
command=[]
command.append('menu')
activemenu = 0
sscommand = ''
sendMsgToMain = []
sendMsgToStream = []
jumpdelay = False
current_round=''
current_heat=''
pilotlist=[]
resultlist={}
bestlist={}
laplist={}
rounddetails={}
maxroundtime = 0
displaycountdown = False
holdon = False
last_stream_message=0
streamtimer=False

reader_a_rr = 0
reader_a_rssi = -135
reader_b_rr = 0
reader_b_rssi = -135
prev_rssi_a = -135
prev_rssi_b = -135

def clearOnExit():
	draw.rectangle((0,0,width,height), outline=0, fill=0)
atexit.register(clearOnExit)

def is_json(myjson):
  try:
    json_object = json.loads(myjson)
  except ValueError:
    return False
  return True


def setcommand(cid):
    global command
    global commandlist
    global activemenu
    global displaycountdown
    global holdon
    global pilotlist
    
    commandfound = False
    cid = commandlist[cid]
    if cid == 'start':
        sendMsgToMain.append('RC|start|')
        command.append('busy')
        commandfound = True
        #activemenu = 3
    if cid == 'nextround':
        sendMsgToMain.append('RC|nextround|')
        command.append('busy')
        commandfound = True
        holdon = False
        pilotlist =[]
        activemenu = 0
    if cid == 'prevround':
        sendMsgToMain.append('RC|prevround|')
        
        command.append('busy')
        commandfound = True
        holdon = False
        pilotlist=[]
        #activemenu = 3
    if cid == 'stop':
        sendMsgToMain.append('RC|stop|')
        #sendMsgToStream.append('stop')
        command.append('busy')
        displaycountdown = False
        #activemenu = 0
        commandfound = True
    if cid == 'fieldtest':
        sendMsgToMain.append('RC|fieldtest|')
        command.append('busy')
        #activemenu = 0
        commandfound = True
    if cid == 'shutdown':
        command=[]
        command.append('busy')
        os.system('sudo shutdown now')
       
        #activemenu = 0
        commandfound = True
    if cid == 'reboot':
        command=[]
        command.append('busy')
        os.system('sudo reboot')
       
        #activemenu = 0
        commandfound = True
    if commandfound == False:
        command.append('comerror')

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
         time.sleep(1)
         command.append('menu')
     except socket.error:
         command.append('comerror')

def MsgToStream(message):
     global last_stream_message   
     host = "172.24.1.99"
     port = 4444
     password = "macilaci88"
     if message=='start':
             name='Flight'
             last_stream_message=0
     if message=='stop':
             name='Ambient+Results'
             last_stream_message=2
     if message=='Ambient2':
             name='Ambient2'
             last_stream_message=3
     if message=='Ambient2+Flight':
             name='Ambient2+Flight'
             last_stream_message=1
     if message=='Ambient':
             name='Ambient'
             last_stream_message=4 
        
     print(name)
     
     try:   
             ws = obsws(host, port)
             ws.connect()
             time.sleep(1)
             ws.call(requests.SetCurrentScene(name))
             time.sleep(1)   
             ws.disconnect()
     except:
        pass
         
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
        global current_heat
        global current_round
        global sscommand
        global pilotlist
        global resultlist
        global laplist
        global reader_a_rr
        global reader_a_rssi
        global reader_b_rr
        global reader_b_rssi
        global rounddetails
        global maxroundtime
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
                         exitthread=True;
                    if 'status' in recmsg:
                         message = str('Remote daemon fut');
                         message = message + '\r\n'
                         client.send(message.encode())
                         exitthread=True;
                    if 'lastlog' in recmsg:
                         message = str(lastlog);
                         message = message + '\r\n'
                         client.send(message.encode())
                         exitthread=True;
                    if 'waitone' in recmsg:
                         sscommand=('waitone')
                         exitthread=True;
                         
                         #print("kene szamolni")

                    if is_json(recmsg) == True:
                        #print(recmsg)
                        data = json.loads(recmsg)
                        if (data['descriptor']) == 'rounddetails':
                                rounddetails = {}
                                for key in data:
                                        if key != 'descriptor':
                                                rounddetails[key] = data[key]
                        exitthread=True;
                   
                            

                    if "|" in recmsg: 
                            
                         data = recmsg.split("|")
                         #print('command', data[0])
                         #print('toplay', data[1])
                         #print('pilot', data[2])    
                         #command = data[0]

                         if data[0] == 'display':
                               #command.append('displayrounddata')
                               pilotname = data[2]
                               if len(pilotname)>5:
                                  pilotname=pilotname[0:5]
                               if pilotname not in pilotlist: 
                                  pilotlist.append(pilotname)
                                  bestlist[pilotname] = 9999
                                  laplist[pilotname] = ['9999']
                               else:   
                                  laplist[pilotname].append(data[1])
                                  bestlist[pilotname] = min(laplist[pilotname])

                               resultlist[pilotname] = data[1]                             
                               #print(laplist)
                     
                         if data[0] == 'correct':
                               #command.append('displayrounddata')
                               pilotname = data[2]
                               if len(pilotname)>5:
                                  pilotname=pilotname[0:5]

                               tempresult = resultlist[pilotname]
                               resultlist[pilotname] = data[1]
                               laplist[pilotname].append(data[1])

                               if tempresult in laplist[pilotname]:
                                  eztkeresed = laplist[pilotname].index(tempresult)
                                  laplist[pilotname].pop(eztkeresed)

                               bestlist[pilotname]=min(laplist[pilotname])
                               #print(laplist)   
                               #print(pilotlist)
                               #print(resultlist)
                               #print(bestlist)
                         if data[0] == 'ftstream':
                                 if command[-1]!='fieldtest':
                                         command.append('fieldtest') 
                                 if data[1] == '0':
                                         #print(data[3])
                                         
                                         if data[2] == "RR":
                                                 reader_a_rr = data[3]
                                         if data[2] == "RSSI":
                                                 reader_a_rssi = data[3]
                                 if data[1] == '1':
                                         if data[2] == "RR":
                                                 reader_b_rr = data[3]
                                         if data[2] == "RSSI":
                                                 reader_b_rssi = data[3]
                         if data[0] == 'countdown':
                                 sscommand=('countdown')
                                 maxroundtime=data[1]
                         exitthread=True;
                    if "," in recmsg:
                         data = recmsg.split(",")
                         message = data[5]
                         #message = message.replace('\'','')
                         #message = message.replace(']','')
                         #message = message.replace(' ','')
                         #print(message)
                         if 'TSR' in message:
                                 command.append('stillrunning')
                         if 'ODR' in message:
                                 #print(message)
                                 command.append('controltransfer')

                         if 'OK' in message:
                                 command.append('menu')

                                 current_round = data[4]
                                 current_heat = data[3]
                         
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

class transportstreamThread (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
       transportstream(self.timeout)
       print("Exiting " + self.name)

def transportstream(timeout):
     global sendMsgToStream
     global last_stream_message
     cte=''
     while True:
          time.sleep(0.01)
          while len(sendMsgToStream)>0:
                    message = sendMsgToStream[0]
                    MsgToStream(message)
                    sendMsgToStream.pop(0)
                    #last_stream_message=message
                    print(last_stream_message)    
                
thread1 = myThread(1, "socketserver", 0)
thread1.daemon = True
thread1.start()

thread2 = transportmainThread(2, "transportmain", 0)
thread2.daemon = True
thread2.start()

thread3 = transportstreamThread(3, "transportstream", 0)
thread3.daemon = True
thread3.start()


sendMsgToMain.append('RC|getposition|')
sendMsgToMain.append('RC|getrounddetails|')
# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))
#print(str(width) + " | " + str(height))
# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0,0,width,height), outline=0, fill=0)


# First define some constants to allow easy resizing of shapes.
padding = 14
top = padding
bottom = height-padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Load default font.
font = ImageFont.load('/home/pi/fonts/6x10.pil')
smallfont = ImageFont.load('/home/pi/fonts/5x7.pil')
largefont = ImageFont.load('/home/pi/fonts/9x18.pil')
# Alternatively load a TTF font.  Make sure the .ttf font file is in the same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('Minecraftia.ttf', 8)

wifidelaycontrol = timer()
cmd ="iwconfig wlan0 | grep -o 'Link Quality=[0-9]*/[0-9]*' | sed -e s/.*=//g"
lq = subprocess.check_output(cmd, shell = True )
# Write two lines of text.
lq = str(lq)
lq = lq.replace('b\'','')
lq = lq.replace('\\n\'','')
#print(lq)
lq = lq.split('/')

positioncheck_start = timer()

displaychanged = True
while True:
        
    
    
    #print(rounddetails)
    if len(command)>0:
           remotecommand=command[-1]
    #print(command)
    # Draw a black filled box to clear the image.
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    if not GPIO.input(A_pin): # button is released
            command=['menu']
            jumpdelay = True
            sendMsgToMain.append('RC|getposition|')
            displaychanged = True
    if remotecommand == "busy":
        #print("busy")
        for n in range(3):
                draw.rectangle([(80+(n*10), 12), (85+(n*10),16)], outline=255, fill=1)
                draw.text((15, 12),"DOLGOZOK",  font=smallfont, fill=255)
                
                time.sleep(0.1)
                disp.image(image)
                disp.display()
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        command=['menu']

    if remotecommand == "controltransfer":
        #print("busy")
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        draw.text((12, 28),"ÁTVETTED AZ IRÁNYÍTÁST",  font=smallfont, fill=255)
        
        
        disp.image(image)
        disp.display()
        time.sleep(2)
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        command=['menu']
        displaychanged = True   

    # KISKIJELZŐ
    if sscommand=="waitone":
            sendMsgToStream.append('stop')
            last_stream_message=1
            streamtime=timer()
            streamtimer=True
            reader_a_rr = 0
            reader_a_rssi = -135
            command=[]
            command.append('menu')
            sscommand='displaypilots'
            wait = timer()
            holdon = True
            activemenu = 2
            displaycountdown = False
            if len(pilotlist) == 0:
               sscommand=''
               holdon = False

    if sscommand=="countdown":
          sendMsgToStream.append('start')
          streamtime=timer()
          last_stream_message=0
          streamtimer=True
          holdon = False
          pilotlist=[]
          resultlist={}
          bestlist={}
          laplist={}
          rounddetails={}
          for n in range(4):
                 draw.rectangle([(0,0) , (120,64)], outline=0, fill=0)
                 if n<3:
                       draw.text((60, 20), str(3-n),  font=largefont, fill=255)
                       
                 if n==3:
                        draw.text((40, 20),"START",  font=largefont, fill=255)
                        
                 #print(n)
                 disp.image(image)
                 disp.display()
                 time.sleep(0.9)
                 draw.rectangle([(0,0) , (120,64)], outline=0, fill=0)
          sscommand='displaypilots'
          activemenu = 1
          pilottimer = timer()
          cdtimer = timer()
          displaycountdown = True
          
    if sscommand=="displaypilots":
       
          
          if holdon == True:
                   
                   if (most>(wait+60)):
                      holdon = False
                      sscommand=''

          most=timer()            
          draw.rectangle([(62,6) , (120,64)], outline=0, fill=0)
          numberofpilots = len(pilotlist)
                #offscreen_canvas.Clear()
          
          for i in range(0,numberofpilots):
                   pilotname=(pilotlist[i])
                   result=str(resultlist[pilotname])
                   if bestlist[pilotname]!=9999:
                      besttime = str(bestlist[pilotname])
                   else:
                      besttime = str(resultlist[pilotname])
                  
                   if len(laplist[pilotname])-1 < 3:
                      draw.text((100, 14+(i*8)), str(len(laplist[pilotname])-1),  font=smallfont, fill=255)
                   
                           
                   if len(laplist[pilotname])-1 >= 3:
                           draw.rectangle([(99, 14+(i*8)-1), (108, 14+(i*8)+6)], outline=1, fill=1)
                           draw.text((100, 14+(i*8)), str(len(laplist[pilotname])-1),  font=smallfont, fill=0)
                   if most-pilottimer < 2 :
                           draw.text((65, 14+(i*8)), str(pilotname),  font=smallfont, fill=255)
                           
                   else:
                      draw.text((64, 14+(i*8)), str(besttime[0:7]),  font=smallfont, fill=255)
                      
                   draw.text((110, 14+(i*8)), "KÖR",  font=smallfont, fill=255)

          if most-pilottimer > 3:
                  pilottimer = timer()
          #print("check")
                 
          #sscommand=''
    if remotecommand == "comerror":
                draw.text((50, 12),"HIBA",  font=smallfont, fill=255)
                displaychanged = True
    if remotecommand == "menu":
        if not GPIO.input(U_pin): # button is released
            if activemenu != 0:
                activemenu -= 1
                displaychanged = True
                jumpdelay = True
            else:
                activemenu=len(menulist)-1

        if not GPIO.input(L_pin): # button is released
            setcommand(3)
            displaychanged = True

        if not GPIO.input(R_pin): # button is released
            setcommand(2)
            displaychanged = True

        if not GPIO.input(D_pin): # button is released
            if activemenu<len(menulist)-1:
                activemenu += 1
                jumpdelay = True
                displaychanged = True
            else:
                activemenu=0
                jumpdelay = True
        if not GPIO.input(B_pin): # button is released
            setcommand(activemenu)
            displaychanged = True
            
            #print(activemenu)
            jumpdelay = True
        if not GPIO.input(C_pin): # button is released
            setcommand(activemenu)
            displaychanged = True
            
            #print(activemenu)
            jumpdelay = True    
        if activemenu > 3:
            top = (padding+(-10*(activemenu-2)))
            
            #print(top)
        else:
            top = padding
        for n in range(len(menulist)):
            if activemenu != n:
                draw.text((x+2, top+(n*10)),menulist[n],  font=font, fill=255)
            else:
                draw.rectangle([(x, top+n*10), (60, top+((n+1)*10)-2)], outline=255, fill=1)
                draw.text((x+2, top+(n*10)),menulist[n],  font=font, fill=0)
        draw.rectangle([(62,13) , (62,64)], outline=255, fill=1)
        draw.rectangle([(0,12) , (128,12)], outline=255, fill=1)
        
        draw.rectangle((0,0,128,6), outline=0, fill=0)
        i = 0
        
        if holdon == False and displaycountdown == False:
                for key in rounddetails:
                     pilotname=key[0:5]
                     pilotname = pilotname.upper()
                     draw.text((65, 14+(i*8)), str(pilotname),  font=smallfont, fill=255)
                     draw.text((100, 14+(i*8)), str(int(rounddetails[key])-1),  font=smallfont, fill=255)
                     draw.text((110, 14+(i*8)), "KÖR",  font=smallfont, fill=255)
                     i += 1
                if i == 0 and len(pilotlist) == 0:
                     draw.rectangle([(82,35) , (115,45)], outline=255, fill=1)
                     draw.text((89, 37), "ÜRES",  font=smallfont, fill=0)
                     
    if remotecommand == "fieldtest":
        fieldtest_start = timer()
        fieldtest_iv = 60
        currenttime = timer()
        while currenttime-fieldtest_start<fieldtest_iv:
             draw.rectangle((0,0,width,height), outline=0, fill=0)
             
             #draw.rectangle([(0,12) , (128,12)], outline=1, fill=1)

             draw.text((0, 12),"READER A",  font=smallfont, fill=255)
             draw.text((70, 12),str(reader_a_rr) + " TAG/SEC",  font=smallfont, fill=255)
             draw.rectangle([(5, 22), (120, 26)], outline=255, fill=0)
             draw.rectangle([(5, 22), (140-abs(int(reader_a_rssi)), 26)], outline=255, fill=1)
             draw.text((0, 32),"READER B",  font=smallfont, fill=255)
             draw.text((70, 32),str(reader_b_rr) + " TAG/SEC",  font=smallfont, fill=255)
             draw.rectangle([(5, 42), (120, 46)], outline=255, fill=0)
             draw.rectangle([(5, 42), (140-abs(int(reader_b_rssi)), 46)], outline=255, fill=1)
             disp.image(image)
             disp.display()
             currenttime = timer()
    #print(displaychanged)          
             
    mainlooptime_current = timer()
    if displaycountdown == False:
            draw.text((65, 2),       "F:" + str(current_heat) +" C:" + str(current_round) ,  font=smallfont, fill=255)
            # ez azért van, hogy ha idle a cucc
            positioncheck_iv = timer()
            if positioncheck_iv-positioncheck_start > 5: 
                sendMsgToMain.append('RC|getposition|')
                positioncheck_start = timer()    
    else:
            remaining_time = float(maxroundtime)-5-(mainlooptime_current-cdtimer)
            m, s = divmod(remaining_time, 60)
            h, m = divmod(m, 60)
            cd = ("%02d:%02d" % (m, s))
            
            draw.text((100, 2),       cd  ,  font=smallfont, fill=255)
            if remaining_time<1:
                    displaycountdown = False
    if mainlooptime_current-wifidelaycontrol > 1:
            
            cmd ="iwconfig wlan0 | grep -o 'Link Quality=[0-9]*/[0-9]*' | sed -e s/.*=//g"
            lq = subprocess.check_output(cmd, shell = True )
            # Write two lines of text.
            lq = str(lq)
            lq = lq.replace('b\'','')
            lq = lq.replace('\\n\'','')
            #print(lq)
            lq = lq.split('/')
            wifidelaycontrol = timer()
            displaychanged=True
    try:
                
            draw.rectangle((0,0,64,11), outline=0, fill=0)
            wifiperc = round(int(lq[0])/int(lq[1])*100)
            draw.text((43, 2),       str(wifiperc) +"%",  font=smallfont, fill=255)
            draw.rectangle([(0, 0), (40, 8)], outline=255, fill=0)
            draw.rectangle([(0, 2), ((round(wifiperc*0.4)), 6)], outline=255, fill=1)
            
            
    except ValueError:
            draw.rectangle((0,0,64,11), outline=0, fill=0)
            draw.text((x, 2), "DISCONNECTED", font=smallfont, fill=255)
            displaychanged=True
    #if mainlooptime_current-wifidelaycontrol > 1 and mainlooptime_current-wifidelaycontrol<2.5:
            
           
    #if mainlooptime_current-wifidelaycontrol > 1:
           
        # Display image.
        
    if streamtimer:
            #print(last_stream_message)
            if last_stream_message==0:
                    if mainlooptime_current-streamtime>120:
                             sendMsgToStream.append('Ambient2+Flight')
                             streamtime=timer()
                             last_stream_message=1

            if last_stream_message==1:
                    if mainlooptime_current-streamtime>20:
                             sendMsgToStream.append('start')
                             streamtime=timer()
                             last_stream_message=0
                                
            if last_stream_message==2:
                    if mainlooptime_current-streamtime>43:
                             sendMsgToStream.append('Ambient2')
                             streamtime=timer()
                             last_stream_message=3
            if last_stream_message==3:
                    if mainlooptime_current-streamtime>30:
                             sendMsgToStream.append('Ambient')
                             streamtime=timer()
                             last_stream_message=4
            if last_stream_message==4:
                    if mainlooptime_current-streamtime>15:
                             sendMsgToStream.append('stop')
                             streamtime=timer()
                             last_stream_message=2

    if displaychanged==True:
            
            disp.image(image)
            disp.display()
    displaychanged=False
    if jumpdelay:
       time.sleep(0.06)
       jumpdelay = False
    time.sleep(0.005)
