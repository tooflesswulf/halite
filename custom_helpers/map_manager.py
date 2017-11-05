import hlt
import numpy as np
import logging

class MapManager():
    def __init__(self, game, spacing=2, detailed_spacing=.25):
        """
        :param hlt.networking.Game game:
        :param float spacing:
        """
        self.game = game
        self.map = game.map

        self.w = self.map.width
        self.h = self.map.height

        # x_partitions = int(self.w/spacing)
        # y_partitions = int(self.h/spacing)
        #
        # self.dxs = np.linspace(0, self.w, x_partitions)
        # self.dys = np.linspace(0, self.h, y_partitions)
        #
        # self.dx = self.dxs[1]
        # self.dy = self.dys[1]

        self.binary_scale = detailed_spacing

        self.update()

    def update(self):
        self.map = self.game.map

        self.reset_binary_img()
        # self.reset_planet_heatmap()
        # self.reset_ship_heatmap()

    def check_collision(self, ship):
        """
        :param hlt.entity.MovedShip ship: We check whether this ship collides with anything on its path.
        :return bool: Whether we collide or not.
        """
        xs, ys = self.obj2locs(ship)
        return np.any(self.binary_map[xs, ys] != 0)

        # cx, cy = ship.x / self.binary_scale, ship.y / self.binary_scale
        # return self.binary_map[int(cx), int(cy)] != 0

    def add_ship(self, ship):
        self.draw_onto_binary_img(ship)
        # self.place_on_map(ship, self.map_ships)

    def draw_onto_binary_img(self, obj, buffer=None):
        locx, locy = self.obj2locs(obj, buffer)

        self.binary_map[locx, locy] = 1

    def pt_in_circ(self, cx, cy, r, xx, yy, fudge=np.sqrt(2)):
        dd_sq = (xx-cx)**2 + (yy-cy)**2
        return dd_sq < (r + fudge)**2

    def pt_in_rect(self, x1, y1, x2, y2, r, xx, yy):
        p1 = np.array([x1, y1])
        p2 = np.array([x2, y2])

        perp = np.array([-(y2-y1), (x2-x1)])

        if np.dot(perp, perp) == 0:
            return np.zeros_like(xx, dtype=bool)

        perp = r * perp / np.sqrt(np.dot(perp, perp))

        pts = np.stack([xx, yy], axis=2)

        ra = p1+perp
        # rb = p1-perp
        # rd = p2+perp

        #https://math.stackexchange.com/questions/190111/how-to-check-if-a-point-is-inside-a-rectangle
        AM_AB = np.dot(pts - ra, -2*perp)
        AM_AD = np.dot(pts - ra, p2 - p1)

        ABAB = 4*r*r
        ADAD = np.dot(p2 - p1, p2 - p1)

        return (0 < AM_AB) & (AM_AB < ABAB) & (0 < AM_AD) & (AM_AD < ADAD)

    # def obj2locs(self, obj, buffer=2*hlt.constants.SHIP_RADIUS):
    def obj2locs(self, obj, buffer=None):
        if buffer is None:
            buffer = .5

        r = (obj.radius + buffer) / self.binary_scale
        cx, cy = obj.x / self.binary_scale, obj.y / self.binary_scale

        xx, yy = np.mgrid[int(cx-r-2):int(cx+r+2), int(cy-r-2):int(cy+r+2)]

        circ = self.pt_in_circ(cx, cy, r, xx, yy)
        tot = circ

        if isinstance(obj, hlt.entity.MovedShip):
            cx2, cy2 = obj.prev_loc.x / self.binary_scale, obj.prev_loc.y / self.binary_scale
            c2 = self.pt_in_circ(cx, cy, r, xx, yy)

            body_box = self.pt_in_rect(cx2, cy2, cx, cy, r, xx, yy)

            tot |= c2
            tot |= body_box
            pass

        return xx[tot], yy[tot]

    def reset_binary_img(self):
        self.binary_map = np.zeros( (int(self.w / self.binary_scale)+10, int(self.h / self.binary_scale)+10) )
        for planet in self.map.all_planets():
            self.draw_onto_binary_img(planet, buffer=2)

        for player in self.map.all_players():
            if player.id == self.map.my_id:
                for ship in player.all_ships():
                    if ship.docking_status != ship.DockingStatus.UNDOCKED:
                        self.draw_onto_binary_img(ship)
                continue
            for ship in player.all_ships():
                self.draw_onto_binary_img(ship)


    # def in_map(self, ix, iy):
    #     assert isinstance(ix, int)
    #     assert isinstance(iy, int)
    #     if ix<0 or iy<0:
    #         return False
    #     if ix>=self.dxs.size or iy>=self.dys.size:
    #         return False
    #     return True
    #
    # def obj_on_point(self, obj, loc):
    #     ix, iy = loc
    #     x, y = self.dxs[ix], self.dys[iy]
    #
    #     dx = abs(obj.x - x)
    #     dy = abs(obj.y - y)
    #
    #     if dx > self.dx/2 + obj.radius: return False
    #     if dy > self.dy/2 + obj.radius: return False
    #
    #     if dx <= self.dx/2: return True
    #     if dy <= self.dy/2: return True
    #
    #     sq_corner_dist = (dx-x/2)**2 + (dy-y/2)**2
    #     return sq_corner_dist <= obj.radius**2
    #
    # def get_neighboring_bins(self, loc, prev_locs):
    #     ix, iy = loc
    #     new_locs = []
    #     for dx, dy in [(-1,0), (0,1), (0,-1), (1,0)]:
    #         nx, ny = ix+dx, iy+dy
    #         if (nx, ny) in prev_locs:
    #             continue
    #         if self.in_map(nx, ny):
    #             prev_locs.add((nx, ny))
    #             new_locs.append((nx, ny))
    #     return new_locs
    #
    # def get_grid_intersections(self, obj):
    #     ix = int(obj.x/self.dx - .5)
    #     iy = int(obj.y/self.dy - .5)
    #
    #     locs = [(ix, iy)]
    #     checked_locs = {(ix, iy)}
    #     while locs:
    #         cur_loc = locs.pop(0)
    #         if self.obj_on_point(obj, cur_loc):
    #             yield cur_loc
    #             locs += self.get_neighboring_bins(cur_loc, checked_locs)
    #
    # def place_on_map(self, obj, img):
    #     for loc in self.get_grid_intersections(obj):
    #         img[loc].add(obj)
    #
    # def reset_planet_heatmap(self):
    #     self.map_planets = np.array( [[set([]) for i in range(self.dxs.size)] for j in range(self.dys.size)] )
    #     for planet in self.map.all_planets():
    #         self.place_on_map(planet, self.map_planets)
    #
    # def reset_ship_heatmap(self):
    #     self.map_ships = np.array( [[set([]) for i in range(self.dxs.size)] for j in range(self.dys.size)] )
    #     for player in self.map.all_players():
    #         if player.id == self.map.my_id:
    #             for ship in player.all_ships():
    #                 if ship.docking_status != ship.DockingStatus.UNDOCKED:
    #                     logging.info('uhh does this even work?')
    #                     self.add_ship(ship)
    #             continue
    #         for ship in player.all_ships():
    #             self.add_ship(ship)
