import sys
import random
import socket
import websocket
from websocket import create_connection, WebSocket

from os import path

import pygame
from pygame.locals import *
from pygame.color import *

import pymunk
from pymunk import Vec2d, BB
import pymunk.pygame_util
import pymunk.autogeometry

import numpy

xSize = 800
ySize = 600
FPS = 120

COLLTYPE_DEFAULT = 0
COLLTYPE_BORDER = 1
COLLTYPE_BOOM = 101
COLLTYPE_TERRAIN = 102
COLLTYPE_PLAYER = 103

TIME_PER_TURN = 20

space = pymunk.Space()
screen = pygame.display.set_mode((xSize,ySize))     #TODO? resizable
bombs = []

terrain_surface = pygame.Surface((xSize,ySize))
HP_surface = pygame.Surface((xSize,ySize))

def clip(x, floor, ceil):
    return max(min(x, ceil), floor)

explosion_anim = {}

all_sprites = pygame.sprite.Group()
img_dir = path.join(path.dirname(__file__), 'img')

class Explosion(pygame.sprite.Sprite): #https://github.com/kidscancode/pygame_tutorials/blob/master/shmup/shmup-10.py
    def __init__(self, center, size):
        pygame.sprite.Sprite.__init__(self)
        self.size = size
        if(self.size not in explosion_anim):
            explosion_anim[self.size] = []
            for i in range(9):
                filename = 'regularExplosion0{}.png'.format(i)
                img = pygame.image.load(path.join(img_dir, filename)).convert()
                img.set_colorkey(THECOLORS["black"])
                imgBuffer = pygame.transform.scale(img, (self.size*2, self.size*2))
                explosion_anim[self.size].append(imgBuffer)
        self.image = explosion_anim[self.size][0]
        self.rect = self.image.get_rect()
        self.rect.center = center
        self.frame = 0
        self.last_update = pygame.time.get_ticks()
        self.frame_rate = 30

    def update(self):
        now = pygame.time.get_ticks()
        if now - self.last_update > self.frame_rate:
            self.last_update = now
            self.frame += 1
            if self.frame == len(explosion_anim[self.size]):
                self.kill()
            else:
                center = self.rect.center
                self.image = explosion_anim[self.size][self.frame]
                self.rect = self.image.get_rect()
                self.rect.center = center

class PlayerBody(pymunk.Poly):
    numberTouching = 0
    def __init__(self, body, size=(10,10), transform=None, radius=0):
        shape = pymunk.Poly.create_box(body, size)
        super().__init__(body, shape.get_vertices(), transform, radius)
        self.color = THECOLORS["red"]
        self.friction = 10
        self.damping = 99
        self.collision_type = COLLTYPE_PLAYER

ended = False

def endGame(winningTeam):
    global winText
    global ended
    ended = True
    font = pygame.font.Font(None, 120)
    winText = font.render("Team {} won!".format(winningTeam), 1,THECOLORS["black"])


def vectorLength(vec):
    return (vec[0]**2 + vec[1]**2)**0.5

def unitVector(vec):
    return vec/vectorLength(vec)

