import logging

import hlt
from custom_helpers import bot_types
from custom_helpers.bot_manager import BotManager
import pickle

game = hlt.Game("Goonsquad")
# Then we print our start message to the logs
logging.info("Start")

my_manager = BotManager(game.map.get_me(), game)


def planet_weights(entity):
    planet_ids = []
    weights = []
    for planet in game.map.all_planets():
        planet_ids.append(planet.id)
        if planet.owner is None:
            weights.append(.6 * planet.dist_to(entity))
            continue
        weights.append(planet.dist_to(entity))


    s_dists, s_ids = zip(*sorted(zip(weights, planet_ids)))
    return zip(s_ids, s_dists)

def is_free_targ(planet):
    return planet.owner is None or planet.owner.id == me

i=0
while True:
    game_map = game.update_map()
    my_manager.update()
    me = game_map.my_id

    command_queue = []

    counts = my_manager.group_nums()

    logging.info('Turn {}'.format(i))
    i += 1
    logging.info('Total ships: {}'.format(len(game_map.get_me().all_ships())))
    # logging.info('squads: {}'.format(counts))

    for bot_id in my_manager.squads[-1].bot_list.copy():
        bot = game_map.get_me().get_ship(bot_id)
        for planet_id, dist in planet_weights(bot):
            planet = game_map.get_planet(planet_id)

            if is_free_targ(planet):
                if planet.is_full():
                    continue
                groupname = 'settle_%d' % planet.id
                if groupname not in counts or counts[groupname] < planet.num_docking_spots:
                    pass
                elif my_manager.squads[groupname].max_dist < dist:
                    continue
                my_manager.assign_bot(bot_id, groupname, planet, squad_type=bot_types.Docking)
                break
            else:
                groupname = 'atk_%d' % planet.id
                waypoint = hlt.entity.Position(bot.x, bot.y)

                my_manager.assign_bot(bot_id, groupname, planet, waypoint, squad_type=bot_types.PlanetAtk)
                break

    atk_squads = [(squad.num_members(), name) for name, squad in my_manager.squads.items() if isinstance(squad, bot_types.PlanetAtk)]
    if len(atk_squads) > 3:
        atk_squads.sort()
        add_to_name = atk_squads[-1][1]
        while(len(atk_squads) > 2):
            squad_name = atk_squads.pop(0)[1]
            for ship_id in my_manager.squads[squad_name].bot_list.copy():
                my_manager.assign_bot(ship_id, add_to_name)

    my_manager.queue_commands(command_queue)

    # logging.info('Commands: {}'.format(command_queue))

    # if i>50:
    #     pickle.dump(my_manager.map_helper, open('map_utils.pkl','wb'))

    game.send_command_queue(command_queue)

