#!/usr/bin/env python3
import atexit
import socket
import sys
import os
import time, datetime
from timeit import default_timer as timer
import threading
from subprocess import call
import subprocess
from rgbmatrix import RGBMatrix, RGBMatrixOptions
from rgbmatrix import graphics
from PIL import Image
import json

stopmeplease = False
command = ['idle']
pilotlist=[]
resultlist={}
bestlist={}
laplist={}
blinker=""
resultout=""
config={}

supporters = ['kts.png','csao.png']

image1 = Image.open("kts.png")
image2 = Image.open("csao.png")

def is_json(myjson):
  try:
    json_object = json.loads(myjson)
  except ValueError:
    return False
  return True

##########SOCKET STUFF############# 

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
        global pilotlist
        global resultlist
        global laplist
        global config
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

                    if 'idle' in recmsg:
                               command=[]
                               command.append('idle')

                    if 'countdown' in recmsg:
                              
                               command=[]
                               command.append('countdown')
                               
                    if 'waitone' in recmsg:
                              
                               command=[]
                               command.append('waitone')
                               
                    if 'syncmeup' in recmsg:
                            message = str(time.time());
                            message = message + '\r\n'
                            client.send(message.encode())

                    if 'status' in recmsg:
                            ls_output = subprocess.check_output(['iwconfig', 'wlan0'])
                            ls_output = str(ls_output)
                            ls_output = ls_output.split("   ")
                            message = str(ls_output[21])
                            message = message + '\r\n'
                            client.send(message.encode())
                            
                    if 'shutdown' in recmsg:
                               command=[]
                               os.system('sudo shutdown now')

                    if 'reboot' in recmsg:
                               command=[]
                               os.system('sudo shutdown -r now')

                    if is_json(recmsg):
                               data=json.loads(recmsg)
                               #print(data)
                               if data['descriptor'] == 'config':
                                  config = data
                                  #print(config)

                               
                    #if 'clear' in socketcommand:
                           #matrix.Clear()

                    if "|" in recmsg: 
                            
                            data = recmsg.split("|")
                            #print('command', data[0])
                            #print('time', data[1])
                            #print('pilot', data[2])    
                            
                            if data[0] == 'display':
                               command.append('displayrounddata')
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
                               print(laplist)
                     
                            if data[0] == 'correct':
                               command.append('displayrounddata')
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
                    exitthread = True
                    #print(command)
                else:
                    raise error('Client disconnected')
            except:
                client.close()
                return False
                
   
thread1 = myThread(1, "socketserver", 30)
thread1.daemon = True
thread1.start()

#sendmsg("display|12.1234|MOLNIGEE|")

################# MATRIX STUFF #############

options = RGBMatrixOptions()
options.rows = 32
options.chain_length = 3
options.parallel = 1
options.gpio_slowdown = 2
options.hardware_mapping = 'adafruit-hat-pwm'  # If you have an Adafruit HAT: 'adafruit-hat'
logoColor = graphics.Color(255, 150, 10)
blueColor = graphics.Color(37, 84, 180)
redColor = graphics.Color(255, 255, 255)
greenColor = graphics.Color(100, 255, 100)
blackColor = graphics.Color(0, 0, 0)

matrix = RGBMatrix(options = options)


def clearOnExit():
	matrix.Clear()



atexit.register(clearOnExit)



offscreen_canvas = matrix.CreateFrameCanvas()
font = graphics.Font()
font.LoadFont("/home/pi/fonts/7x13.bdf")
fontbig = graphics.Font()
fontbig.LoadFont("/home/pi/fonts/9x15B.bdf")
fonthuge = graphics.Font()
fonthuge.LoadFont("/home/pi/fonts/10x20.bdf")
fontsmall = graphics.Font()
fontsmall.LoadFont("/home/pi/fonts/5x8.bdf")
textColor = graphics.Color(255, 255, 0)
pos = offscreen_canvas.width



holdon = False

