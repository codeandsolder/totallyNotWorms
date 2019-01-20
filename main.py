"""This is an example on how the autogeometry can be used for deformable 
terrain.
"""
__docformat__ = "reStructuredText"

import sys
import random

from os import path

import pygame
from pygame.locals import *
from pygame.color import *

import pymunk
from pymunk import Vec2d, BB
import pymunk.pygame_util
import pymunk.autogeometry

xSize = 800
ySize = 600

COLLTYPE_DEFAULT = 0
COLLTYPE_BORDER = 1
COLLTYPE_BOOM = 101
COLLTYPE_TERRAIN = 102
COLLTYPE_PLAYER = 103
FPS = 120

space = pymunk.Space()
bombs = []

terrain_surface = pygame.Surface((xSize,ySize))
terrain_surface.fill(THECOLORS["white"])
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
        self.friction = 100
        self.collision_type = COLLTYPE_PLAYER

class PlayerModel:
    HP = 100
    team = 0
    def __init__(self, position =  [xSize/2,ySize/4], team = 0):
        mass = .3
        moment = pymunk.moment_for_box(mass, [0, 10])
        self.bodyReference = pymunk.Body(mass, moment)
        self.bodyReference.position = position
        self.shape = PlayerBody(self.bodyReference)
        space.add(self.bodyReference, self.shape)
    def makeMovement(self):
        keys_pressed = pygame.key.get_pressed()
        targetForce = [0,0]
        if keys_pressed[pygame.K_LEFT]:
            if self.shape.numberTouching > 0:
                targetForce [0] = -1000;
            else:
                targetForce [0] = -100;
        elif keys_pressed[pygame.K_RIGHT]:
            if self.shape.numberTouching > 0:
                targetForce [0] = 1000;
            else:
                targetForce [0] = 100;
        if keys_pressed[pygame.K_UP] and self.shape.numberTouching > 0:
            targetForce [1] = -20000;
        self.bodyReference._set_force(targetForce)
        v = self.bodyReference._get_velocity()
        self.bodyReference._set_velocity([clip(v[0], -100, 100), clip(v[1], -270, 400)])
    def handle(self):
        self.makeMovement()
    def shoot(self):
        if activeWeapon == 1:
            velocity = (pygame.mouse.get_pos() - self.bodyReference.position)*3
            body = makeMissileR(self.bodyReference.position,10, 3, velocity)
        if activeWeapon == 2:
            velocity = (pygame.mouse.get_pos() - self.bodyReference.position)/self.getDistance(pygame.mouse.get_pos())*500
            body = makeGrenadeR(self.bodyReference.position - [0,20],40, 2, 5, velocity)
        if activeWeapon == 3:
            velocity = (pygame.mouse.get_pos() - self.bodyReference.position)/self.getDistance(pygame.mouse.get_pos())*500
            body = makeGrenadeR(self.bodyReference.position - [0,20],15, 2, 5, velocity, True)
    def modHP(self, delta):
        self.HP += delta
    def setHP(self, val):
        self.HP = val
    def getDistance(self, point):
        return ((self.bodyReference.position[0] - point[0])**2 + (self.bodyReference.position[1] - point[1])**2)**0.5
    def setColor(self, color):
        self.shape.color = color

actors = []
def createActor(position, team):
    while len(actors) <= team:
        actors.append([])
    actors[team].append(PlayerModel(position, team)) 
aID = [0,0]
activeWeapon = 1

def updateColors():    
    for t in actors:
        for a in t:
            a.setColor(THECOLORS["red"])
    for a in actors[aID[0]]:
            a.setColor(THECOLORS["green"])
    actors[aID[0]][aID[1]].setColor(THECOLORS["yellow"])

