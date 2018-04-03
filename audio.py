#!/usr/bin/env python3
import atexit
import socket
import sys
import time, datetime
from timeit import default_timer as timer
import threading
import simpleaudio as sa
#import simpleaudio.functionchecks as fc
import pygame
from os import listdir
from os.path import isfile, join
from random import randrange
import subprocess
from subprocess import call
import json

#default 
command = []
print(command)
stopmeplease = False
soundtobeplayed = []
mpcontrol='play'
autodj = False;


#sound
#pass_snd = sa.WaveObject.from_wave_file("/home/pi/sound/pass.wav")
#start_snd = sa.WaveObject.from_wave_file("/home/pi/sound/mstart.wav")
#finish_snd = sa.WaveObject.from_wave_file("/home/pi/sound/mfinish.wav")
#thirty_snd = sa.WaveObject.from_wave_file("/home/pi/sound/m30.wav")
#ten_snd = sa.WaveObject.from_wave_file("/home/pi/sound/m10.wav")
#egyeni_snd = sa.WaveObject.from_wave_file("/home/pi/sound/megyeni.wav")
#osszetett_snd = sa.WaveObject.from_wave_file("/home/pi/sound/mosszetett.wav")
#negykor_snd = sa.WaveObject.from_wave_file("/home/pi/sound/mnegykor.wav")
#haromkor_snd = sa.WaveObject.from_wave_file("/home/pi/sound/mharomkor.wav")
#ketkor_snd = sa.WaveObject.from_wave_file("/home/pi/sound/mketkor.wav")
#egykor_snd = sa.WaveObject.from_wave_file("/home/pi/sound/megykor.wav")
#complete_snd = sa.WaveObject.from_wave_file("/home/pi/sound/mbefejezted.wav")

pygame.init()
pygame.mixer.init()

pass_snd=pygame.mixer.Sound("/home/pi/sound/pass.wav")
start_snd = pygame.mixer.Sound("/home/pi/sound/mstart.wav")
finish_snd = pygame.mixer.Sound("/home/pi/sound/mfinish.wav")
thirty_snd = pygame.mixer.Sound("/home/pi/sound/m30.wav")
ten_snd = pygame.mixer.Sound("/home/pi/sound/m10.wav")
egyeni_snd = pygame.mixer.Sound("/home/pi/sound/megyeni.wav")
osszetett_snd = pygame.mixer.Sound("/home/pi/sound/mosszetett.wav")
negykor_snd = pygame.mixer.Sound("/home/pi/sound/mnegykor.wav")
haromkor_snd = pygame.mixer.Sound("/home/pi/sound/mharomkor.wav")
ketkor_snd = pygame.mixer.Sound("/home/pi/sound/mketkor.wav")
egykor_snd = pygame.mixer.Sound("/home/pi/sound/megykor.wav")
complete_snd = pygame.mixer.Sound("/home/pi/sound/mbefejezted.wav")

pass_snd.set_volume(0.9)
start_snd.set_volume(0.9)
finish_snd.set_volume(0.9)
thirty_snd.set_volume(0.9)
ten_snd.set_volume(0.9)
egyeni_snd.set_volume(0.9)
osszetett_snd.set_volume(0.9)
negykor_snd.set_volume(0.9)
haromkor_snd.set_volume(0.9)
ketkor_snd.set_volume(0.9)
egykor_snd.set_volume(0.9)
complete_snd.set_volume(0.9)





                                  
def playsound (wave_obj):
    play_obj = wave_obj.play()