while True:
        #print(command)
        if len(command)>0:
           matrixcommand=command[-1]
        offscreen_canvas.Clear()
        if (matrixcommand=="waitone"):
            command=[]
            command.append('displayrounddata')
            wait = timer()
            holdon = True

            if len(pilotlist) == 0:
               command.append('idle')
               holdon = False
            
        if (matrixcommand=="idle"):

                pilotlist=[]
                resultlist={}
                bestlist={}
                laplist={}
                blinker=""
                key = 'eventname'
                add_text =''
                if key not in config:
                   my_text="KTS - KRISTOF TIMING SYSTEM"
                else:
                   my_text="KTS - "+ str(config['eventname'])
                   if config['bestpilot'] != 0:
                        add_text=  " BEST LAP: "+ str(config['bestpilot'][0].upper()) + " " + str(config['bestpilot'][1])
                   #print(config)
               
                ido= time.time()
                ido = time.strftime('%H:%M:%S', time.localtime(time.time()+3600))
                offscreen_canvas.Clear()
                length1 = graphics.DrawText(offscreen_canvas, fontbig, pos, 15, textColor, my_text)
                
                length2 = graphics.DrawText(offscreen_canvas, fontbig, pos+length1, 15, redColor, add_text)
                
                length = length1 + length2
                graphics.DrawText(offscreen_canvas, font, 20, 30, greenColor, ido)
                
                pos -= 1
                if (pos + length < 0):
                    pos = offscreen_canvas.width 
                time.sleep(0.05)
                offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)

        if (matrixcommand=="countdown"):
                holdon = False
                pilotlist=[]
                resultlist={}
                bestlist={}
                laplist={}
                blinker=""
                for i in range(0,4):
                   offscreen_canvas.Clear()

                   if i<3:
                       cdcolor = redColor
                       cdtext  = str(3-i)
                       cdpos = 44
                   else:
                       cdcolor = greenColor
                       cdtext  = "START"
                       cdpos = 22
                       command.append("displayrounddata")
                   graphics.DrawText(offscreen_canvas, fonthuge, cdpos, 22, cdcolor, cdtext)
                   offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
                   time.sleep(1)
                   offscreen_canvas.Clear()
                

        if (matrixcommand=="displayrounddata"):
                
                if holdon == True:
                   
                   if (most>(wait+60)):
                      holdon = False
                      command.append('idle')
                
                if (blinker==""):
                   blinker=timer()
                   blinkColor = greenColor
                   resultColor= redColor
                  
                most=timer()
                #print(blinker)
                #print(most)
                
                numberofpilots = len(pilotlist)
                #offscreen_canvas.Clear()

                if numberofpilots == 0:
                      graphics.DrawLine(offscreen_canvas,0,0,0,31,blinkColor)
                      graphics.DrawLine(offscreen_canvas,95,0,95,31,blinkColor)
                                                 
                for i in range(0,numberofpilots):
                   pilotname=(pilotlist[i])
                   result=str(resultlist[pilotname])
                   if bestlist[pilotname]!=9999:
                      besttime = str(bestlist[pilotname])
                   else:
                      besttime = str(resultlist[pilotname])
                      
                   #if 'resultout' not in locals():
                   #   resultout=result
                   #print(i)

                   if len(laplist[pilotname])-1<3:
                      korColor=greenColor
                      
                   else:
                      korColor=redColor
                   graphics.DrawText(offscreen_canvas, fontsmall, 2, ((i+1)*8)-1, textColor, pilotname)
                   graphics.DrawText(offscreen_canvas, fontsmall, 80, ((i+1)*8)-1, korColor, 'KÖR')
                   graphics.DrawText(offscreen_canvas, fontsmall, 66, ((i+1)*8)-1, korColor, str(len(laplist[pilotname])-1))
                   
                   if (blinker<(most-2)):
                      blinker=timer()
                      if blinkColor == greenColor:
                         blinkColor = blackColor
                         resultColor= greenColor
                         resultout = result
                      else:
                         blinkColor = greenColor
                         resultColor= redColor
                         resultout = besttime
                   if blinkColor == greenColor:
                      graphics.DrawText(offscreen_canvas, fontsmall, 28, ((i+1)*8)-1, resultColor, besttime)
                      
                   if blinkColor == blackColor:
                      graphics.DrawText(offscreen_canvas, fontsmall, 28, ((i+1)*8)-1, resultColor, result)
                   
                #print(blinkColor)
                 
                offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
                    
        
        #time.sleep(0.05)
            
        if (stopmeplease):
                print('i have been killed!')
                sys.exit()

    
    
      



