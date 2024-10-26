import curses
import random
from .runtimedata import download_queue
from .otsconfig import config

def start_snake_game(win):
    curses.curs_set(0)
    win.timeout(100)
    win.keypad(1)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)


    while True:
        snake = [(4, 10), (4, 9), (4, 8)]
        food = (random.randint(3, win.getmaxyx()[0] - 2), random.randint(1, win.getmaxyx()[1] - 3))
        direction = curses.KEY_RIGHT
        score = 0

        while True:
            win.clear()
            draw_borders(win)
            update_header(win, score)

            for y, x in snake:
                win.addch(y, x, '█', curses.color_pair(2))

            win.addch(food[0], food[1], '■', curses.color_pair(3))

            new_dir = win.getch()
            if new_dir in [curses.KEY_RIGHT, curses.KEY_LEFT, curses.KEY_UP, curses.KEY_DOWN]:
                direction = new_dir

            head_y, head_x = snake[0]
            if direction == curses.KEY_RIGHT:
                head_x += 1
            elif direction == curses.KEY_LEFT:
                head_x -= 1
            elif direction == curses.KEY_UP:
                head_y -= 1
            elif direction == curses.KEY_DOWN:
                head_y += 1

            if (head_x in [0, win.getmaxyx()[1] - 2] or
                head_y in [0, win.getmaxyx()[0] - 1] or
                head_y == 2 or
                (head_y, head_x) in snake):
                display_game_over(win, score)
                break

            if (head_y, head_x) == food:
                score += 1
                food = (random.randint(3, win.getmaxyx()[0] - 2), random.randint(1, win.getmaxyx()[1] - 3))
            else:
                snake.pop()

            snake.insert(0, (head_y, head_x))

        while True:
            key = win.getch()
            if key == ord('r'):
                break
            elif key == ord('q'):
                return

def draw_borders(win):
    height, width = win.getmaxyx()
    if width < 2 or height < 2:
        return
    for y in range(height):
        win.addch(y, 0, '┃', curses.color_pair(1))
        win.addch(y, width - 2, '┃', curses.color_pair(1))
    width = win.getmaxyx()[1]
    if width > 2:
        win.addstr(0, 0, '┏' + '━' * (width - 3) + '┓', curses.color_pair(1))
        win.addstr(2, 0, '┣' + '━' * (width - 3) + '┫', curses.color_pair(1))
    if height > 1 and width > 2:
        win.addstr(height - 1, 0, '┗' + '━' * (width - 3) + '┛', curses.color_pair(1))

def update_header(win, score):
    win.addstr(1, 2, f'Score: {score}', curses.A_BOLD)
    if not download_queue:
        item_label = 'Download Queue Empty :('
    else:
        current_item = download_queue[next(iter(download_queue))]
        item_label = f"{current_item['item_name']} by {current_item['item_by']}: {current_item['item_status']}"

    win.addstr(1, 15, item_label, curses.A_BOLD)

def display_game_over(win, score):
    win.clear()
    if score > config.get('snake_high_score', 0):
        config.set_('snake_high_score', score)
        config.update()
    win.addstr(win.getmaxyx()[0] // 2 - 1, win.getmaxyx()[1] // 2 - 10, 'Game Over!', curses.color_pair(1))
    win.addstr(win.getmaxyx()[0] // 2, win.getmaxyx()[1] // 2 - 10, f'Score: {score}', curses.A_BOLD)
    win.addstr(win.getmaxyx()[0] // 2 + 1, win.getmaxyx()[1] // 2 - 10, f'High Score: {config.get('snake_high_score', 0)}', curses.A_BOLD)
    win.addstr(win.getmaxyx()[0] // 2 + 2, win.getmaxyx()[1] // 2 - 10, 'Press r to retry or q to quit.')
    win.refresh()