class PlayerModel:
    shot = 0
    HP = 100
    team = 0
    def __init__(self, position =  [xSize/2,ySize/8], team = 0):
        mass = .3
        moment = pymunk.moment_for_box(mass, [0, 10])
        self.bodyReference = pymunk.Body(mass, moment)
        self.bodyReference.position = position
        self.shape = PlayerBody(self.bodyReference)
        self.team = team
        space.add(self.bodyReference, self.shape)
    def getPosition(self):
        return self.bodyReference.position
    def makeMovement(self):
        kP = pygame.key.get_pressed()
        targetForce = [0,0]
        if kP[K_LEFT] or kP[K_a]:
            if self.shape.numberTouching > 0:
                targetForce [0] = -1000;
            else:
                targetForce [0] = -100;
        elif kP[K_RIGHT] or kP[K_d]:
            if self.shape.numberTouching > 0:
                targetForce [0] = 1000;
            else:
                targetForce [0] = 100;
        if (kP[K_UP] or kP[K_w])and self.shape.numberTouching > 0:
            targetForce [1] = -20000;
        self.bodyReference._set_force(targetForce)
        v = self.bodyReference._get_velocity()
        self.bodyReference._set_velocity([clip(v[0], -100, 100), clip(v[1], -270, 400)])
    def handleActive(self):
        self.makeMovement()
    def handleInactive(self):
        if not (self.getPosition()[0] >= 0 and self.getPosition()[0] <= xSize and self.getPosition()[1] >= 0 and self.getPosition()[1] <= ySize):
            self.setHP(-1)
        v = self.bodyReference._get_velocity()
        self.bodyReference._set_velocity([clip(v[0], -2, 2), clip(v[1], -270, 400)])
    def shoot(self):
        global turnRemaining
        mouseOffset = pygame.mouse.get_pos() - self.getPosition()
        mouseVector = unitVector(mouseOffset)
        turnRemaining = min(turnRemaining, 4)
        if activeWeapon == 1 and self.shot == 0:
            velocity = mouseVector*clip(self.getDistance(pygame.mouse.get_pos()), 0, 350)*3
            body = makeMissileR(self.getPosition(),20, 3, velocity)
        if activeWeapon == 2 and self.shot == 0:
            velocity = mouseVector*800
            body = makeGrenadeR(self.getPosition() - [0,2],50, 5, 5, velocity)
        if activeWeapon == 3 and self.shot == 0:
            velocity = mouseVector*500
            body = makeGrenadeR(self.getPosition() - [0,2],10, 2, 5, velocity, True)
        if activeWeapon == 4 and self.shot < 5:
            torchPos = self.getPosition() + mouseVector*10
            pygame.draw.circle(terrain_surface, THECOLORS["white"], [int(torchPos[0]), int(torchPos[1])], 13)
            generate_geometry(terrain_surface, space)
        self.shot += 1
    def modHP(self, delta):
            self.setHP(self.HP + delta)
    def setHP(self, val):
        self.HP = val
        if self.HP <= 0:
            actors[self.team].remove(self)
            self.setColor(THECOLORS["black"])
            if len(actors[self.team]) == 0:
                endGame(1 - self.team)
                return
            aID[1] = 0
            turnRemaining = 0
            updateColors()
    def getDistance(self, point):
        return ((self.getPosition()[0] - point[0])**2 + (self.getPosition()[1] - point[1])**2)**0.5
    def setColor(self, color):
        self.shape.color = color

actors = [[],[]]
def createActor(position, team):
    actors[team].append(PlayerModel(position, team))
aID = [1,0]
activeWeapon = 1
turnRemaining = 3

def updateColors():
    for a in actors[0]:
        a.setColor(THECOLORS["green"])
    for a in actors[1]:
        a.setColor(THECOLORS["red"])
    actors[aID[0]][aID[1]].setColor(THECOLORS["yellow"])

def draw_helptext(screen):
    font = pygame.font.Font(None, 16)
    text = ["Weapons:",
            "1. Bazooka",
            "2. Grenade",
            "3: Cluster Bomb",
            "4: Blowtorch",
            "",
            "Active weapon: {}".format(activeWeapon)
            ]
    y = 5
    for line in text:
        text = font.render(line, 1,THECOLORS["black"])
        screen.blit(text, (5,y))
        y += 10
    

def drawOverlays(screen):
    font = pygame.font.Font(None, 20)
    for t in actors:
        for a in t:
            text = font.render("{:3}".format(str(a.HP)), 1,THECOLORS["black"])
            screen.blit(text, (a.getPosition() - [0,20]))
    for b in bombs:
        time = (b.timeout - (pygame.time.get_ticks() - b.launchTime)/1000.0)
        text = font.render("{:01.1f}".format(time), 1,THECOLORS["black"])
        screen.blit(text, (b._get_body()._get_position() - [0,20]))
    if not ended:
        font = pygame.font.Font(None, 50)
        text = font.render("Turn time remaining: {:01.2f}s".format(turnRemaining), 1,THECOLORS["black"])
        screen.blit(text, (xSize/4,20)) 

def generate_geometry(surface, space):
    for s in space.shapes:
        if hasattr(s, "generated") and s.generated:
            space.remove(s)

    def sample_func(point):
        try:
            p = int(point.x), int(point.y)
            color = surface.get_at(p)
            return color.hsla[2] # use lightness
        except:
            return 0 

    line_set = pymunk.autogeometry.PolylineSet()
    def segment_func(v0, v1):
        line_set.collect_segment(v0, v1)
    
    pymunk.autogeometry.march_soft(
        BB(0,0,xSize - 1,ySize - 1), 250, 250, 92, segment_func, sample_func) #generateBounding

    for polyline in line_set:
        line = pymunk.autogeometry.simplify_curves(polyline, 0.8)
        for i in range(len(line)-1):
            p1 = line[i]
            p2 = line[i+1]
            shape = pymunk.Segment(space.static_body, p1, p2, 2)
            shape.friction = 10
            shape.color = THECOLORS["grey"]
            shape.generated = True
            shape.collision_type = COLLTYPE_TERRAIN
            space.add(shape) 

