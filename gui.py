import RPi.GPIO as gpio
import time
import Adafruit_GPIO.SPI as SPI
import Adafruit_SSD1306
import subprocess
import atexit
import socket
from timeit import default_timer as timer
from subprocess import call
import threading
import json
import os
import sys
import math

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

gpio.setmode(gpio.BCM)
gpio.setup(23, gpio.IN)
gpio.setup(24, gpio.IN)
gpio.setup(25, gpio.IN)

RST = None     # on the PiOLED this pin isnt used
# Note the following are only used with SPI:
DC = 23
SPI_PORT = 0
SPI_DEVICE = 0

disp = Adafruit_SSD1306.SSD1306_128_32(rst=RST)

disp.begin()
width = disp.width
height = disp.height
image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)
draw.rectangle((0,0,width,height), outline=0, fill=0)
command = ''
font = ImageFont.load('/home/pi/fonts/6x10.pil')
smallfont = ImageFont.load('/home/pi/fonts/5x7.pil')
largefont = ImageFont.load('/home/pi/fonts/9x18.pil')

# Clear display.
disp.clear()
disp.display()
x=0
padding = -2
top = padding
bottom = height-padding

def clearOnExit():
    disp.clear()
    draw.rectangle((0,0,128,32), outline=0, fill=0)

def is_json(myjson):
  try:
    json_object = json.loads(myjson)
  except ValueError:
    return False
  return True

#atexit.register(clearOnExit())

menulist = ['STATUS','SET ROLE', 'ENV. TEST','RESTART','SHUTDOWN']
commandlist = ['status','rolesetup','environment','restart','shutdown']
commandtype = ['loc','msg','msg','loc','loc']
displaytypelist = ['statusmenu','menu','menu','restart','shutdown']


statusmenulist=['BACK', '< PREV', 'NEXT >']
statuscommandlist=['home', 'prevpage', 'nextpage']
statusdisplaytypelist = ['menu','statusmenu','statusmenu']
statuspages = 2

selectedmenu = 0
subselectedmenu = 0
displaytype='menu'
mc=''
maxmenuitem=3
submaxmenuitem=5
offset=0
bpresslatency = False
daemonpresent = False
talkback = ''
currentpage = 1

stat_IP = ''
stat_WIFI = ['','']
stat_CPU = ''
stat_MEM = ''
stat_DISK = ''
stat_ADJ = ''

old_wifiperc=0
wifidelaycontrol = timer()
statusdelaycontrol = timer()
cddelaycontrol = 0
def MsgToLocal(message,answere = False):

     #global audiopresent
     #log("Transport To AUDIO: " + message)
     global daemonpresent
     global talkback     
     ss=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
     host= '127.0.0.1'
     port=int(2000)
     try:
         ss.connect((host,port))
         ss.sendall(message.encode())
         
         daemonpresent = True;
         if answere == True:
             #print('running')
             data=ss.recv(1024)
             data=data.decode()
             #print(data)
             if is_json(data):
                 #print(data)
                 return(json.loads(data))
         ss.close()
     except socket.error:
         daemonpresent = False;
     #    log('Nincs Audio controller / Nem válaszol')
#sendMsgToSound('start_snd')


