from socket import *
import sys
import time
from datetime import datetime
import select
import math
import matplotlib.pylab as plt
import os
import base64


# Statistics
trans_start_time = 0
trans_end_time = 0
elapsed_time = 0
num_packets = 0
num_bytes = 0
num_retrans = 0
num_lost = 0
#graph
tstime = time.time()
pcktdic={}
repcktdic={}


# Parameters
filename = sys.argv[1]
rec_IP = sys.argv[2]
rec_port = int(sys.argv[3])

win_size = 8
mss = 2048
timeout = 0.001
sen_port = 12000
base = nextSeqnum = 0
recpckt_id = None

senderSocket = socket(AF_INET, SOCK_DGRAM)
#senderSocket.setblocking(0)
senderSocket.bind(('', sen_port))

with open(filename, "rb") as file:
    ff = file.read()
if len(ff) // mss > (2 ** 16) - 1:
    raise Exception('16 bit packet ID is not enough to represent the whole file with the current mss')

trans_start_time = datetime.now()    # Statistics
last_id = math.ceil(len(ff) / mss) - 1  # calculate last packet id to terminate the sending loop

file_id = base64.b64encode(os.urandom(32))[:2]

while recpckt_id != last_id:
    if nextSeqnum < base + win_size and nextSeqnum <= last_id:
        print(f"Sending packet with ID: {nextSeqnum}  |  Time Stamp: {datetime.now().strftime('%H:%M:%S')}")
        segment_byte = nextSeqnum * mss
        if segment_byte + mss >= len(ff):
            trailer = "ffff"
        else:
            trailer = "0000"
        pckt_id = nextSeqnum.to_bytes(2, sys.byteorder)
        data = ff[segment_byte: segment_byte + mss]
        pckt_trailer = bytearray.fromhex(trailer)
        sndpckt = pckt_id + file_id + data + pckt_trailer  # a bytearray with all the data to be sent
        senderSocket.sendto(sndpckt, (rec_IP, rec_port))

        pcktime = time.time() - tstime  # graph
        pcktdic[pcktime] = nextSeqnum  # graph

        num_packets += 1  # Statistics
        num_bytes += len(sndpckt)  # Statistics

        if base == nextSeqnum:  # start timer
            start_time = time.perf_counter()
        nextSeqnum += 1
        
    else:  # receive ack
        ready = select.select([senderSocket], [], [], 0.00001)
        if ready[0]:  # set a timeout for receiving from the server
            ack_pckt, _ = senderSocket.recvfrom(4)  # packet_id and file_id
            recpckt_id = int.from_bytes(ack_pckt[:2], sys.byteorder)
            print(f"Received ACK for packet: {recpckt_id}  |  Time Stamp: {datetime.now().strftime('%H:%M:%S')}")
            last_base = base
            base = recpckt_id + 1  # slide window
            if base == nextSeqnum:
                start_time = 0
            elif last_base != base:  # if the same ack is received don't update the timer
                start_time = time.perf_counter()
        else:
            print('No data found to be received')

    if time.perf_counter() > start_time + timeout:  # if timeout occurs transmit all packets after the last acked
        start_time = time.perf_counter()
        print('Retransmitting Packets')
        for p_id in range(base, nextSeqnum):
            print(f"Resending packet with ID: {p_id}  |  Time Stamp: {datetime.now().strftime('%H:%M:%S')}")
            f_id = 0  # change later
            segment_byte = p_id * mss
            if segment_byte + mss >= len(ff):
                trailer = "ffff"
            else:
                trailer = "0000"
            pckt_id = p_id.to_bytes(2, sys.byteorder)
            file_id = f_id.to_bytes(2, sys.byteorder)
            data = ff[segment_byte: segment_byte + mss]
            pckt_trailer = bytearray.fromhex(trailer)
            sndpckt = pckt_id + file_id + data + pckt_trailer
            senderSocket.sendto(sndpckt, (rec_IP, rec_port))

            pcktime = time.time() - tstime  # graph
            repcktdic[pcktime] = p_id  # graph

            num_retrans += 1    # Statistics
            num_packets += 1  # Statistics
            num_bytes += len(sndpckt)  # Statistics
        num_lost += 1
print("All Packets Sent")

trans_end_time = datetime.now()    # Statistics
elapsed_time = (trans_end_time - trans_start_time).total_seconds()    # Statistics

# Protocol Attack
'''
print("Starting attack")
fakeid=0
while True:
    trailer = "0000"

    data = 10101
    pckt_id = fakeid.to_bytes(2,sys.byteorder)
    file_id = 0
    data = data.to_bytes(2,sys.byteorder)
    pcktfile = file_id.to_bytes(2, sys.byteorder)
    pckttrailer = bytearray.fromhex(trailer)
    sndpckt = pckt_id + pcktfile + data + pckttrailer
    print('Sending fake packet with ID: ', fakeid)
    senderSocket.sendto(sndpckt, (rec_IP, rec_port))
    if fakeid>=65535:
        fakeid=0
    else:
        fakeid += 1
'''

senderSocket.close()


print("\n")
print("===============================================================")
print(f"Statistics:   MSS = {mss},  Window Size = {win_size},  Timeout = {timeout} sec ")
print("===============================================================")
print(f"Transfer Start Time:   Date: {trans_start_time.strftime('%d-%b-%Y')}  |  Time: {trans_start_time.strftime('%H:%M:%S')}")
print(f"Transfer End Time:   Date: {trans_end_time.strftime('%d-%b-%Y')}  |  Time: {trans_end_time.strftime('%H:%M:%S')}")
print(f"Elapsed Time in Seconds:   {'%.2f' % elapsed_time} sec")
print(f"Number of Packets:   {num_packets}")
print(f"Number of Bytes:   {num_bytes}")
print(f"Number of Retransmitted Packets:   {num_retrans}")
print(f"Average Transfer Rate (bytes/sec):   {'%.2f' %(num_bytes / elapsed_time)}")
print(f"Average Transfer Rate (packets/sec):   {'%.2f' %(num_packets / elapsed_time)}")
list1 = sorted(pcktdic.items())
list2 = sorted(repcktdic.items())
x1, y1 = zip(*list1)   # unpack a list of pairs into two tuples
x2, y2 = zip(*list2)
fig = plt.figure()
ax1 = fig.add_subplot(111)
packnums = math.ceil(len(ff)/mss)
ax1.scatter(x1, y1, s=10, c='b', marker="s", label='Sent Packets')
ax1.scatter(x2, y2, s=10, c='r', marker="o", label='Resent Packets')
plt.legend(loc='upper left')
plt.text(0,packnums * 0.7, "Number of retransmissions: "+str(num_retrans)+" packets")
plt.text(0,3*packnums/5,"Window Size: "+str(win_size)+" packets")
plt.text(0,packnums/2,"MSS: "+str(mss)+" bytes")
plt.text(0,2*packnums/5,"Timeout: "+str(timeout)+" seconds")
plt.text(0,packnums/3,"Loss Rate: "+str(int(num_lost/num_packets*100))+" %")
plt.xlabel("Time since transmission started (s)")
plt.ylabel("Packet ID")
plt.show()