def makeGrenadeR(position, size, timeout, radius, velocity = [0,0], cluster = False):
    mass = .2
    moment = pymunk.moment_for_circle(mass, 0, size/5)
    body = pymunk.Body(mass, moment)
    body.position = position
    shape = Bomb(body, radius, size, timeout, cluster)
    shape.friction = .5
    bombs.append(shape)
    space.add(body, shape)
    body._set_velocity(velocity)
    return body


def makeMissileR(position, size, radius, velocity = [0,0]):
    mass = 1
    moment = pymunk.moment_for_circle(mass, 0, radius)
    body = pymunk.Body(mass, moment)
    body.position = position
    shape = Bomb(body, radius, size)
    shape.friction = .5
    shape.collision_type = COLLTYPE_BOOM
    space.add(body, shape)
    body._set_velocity(velocity)
    return body
def makeMissile(position, size, velocity = [0,0]):
    return makeMissileR(position, size, size/5, velocity)

class Bomb(pymunk.Circle):
    exploded = False
    afterExplode = []
    def __init__(self, body, radius, size, timeout = 9999, cluster = False):
        super().__init__(body, radius)
        self.explosionSize = size
        self.timeout = timeout
        self.launchTime = pygame.time.get_ticks()
        self.color = THECOLORS["black"]
        self.cluster = cluster

    def clusterSpawn(self):
        position = self._get_body()._get_position()
        for i in range(10):
            size = random.randint(4,6) + random.randint(0,2)
            makeMissileR(position - [0,10],size, size/2, [random.randint(-60,60), random.randint(-420, -200)])
        #makeMissile(position,6, [20,-400])
        #makeMissile(position,6, [0,-420])
        #makeMissile(position,6, [-20,-400])
    def explode(self):
        self.exploded = True
        position = self._get_body()._get_position()
        expl = Explosion(position, self.explosionSize)
        all_sprites.add(expl)
        pygame.draw.circle(terrain_surface, THECOLORS["white"], [int(position[0]), int(position[1])], self.explosionSize)
        generate_geometry(terrain_surface, space)
        if self in bombs:
            bombs.remove(self)
        if(self.cluster):
            self.clusterSpawn()
        try:
            space.remove(self.body, self)
        except:
            pass
        for t in actors:
            for a in t:
                a.modHP(-clip(int(self.explosionSize*200000.0/(clip(a.getDistance(position) - self.explosionSize/1.5, 1, 200000))**4), 0, self.explosionSize*2.5))
    def update(self):
        if (pygame.time.get_ticks() - self.launchTime)/1000 >= self.timeout:
            self.explode()


def BOOM(a,s,d):
    x = a.shapes[0]
    if not x.exploded:
        x.explode()
    return False

def ignore(a,s,d):
    return False

def beginTouchingP(a,s,d):
    a.shapes[0].numberTouching += 1
    a.shapes[1].numberTouching += 1
    return True

def endTouchingP(a,s,d):
    a.shapes[0].numberTouching -= 1
    a.shapes[1].numberTouching -= 1
    return True

def beginTouchingG(a,s,d):
    a.shapes[0].numberTouching += 1
    return True

def endTouchingG(a,s,d):
    a.shapes[0].numberTouching -= 1
    return True


space.add_collision_handler(COLLTYPE_BOOM, COLLTYPE_TERRAIN).pre_solve = BOOM
space.add_collision_handler(COLLTYPE_DEFAULT, COLLTYPE_BOOM).pre_solve = ignore
space.add_collision_handler(COLLTYPE_PLAYER, COLLTYPE_BOOM).pre_solve = ignore
space.add_collision_handler(COLLTYPE_BOOM, COLLTYPE_BOOM).pre_solve = ignore
space.add_collision_handler(COLLTYPE_PLAYER, COLLTYPE_TERRAIN).begin = beginTouchingG
space.add_collision_handler(COLLTYPE_PLAYER, COLLTYPE_TERRAIN).separate = endTouchingG
space.add_collision_handler(COLLTYPE_PLAYER, COLLTYPE_PLAYER).begin = beginTouchingP
space.add_collision_handler(COLLTYPE_PLAYER, COLLTYPE_PLAYER).separate = endTouchingP

def handleExit(events):
    for event in events:
        if event.type == QUIT or event.type == KEYDOWN and (event.key in [K_ESCAPE]):  
            sys.exit(0)

weaponsDict = {K_1:1, K_2:2, K_3:3, K_4:4}

def nextActor():
    global aID
    aID = [aID[0], (aID[1] + 1)%len(actors[aID[0]])]
    updateColors()

def nextTeam():
    global aID
    aID = [(aID[0] + 1)%len(actors), 0]
    aID[1] = random.randint(0, len(actors[aID[0]]) - 1)
    for t in actors:
        for a in t:
            a.shot = 0
    updateColors()

