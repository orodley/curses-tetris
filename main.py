#!/usr/bin/env python
import curses
from curses.textpad import rectangle
import time
import random
import sys

BOARD_WIDTH  = 10   # Width of tetris board
BOARD_HEIGHT = 22   # Height of tetris board
HIDDEN_ROWS  =  2   # Top two rows, where pieces are spawned, are hidden

BASE_SPEED   =  1.0 # Time taken for a block to drop 1 square

SPAWN_X      =  (BOARD_WIDTH / 2) - 2
SPAWN_Y      =  1   # Co-ordinates to place new blocks at

CHAR = "O"          # Character to use for drawing blocks

DIFFICULTY_CHANGE = 0.8 # Multiply BASE_SPEED by this when increasing difficulty
DIFFICULTY_TIME   = 5   # Increase difficulty every DIFFICULTY_TIME lines

class Block:
    """ A tetris block/tetromino
    square_rotations -- the four states of the block rotated each way
                        states are stored as a list of (x, y) tuples
    squares          -- the current state index
    color            -- color attr to draw the square in
    """

    def __init__(self, square_rotations, color):
        self.square_rotations = square_rotations
        self.rotation = 0 # position to use in square_rotations
        self.squares = square_rotations[0]
        self.color = color

    def rotate(self, direction):
        """ Cycle to the next rotation in square_rotations, wrapping around """
        if direction == "right":
            self.rotation = (self.rotation + 1) % len(self.square_rotations)
        elif direction == "left":
            self.rotation = (self.rotation - 1) % len(self.square_rotations)

        self.squares = self.square_rotations[self.rotation]

    def reset(self):
        self.rotation = 0
        self.squares = self.square_rotations[0]

def draw_block(screen, block, x, y):
    for square in block.squares:
        try:
            screen.addstr(y + square[1], x + square[0], CHAR, block.color)
        except curses.error as error:
            pass # curses raises error when drawing to lower right corner, but still works

"""
def clear_block(screen, block, x, y):
    for square in block.squares:
        try:
            screen.addstr(y + square[1], x + square[0], CHAR, block.color)
"""

def draw_board(root_screen, screen, board, active_block, block_x, block_y, ghost_x, ghost_y):
    #screen.clear()

    for y in xrange(BOARD_HEIGHT):
        for x in xrange(BOARD_WIDTH):
            if board[y][x] != -1:
                try:
                    screen.addstr(y, x, CHAR, board[y][x])
                except curses.error as error:
                    pass # curses raises error when drawing to lower right corner, but still works
    original_color = active_block.color

    active_block.color = curses.color_pair(8)
    draw_block(screen, active_block, ghost_x, ghost_y)

    active_block.color = original_color
    draw_block(screen, active_block, block_x, block_y)
    root_screen.refresh()
    screen.refresh()

def has_collided(board, block, x, y):
    for square in block.squares:
        if (not (0 <= x + square[0] < BOARD_WIDTH)  or
            not (0 <= y + square[1] < BOARD_HEIGHT) or
            board[y + square[1]][x + square[0]] != -1):
            return True
    return False

def has_block_landed(board, block, x, y):
    for square in block.squares:
        if (y + square[1] >= BOARD_HEIGHT or # If square is below bottom of board or...
            (board[y + square[1]][x + square[0]] != -1 and    # ...the square collides and...
             board[y + square[1] - 1][x + square[0]] == -1)): # ...the square above is clear
            return True

def get_cleared_rows(board):
    cleared_rows = []

    for row in xrange(BOARD_HEIGHT):
        clear = True
        for square in board[row]:
            if square == -1:
                clear = False
                break

        if clear:
            cleared_rows.append(row)

        clear = False

    return cleared_rows

def have_lost(board, block, x, y):
    for square in block.squares:
        if y + square[1] < 0:
            messages.append("1")
            return True

    for square in block.squares:
        if board[y + square[1]][x + square[0]] != -1:
            messages.append("2")
            return True

    return False

def shift_rows(board, cleared_row):
    for row in xrange(cleared_row, 0, -1):
        board[row] = board[row-1]

    board[0] = [-1 for column in xrange(BOARD_WIDTH)]

