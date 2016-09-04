
from gamebot import GameBot

from itertools import product


def neighbours(position):
    x, y = position
    return [((x + d.x, y + d.y), d) for d in GameBot.DIRECTIONS]


class DistanceMap(object):

    def __init__(self, position, not_blocked_positions):
        self.distance = {p: -1 for p in not_blocked_positions}
        self.visited = {p: False for p in not_blocked_positions}
        self.parent = {p: None for p in not_blocked_positions}
        self.explore_positions(position, not_blocked_positions)

    def explore_positions(self, position, not_blocked_positions):
        self.distance[position] = 0
        self.visited[position] = True
        self.parent[position] = None

        to_visit = [position]
        while to_visit:
            u = to_visit.pop(0)
            for p, d in neighbours(u):
                if p in not_blocked_positions and not self.visited[p]:
                    self.distance[p] = self.distance[u] + 1
                    self.visited[p] = True
                    self.parent[p] = (u, d)
                    to_visit.append(p)

    def path_to(self, position):
        path = []
        parent = self.parent[position]
        while parent is not None:
            p, d = parent
            path.insert(0, d)
            parent = self.parent[p]
        return path

    def reacheable(self, position):
        return self.visited[position]

    def reacheables(self):
        return {p for p, visited in self.visited.iteritems() if visited}


def get_blocked_positions(game_map):
    return {p for p, t in game_map.iteritems() if tile_blocked(t)}


def tile_blocked(t):
    return (t.enemies_count > 0 and not t.enemy_hq) \
            or t.own_hq \
            or not t.reachable


def explored_area(position, vision_range=3):
    pos_x, pos_y = position
    area_generator = product(range(-vision_range, vision_range + 1), repeat=2)
    return {(pos_x + x, pos_y + y) for x, y in area_generator}


class Bot(GameBot):

    # Possible directions where a unit can move to
    # self.NW, self.N, self.NE, self.E, self.SE, self.S, self.SW, self.W
    # game_map : Is a python dictionary:
    #  - key = (x, y) that indicates a coordinate. x and y are integers.
    #  - value = a Tile object.
    # Tile object attributes:
    # own_hq: Boolean. Indicates that this tile is our own base
    # enemies_count: Integer. Indicate the amount of enemies in the tile
    # enemy_hq: Boolean. Indicates that the enemy HQ is present in the tile.
    # units: list of units objects currently on that tile.
    # reachable: boolean. Indicates that this tile is not a blocker.
    # x: integer. The x coordinate
    # y: integer. The y coordinate
    # Unit Object attributes:
    # x, y: integers. Analog to the x, y attributes in Tile object.
    # unit_id: integer: Indicates the id of the unit.

    # Usefull methods:
    # self.attack(tile, direction): Attack from one tile in a certain
    # direction. The direction must be one of the possible defined above.
    # self.move(unit, direction): Move a unit from its current
    # position in a certain direction. The direction must be one of the
    # possible defined above. IE: self.move(unit_id, self.N)

    def __init__(self):
        self.enemy_hq_position = None
        self.own_hq_position = None
        self.explored_positions = set()
        self.blocked_positions = set()
        self.frontier = set()
        self.units_tiles = set()

    def find_enemy_hq(self, game_map):
        for tile in game_map.values():
            if tile.enemy_hq:
                return tile.as_tuple()
        return None

    def find_own_hq(self, game_map):
        for tile in game_map.values():
            if tile.own_hq:
                return tile.as_tuple()
        return None

    def move_units_far_away(self, tile, tile_distance_map):
        tile_reacheable_distance_map = tile_distance_map.reacheables()

        reachable_frontier = {p for p in self.frontier
                              if p in tile_reacheable_distance_map}

        next_target_position = \
            min(reachable_frontier,
                key=lambda p: tile_distance_map.distance[p])

        min_path_to_target = tile_distance_map.path_to(next_target_position)
        next_movement = min_path_to_target[0]
        for unit in tile.units:
            self.move(unit, next_movement)

    def update_explored_positions(self, game_map):
        self.units_tiles = set()
        for p, tile in game_map.iteritems():
            if tile.units and p != self.own_hq_position:
                self.units_tiles.add(tile)
                for e_p in explored_area(p):
                    if e_p in game_map:
                        if game_map[e_p].reachable:
                            self.explored_positions.add(e_p)
                        else:
                            self.blocked_positions.add(e_p)
                    else:
                        self.blocked_positions.add(e_p)

        self.frontier = {e for e in self.explored_positions
                         if not all(self.visited(n) for n, _ in neighbours(e))}

    def visited(self, p):
        return p in self.explored_positions or p in self.blocked_positions

    def play(self, player_id, game_map):
        """
        Method were the player can develop its strategy using the player_id
        and the game_map as input.
        """
        if self.enemy_hq_position is None:
            self.enemy_hq_position = self.find_enemy_hq(game_map)

        if self.own_hq_position is None:
            self.own_hq_position = self.find_own_hq(game_map)

        self.update_explored_positions(game_map)

        not_blocked_positions =  \
            self.explored_positions - get_blocked_positions(game_map)

        for tile in self.units_tiles:
            tile_distance_map = DistanceMap(tile.as_tuple(),
                                            not_blocked_positions)
            if self.enemy_hq_position is not None:
                if tile_distance_map.reacheable(self.enemy_hq_position):
                    min_path_to_base = \
                        tile_distance_map.path_to(self.enemy_hq_position)
                    next_movement = min_path_to_base[0]
                    if len(min_path_to_base) == 1:
                        enemy_hq_tile = game_map[self.enemy_hq_position]
                        if enemy_hq_tile.enemies_count == 0:
                            for unit in tile.units:
                                self.move(unit, next_movement)
                        else:
                            self.attack(tile, next_movement)
                    else:
                        for unit in tile.units:
                            self.move(unit, next_movement)
                else:
                    self.move_units_far_away(tile, tile_distance_map)
            else:
                self.move_units_far_away(tile, tile_distance_map)
