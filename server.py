from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import hashlib


clients = {}

def nameLokup(name):
    for c in clients.values():
        if c.nickname == name:
            return c.address

def updateClientList():
    print("Updating the client list!")
    message = "l "
    for c in clients.values():
        if c.available:
            message += c.nickname + "/"
    for c in clients.values():
        print("Sent", message , "to", c.nickname)
        c.handler.sendMessage(message)

class ClientData:
    available = False
    nickname = ""
    def __init__(self, handler, address, nickname):
        self.address = address
        self.nickname = nickname
        self.handler = handler

class notWorms(WebSocket):

    def handleMessage(self): #used codes: a,c,n,s,y
        action = self.data[0]
        argument = self.data[2:]
        if action == "l": #it's a launcher
            tempName = (hashlib.md5(str(self.address).encode('utf-8')).hexdigest())[:5]
            clients[self.address] = ClientData(self, self.address, tempName)
            self.sendMessage("t " + tempName)
            print(self.address, 'is a launcher, assigning name:', tempName)
        if self.address in clients:
            if action == "s": #set name
                print("name change:", self.address, argument)
                clients[self.address].nickname = argument
                updateClientList()
            elif action == "a": #set availability
                clients[self.address].available = (argument == "True")
                print("availability change:", clients[self.address].nickname, argument)
                updateClientList()
            elif action == "c": #challenge
                print("Challenge:", clients[self.address].nickname, self.address, "-->", argument, nameLokup(argument))
                clients[nameLokup(argument)].handler.sendMessage("c " + clients[self.address].nickname)
            elif action == "n": #rejected
                clients[nameLokup(argument)].handler.sendMessage("n " + clients[self.address].nickname)
            elif action == "y": #accepted
                clients[nameLokup(argument)].handler.sendMessage("y " + clients[self.address].nickname)
            else:
                print(action, argument)

    def handleConnected(self):
        print(self.address, 'connected')

    def handleClose(self):
        clients.pop(self.address)
        print(self.address, 'closed')

server = SimpleWebSocketServer('', 8000, notWorms)
server.serveforever()