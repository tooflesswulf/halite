import logging

import hlt
from custom_helpers.bot_manager import BotSquad
from custom_helpers.map_manager import MapManager as mp_helper
import custom_helpers.helper_functions as helper

class Docking(BotSquad):
    def __init__(self, game, del_callback, targ_planet):
        self.targ = targ_planet
        super().__init__(game, del_callback)
        self.prio = 0

    def act(self, command_queue, map_helper):
        """
        :param mp_helper map_helper:
        """
        dists = []

        for ship_id in self.bot_list:
            ship = self.game.map.get_me().get_ship(ship_id)
            dists.append((ship.dist_to(self.targ), ship_id))

        for d, ship_id in sorted(dists):
            ship = self.game.map.get_me().get_ship(ship_id)
            if ship.docking_status != ship.DockingStatus.UNDOCKED:
                map_helper.add_ship(ship)
                continue
            if ship.can_dock(self.targ):
                command_queue.append(ship.dock(self.targ))
                map_helper.add_ship(ship)
                continue

            speed, angle = helper.move(map_helper, ship_id,
                                       ship.closest_point_to(self.targ))

            map_helper.add_ship(hlt.entity.MovedShip(ship, speed, angle))
            command_queue.append(ship.thrust(speed, angle))

    def cull(self):
        if self.targ is None or not (self.targ.owner is None or self.targ.owner.id == self.game.map.my_id):
            for ship_id in self.bot_list.copy():
                self.delete(ship_id)
            return

        super().cull()
        if len(self.bot_list) > self.targ.num_docking_spots:
            to_del = len(self.bot_list) - self.targ.num_docking_spots

            dists = []
            ship_ids = []
            for ship_id in self.bot_list:
                ship = self.game.map.get_me().get_ship(ship_id)
                dist = ship.dist_to(self.targ)
                dists.append(dist)
                ship_ids.append(ship_id)

            to_kill = [id for _, id in sorted(zip(dists, ship_ids), reverse=True)][:to_del]

            for k in to_kill:
                self.delete(k)

    def update_max_dist(self):
        self.max_dist = -1
        for ship_id in self.bot_list:
            ship = self.game.map.get_me().get_ship(ship_id)
            dist = ship.dist_to(self.targ)
            if dist > self.max_dist:
                self.max_dist = dist

    def update(self):
        if self.targ is None:
            super().update()
            return
        planet_id = self.targ.id
        self.targ = self.game.map.get_planet(planet_id)
        super().update()
        self.update_max_dist()


nearby_dist = 10
class PlanetAtk(BotSquad):
    def __init__(self, game, del_callback, targ_planet, waypoint):
        """
        :param hlt.networking.Game game:
        :param function del_callback:
        :param hlt.entity.Planet targ_planet:
        """
        self.targ = targ_planet
        super().__init__(game, del_callback)
        self.prio = 5

        self.update_mean_pos()
        self.gather_pt = waypoint

    def change_targ(self, new_targ):
        self.targ = new_targ

    def set_gather(self, pt):
        """
        :param hlt.entity.Position pt:
        """
        self.gather_pt = pt

    def act(self, command_queue, map_helper):
        n_ships = len(self.bot_list)

        if n_ships == 0:
            return

        count_enemy = 0
        enemy = None
        closest_dist = -1
        for player in self.game.map.all_players():
            if player.id == self.game.map.get_me().id:
                continue
            for ship in player.all_ships():
                dist = self.targ.dist_to(ship)
                if dist < nearby_dist:
                    if enemy is None or ship.dist_to(self.pos) < closest_dist:
                        enemy = ship
                        closest_dist = ship.dist_to(self.pos)
                    if ship.docking_status == ship.DockingStatus.UNDOCKED:
                        count_enemy += 1

        count_docked = len(self.targ.all_docked_ships())
        avg_dist = self.pos.dist_to(self.targ)
        enemies = self.targ.all_docked_ships()

        if n_ships < 10 and n_ships < count_enemy + count_docked/12 * avg_dist/hlt.constants.MAX_SPEED:
            targ_spot = self.gather_pt
        else:
            if enemy:
                targ_spot = enemy
            elif enemies:
                targ_spot = enemies[0]
            else:
                targ_spot = self.targ

        for ship_id in self.bot_list:
            ship = self.game.map.get_me().get_ship(ship_id)

            speed, angle = helper.move(map_helper, ship_id,
                                       ship.closest_point_to(targ_spot))
            map_helper.add_ship(hlt.entity.MovedShip(ship, speed, angle))
            command_queue.append(ship.thrust(speed, angle))

    def cull(self):
        super().cull()
        if self.targ is None or self.targ.owner is None or self.targ.owner == self.game.map.get_me().id:
            for ship_id in self.bot_list.copy():
                self.delete(ship_id)

    def update(self):
        if self.targ is None:
            super().update()
            return
        planet_id = self.targ.id
        self.targ = self.game.map.get_planet(planet_id)

        super().update()
        self.gather_pt = self.pos