def draw_helptext(screen):
    font = pygame.font.Font(None, 16)
    text = ["Weapons:",
            "1. Bazooka",
            "2. Grenade",
            "3: Cluster Bomb",
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
            text = font.render(str(a.HP), 1,THECOLORS["black"])
            screen.blit(text, (a.bodyReference.position - [0,20]))
    for b in bombs:
        time = (b.timeout - (pygame.time.get_ticks() - b.launchTime)/1000.0)
        text = font.render("{:01.1f}".format(time), 1,THECOLORS["black"])
        screen.blit(text, (b._get_body()._get_position() - [0,20]))

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
        BB(0,0,xSize - 1,ySize - 1), 200, 200, 92, segment_func, sample_func) #generateBounding

    for polyline in line_set:
        line = pymunk.autogeometry.simplify_curves(polyline, 0.8)
        for i in range(len(line)-1):
            p1 = line[i]
            p2 = line[i+1]
            shape = pymunk.Segment(space.static_body, p1, p2, 1)
            shape.friction = 1
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
            makeMissileR(position - [0,10],10, 3, [random.randint(-60,60), random.randint(-420, -200)])
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
        for t in actors:
            for a in t:
                a.modHP(-clip(int(self.explosionSize*300000.0/a.getDistance(position)**4), 0, self.explosionSize*5))
        if self in bombs:
            bombs.remove(self)
        if(self.cluster):
            self.clusterSpawn()
        try:
            space.remove(self.body, self)
        except:
            pass
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

def handleInputs():
    global aID
    global actors
    global activeWeapon
    events = pygame.event.get()
    for event in events:
        if event.type == QUIT or \
            event.type == KEYDOWN and (event.key in [K_ESCAPE, K_q]):  
            sys.exit(0)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not (pygame.key.get_mods() & KMOD_CTRL):
            actors[aID[0]][aID[1]].shoot()
        #elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and (pygame.key.get_mods() & KMOD_SHIFT):       
        #    actors[aID[0]][aID[1]].shoot()           
        elif event.type == KEYDOWN and event.key == K_r:
            terrain_surface.fill(THECOLORS["white"])
            for s in space.shapes:
                if hasattr(s, "generated") and s.generated:
                    space.remove(s)

        elif event.type == KEYDOWN and event.key == K_TAB:
            aID = [aID[0], (aID[1] + 1)%len(actors[aID[0]])]
            updateColors()

        elif event.type == KEYDOWN and event.key == K_e:
            for a in actors:
                a.setHP(100)

        elif event.type == KEYDOWN and event.key == K_k:
            createActor(pygame.mouse.get_pos(), 0)

        elif event.type == KEYDOWN and event.key == K_l:
            createActor(pygame.mouse.get_pos(), 1)
       
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and (pygame.key.get_mods() & KMOD_CTRL):
            generate_geometry(terrain_surface, space)

        elif event.type == KEYDOWN and event.key == K_1:
            activeWeapon = 1

        elif event.type == KEYDOWN and event.key == K_2:
            activeWeapon = 2

        elif event.type == KEYDOWN and event.key == K_3:
            activeWeapon = 3
    
    if pygame.mouse.get_pressed()[0]:
        #if pygame.key.get_mods() & KMOD_SHIFT:
        #    pass
        if pygame.key.get_mods() & KMOD_CTRL:
            color = THECOLORS["pink"] 
            pos =  pygame.mouse.get_pos()
            pygame.draw.circle(terrain_surface, color, pos, 20)
        else:
        #    actors[aID[0]][aID[1]].shoot()
            pass

    actors[aID[0]][aID[1]].handle()

def main():
    global actors
    global aID
    createActor([xSize*1/7,ySize/5], 0)
    createActor([xSize*2/7,ySize/5], 0)
    createActor([xSize*5/7,ySize/5], 1)
    createActor([xSize*6/7,ySize/5], 1)
    updateColors()
    pygame.init()
    screen = pygame.display.set_mode((xSize,ySize))     #TODO? resizable
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
    color = THECOLORS["pink"] 
    pygame.draw.line(terrain_surface, color, (0,ySize*3/4), (xSize,ySize*3/4), 100)
    generate_geometry(terrain_surface, space)


    draw_options = pymunk.pygame_util.DrawOptions(screen)
    pymunk.pygame_util.positive_y_is_up = False #using pygame coordinates
    while True:
        handleInputs()
        space.step(1./FPS)
        
        screen.fill(THECOLORS["white"])
        screen.blit(terrain_surface, (0,0))
        space.debug_draw(draw_options)
        drawOverlays(screen)
        draw_helptext(screen)
        for b in bombs:
            b.update()
        all_sprites.update()        
        all_sprites.draw(screen)
        pygame.display.flip()

        clock.tick(FPS)
        pygame.display.set_caption("fps: " + str(clock.get_fps()))

if __name__ == '__main__':
    sys.exit(main())
