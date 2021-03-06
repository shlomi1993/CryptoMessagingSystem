# Shlomi Ben-Shushan & Ofir Ben-Ezra

import socket, sys, base64
from threading import Thread, Lock
from cryptography.fernet import Fernet
from datetime import datetime
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

# Set buffer.
BUFFER = 8192

# Get arguments
password = sys.argv[1].encode()
salt = sys.argv[2].encode()
port = int(sys.argv[3])

# Generate a symmetric key.
kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
k = Fernet(base64.urlsafe_b64encode(kdf.derive(password)))

# Create a socket, bind and listen.
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', port))
s.settimeout(0.1)
s.listen(5)

# Set print lock.
print_mutex = Lock()

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
    
# This is a client handler function that called for each client in a different thread.
def handleClient(conn):
    conn.settimeout(5)
    data = read(conn)
    if len(data) > 0:
        plaintext = k.decrypt(data).decode()
        time = datetime.now().strftime("%H:%M:%S")
        print_mutex.acquire()
        print(plaintext + " " + time)
        print_mutex.release()
    
# Receiver's operation loop.
while True:
    try:
        conn, addr = s.accept()
        Thread(target=handleClient, args=(conn,)).start()
    except socket.timeout:
        continue
