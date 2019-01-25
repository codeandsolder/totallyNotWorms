from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket
import hashlib


clients = {}
cInGame = {}

def nameLokup(name):
    for c in clients.values():
        if c.nickname == name:
            return c.launcher.address

class GameController:
    masterName = ""
    slaveName = ""
    #masterHandler
    #slaveHandler
    connected = 0;
    def __init__(self, mN, sN):
        self.masterName = mN
        self.slaveName = sN

games = []

def updateClientList():
    message = "l "
    for c in clients.values():
        if c.available:
            message += c.nickname + "/"
    for c in clients.values():
        c.launcher.sendMessage(message)
    print("Updating the client list:", message)

class ClientData:
    available = False
    nickname = ""
    #gameController
    def __init__(self, launcher, nickname):
        self.nickname = nickname
        self.launcher = launcher

class notWorms(WebSocket):

    def handleMessage(self): #used codes: a,c,n,s,y
        #print(self.address, "sent:", "|" + self.data + "|")#DEBUG
        action = self.data[0]
        argument = self.data[2:]
        if action == "l": #it's a launcher
            tempName = (hashlib.md5(str(self.address).encode('utf-8')).hexdigest())[:5]
            clients[self.address] = ClientData(self, tempName)
            self.sendMessage("t " + tempName)
            print(self.address, 'is a launcher, assigning name:', tempName)
        elif action == "g": #it's a game
            clients[nameLokup(argument)].gameController = self
            myLauncher = clients[nameLokup(argument)]
            cInGame[self.address] = myLauncher
            print(self.address, 'is a game of name:', argument, "launcher:", myLauncher)
            self.sendMessage("hello there")
        if self.address in clients: #message from launcher
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
                clients[nameLokup(argument)].launcher.sendMessage("c " + clients[self.address].nickname)
            elif action == "n": #rejected
                clients[nameLokup(argument)].launcher.sendMessage("n " + clients[self.address].nickname)
            elif action == "y": #accepted
                clients[nameLokup(argument)].launcher.sendMessage("y " + clients[self.address].nickname)
                games.append(GameController[argument,clients[self.address].nickname])
            else:
                print(action, argument)
        elif self.address in cInGame: #message from game
            pass

    def handleConnected(self):
        print(self.address, 'connected')

    def handleClose(self):
        clients.pop(self.address)
        print(self.address, 'closed')

server = SimpleWebSocketServer('', 8000, notWorms)
server.serveforever()