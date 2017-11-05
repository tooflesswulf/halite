import hlt
import numpy as np
import logging
import pickle

class MapManager():
    def __init__(self, game, grid_spacing=.25):
        """
        :param hlt.networking.Game game:
        :param float spacing:
        """
        self.game = game
        self.map = game.map

        self.w = self.map.width
        self.h = self.map.height

        self.scale = grid_spacing

        self.open_spots = np.zeros((int(self.w / self.scale) + 10, int(self.h / self.scale) + 10))
        self.open_moves = np.zeros((int(self.w / self.scale) + 10, int(self.h / self.scale) + 10))

        self.update()

    def update(self):
        self.map = self.game.map

        self.reset_binary_maps()

    def quick_collision_check(self, from_loc, to_loc):
        x1, y1 = from_loc
        x2, y2 = to_loc

        x1, x2 = sorted((x1, x2))
        y1, y2 = sorted((y1, y2))

        pts = np.mgrid[int(x1-1):int(x2+1), int(y1-1):int(y2+1)].transpose(1,2,0)
        rect = self.pt_in_rect(from_loc, to_loc, 0, pts)

        mask = tuple(map(tuple, pts[rect].T))
        return np.any(self.open_spots[mask] != 0)

    def check_collision(self, ship):
        """
        :param hlt.entity.MovedShip ship: We check whether this ship collides with anything on its path.
        :return bool: Whether we collide or not.
        """


        pts = self.obj2locs(ship)
        pt_tup = tuple(map(tuple, pts.T))

        return np.any(self.open_spots[pt_tup] != 0)

        # cx, cy = ship.x / self.binary_scale, ship.y / self.binary_scale
        # return self.binary_map[int(cx), int(cy)] != 0

    def add_ship(self, ship):
        self.mark_occupied_spots(ship)
        self.mark_invalid_moves(ship)

    def mark_occupied_spots(self, obj):
        pts = self.obj2locs(obj)

        pt_tup = tuple(map(tuple, pts.T))
        self.open_spots[pt_tup] = 1

    def mark_invalid_moves(self, obj):
        pts = self.obj2locs(obj, buffer=hlt.constants.SHIP_RADIUS)

        pt_tup = tuple(map(tuple, pts.T))
        self.open_moves[pt_tup] = 1

    def pt_in_circ(self, center, r, pts):
        orthog_dists = np.abs(pts - center)

        l1 = np.abs(np.dot(orthog_dists, [1, -1]))
        l2 = np.sqrt(2) * (np.amin(orthog_dists, axis=-1) - 1 / 2)  # box width is 1.

        l3 = np.sqrt(l1 ** 2 + l2 * l2 + np.sqrt(2) * l1 * l2)  # Application of law of cosines
        l3[l2 < 0] = np.amax(orthog_dists, axis=-1)[l2 < 0] - 1 / 2

        # l3 is circle squared radius to contact a square centered at <pts> with width 1.
        return l3 <= r

    def pt_in_rect(self, box1, box2, r, pts):
        perp = np.dot([[0,-1],[1,0]], box2 - box1)
        perp = perp / np.sqrt(np.dot(perp, perp)) #normalize perp to mag 1

        proj_axis = np.dot(pts - box1, box2-box1)
        in_bounds = (0 < proj_axis) & (proj_axis < np.dot(box2 - box1, box2-box1))

        line_dists = np.abs(np.dot(pts - box1, perp))

        # A = np.stack((box2-box1, perp), axis=1)
        # Ainv = np.linalg.inv(A)
        #
        # proj_trans = np.dot(np.dot(A, [[0, 0], [0, 1]]), Ainv)
        # perp_projs = np.dot(shifted_pts, proj_trans)

        perp_q1_dir = np.abs(perp)

        box_loss = np.dot(perp_q1_dir, [1/2,1/2]) #box width is 1.

        min_rect_widths = line_dists - box_loss

        return (min_rect_widths <= r) & in_bounds

    def obj2locs(self, obj, buffer=None):
        if buffer is None:
            buffer = 0

        lx, ux, ly, uy = obj.bounding_box(buffer+1)

        px_lx = int(lx/self.scale)
        px_ly = int(ly/self.scale)
        px_ux = int(ux/self.scale)
        px_uy = int(uy/self.scale)

        maxx, maxy = self.open_spots.shape
        xrange = slice(max(px_lx, 0), min(px_ux, maxx))
        yrange = slice(max(px_ly, 0), min(px_uy, maxy))

        xx, yy = np.mgrid[xrange, yrange]
        pts = np.stack([xx, yy], axis=2)

        r = (obj.radius + buffer) / self.scale
        c1 = np.array([obj.x, obj.y], dtype=float) / self.scale
        tot = self.pt_in_circ(c1, r, pts)

        if isinstance(obj, hlt.entity.MovedShip):
            c2 = np.array([obj.prev_loc.x, obj.prev_loc.y], dtype=float) / self.scale

            circ2 = self.pt_in_circ(c2, r, pts)

            body_box = self.pt_in_rect(c2, c1, r, pts)

            tot |= circ2
            tot |= body_box

        return pts[tot]

    def reset_binary_maps(self):
        self.open_spots = np.zeros((int(self.w / self.scale) + 10, int(self.h / self.scale) + 10))
        self.open_moves = np.zeros((int(self.w / self.scale) + 10, int(self.h / self.scale) + 10))

        for planet in self.map.all_planets():
            self.mark_occupied_spots(planet)
            self.mark_occupied_spots(planet)

        for player in self.map.all_players():
            if player.id == self.map.my_id:
                for ship in player.all_ships():
                    self.mark_invalid_moves(ship)
                    if ship.docking_status != ship.DockingStatus.UNDOCKED:
                        self.add_ship(ship)
                continue
            for ship in player.all_ships():
                self.add_ship(ship)

