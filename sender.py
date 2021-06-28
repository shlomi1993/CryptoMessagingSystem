# Shlomi Ben-Shushan, 311408264, Ofir Ben-Ezra, 206073488
import socket, sys
import base64
import time
from datetime import datetime
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# TODO: check if argv[1] is exsist with try - maybe in function?
Xname = sys.argv[1]
MESSAGES_FILE_NAME = "messages" + Xname + ".txt"
IPS_FILE_NAME = "ips.txt"
ips = []
ports = []


def loadIPsFile():
    try:
        ipFile = open(IPS_FILE_NAME, "r")
    except IOError:
        print("IPS File Not Found or path incorrect")
        exit(1)

        # start send message flow line by line
    for line in ipFile:
        try:
            ip, port = line.split(' ')
            ip, port = convertIPandPORT(ip, port)
            ips.append(ip)
            ports.append(port)
        except ValueError:
            print("IPS/PORT Problem")
    ipFile.close()

# Convert IP and Port from string to bytes
def convertIPandPORT(ip,port):
    strIpArr = ip.split('.')
    ipArr = [int(str) for str in strIpArr]
    ip = bytes(ipArr)
    port = int(port.rstrip())
    port = (port).to_bytes(2, 'big')
    return ip,port


# Open and read messages file for get all the variables and start the flow
# save all massages details in a tuples of (round,details) in msgList
# and then sort it by round and return it
def handleMessagesFile():
    msgList = []
    try:
        messagesFile = open(MESSAGES_FILE_NAME, "r")
    except IOError:
        # print("Messages File Not Found or path incorrect")
        exit(1)

    # start send message flow line by line
    for line in messagesFile:
        # save msg details in list
        try:
            message, path, round, password, salt, dest_ip, dest_port = line.rsplit(' ', 6)

            # Convert variables
            password = bytes(password, 'utf-8')
            salt = bytes(salt, 'utf-8')
            message = bytes(message, 'utf-8')
            dest_ip, dest_port = convertIPandPORT(dest_ip, dest_port)
            pathList = path.split(',')
            round = int(round)
            msgDetails =[message,pathList,password,salt,dest_ip,dest_port]
            msgList.append((round, msgDetails))

        except ValueError:
            # print("ARGS Problem - exit")
            messagesFile.close()
            exit(1)
    messagesFile.close()
    msgList = sorted(msgList, key=lambda msg: msg[0])  # sort by round of the msg
    return msgList


def handelOneMessage(msgDetails):
    # extract details
    message, pathList, password, salt, dest_ip, dest_port = msgDetails

    # Create symmetric key and Enc the msg with it
    k = genSymmetricKey(password, salt)
    c = k.encrypt(message)

    # Create a msg from destIP||destPort||c
    msg = dest_ip + dest_port + c

    # print("start encrypt msg", msg)

    for mixServer in reversed(pathList):

        pk = handlePKFile(mixServer)
        l = encryptionByKey(pk, msg)
        mixIP = ips[int(mixServer) - 1]  # -1 because ips list start from index 0
        mixPort = ports[int(mixServer) - 1]  # -1 because portss list start from index 0
        msg = mixIP + mixPort + l

    sendMsg(l, mixIP, mixPort)

    return


# read public key from file
def handlePKFile(n):
    # try to load pk2 file
    try:
        pkFileName = 'pk' + n + '.pem'
        pkFile = open(pkFileName, 'rb')
        publicKeyText = pkFile.read()
        pk = load_pem_public_key(publicKeyText, backend = default_backend())
        pkFile.close()
    except IOError:
        # print("PK" + n + " File Not Found or path incorrect")
        exit(1)
    return pk


# Generate symmetric key with the password and salt from the massages file
def genSymmetricKey(password, new_salt):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=new_salt, iterations=100000, backend=default_backend())
    key = base64.urlsafe_b64encode(kdf.derive(password))
    fKey = Fernet(key)
    return fKey


# Encryption the message with Symmetric key
def encryptionByKey(key, message):
    ciphertext = key.encrypt(message,
                             padding.OAEP(
                                 mgf=padding.MGF1(algorithm=hashes.SHA256()),
                                 algorithm=hashes.SHA256(),
                                 label=None)
                             )
    return ciphertext


# Send message to server
def sendMsg(l, ip, port):

    # Parse IP.
    ip = str(ip[0]) + "." + str(ip[1]) + "." + str(ip[2]) + "." + str(ip[3])

    # Parse port.
    port = int(hex(port[0])[2:] + hex(port[1])[2:], 16)

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    msg = l
    adrr = ip, int(port)
    s.connect(adrr)
    s.send(msg)
    s.close()
    return


# Program Flow

start_seconds = datetime.now().strftime("%H:%M:%S").split(":")[2]
currentRound = 0
doing = False
firstTime = 1
loadIPsFile()
msgListSortedByRounds = handleMessagesFile()
maxRound = msgListSortedByRounds[-1][0]

while currentRound <= maxRound:
    time_splitted = datetime.now().strftime("%H:%M:%S").split(":")

    if time_splitted[2] != start_seconds:
        doing = False

    elif doing == False:
        doing = True
        for msg in msgListSortedByRounds:
            # if it is the first msg at the first round, wait 1 sec until the servers is up for sure
            if (msg[0] == 0 and (firstTime == 1)):
                firstTime = 0
                time.sleep(1)
            if (msg[0] == currentRound):
                handelOneMessage(msg[1])
        currentRound += 1