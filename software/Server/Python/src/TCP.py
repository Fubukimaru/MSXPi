#!/usr/bin/python3
import socket

def openConnection(remoteIP, remotePort, localPort, userTimeout, flags):
    # Passive mode: Open port and listen to connections. (flags bit 0: 1)

    ## Passive connections with unespecified port 
    ## There can be more than passive connection with same port and 0.0.0.0 IP
    ## TODO: Ask Nestor. Allow services on same port?

    ## If localPort 0FFFFh -> Random port that isn't open yet. 
    ## TODO: Check if having Port = 0 uses a random port.
    ## TODO: Asign a port on the range 16384-32767


    # TODO: Support sending data before connection ACTIVE?
    #       If so, we need a buffer to store messages and also claim that it is
    #       allowed in the CAPABILITIES function
    

    # User timeout:
    #   - 1 - 1080 (1s to 18 minutes)
    #   - 0 (Use default timeout)
    #   - 0FFFFh (Infinite)


# https://shakeelosmani.wordpress.com/2015/04/13/python-3-socket-programming-example/
def Main():
    host = "127.0.0.1"
    port = 5000
     
    mySocket = socket.socket()
    #client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    mySocket.connect((host, port))
    print ("Connected to: " + str(host))
    msg = "Hellou!"
    while True:
            count = mySocket.send(msg.encode())
            print ("N. bytes sent: " + str(count))
            print(mySocket.recv(1024).decode())         
    mySocket.close()
     
if __name__ == '__main__':
    Main()
