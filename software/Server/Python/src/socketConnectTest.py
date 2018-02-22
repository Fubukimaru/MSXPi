#!/usr/bin/python3
import socket

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
