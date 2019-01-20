"""This is an example on how the autogeometry can be used for deformable 
terrain.
"""
__docformat__ = "reStructuredText"

import sys

import pygame
from pygame.locals import *
from pygame.color import *

import pymunk
from pymunk import Vec2d, BB
import pymunk.pygame_util
import pymunk.autogeometry

import numpy

xSize = 600
ySize = 600

COLLTYPE_DEFAULT = 0
COLLTYPE_BORDER = 1
COLLTYPE_BOOM = 101
COLLTYPE_TERRAIN = 102
#def PlayerModel:


def draw_helptext(screen):
    font = pygame.font.Font(None, 16)
    text = ["LMB(hold): Draw pink color",
            "LMB(hold) + Shift: Create balls",
            "g: Generate segments from pink color drawing",
            "r: Reset",
            ]
    y = 5
    for line in text:
        text = font.render(line, 1,THECOLORS["black"])
        screen.blit(text, (5,y))
        y += 10

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
        BB(0,0,xSize - 1,ySize - 1), 200, 200, 90, segment_func, sample_func) #generateBounding

    for polyline in line_set:
        line = pymunk.autogeometry.simplify_curves(polyline, 0.5)
        #line = polyline
        #print(line)
        #line2 = []
        #oldFit = numpy.polyfit([line[len(line)-1][0], line[0][0], line[1][0]], [line[len(line)-1][1], line[0][1], line[1][1]],2)
        #for i in range(len(line)-2):
        #    #line2.append(line[i])
        #    fit = numpy.polyfit([line[i][0], line[i+1][0], line[i+2][0]], [line[i][1], line[i+1][1], line[i+2][1]],2)
        #    newX = (line[i][0] + line[i+1][0])/2
        #    line2.append(Vec2d(newX,(numpy.polyval(fit, newX) + numpy.polyval(oldFit, newX))/2))
        #    oldFit = fit
        #line2.append(line[len(line)-1])
        #newX = (line[0][0] + line[len(line)-1][0])/2
        #fit = numpy.polyfit([line[len(line)-2][0],line[len(line)-1][0], line[0][0]], [line[len(line)-2][1], line[len(line)-1][1], line[0][1]],2)

        #line = line2
        for i in range(len(line)-1):
            p1 = line[i]
            p2 = line[i+1]
            shape = pymunk.Segment(space.static_body, p1, p2, 1)
            shape.friction = 1000
            shape.color = pygame.color.THECOLORS["black"]
            shape.generated = True
            shape.collision_type = COLLTYPE_TERRAIN
            space.add(shape) 


def main():
    pygame.init()
    screen = pygame.display.set_mode((xSize,ySize),HWSURFACE|DOUBLEBUF|RESIZABLE)
    clock = pygame.time.Clock()
    
    space = pymunk.Space()   
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

    terrain_surface = pygame.Surface((xSize,ySize))
    terrain_surface.fill(pygame.color.THECOLORS["white"])


    color = pygame.color.THECOLORS["pink"] 
    #pygame.draw.circle(terrain_surface, color, (450,120), 100)
    #generate_geometry(terrain_surface, space)
    #for x in range(25):
    #    mass = 1
    #    moment = pymunk.moment_for_circle(mass, 0, 10)
    #    body = pymunk.Body(mass, moment)
    #    body.position = 450, 120
    #    shape = pymunk.Circle(body, 10)
    #    shape.friction = .5
    #    space.add(body, shape)


    draw_options = pymunk.pygame_util.DrawOptions(screen)
    pymunk.pygame_util.positive_y_is_up = False #using pygame coordinates

    fps = 120

    class Bomb(pymunk.Circle):
        def __init__(self, body, radius, offset = (0, 0)):
            super().__init__(body, radius, offset)
        exploded = 0

    def BOOM(arbiter, space, data):
        x = arbiter.shapes[0]
        if not x.exploded:
            x.exploded = 1
            position = x._get_body()._get_position()
            color = pygame.color.THECOLORS["white"]
            pygame.draw.circle(terrain_surface, color, [int(position[0]), int(position[1])], 30)
            generate_geometry(terrain_surface, space)
        space.remove(x.body, x)
        return(False)

    def ignore(a,s,d):
        return False

    space.add_collision_handler(COLLTYPE_BOOM, COLLTYPE_TERRAIN).pre_solve = BOOM
    space.add_collision_handler(COLLTYPE_DEFAULT, COLLTYPE_BOOM).pre_solve = ignore

    while True:
        events = pygame.event.get()
        #print(events)
        for event in events:
            if event.type == QUIT or \
                event.type == KEYDOWN and (event.key in [K_ESCAPE, K_q]):  
                sys.exit(0)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and (pygame.key.get_mods() & KMOD_CTRL): #mouse clicked while holding ctrl
                mass = 1
                moment = pymunk.moment_for_box(mass, [0, 10])
                body = pymunk.Body(mass, moment)
                body.position = event.pos
                shape = Bomb(body, 10)
                shape.friction = .5
                shape.collision_type = COLLTYPE_BOOM
                space.add(body, shape)
            elif event.type == KEYDOWN and event.key == K_r:
                terrain_surface.fill(pygame.color.THECOLORS["white"])
                for s in space.shapes:
                    if hasattr(s, "generated") and s.generated:
                        space.remove(s)

            elif event.type == KEYDOWN and event.key == K_b:
                for s in space.shapes:
                    print(s, hasattr(s, "generated"))

            elif event.type == KEYDOWN and event.key == K_g:
                generate_geometry(terrain_surface, space)

            elif event.type == KEYDOWN and event.key == K_p:
                pygame.image.save(screen, "deformable.png")
        
        if pygame.mouse.get_pressed()[0]:
            if pygame.key.get_mods() & KMOD_SHIFT:
                mass = 1
                moment = pymunk.moment_for_box(mass, [0, 10])
                body = pymunk.Body(mass, moment)
                body.position = event.pos
                #shape = pymunk.Circle(body, 10)
                shape = pymunk.Poly.create_box(body)
                shape.friction = .5
                space.add(body, shape)                
            elif pygame.key.get_mods() & KMOD_CTRL:
                pass
            else:
                color = pygame.color.THECOLORS["pink"] 
                pos =  pygame.mouse.get_pos()
                pygame.draw.circle(terrain_surface, color, pos, 25)

        space.step(1./fps)
        
        screen.fill(pygame.color.THECOLORS["white"])
        screen.blit(terrain_surface, (0,0))
        space.debug_draw(draw_options)
        draw_helptext(screen)
        pygame.display.flip()

        clock.tick(fps)
        pygame.display.set_caption("fps: " + str(clock.get_fps()))

if __name__ == '__main__':
    sys.exit(main())
