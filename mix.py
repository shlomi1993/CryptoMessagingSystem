# Shlomi Ben-Shushan & Ofir Ben-Ezra

import socket, sys, random
from datetime import datetime
from threading import Thread, Lock
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key

# Set buffer.
BUFFER = 8192

# This class defines a Data-Structure that holds deliveries and use them among threads.
class Outbox:
    
    # Outbox's constructor.
    def __init__(self):
        self.deliveries = []     # Each delivery is a touple of [IP, Port, Message]
        self.mutex = Lock()      # Allow only one thread to access deliveries array at a time.

    # This function adds a new delivery while holding other threads from using the deliveries array.
    def addDelivery(self, touple):
        self.mutex.acquire()
        self.deliveries.append(touple)
        self.mutex.release()

    # This function sends all deliveries in a random order while holding other threads from using the deliveries array.
    def sendAllMessages(self):
        self.mutex.acquire()
        while len(self.deliveries) > 0:
            delivery = random.choice(self.deliveries)
            self.deliveries.remove(delivery)
            t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                t.connect((delivery[0], delivery[1]))
                t.send(delivery[2])
            finally:
                t.close()
        self.mutex.release()

# Set activation time.
interval = datetime.now().strftime("%H:%M:%S").split(":")[2]

# Parse the given number.
number = int(sys.argv[1])

# Get IP address and port number.
with open("ips.txt", "r") as ips:
    ip, port = ips.read().split("\n")[number - 1].split(" ")
    
# Load private key.
with open("sk" + str(number) + ".pem", "rb") as skey:
	sk = load_pem_private_key(skey.read(), password = None, backend = default_backend())
    
# Create an instance of Outbox.
outbox = Outbox()

# Open server's socket.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', int(port)))
s.settimeout(0.1)
s.listen(5)    

# This function send all the deliveries each time interval. Each delivery is sent in a different thread.
def sendingThread():
    sending = False
    while True:    
        current = datetime.now().strftime("%H:%M:%S").split(":")[2]
        if current != interval:
            sending = False
        elif sending == False:
            sending = True
            outbox.sendAllMessages()

# This function reads received data in chunks and return the whole data.
def read(conn):    
    data = conn.recv(BUFFER)
    if data:
        while True:
            packet = conn.recv(BUFFER)
            if packet:
                data += packet
            else:
                break
    return data
         
# This is a client handler function that is called for each client in a different thread.
def handleClient(conn):
    conn.settimeout(5)
    data = read(conn)
    if len(data) > 0:            
        plaintext = sk.decrypt(data,
                padding.OAEP(mgf = padding.MGF1(algorithm = hashes.SHA256()),
                    algorithm = hashes.SHA256(),
                    label = None)
                )
        ip = plaintext[:4]
        ip = str(ip[0]) + "." + str(ip[1]) + "." + str(ip[2]) + "." + str(ip[3])
        port = plaintext[4:6]
        port = int(hex(port[0])[2:] + hex(port[1])[2:], 16)
        msg = plaintext[6:]
        outbox.addDelivery([ip, port, msg])
        
# This functions accepts new clients in a loop.
def clientsThread():
    while True:
        try:
            conn, addr = s.accept()
            Thread(target=handleClient, args=(conn,)).start()
        except socket.timeout:
            continue
    
# Activate server's threads.
Thread(target=sendingThread, args=()).start()
Thread(target=clientsThread, args=()).start()
