from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import hashlib


clients = {}

def nameLokup(name):
    for c in clients:
        if c.nickname == name:
            return c.address

class ClientData:
    available = False
    nickname = ""
    def __init__(self, address, nickname):
        self.address = address

class notWorms(WebSocket):

    def handleMessage(self):
        action = self.data[0]
        argument = self.data[2:]
        if action == "n": #set name
            print("name change: ", self.address, argument)
            clients[self.address].nickname == argument
        elif action == "a":
            clients[self.address].available = argument
            print("availability change: ", clients[self.address].nickname, argument)

    def handleConnected(self):
        tempName = (hashlib.md5(str(self.address).encode('utf-8')).hexdigest())
        clients[self.address] = ClientData(self.address, tempName)
        print(self.address, 'connected', tempName)
        self.sendMessage("t " + tempName)

    def handleClose(self):
        clients.pop(self.address)
        print(self.address, 'closed')

server = SimpleWebSocketServer('', 8000, notWorms)
server.serveforever()