def place_block(board, block, x, y):
    for square in block.squares: # Copy each square onto the board
        board[y + square[1]][x + square[0]] = block.color

def get_ghost(board, block, x):
    ghost_x, ghost_y = x, 1
    for row in xrange(BOARD_HEIGHT):
        ghost_y += 1
        if has_collided(board, block, ghost_x, ghost_y):
            return (ghost_x, ghost_y - 1)

def main(screen):
    global messages
    messages = []

    curses.use_default_colors() # Use the default background color
    curses.curs_set(0)          # Don't show cursor
    screen.nodelay(1)           # We want non-blocking input

    # Initialise all needed color pairs, and set constants to refer to them
    # Also set constants for the attr of the pieces, e.g. "O" pieces are bold yellow
    # All colors use the default background of -1

    curses.init_pair(0, curses.COLOR_WHITE, -1)
    WHITE = 0 

    curses.init_pair(1, curses.COLOR_CYAN, -1)
    CYAN = 1

    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    ORANGE = 2 # COLOR_YELLOW is actually brown, which is being used as orange

    curses.init_pair(3, curses.COLOR_MAGENTA, -1)
    MAGENTA = 3

    curses.init_pair(4, curses.COLOR_GREEN, -1)
    GREEN = 4

    curses.init_pair(5, curses.COLOR_RED, -1)
    RED = 5

    curses.init_pair(6, curses.COLOR_BLUE, -1)
    BLUE = 6
        
    curses.init_pair(7, curses.COLOR_BLACK, -1)
    BLACK = 7

    curses.init_pair(8, curses.COLOR_WHITE, -1)
    GREY = 8 # COLOR_WHITE is more like a grey

    # Dict to store information on the block types.
    # Indexed by letter corresponding to shape (I, S, Z, etc)
    # Values are block objects
    blocks =\
            {
              "I": Block([[(0,  0), (1,  0), (2,  0), (3,  0)],
                          [(2,  1), (2,  0), (2, -1), (2, -2)],
                          [(0, -1), (1, -1), (2, -1), (3, -1)],
                          [(1,  1), (1,  0), (1, -1), (1, -2)]],
                                curses.color_pair(CYAN)),

              "O": Block([[(0, 0), (0, 1), (1, 0), (1, 1)]], # All rotations are the same
                         curses.color_pair(ORANGE) | curses.A_BOLD),

              "T": Block([[(0, 0), (1, 0), (2,  0), (1,  1)],
                          [(1, 1), (1, 0), (1, -1), (2,  0)],
                          [(0, 0), (1, 0), (2,  0), (1, -1)],
                          [(0, 0), (1, 1), (1,  0), (1, -1)]], curses.color_pair(MAGENTA)),

              "S": Block([[(0,  0), (1,  0), (1, 1), (2,  1)],
                          [(1,  1), (1,  0), (2, 0), (2, -1)],
                          [(0, -1), (1, -1), (1, 0), (2,  0)],
                          [(0,  1), (0,  0), (1, 0), (1, -1)]], curses.color_pair(GREEN)),

              "Z": Block([[(0,  1), (1, 1), (1,  0), (2,  0)],
                          [(1, -1), (1, 0), (2,  0), (2,  1)],
                          [(0,  0), (1, 0), (1, -1), (2, -1)],
                          [(0, -1), (0, 0), (1,  0), (1,  1)]], curses.color_pair(RED)),

              "J": Block([[(0,  1), (0,  0), (1, 0), (2,  0)],
                          [(1, -1), (1,  0), (1, 1), (2,  1)],
                          [(0,  0), (1,  0), (2, 0), (2, -1)],
                          [(0, -1), (1, -1), (1, 0), (1,  1)]], curses.color_pair(BLUE)),

              "L": Block([[(0,  0), (1, 0), (2,  0), (2,  1)],
                          [(1,  1), (1, 0), (1, -1), (2, -1)],
                          [(0, -1), (0, 0), (1,  0), (2,  0)],
                          [(0,  1), (1, 1), (1,  0), (1, -1)]], curses.color_pair(ORANGE)),
            } 
                    
    # Populate board with -1s (indicating an empty square).
    # Other numbers indicate the color in which to draw that square
    board = [[-1 for x in xrange(BOARD_WIDTH)] for y in xrange(BOARD_HEIGHT)]

    # Board should be centered in the terminal
    term_height, term_width, = screen.getmaxyx()
    board_window = curses.newwin(BOARD_HEIGHT, BOARD_WIDTH, (term_height / 2) - (BOARD_HEIGHT / 2),
                                 (term_width / 2) - (BOARD_WIDTH / 2))

    border_ul = ((term_width / 2) - (BOARD_WIDTH / 2) - 1,
                 (term_height / 2) - (BOARD_HEIGHT / 2) - 1)
    border_lr = (border_ul[0] + BOARD_WIDTH + 1, border_ul[1] + BOARD_HEIGHT + 1)

    # Generate the inital block queue and get the first item
    block_queue = blocks.values()
    random.shuffle(block_queue)
    active_block = block_queue.pop()

    rectangle(screen, border_ul[1], border_ul[0], border_lr[1], border_lr[0])
    curses.doupdate()

    # Initial block position
    block_x, block_y = SPAWN_X, SPAWN_Y

    ghost_x, ghost_y = get_ghost(board, active_block, block_x)

    draw_block(board_window, active_block, block_x, block_y)
    draw_block(board_window, active_block, ghost_x, ghost_y)
    board_window.refresh()

    timeout = time.time()
    speed = BASE_SPEED

    score = 0

    while True:
        key = screen.getch()

        if key == curses.KEY_LEFT: # Move block left
            block_x -= 1
            if has_collided(board, active_block, block_x, block_y):
                block_x += 1
            else:
                ghost_x, ghost_y = get_ghost(board, active_block, block_x)
                draw_board(screen, board_window, board, active_block, block_x, block_y, ghost_x, ghost_y)
        elif key == curses.KEY_RIGHT: # Move block right
            block_x += 1
            if has_collided(board, active_block, block_x, block_y):
                block_x -= 1
            else:
                ghost_x, ghost_y = get_ghost(board, active_block, block_x)
                draw_board(screen, board_window, board, active_block, block_x, block_y, ghost_x, ghost_y)
        elif key == ord("z"): # Rotate block left
            active_block.rotate("left")
            ghost_x, ghost_y = get_ghost(board, active_block, block_x)
            draw_board(screen, board_window, board, active_block, block_x, block_y, ghost_x, ghost_y)
        elif key == ord("x"): # Rotate block right
            active_block.rotate("right")
            ghost_x, ghost_y = get_ghost(board, active_block, block_x)
            draw_board(screen, board_window, board, active_block, block_x, block_y, ghost_x, ghost_y)
        elif key == curses.KEY_DOWN: # Hard drop block
            block_x, block_y = ghost_x, ghost_y
            timeout = 0 # Force timeout
        elif key == ord("q"):
            break
        
        if time.time() - timeout > speed:
            timeout = time.time()
            block_y += 1
            
            if has_block_landed(board, active_block, block_x, block_y):
                block_y -= 1
                place_block(board, active_block, block_x, block_y)
                active_block.reset()

                active_block = block_queue.pop()
                block_x, block_y = SPAWN_X, SPAWN_Y
                ghost_x, ghost_y = get_ghost(board, active_block, block_x)

                if have_lost(board, active_block, block_x, block_y):
                    messages.append(" 1")
                    break

                cleared_rows = get_cleared_rows(board)
                if cleared_rows:
                    for row in cleared_rows:
                        shift_rows(board, row)
                        score += 1
                        
                        if score % DIFFICULTY_TIME == 0:
                            speed *= DIFFICULTY_CHANGE

                if len(block_queue) == 0:
                    block_queue = blocks.values()
                    random.shuffle(block_queue)

                if have_lost(board, active_block, block_x, block_y):
                    messages.append(" 2")
                    break

            draw_board(screen, board_window, board, active_block, block_x, block_y, ghost_x, ghost_y)

if __name__ == "__main__":
    curses.wrapper(main)

    for message in messages: print message
