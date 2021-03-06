#!/usr/bin/python3
import socket

# https://shakeelosmani.wordpress.com/2015/04/13/python-3-socket-programming-example/
def Main():
    host = "127.0.0.1"
    port = 5000
     
    mySocket = socket.socket()
    mySocket.bind((host,port))
     
    
    mySocket.listen(1)
    conn, addr = mySocket.accept()
    print ("Connection from: " + str(addr))
    i = 0
    while True:
            data = conn.recv(1024).decode()
            if not data:
                    break
            i += 1
            print ("Message ", i ," from connected  user: " + str(data))
             
            data = str(data).upper()
            print ("sending: " + str(data))
            conn.send(data.encode())
             
    conn.close()
     
if __name__ == '__main__':
    Main()
