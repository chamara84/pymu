import sys
import os
import time
import datetime
import socket
import re
import signal

from pymu.server import Server
from pymu.client import Client
from pymu.pmuDataFrame import DataFrame
from pymu.pmuLib import *
import pymu.tools as tools
import matplotlib
import numpy as np
import matplotlib.pyplot as plt

import datetime as dt
import matplotlib.animation as animation
from matplotlib.lines import Line2D
import math 

CSV_DIR = "./data"

RUNNING = True

def csvPrint(dFrame, csv_handle):

    strOut = ""
    for i in range(0, len(dFrame.pmus)):
        strOut += dFrame.soc.formatted + ","
        for j in range(0, len(dFrame.pmus[i].phasors)):
            strOut += str(dFrame.pmus[i].phasors[j].deg) + ","
        strOut += str(dFrame.pmus[i].freq) + ","
        strOut += str(dFrame.pmus[i].dfreq)
        if i != (len(dFrame.pmus) - 1):
            strOut += ","
    strOut += "\n"
    print(strOut)
    csv_handle.write(strOut)

def getNextIndex(originalPath):
    splitArr1 = originalPath.split('_')
    nextIndex = -1
    if len(splitArr1) == 2:
        nextIndex = 1
    elif len(splitArr1) > 2:
        splitArr2 = splitArr1[-1].split('.')
        nextIndex = int(splitArr2[0]) + 1

    if nextIndex <= 0:
        print("# Error creating next csv file from '{}'".format(originalPath))
        sys.exit()

    return nextIndex

def createCsvDir():
    global CSV_DIR

    if (not os.path.isdir(CSV_DIR)):
        os.mkdir(CSV_DIR)

def createCsvFile(confFrame):

    createCsvDir()

    stationName = confFrame.stations[0].stn
    prettyDate = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    csvFileName = "{}_{}.csv".format(prettyDate, stationName.rstrip())
    csv_path = "{}/{}".format(CSV_DIR, csvFileName)

    if (os.path.isfile(csv_path)):
        nextIndex = getNextIndex(csv_path)
        csvFileName = "{}_{}.csv".format(prettyDate, nextIndex)
        csv_path = "{}/{}".format(CSV_DIR, csvFileName)

    csv_handle = open(csv_path, 'w')
    csv_handle.write("Timestamp")
    for ch in confFrame.stations[0].channels:
        csv_handle.write(",{}".format(ch.rstrip())) if ch.rstrip() != '' else None
    csv_handle.write(",Freq")
    csv_handle.write(",ROCOF")
    csv_handle.write("\n")

    return csv_handle 

# Create figure for plotting
# Format plot

plt.title('VA angle over time')
plt.ylabel('Time')
fig1, ax1 = plt.subplots()

xs = [(dt.datetime.now()-dt.datetime.utcfromtimestamp(0)).total_seconds()]
ys = [0]

line = Line2D(xs,ys)
ax1.add_line(line)
ax1.set_ylim(-math.pi, math.pi)
ax1.set_xlim(xs[0], 2)

# This function is called periodically from FuncAnimation
def animate(i,dataRcvr,confFrame):

    global xs,ys
    global  fig1,ax1,line
    
    d = tools.getDataSample(dataRcvr,True)
    if d == '':
                return
    dFrame = DataFrame(d, confFrame) # Create dataFrame
    
    xs.append(dFrame.soc.utcSec)
   
    ys.append(dFrame.pmus[0].phasors[3].rad)
    lastt = xs[-1]
    if lastt >= xs[0] + 2.0:  # reset the arrays
            xs = [xs[-1]]
            ys = [ys[-1]]
            ax1.set_xlim(xs[0], xs[0] + 2.0)
            ax1.figure.canvas.draw()
    
    # Add x and y to lists
    
    print("Sec: {}".format(dFrame.soc.utcSec))
    print("Phasor: {}".format(dFrame.pmus[0].phasors[0].rad))
    line.set_data(xs, ys)

    return line,