def frange(start, stop, step):
     i = start
     while i < stop:
         yield i
         i += step    
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
            client.settimeout(5)
            threading.Thread(target = self.listenToClient,args = (client,address)).start()

    def listenToClient(self, client, address):
        global stopmeplease
        global command
        global soundtobeplayed
        global autodj
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

                    if 'autodj' in recmsg:
                               command=[]
                               command.append('autodj')

                    if 'guistatus' in recmsg:
                               command=[]
                               statusreport = ['OK',autodj]
                               #print(statusreport)
                               message = json.dumps(statusreport)
                               client.send(message.encode())
                    

                    if 'shutdown' in recmsg:
                               command=[]
                               call("sudo poweroff", shell=True)
                               
                               message = 'RCV'
                               message = message + '\r\n'
                               client.send(message.encode())

                    if 'reboot' in recmsg:
                               command=[]
                               call("sudo reboot", shell=True)
                               message = 'RCV'
                               message = message + '\r\n'
                               client.send(message.encode())
                               
                    if 'syncmeup' in recmsg:
                            message = str(time.time());
                            message = message + '\r\n'
                            client.send(message.encode())

                    if 'status' in recmsg:
                            ls_output = subprocess.check_output(['iwconfig', 'wlan0'])
                            ls_output = str(ls_output)
                            ls_output = ls_output.split("   ")
                            message = str(ls_output[24])
                            message = message + '\r\n'
                            client.send(message.encode())
                    

                    if "|" in recmsg: 
                            
                            data = recmsg.split("|")
                           
                            #print('pilot', data[2])    
                            
                            if data[0] == 'play':
                               command.append('play')
                               soundtobeplayed.append(data[1])
                    
                            
                    else:
                       raise error('Client disconnected')
                    exitthread = True
            except:
                client.close()
                return False


class mp (threading.Thread):
   def __init__(self, threadID, name, timeout):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.timeout = timeout
   def run(self):
       musicplayer(self.timeout)
       print("Exiting " + self.name)
def musicplayer(timeout):
    global mpcontrol
    global autodj
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.set_volume(0.7)
    #print(mpcontrol + " Vol.: 70%")
    musicfiles = readmusic('music/')
    currentvol = 'highvol'
    while True:
        #print(mpcontrol)
        time.sleep(0.5)
        if not (pygame.mixer.music.get_busy()):
            if autodj:
                pygame.mixer.music.stop()
                if len(musicfiles)==0:
                    musicfiles = readmusic('music/')
                random_index = randrange(0,len(musicfiles))
                
                music = (musicfiles.pop(random_index))
                #print('Ez szól most:' + music)
                musicfile = 'music/' + music
                
                pygame.mixer.music.load(musicfile)
                pygame.mixer.music.play()    
                #print(mpcontrol)
        if (pygame.mixer.music.get_busy()):
                if not autodj:
                     pygame.mixer.music.stop()   
        if mpcontrol == "stop":
            #print(mpcontrol + " Vol.: 0%")
            pygame.mixer.music.stop()
            mpcontrol = "play"
        if mpcontrol == "lowvol" and currentvol =="highvol":
            #print(mpcontrol + " Vol.: 20%")
            for n in range(5):
                vol=1-(n+2)*15/100
                #print(vol)
                pygame.mixer.music.set_volume(vol)
                time.sleep(0.05)
            currentvol = 'lowvol'
            mpcontrol=''
        if mpcontrol == "highvol" and currentvol =="lowvol":
            time.sleep(2)
            #print(mpcontrol + " Vol.: 70%")
            for n in range(5):
                vol=(n+1)*14/100
                #print(vol)
                pygame.mixer.music.set_volume(vol)
                time.sleep(0.5)
            currentvol = 'highvol'
            mpcontrol=''
            
def readmusic(path):
    musicfiles = [f for f in listdir(path) if isfile(join(path, f))]  
    return musicfiles


thread1 = myThread(1, "socketserver", 30)
thread1.daemon = True
thread1.start()
thread2 = mp(2, "musciplayer", 30)
thread2.daemon = True
thread2.start()

basetimer = timer()
while True:
        #print(command)
        timelimit=60
        currenttimer = timer()
        #if (currenttimer-basetimer>timelimit):
            #mpcontrol='stop'
            #basetimer=timer()
        if len(command)>0:
           soundcommand=command.pop()
        else:
           soundcommand=''
        if (soundcommand == 'play'):
            sound_id=soundtobeplayed.pop()
            playsound(eval(sound_id))
            if sound_id=='finish_snd':
                mpcontrol='highvol'
            else:
                mpcontrol='lowvol'
            soundcommand=''
        if (soundcommand == 'autodj'):
            if autodj == False:
                autodj = True
            else:
                autodj = False
            soundcommand=''
       
        time.sleep(0.01)
        if (stopmeplease):
                print('i have been killed!')
                sys.exit() 