class statusThread (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
       status(self.timeout)
       print("Exiting " + self.name)

def status(timeout):
     global stat_IP
     global stat_WIFI
     global stat_ADJ
     
     
     while True:
          time.sleep(2)
          message = {'descriptor':'command'}
          message['command'] = 'statusrequest'
          message['device_id'] = 'OLEDGUI'
          ADJ = MsgToLocal(json.dumps(message),True)
          #print(ADJ[1])
          #try:
          #    if ADJ[1] == True:
          #        stat_ADJ = 'ON'
          #    else:
          #        stat_ADJ ='OFF'
          #except:
          #    stat_ADJ = 'N/A'
          cmd ="iwconfig wlan0 | grep -o 'Link Quality=[0-9]*/[0-9]*' | sed -e s/.*=//g"
          lq = subprocess.check_output(cmd, shell = True )
          # Write two lines of text.
          lq = str(lq)
          lq = lq.replace('b\'','')
          lq = lq.replace('\\n\'','')
          #print(lq)
          stat_WIFI = lq.split('/')
          cmd = "hostname -I | cut -d\' \' -f1"
          IP = subprocess.check_output(cmd, shell = True )
          cmd = "top -bn1 | grep load | awk '{printf \"%.2f\", $(NF-2)}'"
          IP=str(IP)
          IP=IP.replace("b'","")
          stat_IP=IP.replace("\\n'","")
          
class myThread (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
        ThreadedServer('',int(2001)).listen()
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
        global command
        global commandlist
        
        
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
                                
                                                                                                  
                                if rcommand == "reboot":
                                   command = "restart"           
                                if rcommand == "shutdown":
                                   command = "shutdown" 
                                                
                        exitthread=True;
                    else:
                       raise error('Client disconnected')
            except:
                client.close()
                return False

thread1 = statusThread(1, "statusThread", 0)
thread1.daemon = True
thread1.start()

thread2 = myThread(2, "socketserver", 0)
thread2.daemon = True
thread2.start()            

displaychanged=False
while True:
    draw.rectangle((0,0,width,height), outline=0, fill=0)
    if  bpresslatency == True:
        time.sleep(0.08)
        bpresslatency = False
    if gpio.input(23) == 0:
         pass
    else:
        mc='up'
    if gpio.input(24) == 0:
        pass
    else:
        mc='down'
    if gpio.input(25) == 0:
        pass
    else:
        mc='enter'
  
    if displaytype == 'statusmenu':
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        
        subdisplaytypelist = statusdisplaytypelist
        subcommandlist = statuscommandlist
        submenulist = statusmenulist
        pages = statuspages
        mainlooptime_current = timer()
                 
            
        if mc=='down':
            subselectedmenu+=1
            mc=''
            bpresslatency = True
            
        if mc=='up':
            subselectedmenu-=1
            mc=''
            bpresslatency = True
            
        if mc=='enter':
            subcommand=subcommandlist[subselectedmenu]
            if subcommand == 'nextpage':
                currentpage += 1
            if subcommand == 'prevpage':
                currentpage -= 1
            if subcommand == 'home':
                displaychanged = True
                
                
                #currentpage = 1
            if currentpage <1:
                currentpage=pages
            if currentpage >pages:
                currentpage=1
            displaytype=subdisplaytypelist[subselectedmenu]
            mc=''
            bpresslatency = True
            
            
        if subselectedmenu>submaxmenuitem-1:
            offset=22
        else:
            offset=0
        if subselectedmenu>len(submenulist)-1:
            subselectedmenu=0
        if subselectedmenu<0:
            subselectedmenu=len(submenulist)-1
       
        if currentpage == 1:
            if daemonpresent == True:
                stat_DAEMON = 'OK'
            else:
                stat_DAEMON = 'NOT OK'
            draw.text((2, 0), 'IP:', font=font, fill=255)
            draw.text((33, 0), stat_IP, font=font, fill=255)
            draw.text((2, 10), 'TDMN:', font=font, fill=255)
            draw.text((33, 10), stat_DAEMON, font=font, fill=255)
        if currentpage == 2:
           
            draw.text((2, 0), 'ROLE:', font=font, fill=255)
            draw.text((56, 0), 'STARTGATE', font=font, fill=255)
            draw.text((2, 10), 'UPTIME:', font=font, fill=255)
            draw.text((56, 10), str(timer()) , font=font, fill=255)
            
        for i in range (len(submenulist)):
            #print(selectedmenu,i)
            if subselectedmenu!=i:
                draw.text((2+(i*45)+1-offset, 22), submenulist[i], font=font, fill=255)
            if subselectedmenu==i:
                #print(i*11)
                draw.rectangle((0+(i*45)+1-offset,20,40+(i*45)+1-offset,32), outline=0, fill=255)
                draw.text((2+(i*45)+1-offset, 22), submenulist[i], font=font, fill=0)
        displaychanged = True    
    #common
    #print(displaytype)
    if displaytype == 'shutdown':
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            if cddelaycontrol == 0:
                cddelaycontrol = timer()
            currentlooptime = timer ()
            timediff = 10-(round(currentlooptime-cddelaycontrol,2))
            #print(timediff)
            if timediff>0:
                draw.text((38, 3), 'SHUTDOWN IN', font=font, fill=255)
                draw.text((55, 12), str(round(timediff,2)), font=largefont, fill=255)
            if timediff<0:
                draw.text((10, 6), 'PLEASE WAIT 10 SEC', font=font, fill=255)
                draw.text((5, 16), 'BEFORE SWITCHING OFF', font=font, fill=255)
                #draw.text((55, 12), str(round(timediff,2)), font=largefont, fill=255)
            
    if displaytype == 'menu':
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        if mc=='down':
            selectedmenu+=1
            mc=''
            bpresslatency = True
            displaychanged = True
        if mc=='up':
            selectedmenu-=1
            mc=''
            bpresslatency = True
            displaychanged = True
        if mc=='enter':
            command=commandlist[selectedmenu]
            displaytype=displaytypelist[selectedmenu]
            mc=''
            bpresslatency = True
            displaychanged = True
        #print(selectedmenu)
        #print(offset)
        
        if selectedmenu>len(menulist)-1:
            selectedmenu=0
            displaychanged=True
        if selectedmenu<0:
            selectedmenu=len(menulist)-1
            displaychanged=True

        if selectedmenu>maxmenuitem-1:
            offset=22*math.floor(selectedmenu/maxmenuitem)
            
        else:
            offset=0
        for i in range (len(menulist)):
            #print(selectedmenu,i)
            if selectedmenu!=i:
                draw.text((2, (i*11)+1-offset), menulist[i], font=font, fill=255)
            if selectedmenu==i:
                #print(i*11)
                draw.rectangle((0,i*11-offset,60,i*11+10-offset), outline=0, fill=255)
                draw.text((2, (i*11)+1-offset), menulist[i], font=font, fill=0)
        if command!='':
            print(command)
            if command=="restart":
                print("restarting")
                draw.rectangle((0,0,width,height), outline=0, fill=0)
                draw.text((38, 10), 'RESTARTING', font=font, fill=255)
                disp.image(image)
                disp.display()
                time.sleep(1)
                os.system("sudo reboot")
                sys.exit()
                displaychanged=True
            if command=="shutdown":
                print("shutting down") 
                draw.rectangle((0,0,width,height), outline=0, fill=0)
                draw.text((10, 6), 'PLEASE WAIT 10 SEC', font=font, fill=255)
                draw.text((5, 16), 'BEFORE SWITCHING OFF', font=font, fill=255)
                disp.image(image)
                disp.display()
                time.sleep(1)
                os.system("sudo poweroff")
                sys.exit()
                displaychanged=True
            if commandtype[commandlist.index(command)] == 'msg':
                MsgToLocal(command)
            command=''
            

        mainlooptime_current = timer()
        if mainlooptime_current-wifidelaycontrol > 1:

            try:
                    
                    wifiperc = round(int(stat_WIFI[0])/int(stat_WIFI[1])*100)
                    if old_wifiperc!= wifiperc:
                        displaychanged=True
                        
                    draw.text((96, 5),       "WIFI",  font=smallfont, fill=255)
                    draw.text((89, 10),       str(wifiperc) +"%",  font=largefont, fill=255)
                    old_wifiperc = wifiperc           
            except ValueError:
                    draw.text((89, 14), "DSCTD", font=smallfont, fill=255)
                    displaychanged = True
                
        #if mainlooptime_current-wifidelaycontrol > 1:
                #print("putty")
                #wifidelaycontrol = timer()
                           
        draw.rectangle((62,0,64,32), outline=0, fill=255)            
            
    if displaychanged == True:
        disp.image(image)
        disp.display()

    displaychanged=False
    time.sleep(0.06)
