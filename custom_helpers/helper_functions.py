import hlt
import custom_helpers.map_manager as mm
import numpy as np
import logging

def move(map_helper, ship_id, target):
    """
    :param mm.MapManager map_helper:    Our very convenient helper
    :param int ship_id:                 The ship to move
    :param hlt.entity.Entity target:    Move towards target
    :return:
    """
    game = map_helper.game
    ship = game.map.get_me().get_ship(ship_id)

    speed = hlt.constants.MAX_SPEED
    angle = ship.radians_between(target)
    if angle<0:
        angle += 2*np.pi
    angle_range = 2*np.pi/3

    movement_range = hlt.entity.Position(ship.x, ship.y)
    movement_range.radius = speed

    xx, yy = map_helper.obj2locs(movement_range, buffer=0)

    open_spots = map_helper.binary_map[xx, yy] == 0
    xx = xx[open_spots]
    yy = yy[open_spots]

    shipx_pixel = ship.x / map_helper.binary_scale
    shipy_pixel = ship.y / map_helper.binary_scale
    angles = np.arctan2(yy-shipy_pixel, xx-shipx_pixel)
    angles[angles < angle-np.pi] += 2*np.pi

    in_right_direction = (angle-angle_range < angles) & (angles < angle+angle_range)
    xx = xx[in_right_direction]
    yy = yy[in_right_direction]

    assert(len(xx.shape) == 1)

    tx_px = target.x / map_helper.binary_scale
    ty_px = target.y / map_helper.binary_scale
    dist_to_targ = (xx-tx_px)**2 + (yy-ty_px)**2
    order = np.argsort(dist_to_targ)

    xs, ys = xx[order]*map_helper.binary_scale, yy[order]*map_helper.binary_scale

    dist = hlt.constants.MAX_SPEED
    angle = 0

    for x, y in zip(xs, ys):
        move_to = hlt.entity.Position(x, y)
        dist = int(round(ship.dist_to(move_to)))
        angle = int(round(ship.calculate_angle_between(move_to)))

        sim_mov = hlt.entity.MovedShip(ship, dist, angle)
        if not map_helper.check_collision(sim_mov):
            break

    return dist, angle #angle is now in degrees...