def runPmuToCsv(ip, tcpPort, frameId, udpPort, index=-1, printInfo = True):
    global RUNNING
    global xs, ys
    print("#{}# Creating Connection\n\t{:<10} {}\n\t{:<10} {}\n\t{:<10} {}".format(index, "IP:", ip, "Port:", tcpPort, "ID Code:", frameId))

    if udpPort > -1:
        print("\t{:<10} {}".format("UDP Port:", udpPort))

    print("----- ----- -----")

    try:
        print("#{}# Reading Config Frame...".format(index)) if printInfo else None
        confFrame = tools.startDataCapture(frameId, ip, tcpPort) # IP address of openPDC
    except Exception as e:
        print("#{}# Exception: {}".format(index, e))
        print("#{}# Config Frame not received...Exiting".format(index))
        sys.exit()

    if confFrame:
        print("#{}# Success!!".format(index)) if printInfo else None
    else:
        print("#{}# Failure!!".format(index)) if printInfo else None

    csv_handle = createCsvFile(confFrame)

    dataRcvr = None

    if udpPort == -1:
        dataRcvr = Client(ip, tcpPort, "TCP")
    else:
        dataRcvr = Server(udpPort, "UDP")

    dataRcvr.setTimeout(10)
    configFrame = None

   

    # force square figure and square axes looks better for polar, IMO
   
    # make a square figure
    fig, axs = plt.subplots(1, 2,subplot_kw={'projection': 'polar'})
   

 
   # ax.plot(theta, r, color='#ee8d18', lw=3)
    
    plt.grid(True)

    axs[0].set_title("Voltage Phasors", fontsize=20)
    axs[1].set_title("Current Phasors", fontsize=20)
  
    
    while configFrame == None:
        tools.requestConfigFrame2(dataRcvr, frameId)
        configFrame = tools.readConfigFrame2(dataRcvr, True)


    
    tools.turnDataOn(dataRcvr, frameId)
    print("#{}# Starting data collection...\n".format(index))# if printInfo else None
    p = 0
    milliStart = int(round(time.time() * 1000))
    
    while RUNNING:
        try:
            d = tools.getDataSample(dataRcvr,True)
            if d == '':
                break
            dFrame = DataFrame(d, confFrame) # Create dataFrame
           #csvPrint(dFrame, csv_handle)
           #This is the line I added:
            VA = axs[0].arrow(0.0, 0.0, dFrame.pmus[0].phasors[0].rad, dFrame.pmus[0].phasors[0].mag, alpha = 0.5, width = 0.015,
                    edgecolor = 'red', facecolor = 'red', lw = 2, zorder = 5)

            # arrow at 45 degree
            VB = axs[0].arrow(0.0,0.0, dFrame.pmus[0].phasors[1].rad, dFrame.pmus[0].phasors[1].mag, alpha = 0.5, width = 0.015,
                    edgecolor = 'blue', facecolor = 'blue', lw = 2, zorder = 5)
            VC = axs[0].arrow(0.0,0.0, dFrame.pmus[0].phasors[2].rad, dFrame.pmus[0].phasors[2].mag, alpha = 0.5, width = 0.015,
                    edgecolor = 'green', facecolor = 'green', lw = 2, zorder = 5)
            

            IA = axs[1].arrow(0.0, 0.0, dFrame.pmus[0].phasors[3].rad, dFrame.pmus[0].phasors[3].mag, alpha = 0.5, width = 0.015,
                    edgecolor = 'red', facecolor = 'red', lw = 2, zorder = 5)

            # arrow at 45 degree
            IB = axs[1].arrow(0.0,0.0, dFrame.pmus[0].phasors[4].rad, dFrame.pmus[0].phasors[4].mag, alpha = 0.5, width = 0.015,
                    edgecolor = 'blue', facecolor = 'blue', lw = 2, zorder = 5)
            IC = axs[1].arrow(0.0,0.0, dFrame.pmus[0].phasors[5].rad, dFrame.pmus[0].phasors[5].mag, alpha = 0.5, width = 0.015,
                    edgecolor = 'green', facecolor = 'green', lw = 2, zorder = 5)
            
            
            # xs.append(dFrame.soc.utcSec)
   
            # ys.append(dFrame.pmus[0].phasors[0].rad)
            
           # animate(1, xs, ys,dFrame)
            
    #         lastt = xs[-1]
    #         if lastt >= xs[0] + 0.02:  # reset the arrays
    #             xs = [xs[-1]]
    #             ys = [ys[-1]]
    #             ax1.set_xlim(xs[0], xs[0] + 2.0)
    #             ax1.figure.canvas.draw()
    
    # # Add x and y to lists
    #         xs.append(dFrame.soc.utcSec)
   
    #         ys.append(dFrame.pmus[0].phasors[0].rad)
    #         print("Sec: {}".format(dFrame.soc.utcSec))
    #         print("Phasor: {}".format(dFrame.pmus[0].phasors[0].rad))
    #         line.set_data(xs, ys)
            
            
            

            
            
            if p == 0:
                print("Data Collection Started...")
                # Set up plot to call animate() function periodically
                ani = animation.FuncAnimation(fig1, animate, fargs=(dataRcvr,confFrame), interval=200, blit=True, save_count=100)
                plt.show()
            p += 1

            
           
           # plt1.show()
            
            
        except KeyboardInterrupt:
            break
            RUNNING = False
        except socket.timeout:
            print("#{}# Data not available right now...Exiting".format(index))
            break
        except Exception as e:
            print("#{}# Exception: {}".format(index, e))
            break
            
    # Print statistics about processing speed
    milliEnd = int(round(time.time() * 1000))
    if printInfo:
        print("")
        print("##### ##### #####")
        print("Python Stats")
        print("----- ----- -----")
        print("Duration:  ", (milliEnd - milliStart)/1000, "s")
        print("Total Pkts:", p);
        print("Pkts/Sec:  ", p/((milliEnd - milliStart)/1000))
        print("##### ##### #####")
    dataRcvr.stop()
    csv_handle.close()

if __name__ == "__main__":
    RUNNING = True
    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print("Usage: python {} <ip> <tcpPort> <frameId> <optional:udpPort>".format(__file__))
        sys.exit()

    ip = sys.argv[1]
    tcpPort = int(sys.argv[2])
    frameId = int(sys.argv[3])
    udpPort = -1
    if len(sys.argv) == 5:
        udpPort = int(sys.argv[4])

    runPmuToCsv(ip, tcpPort, frameId, udpPort, "")


