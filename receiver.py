from socket import *
import random
import sys
from datetime import datetime

#Statistics
trans_start_time = 0
trans_end_time = 0
elapsed_time = 0
num_rcvd_packets = 0
num_rcvd_bytes = 0
num_tran_packets = 0
num_tran_bytes = 0
num_retrans = 0


filename = 'received.png'
rec_port = 12000
MSS = 2048
loss_rate = 0.1
seq_no = 0

rec_packet_size = MSS + 6   #MSS + 64 bits (Headers)
dataArr = bytearray()

receiverSocket = socket(AF_INET, SOCK_DGRAM)
receiverSocket.bind(('', rec_port))

while True:
    x = random.uniform(0, 1)
    packet, senderAddress = receiverSocket.recvfrom(rec_packet_size)
    if x >= loss_rate:
        if seq_no == 0:
            trans_start_time = datetime.now()  # Statistics

        num_rcvd_packets += 1  # Statistics
        num_rcvd_bytes += len(packet)  # Statistics

        packetID = packet[:2]
        fileID = packet[2:4]
        data = packet[4:-2]
        trailer = packet[-2:].hex()
        rec_seq_no = int.from_bytes(packetID, sys.byteorder)

        if rec_seq_no == seq_no:
            print(f"Received packet with ID: {seq_no}, Time Stamp: {datetime.now().strftime('%H:%M:%S')}")

            dataArr.extend(data)
            print(f"Sending ACK no: {seq_no}, Time Stamp: {datetime.now().strftime('%H:%M:%S')}")

            receiverSocket.sendto(packetID + fileID, senderAddress)  # Sending Ack
            seq_no += 1

            num_tran_packets += 1  # Statistics
            num_tran_bytes += len(packetID + fileID)  # Statistics

            if trailer == "ffff":
                print(f"All packets are received.")
                break
        else:
            print(f"Received packet no. {rec_seq_no}, while waiting for packet no. {seq_no}.")
            print(f"Discarding packet no. {rec_seq_no}.")
            receiverSocket.sendto((seq_no - 1).to_bytes(2, sys.byteorder) + fileID, senderAddress)  # Sending Ack

            num_tran_packets += 1  # Statistics
            num_tran_bytes += len(seq_no.to_bytes(2, sys.byteorder) + fileID)  # Statistics
            num_retrans += 1  # Statistics
    else:
        loss = int.from_bytes(packet[:2],sys.byteorder)
        print("Packet ", loss, " is lost.")


print(f"Writing data into file: {filename}.")
with open(filename, 'wb') as f:  # write received data to file
    f.write(dataArr)

trans_end_time = datetime.now()    # Statistics
elapsed_time = (trans_end_time - trans_start_time).total_seconds()    # Statistics

receiverSocket.close()


print("\n")
print("=================================================")
print("Statistics: ")
print("=================================================")
print(f"Transfer Start Time:   Date: {trans_start_time.strftime('%d-%b-%Y')}  |  Time: {trans_start_time.strftime('%H:%M:%S')}")
print(f"Transfer End Time:   Date: {trans_end_time.strftime('%d-%b-%Y')}  |  Time: {trans_end_time.strftime('%H:%M:%S')}")
print(f"Elapsed Time in Seconds:   {'%.2f' % elapsed_time} sec")
print(f"Number of Received Packets (Data):   {num_rcvd_packets}")
print(f"Number of Received Bytes (Data):   {num_rcvd_bytes}")
print(f"Number of Transmitted Packets (ACK):   {num_tran_packets}")
print(f"Number of Transmitted Bytes (ACK):   {num_tran_bytes}")
print(f"Number of Lost Packets:   {num_retrans}")
print(f"Average Transfer Rate (bytes/sec):   {'%.2f' %(num_rcvd_bytes / elapsed_time)}")
print(f"Average Transfer Rate (packets/sec):   {'%.2f' %(num_rcvd_packets / elapsed_time)}")
