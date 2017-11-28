import hlt
import custom_helpers.map_manager as mm
import numpy as np
import logging
import scipy.ndimage as nd
import math

import pickle
import time

def move(map_helper, ship_id, target, iterlimit = 10):
    """
    :param mm.MapManager map_helper:    Our very convenient helper
    :param int ship_id:                 The ship to move
    :param hlt.entity.Entity target:    Move towards target
    :return:
    """

    # pickle.dump(map_helper.open_spots, open('zzz.pkl', 'wb'))

    game = map_helper.game
    ship = game.map.get_me().get_ship(ship_id)
    ship_loc = np.array([ship.x, ship.y])

    speed = hlt.constants.MAX_SPEED
    angle = ship.radians_between(target)
    if angle<0:
        angle += 2*np.pi
    # angle_range = 2*np.pi/3

    pts = pts_in_FOV(map_helper, ship, speed)

    ship_pixel = ship_loc / map_helper.scale
    # dx, dy = (pts - ship_pixel).T
    # angles = np.arctan2(dy, dx)
    # angles[angles < angle-np.pi] += 2*np.pi
    #
    # in_right_direction = (angle-angle_range < angles) & (angles < angle+angle_range)
    # pts = pts[in_right_direction]

    targ_loc = np.array([target.x, target.y])
    t_px = targ_loc / map_helper.scale

    dist_to_targ = np.sum((pts-t_px)**2, axis=1)
    order = np.argsort(dist_to_targ)

    pts_actual = pts * map_helper.scale

    checked_set = set([])
    dist, angle = 0, 0
    i=0
    for pt, px_pt in zip(pts_actual[order], pts[order]):
        if map_helper.quick_collision_check(ship_pixel, px_pt):
            continue

        i += 1
        if i>iterlimit:
            logging.info('----------------------HIT ITERLIMIT----------------------')
            pickle.dump((ship, target, map_helper), open('debug.pkl', 'wb'))
            dist = 0
            break

        dx, dy = (pt-ship_loc)
        dist = int(round( np.sqrt(np.sum((pt-ship_loc)**2)) ))
        angle = int(round( (180/np.pi * math.atan2(dy, dx))%360 ))

        if (dist, angle) in checked_set:
            continue
        checked_set.add((dist, angle))
        if dist>7:
            continue

        sim_mov = hlt.entity.MovedShip(ship, dist, angle)
        if not map_helper.check_collision(sim_mov):
            logging.info('iters: {}'.format(i))
            break

    assert dist<=7

    #dist and angle are both integers.
    return dist, angle #angle is now in degrees...

def pts_in_FOV(map_helper, ship, maxdist=hlt.constants.MAX_SPEED):
    """
    :param mm.MapManager map_helper:
    :param hlt.entity.Entity ship:
    :param int maxdist:
    :return:
    """
    movement_range = hlt.entity.Position(ship.x, ship.y)
    movement_range.radius = maxdist

    #Working in px units now.
    big_circ = map_helper.obj2locs(movement_range, buffer=0)
    ship_circ = map_helper.obj2locs(ship, buffer=.6)

    lx, ly = np.amin(big_circ, axis=0)
    ux, uy = np.amax(big_circ, axis=0)+1
    focus_shift = np.array([lx, ly])
    focus_range = (slice(lx, ux), slice(ly, uy))

    big_tup = tuple(map(tuple, (big_circ - focus_shift).T))
    ship_tup = tuple(map(tuple, (ship_circ - focus_shift).T))

    center = np.mean(ship_circ, axis=0).astype(int)

    obstacles = np.full((ux-lx, uy-ly), 0)
    obstacles[big_tup] = map_helper.open_moves[focus_range][big_tup]

    nearby = np.zeros((ux-lx, uy-ly))
    nearby[ship_tup] = map_helper.open_spots[focus_range][ship_tup]

    struct = np.zeros((5,5))
    struct[2] = 1; struct[:,2] = 1; struct[1:4,1:4] = 1

    nearby = nd.binary_dilation(nearby, structure=struct).astype(int)
    obstacles[ship_tup] = nearby[ship_tup]

    if np.all(obstacles[big_tup]==0):
        return big_circ

    objs = tuple(nd.find_objects(obstacles))
    objs = objs[0]

    labeled, n_feat = nd.measurements.label(obstacles[objs], structure=np.ones((3, 3), dtype=int))
    obstacles[objs] = labeled

    poi = []
    thetas = []
    for blob, lab in zip(nd.find_objects(obstacles), range(n_feat)):
        shift = np.array((blob[0].start, blob[1].start))
        block = obstacles[blob]
        block_meat = nd.binary_erosion(block)

        pts = np.argwhere(block-block_meat == lab+1)
        vx, vy = (pts - (center - shift)).T
        angles = np.arctan2(vy, vx)
        a1 = np.argmax(angles)
        a2 = np.argmin(angles)

        poi.append(pts[a1] + shift)
        thetas.append(angles[a1])
        poi.append(pts[a2] + shift)
        thetas.append(angles[a2])

    obstacles += 1
    obstacles[big_tup] -= 1

    poi = np.array(poi)
    for pt, theta in zip(poi, thetas):
        p2 = np.array((math.cos(theta), math.sin(theta))) * maxdist / map_helper.scale
        line = map_helper.pt_in_rect(pt, p2 + center, 1, big_circ)

        l_tup = tuple(map(tuple, (big_circ[line] - focus_shift).T))

        obstacles[l_tup] = 1

    regions, nregion = nd.measurements.label(obstacles == 0)
    x, y = center - focus_shift
    lab = regions[x, y]
    retval = np.argwhere(regions == lab) + focus_shift

    return retval
