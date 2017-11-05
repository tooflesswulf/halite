import hlt
import custom_helpers.map_manager as mm
import numpy as np
import logging

import pickle

def move(map_helper, ship_id, target, iterlimit = 100):
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
    angle_range = 2*np.pi/3

    movement_range = hlt.entity.Position(ship.x, ship.y)
    movement_range.radius = speed

    pts = map_helper.obj2locs(movement_range, buffer=0)
    pt_tup = tuple(map(tuple, pts.T))

    open_spots = map_helper.open_moves[pt_tup] == 0

    pts = pts[open_spots]

    ship_pixel = np.array([ship.x, ship.y]) / map_helper.scale
    angles = np.arctan2(pts[...,1]-ship_pixel[1], pts[...,0]-ship_pixel[0])
    angles[angles < angle-np.pi] += 2*np.pi

    in_right_direction = (angle-angle_range < angles) & (angles < angle+angle_range)
    pts = pts[in_right_direction]

    targ_loc = np.array([target.x, target.y])
    t_px = targ_loc / map_helper.scale

    dist_to_targ = np.sum((pts-t_px)**2, axis=1)
    order = np.argsort(dist_to_targ)

    pts_actual = pts[order] * map_helper.scale


    checked_set = set([])
    dist, angle = 0, 0
    i=0
    for pt, px_pt in zip(pts_actual, pts[order]):
        if map_helper.quick_collision_check(ship_pixel, px_pt):
            continue

        dx, dy = (pt-ship_loc)
        dist = int(round( np.sqrt(np.sum((pt-ship_loc)**2)) ))
        angle = int(round( (180/np.pi * np.arctan2(dy, dx))%360 ))

        if (dist, angle) in checked_set:
            continue
        checked_set.add((dist, angle))

        if dist>7:
            continue

        sim_mov = hlt.entity.MovedShip(ship, dist, angle)
        if not map_helper.check_collision(sim_mov):
            break

        i += 1
        if i>iterlimit:
            logging.info('----------------------HIT ITERLIMIT----------------------')
            break

    #dist and angle are both integers.
    return dist, angle #angle is now in degrees...
