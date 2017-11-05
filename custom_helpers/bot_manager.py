import hlt
import logging
import time
from custom_helpers.map_manager import MapManager as map_helper

class BotSquad():
    def __init__(self, game, del_callback):
        """
        Creates a Squad, which organizes ships and their objectives.
        :param hlt.networking.Game game: game state
        :param function del_callback(bot_id):
        """
        self.game = game

        self.bot_list = set([])
        self.pos = hlt.entity.Position(0, 0)
        self.update_mean_pos()
        self.delete = del_callback
        self.prio = -1

    def update_mean_pos(self):
        if self.is_empty():
            return hlt.entity.Position(0, 0)

        avgx, avgy, i = 0, 0, 0
        for ship_id in self.bot_list:
            ship = self.game.map.get_me().get_ship(ship_id)
            avgx += ship.x
            avgy += ship.y
            i += 1
        self.pos = hlt.entity.Position(avgx/i, avgy/i)

    def update(self):
        self.cull()
        self.update_mean_pos()

    def add_bot(self, bot_id):
        """
        :param int bot_id:
        """
        self.bot_list.add(bot_id)

    def remove_bot(self, bot_id):
        """
        :param int bot_id:
        """
        self.bot_list.remove(bot_id)

    def num_members(self):
        return len(self.bot_list)

    def is_empty(self):
        return not self.bot_list

    def cull(self):
        dead_ids = []
        for ship_id in self.bot_list:
            ship = self.game.map.get_me().get_ship(ship_id)
            if ship is None:
                dead_ids.append(ship_id)

        for ship_id in dead_ids:
            self.delete(ship_id)

    def act(self, command_queue, map_helper):
        for ship_id in self.bot_list:
            ship = self.game.map.get_me().get_ship(ship_id)
            map_helper.add_ship(ship)
        pass


class BotManager():
    def __init__(self, player, game):
        """

        :param hlt.game_map.Player player:
        :param hlt.networking.Game game:
        """
        self.game = game
        self.player = player
        self.all_ships = {}  # Dictionary of all ship ids and which group they're in.

        self.map_helper = map_helper(game)

        self.squads = {-1: BotSquad(game, self.eject)}  #Dictionary of group names and the associated group

        for ship in player.all_ships():
            self.all_ships[ship.id] = -1
            self.squads[-1].add_bot(ship.id)

    def update(self):
        game_map = self.game.map

        self.map_helper.update()

        for ship in game_map.get_me().all_ships():
            if ship.id in self.all_ships:
                continue

            self.all_ships[ship.id] = -1
            self.squads[-1].add_bot(ship.id)

        for squad_name in self.squads.copy():
            squad = self.squads[squad_name]
            squad.update()

    def assign_bot(self, bot_id, to_squad, *args, squad_type=BotSquad):
        """
        :param int bot_id:  which bot to act on
        :param to_squad:    which squad to send to
        :param args:        Args for the class type to instantiate
        :param class squad_type:
        """
        assert bot_id in self.all_ships, 'Bot {} does not exist.'.format(bot_id)
        logging.info('Moved bot {} from {} to group {}'.format(bot_id, self.all_ships[bot_id], to_squad))

        self.eject(bot_id)

        if to_squad not in self.squads:
            self.squads[to_squad] = squad_type(self.game, self.eject, *args)

        self.all_ships[bot_id] = to_squad
        self.squads[to_squad].add_bot(bot_id)

    def eject(self, bot_id):
        group = self.all_ships.pop(bot_id)
        self.squads[group].remove_bot(bot_id)
        if group is not -1 and self.squads[group].num_members() == 0:
            self.squads.pop(group)

    def group_nums(self):
        group_nums = {k: v.num_members() for k, v in self.squads.items()}
        return group_nums

    def queue_commands(self, command_queue):
        t = time.time()

        ordering = sorted([(squad.prio, squad.num_members(), name) for name, squad in self.squads.items()],
                          key=lambda x: (x[0], -x[1]))

        for _, _, name in ordering:
            squad = self.squads[name]
            squad.act(command_queue, self.map_helper)

        logging.info('Total took {}s to queue.'.format(time.time()-t))

