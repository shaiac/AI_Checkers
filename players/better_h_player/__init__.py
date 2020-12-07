# ===============================================================================
# Imports
# ===============================================================================
import operator

import abstract
from utils import MiniMaxWithAlphaBetaPruning, INFINITY, run_with_limited_time, ExceededTimeError
from checkers.consts import EM, PAWN_COLOR, KING_COLOR, OPPONENT_COLOR, MAX_TURNS_NO_JUMP, RP, RK, BP, BK, RED_PLAYER, BLACK_PLAYER, MY_COLORS, OPPONENT_COLORS
import time
from collections import defaultdict

# ===============================================================================
# Globals
# ===============================================================================

PAWN_WEIGHT = 1
KING_WEIGHT = 1.5
CENTER = 0.6
BACK_LINE = 0.7
ATTACK_PAWN = 0.5
ATTACK_KING = 1.5


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
        self.time_for_current_move = self.time_remaining_in_round / self.turns_remaining_in_round - 0.05

    def get_move(self, game_state, possible_moves):
        self.clock = time.process_time()
        self.time_for_current_move = self.time_remaining_in_round / self.turns_remaining_in_round - 0.05
        if len(possible_moves) == 1:
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

            print('going to depth: {}, remaining time: {}, prev_alpha: {}, best_move: {}'.format(
                current_depth,
                current_depth,
                self.time_for_current_move - (time.process_time() - self.clock),
                prev_alpha,
                best_move))

            try:
                (alpha, move), run_time = run_with_limited_time(
                    minimax.search, (game_state, current_depth, -INFINITY, INFINITY, True), {},
                    self.time_for_current_move - (time.process_time() - self.clock))
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
        return best_move

    @staticmethod
    def is_in_center(loc):
        x, y = loc[0], loc[1]
        if (x == 3 and y == 2) or (x == 3 and y == 4) or (x == 4 and y == 5) or (x == 4 and y ==3):
            return True
        return False

    @staticmethod
    def is_in_back_line(loc, loc_val, player_color):
        if loc_val in KING_COLOR.values():
            return False
        x, y = loc[0], loc[1]
        if player_color == BLACK_PLAYER:
            if x == 7 and (y == 2 or y == 6):
                return True
        if player_color == RED_PLAYER:
            if x == 0 and (y == 2 or y == 6):
                return True

    @staticmethod
    def attack(loc, color, board, tools):
        x, y = loc[0], loc[1]
        opponent_color = OPPONENT_COLOR[color]
        if color == BLACK_PLAYER:
            try:
                if board[(x - 1, y + 1)] == tools[opponent_color] and board[(x - 2, y + 2)] == EM:  # right diagonal
                    return True
            except KeyError:
                error = 1
            try:
                if board[(x - 1, y - 1)] == tools[opponent_color] and board[(x - 2, y - 2)] == EM:  # left diagonal
                    return True
            except KeyError:
                error = 1
        else:
            try:
                if board[(x + 1, y + 1)] == tools[opponent_color] and board[(x + 2, y + 2)] == EM:  # right diagonal
                    return True
            except KeyError:
                error = 1
            try:
                if board[(x + 1, y - 1)] == tools[opponent_color] and board[(x + 2, y - 2)] == EM:  # left diagonal
                    return True
            except KeyError:
                error = 1


    def sum_util(self, loc, loc_val, color, board):
        h_sum = 0
        if self.is_in_center(loc):
            h_sum += CENTER
        elif self.is_in_back_line(loc, loc_val, color):
            h_sum += BACK_LINE
        if self.attack(loc, color, board, PAWN_COLOR):
           h_sum += ATTACK_PAWN
        if self.attack(loc, color, board, KING_COLOR):
           h_sum += ATTACK_KING
        return h_sum

    @staticmethod
    def get_truth(inp, relate, cut):
        ops = {'+': operator.add,
               '-': operator.sub}
        return ops[relate](inp, cut)

    def utility(self, state):
        if len(state.get_possible_moves()) == 0:
            return INFINITY if state.curr_player != self.color else -INFINITY
        if state.turns_since_last_jump >= MAX_TURNS_NO_JUMP:
            return 0

        opponent_color = OPPONENT_COLOR[self.color]
        piece_counts = defaultdict(lambda: 0)
        my_h_sum = 0
        op_h_sum = 0
        for loc in state.board.keys():
            loc_val = state.board[loc]
            if loc_val != EM:
                if loc_val in MY_COLORS[self.color]:
                    my_h_sum += self.sum_util(loc, loc_val, self.color, state.board)
                elif loc_val in OPPONENT_COLORS[self.color]:
                    op_h_sum += self.sum_util(loc, loc_val, opponent_color, state.board)
                piece_counts[loc_val] += 1

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
        # Simple player does not selectively deepen into certain nodes.
        return False

    def no_more_time(self):
        return (time.process_time() - self.clock) >= self.time_for_current_move

    def __repr__(self):
        return '{} {}'.format(abstract.AbstractPlayer.__repr__(self), 'better_h')

# c:\python35\python.exe run_game.py 3 3 3 y simple_player random_player
