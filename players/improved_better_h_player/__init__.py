# ===============================================================================
# Imports
# ===============================================================================

import abstract
from utils import MiniMaxWithAlphaBetaPruning, INFINITY, run_with_limited_time, ExceededTimeError
from checkers.consts import EM, PAWN_COLOR, KING_COLOR, OPPONENT_COLOR, MAX_TURNS_NO_JUMP, BLACK_PLAYER, RED_PLAYER, \
    MY_COLORS, OPPONENT_COLORS, BK, RK
import time
from collections import defaultdict

# ===============================================================================
# Globals
# ===============================================================================

PAWN_WEIGHT = 2
KING_WEIGHT = 3
CENTER = 0.7
BACK_LINE = 0.9
ATTACKED = -2
RUN_AWAY_KING = -1
KING_ATTACK = 4


# ===============================================================================
# Player
# ===============================================================================

class Player(abstract.AbstractPlayer):

    def __init__(self, setup_time, player_color, time_per_k_turns, k):
        abstract.AbstractPlayer.__init__(self, setup_time, player_color, time_per_k_turns, k)
        self.clock = time.process_time()

        # We are simply providing (remaining time / remaining turns) for each turn in round.
        # Taking a spare time of 0.05 seconds.
        self.turns_remaining_in_round = self.k
        self.time_remaining_in_round = self.time_per_k_turns
        # Percents for splitting the time for each depth
        self.split_time_array = [0.05, 0.1, 0.15, 0.19, 0.25, 0.26]
        self.time_for_current_move = self.time_remaining_in_round / self.turns_remaining_in_round - 0.05
        self.curr_board = None  # save the current game board

    def get_move(self, game_state, possible_moves):
        self.clock = time.process_time()
        self.time_for_current_move = self.time_remaining_in_round / self.turns_remaining_in_round - 0.05
        if len(possible_moves) == 1:  # update time and turns
            if self.turns_remaining_in_round == 1:
                self.turns_remaining_in_round = self.k
                self.time_remaining_in_round = self.time_per_k_turns
            else:
                self.turns_remaining_in_round -= 1
                self.time_remaining_in_round -= (time.process_time() - self.clock)
            self.curr_board = game_state.board  # save game board
            return possible_moves[0]

        current_depth = 1
        prev_alpha = -INFINITY

        # Choosing an arbitrary move in case Minimax does not return an answer:
        best_move = possible_moves[0]

        # Initialize Minimax algorithm, still not running anything
        minimax = MiniMaxWithAlphaBetaPruning(self.utility, self.color, self.no_more_time,
                                              self.selective_deepening_criterion)

        # Iterative deepening until the time runs out.
        while True:
            time_for_current_depth: float
            print('going to depth: {}, remaining time: {}, prev_alpha: {}, best_move: {}'.format(
                current_depth,
                current_depth,
                self.time_for_current_move - (time.process_time() - self.clock),
                prev_alpha,
                best_move))
            # The array is init for 6 depth (the average depth) if he succeeded more than that give the remain time
            if current_depth - 1 > 5:
                time_for_current_depth = self.time_for_current_move - (time.process_time() - self.clock)
            else:
                # Deeper in the tree get more time (see array values)
                time_for_current_depth = self.time_for_current_move * self.split_time_array[current_depth - 1]
            try:
                (alpha, move), run_time = run_with_limited_time(
                    minimax.search, (game_state, current_depth, -INFINITY, INFINITY, True), {},
                    time_for_current_depth)
            except (ExceededTimeError, MemoryError):
                print('no more time, achieved depth {}'.format(current_depth))
                break

            if self.no_more_time():
                print('no more time')
                break

            prev_alpha = alpha
            best_move = move

            if alpha == INFINITY:
                print('the move: {} will guarantee victory.'.format(best_move))
                break

            if alpha == -INFINITY:
                print('all is lost')
                break

            current_depth += 1

        if self.turns_remaining_in_round == 1:
            self.turns_remaining_in_round = self.k
            self.time_remaining_in_round = self.time_per_k_turns
        else:
            self.turns_remaining_in_round -= 1
            self.time_remaining_in_round -= (time.process_time() - self.clock)
        self.curr_board = game_state.board  # save game board
        return best_move

    # check if the given location is in the center of the board
    @staticmethod
    def is_in_center(loc):
        middle = [(3, 3), (3, 5), (4, 2), (4, 4)]
        if loc in middle:
            return True
        return False

    # check if the given location is in the back line, depending on its player color
    @staticmethod
    def is_in_back_line(loc, loc_val, player_color):
        if loc_val in KING_COLOR.values():
            return False
        x, y = loc[0], loc[1]
        if player_color == BLACK_PLAYER:
            if x == 7 and (y == 1 or y == 3 or y == 5):
                return True
        if player_color == RED_PLAYER:
            if x == 0 and (y == 2 or y == 4 or y == 6):
                return True

    # check if the move will put us in a vulnerable position (ATTACKED value < 0)
    @staticmethod
    def attacked(loc, board, loc_val):
        x, y = loc[0], loc[1]
        if loc_val in MY_COLORS[RED_PLAYER]:  # RP or RK
            try:  # attacked from front
                if board[(x + 1, y + 1)] in OPPONENT_COLORS[RED_PLAYER] and board[(x - 1, y - 1)] == EM:
                    return True
                if board[(x + 1, y - 1)] in OPPONENT_COLORS[RED_PLAYER] and board[(x - 1, y + 1)] == EM:
                    return True
                # attacked from back (only a king can attack from the back):
                if board[(x - 1, y + 1)] == BK and board[(x + 1, y - 1)] == EM:
                    return True
                if board[(x - 1, y - 1)] == BK and board[(x + 1, y + 1)] == EM:
                    return True
            except KeyError:
                error = 'out of board'
        elif loc_val in MY_COLORS[BLACK_PLAYER]:  # BP or BK
            try:  # attacked from front
                if board[(x - 1, y + 1)] in OPPONENT_COLORS[BLACK_PLAYER] and board[(x + 1, y - 1)] == EM:
                    return True
                if board[(x - 1, y - 1)] in OPPONENT_COLORS[BLACK_PLAYER] and board[(x + 1, y + 1)] == EM:
                    return True
                # attacked from back (only a king can attack from the back):
                if board[(x + 1, y + 1)] == RK and board[(x - 1, y - 1)] == EM:
                    return True
                if board[(x + 1, y - 1)] == RK and board[(x - 1, y + 1)] == EM:
                    return True
            except KeyError:
                error = 'out of board'
        return False

    # sum utility of our heuristic
    def sum_util(self, loc, loc_val, color, board):
        h_sum = 0
        if self.is_in_center(loc):
            h_sum += CENTER  # being in the center of the board is good
        elif self.is_in_back_line(loc, loc_val, color):
            h_sum += BACK_LINE  # being in the back line is good
        if self.attacked(loc, board, loc_val):
            h_sum += ATTACKED  # being in a position that could be attacked is bad
        return h_sum

    # when only (or mostly) kings are left in the game, if we have more kings than the opponent we want to push our
    # kings towards the opponent to attack, and if we have less kings than the opponent we want our kings to run away
    # and increase their distance from the opponent tools.
    def only_kings_util(self, next_board, color, my_king_num, op_king_num):
        opponent_color = OPPONENT_COLOR[color]
        curr_dist = 0
        # current distance sum:
        for loc_1 in self.curr_board.keys():
            loc_val_1 = self.curr_board[loc_1]
            if loc_val_1 in KING_COLOR[color]:  # my king
                for loc_2 in self.curr_board.keys():
                    loc_val_2 = self.curr_board[loc_2]
                    if loc_val_2 in KING_COLOR[opponent_color]:  # opponent king
                        curr_dist += ((loc_1[0] - loc_2[0]) ** 2 + (loc_1[1] - loc_2[1]) ** 2) ** 0.5
        # next distance sum:
        next_dist = 0
        op_next_dist = 0
        for loc_1 in next_board.keys():
            loc_val_1 = next_board[loc_1]
            if loc_val_1 in KING_COLOR[color]:  # my king
                for loc_2 in next_board.keys():
                    loc_val_2 = next_board[loc_2]
                    if loc_val_2 in KING_COLOR[opponent_color]:  # opponent king
                        next_dist += ((loc_1[0] - loc_2[0]) ** 2 + (loc_1[1] - loc_2[1]) ** 2) ** 0.5

        if curr_dist >= next_dist:
            # distance decreases
            if my_king_num > op_king_num:
                # we have more kings, increase utility so we get closer to opponent in order to attack
                return KING_ATTACK
            else:
                # we have less kings, decrease utility so we don't get closer to opponent (run away)
                return RUN_AWAY_KING
        return 0

    def utility(self, state):
        if len(state.get_possible_moves()) == 0:
            return INFINITY if state.curr_player != self.color else -INFINITY
        if state.turns_since_last_jump >= MAX_TURNS_NO_JUMP:
            return 0

        opponent_color = OPPONENT_COLOR[self.color]
        # Count how many red and black pawn
        piece_counts = defaultdict(lambda: 0)
        my_h_sum = 0
        op_h_sum = 0
        for loc in state.board.keys():
            loc_val = state.board[loc]
            if loc_val != EM:
                if loc_val in MY_COLORS[self.color]:
                    my_h_sum += self.sum_util(loc, loc_val, self.color, state.board)  # add heuristic utility
                elif loc_val in OPPONENT_COLORS[self.color]:
                    op_h_sum += self.sum_util(loc, loc_val, opponent_color, state.board)  # add heuristic utility
                piece_counts[loc_val] += 1

        # if there are mostly kings on the board we want to activate the "only_kings" utility:
        if piece_counts[PAWN_COLOR[self.color]] < piece_counts[KING_COLOR[self.color]] \
                and piece_counts[PAWN_COLOR[opponent_color]] < piece_counts[KING_COLOR[opponent_color]]:
            my_h_sum += self.only_kings_util(state.board, self.color,
                                             piece_counts[KING_COLOR[self.color]],
                                             piece_counts[KING_COLOR[opponent_color]])
            op_h_sum += self.only_kings_util(state.board, opponent_color,
                                             piece_counts[KING_COLOR[opponent_color]],
                                             piece_counts[KING_COLOR[self.color]])

        # sum total utility
        my_u = ((PAWN_WEIGHT * piece_counts[PAWN_COLOR[self.color]]) +
                (KING_WEIGHT * piece_counts[KING_COLOR[self.color]])) + my_h_sum
        op_u = ((PAWN_WEIGHT * piece_counts[PAWN_COLOR[opponent_color]]) +
                (KING_WEIGHT * piece_counts[KING_COLOR[opponent_color]])) + op_h_sum
        if my_u == 0:
            # I have no tools left
            return -INFINITY
        elif op_u == 0:
            # The opponent has no tools left
            return INFINITY
        else:
            return my_u - op_u

    def selective_deepening_criterion(self, state):
        # improve player does not selectively deepen into certain nodes.
        return False

    def no_more_time(self):
        return (time.process_time() - self.clock) >= self.time_for_current_move

    def __repr__(self):
        return '{} {}'.format(abstract.AbstractPlayer.__repr__(self), 'improved_better_h_player')

