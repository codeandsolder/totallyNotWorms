"""This is an example on how the autogeometry can be used for deformable 
terrain.
"""
__docformat__ = "reStructuredText"

import sys

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

space = pymunk.Space()

terrain_surface = pygame.Surface((xSize,ySize))
terrain_surface.fill(THECOLORS["white"])
HP_surface = pygame.Surface((xSize,ySize))

def clip(x, floor, ceil):
 return max(min(x, ceil), floor)

explosion_anim = {}
explosion_anim[15] = []
explosion_anim[30] = []


class Explosion(pygame.sprite.Sprite):
    def __init__(self, center, size):
        pygame.sprite.Sprite.__init__(self)
        self.size = size
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
    HP = 100
    def __init__(self, body, size=(10,10), transform=None, radius=0):
        shape = pymunk.Poly.create_box(body, size)
        super().__init__(body, shape.get_vertices(), transform, radius)
        self.color = THECOLORS["red"]
        self.friction = 100
        self.collision_type = COLLTYPE_PLAYER

class PlayerModel:
    def __init__(self, position =  [xSize/2,ySize/4]):
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
        body = makeBomb(self.bodyReference.position,15)
        body._set_velocity((pygame.mouse.get_pos() - self.bodyReference.position)*3)
    def setHP(self, delta):
        self.shape.HP += delta
    def getDistance(self, point):
        return ((self.bodyReference.position[0] - point[0])**2 + (self.bodyReference.position[1] - point[1])**2)**0.5

actors = [PlayerModel(), PlayerModel()]
activeActor = actors[0]
aID = 0;

#def draw_helptext(screen):
#    font = pygame.font.Font(None, 16)
#    text = ["LMB(hold): Draw pink color",
#            "LMB(hold) + Shift: Create balls",
#            "g: Generate segments from pink color drawing",
#            "r: Reset",
#            ]
#    y = 5
#    for line in text:
#        text = font.render(line, 1,THECOLORS["black"])
#        screen.blit(text, (5,y))
#        y += 10

def drawHP(screen):
    font = pygame.font.Font(None, 20)
    for a in actors:
        text = font.render(str(a.shape.HP), 1,THECOLORS["black"])
        screen.blit(text, (a.bodyReference.position[0], a.bodyReference.position[1]-20))

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

def makeBomb(position, size):
    mass = 1
    moment = pymunk.moment_for_circle(mass, 0, 10)
    body = pymunk.Body(mass, moment)
    body.position = position
    shape = Bomb(body, size/5, size)
    shape.friction = .5
    shape.collision_type = COLLTYPE_BOOM
    space.add(body, shape)
    return body

class Bomb(pymunk.Circle): 
    exploded = False
    explosionSize = 30
    def __init__(self, body, radius, size, offset = (0, 0)):
        super().__init__(body, radius, offset)
        self.explosionSize = size
        self.color = THECOLORS["black"]

def BOOM(arbiter, space, data):
    x = arbiter.shapes[0]
    if not x.exploded:
        x.exploded = True
        position = x._get_body()._get_position()
        pygame.draw.circle(terrain_surface, THECOLORS["white"], [int(position[0]), int(position[1])], x.explosionSize)
        generate_geometry(terrain_surface, space)
        for a in actors:
            a.setHP(-int(x.explosionSize*500000.0/(a.getDistance(position)+10)**3.5))
        space.remove(x.body, x)
        expl = Explosion(position, x.explosionSize)
        all_sprites.add(expl)
    return False

def ignore(a,s,d):
    return False

def beginTouching(a,s,d):
    a.shapes[0].numberTouching += 1
    return True

def endTouching(a,s,d):
    a.shapes[0].numberTouching -= 1
    return True

space.add_collision_handler(COLLTYPE_BOOM, COLLTYPE_TERRAIN).pre_solve = BOOM
space.add_collision_handler(COLLTYPE_DEFAULT, COLLTYPE_BOOM).pre_solve = ignore
space.add_collision_handler(COLLTYPE_PLAYER, COLLTYPE_BOOM).pre_solve = ignore
space.add_collision_handler(COLLTYPE_PLAYER, COLLTYPE_TERRAIN).begin = beginTouching
space.add_collision_handler(COLLTYPE_PLAYER, COLLTYPE_TERRAIN).separate = endTouching

def handleInputs():
    global activeActor
    global aID
    global actors
    events = pygame.event.get()
    for event in events:
        if event.type == QUIT or \
            event.type == KEYDOWN and (event.key in [K_ESCAPE, K_q]):  
            sys.exit(0)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and (pygame.key.get_mods() & KMOD_CTRL):
            makeBomb(event.pos, 30)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and (pygame.key.get_mods() & KMOD_SHIFT):       
            activeActor.shoot()           
        elif event.type == KEYDOWN and event.key == K_r:
            terrain_surface.fill(THECOLORS["white"])
            for s in space.shapes:
                if hasattr(s, "generated") and s.generated:
                    space.remove(s)

        elif event.type == KEYDOWN and event.key == K_b:
            aID = (aID + 1)%len(actors)
            activeActor = actors[aID]

        elif event.type == KEYDOWN and event.key == K_g:
            generate_geometry(terrain_surface, space)

        elif event.type == KEYDOWN and event.key == K_p:
            pygame.image.save(screen, "deformable.png")
    
    if pygame.mouse.get_pressed()[0]:
        if pygame.key.get_mods() & KMOD_SHIFT:
            pass
        elif pygame.key.get_mods() & KMOD_CTRL:
            pass
        else:
            color = THECOLORS["pink"] 
            pos =  pygame.mouse.get_pos()
            pygame.draw.circle(terrain_surface, color, pos, 25)

    activeActor.handle()

all_sprites = pygame.sprite.Group()
img_dir = path.join(path.dirname(__file__), 'img')

def main():
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

    for i in range(9):
        filename = 'regularExplosion0{}.png'.format(i)
        img = pygame.image.load(path.join(img_dir, filename)).convert()
        img.set_colorkey(THECOLORS["black"])
        img_lg = pygame.transform.scale(img, (60, 60))
        explosion_anim[30].append(img_lg)
        img_sm = pygame.transform.scale(img, (30, 30))
        explosion_anim[15].append(img_sm)

    fps = 120
    while True:
        handleInputs()
        space.step(1./fps)
        
        screen.fill(THECOLORS["white"])
        screen.blit(terrain_surface, (0,0))
        space.debug_draw(draw_options)
        drawHP(screen)
        all_sprites.update()        
        all_sprites.draw(screen)
        pygame.display.flip()

        clock.tick(fps)
        pygame.display.set_caption("fps: " + str(clock.get_fps()))

if __name__ == '__main__':
    sys.exit(main())