def handleInputs(events):
    global activeWeapon
    if(aID[0] == 0): #player turn
        try:
            actors[aID[0]][aID[1]].handleActive()
        except:
            pass
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not (pygame.key.get_mods() & KMOD_CTRL):
                actors[aID[0]][aID[1]].shoot()

            elif event.type == KEYDOWN and event.key in weaponsDict:
                activeWeapon = weaponsDict[event.key]    

def generateTerrain():
    color = THECOLORS["green"] 
    terrain_surface.fill(THECOLORS["white"])
    pygame.draw.line(terrain_surface, color, (0,ySize-10), (xSize,ySize-10), 20)
    pygame.draw.line(terrain_surface, color, (0,0), (0,ySize), 5)
    pygame.draw.line(terrain_surface, color, (xSize,0), (xSize,ySize), 5)
    for i in range(random.randint(4,7)):
        cSize = random.randint(5, 15)
        coords = [random.randint(0, xSize),random.randint(ySize/3, ySize*2/5)]
        while coords[1] < ySize+100:
            pygame.draw.circle(terrain_surface, color, coords, cSize)
            coords = [coords[0] + random.randint(int(-xSize/16), int(xSize/16)), coords[1] + random.randint(0, int(ySize/18))]
            cSize += random.randint(1, 5)            
    for i in range(random.randint(10,15)):
        cSize = random.randint(3, 10)
        coords = [random.randint(0, xSize),random.randint(ySize*2/3, ySize)]
        while coords[1] < ySize+100:
            pygame.draw.circle(terrain_surface, color, coords, cSize)
            coords = [coords[0] + random.randint(int(-xSize/16), int(xSize/16)), coords[1] + random.randint(0, int(ySize/18))]
            cSize += random.randint(1, 5)
    generate_geometry(terrain_surface, space)

lastCheck = pygame.time.get_ticks()
turnRemaining = 4
def handleTurnTime():
    global turnRemaining
    global turnTime
    global lastCheck
    turnRemaining -= (pygame.time.get_ticks() - lastCheck)/1000.0
    if turnRemaining < 0:
        nextTeam()
        turnRemaining = TIME_PER_TURN
    lastCheck = pygame.time.get_ticks()

def main():
    createActor([xSize*1/7,ySize/5], 0)
    createActor([xSize*2/7,ySize/5], 0)
    createActor([xSize*5/7,ySize/5], 1)
    createActor([xSize*6/7,ySize/5], 1)
    updateColors()
    pygame.init()
    clock = pygame.time.Clock()
    space.gravity = 0,980
    static= [
                pymunk.Segment(space.static_body, (0, -50), (-50, ySize + 50), 5),
                pymunk.Segment(space.static_body, (0, ySize + 50), (xSize + 50, ySize + 50), 5),
                pymunk.Segment(space.static_body, (xSize + 50, ySize + 50), (xSize + 50, -50), 5),
                pymunk.Segment(space.static_body, (-50, -50), (xSize + 50, -50), 5),
                ] 
    for s in static:
        s.collision_type = COLLTYPE_BORDER
    space.add(static)

    def cRemove(arb, space, data):
        s = arb.shapes[0]
        space.remove(s.body, s)
        return False
    space.add_collision_handler(COLLTYPE_DEFAULT, COLLTYPE_BORDER).pre_solve = cRemove
    space.add_collision_handler(COLLTYPE_BOOM, COLLTYPE_BORDER).pre_solve = cRemove

    generateTerrain()

    draw_options = pymunk.pygame_util.DrawOptions(screen)
    pymunk.pygame_util.positive_y_is_up = False #using pygame coordinates
    while True:
        space.step(1./FPS)
        clock.tick(FPS)        
        screen.fill(THECOLORS["white"])
        screen.blit(terrain_surface, (0,0))
        space.debug_draw(draw_options)
        drawOverlays(screen)
        draw_helptext(screen)
        events = pygame.event.get()
        if ended:
            screen.blit(winText, (100, ySize/2-50))
        else:
            for b in bombs:
                b.update()
            for t in range(len(actors)):
                for a in range(len(actors[t])):
                    if t == aID[0] and a == aID[1]:
                        handleInputs(events)
                    else:
                        actors[t][a].handleInactive()
            handleTurnTime()
        all_sprites.update()        
        all_sprites.draw(screen)        
        pygame.display.flip()
        pygame.display.set_caption("fps: " + str(clock.get_fps()))
        handleExit(events)

def debug():
    print(sys.argv)
    global server
    serverAddress = sys.argv[1]
    myName = sys.argv[2]
    server = websocket.create_connection(serverAddress)
    server.send("g " + myName)
    while True:
        result =  server.recv()
        print("Received '%s'" % result)

if __name__ == '__main__':
    #sys.exit(main())
    sys.exit(debug())
