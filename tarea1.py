import requests
import random
from collections import Counter
import copy
import time

base_url = 'https://blockmaster-78b623003250.herokuapp.com/'
player_key = 'PKEY-96739'

def get_games():
    r = requests.get(f'{base_url}api/games/')
    r.raise_for_status()
    return r.json()

def get_status(game_id):
    params = {'game': game_id, 'key': player_key}
    r = requests.get(f'{base_url}api/status/', params=params)
    r.raise_for_status()
    return r.json()

def print_status(game_id):
    params = {'game': game_id, 'key': player_key}
    r = requests.get(f'{base_url}api/status/', params=params)
    for key, value in r.json().items():
      print(f'{key}: {value}')

def play_move(game_id, row, col):
    data = {
        'game': game_id,
        'key': player_key,
        'row': str(row),
        'col': str(col)
    }
    r = requests.post(f'{base_url}api/play/', data=data)
    r.raise_for_status()
    return r.json()

def board_to_matrix(board_string):
    matrix =[]
    board_parsed = board_string.split('|')
    for fila in board_parsed:
      fila_parsed = fila.split(',')
      matrix.append(fila_parsed)
    return matrix

def dfs(board, visited, r, c, color):
    stack = [(r, c)]
    group = []
    while stack:
        x, y = stack.pop()
        if (0 <= x < len(board) and 0 <= y < len(board[0]) and not visited[x][y] and board[x][y][-1] == color):
            visited[x][y] = True
            group.append((x, y))
            stack.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
    return group

def count_colors(board):
    colors_list = []
    for row in board:
        for block in row:
            if block != '.':
                color = block[-1]
                colors_list.append(color)
    color_count = Counter(colors_list)
    return color_count

def simulate_gravity(board, color_probs):
    rows = len(board)
    cols = len(board[0])

    for col in range(cols):
        blocks = []
        for row in range(rows):
            if board[row][col] != '.':
                blocks.append(board[row][col])

        for row in range(rows - 1, -1, -1):
            if blocks:
                board[row][col] = blocks.pop()
            else:
                val = random.random()  
                acc_prob = 0
                for color_prob in color_probs:
                    acc_prob += color_prob['p']
                    if val <= acc_prob:
                        board[row][col] = "0" + color_prob['code']
                        break
    return board

def get_all_groups(board, min_size=3):
    rows = len(board)
    cols = len(board[0])
    visited = []
    for _ in range(rows):
        visited_row = []
        for _ in range(cols):
            visited_row.append(False)
        visited.append(visited_row)

    groups = []

    for row in range(rows):
        for col in range(cols):
            if not visited[row][col] and board[row][col] != '.':
                current_color = board[row][col][-1]
                connected_group = dfs(board, visited, row, col, current_color)
                if len(connected_group) >= min_size:
                    groups.append(connected_group)
    return groups

def simulate_move(board, group, color_probs):
    temp = copy.deepcopy(board)
    for r, c in group:
        temp[r][c] = '.'
    temp = simulate_gravity(temp, color_probs)
    return temp

def simulate_score(board, group, goal_type, color_target=None):
    if goal_type == "score_target":
        return len(group) ** 2  
    elif goal_type == "color_target" and color_target:
        count = 0
        for r, c in group:
            block_color = board[r][c][-1]
            if block_color == color_target:
                count += 1
        return count
    else:
        return 0

def find_best_move(board, goal_type, colors, remaining=None):
    best_move = None
    best_score = -1

    color_target = None
    if goal_type == "color_target":
        if len(remaining) > 0:
            color_target = None
            max_missing = -1
            for color, missing in remaining.items():
                if missing > max_missing:
                    max_missing = missing
                    color_target = color

    all_groups = get_all_groups(board, min_size=3)
    if len(all_groups) == 0:
        all_groups = get_all_groups(board, min_size=1)

    for group in all_groups:
        current_score = simulate_score(board, group, goal_type, color_target)
        simulated_future_board = simulate_move(board, group, colors)

        future_groups = get_all_groups(simulated_future_board, min_size=3)
        if len(future_groups) == 0:
            future_groups = get_all_groups(simulated_future_board, min_size=1)

        if len(future_groups) > 0:
            best_future = -1
            for future_group in future_groups:
                puntaje = simulate_score(board, future_group, goal_type, color_target)
                if puntaje > best_future:
                    best_future = puntaje
        else:
            best_future = 0

        total_score = current_score + 0.8 * best_future
        if total_score > best_score:
            best_score = total_score
            best_move = group

    return random.choice(best_move)

def play_game(game):
    print(f"Playing game {game['id']}")
    status = get_status(game['id'])
    goal_type = game['goal_type']
    goal_params = game['goal_params']
    if goal_type == "color_target":
        remaining = goal_params['color_requirements']

    while status['status'] == 'in_progress':
        board_str = status['board_string']
        board = board_to_matrix(board_str)
        colors = game['colors']

        if goal_type == "score_target":
            row, col = find_best_move(board, goal_type, colors)
        if goal_type == "color_target":
            row, col = find_best_move(board, goal_type, colors, remaining)

        play = play_move(game['id'], row, col)
        if goal_type == "color_target":
            played_blocks = play['removed_colors']
            for color in remaining:
                removed = played_blocks.get(color, 0)
                remaining[color] = max(0, remaining[color] - removed)
            print(remaining)
        status = get_status(game['id'])

    print(f"Game {game['id']} --> {status['status']}.")
    print_status(game['id'])

start_time = time.time()
games = get_games()
count = 0
for game in games:
    play_game(game)
    status = get_status(game['id'])
    count += status['turn_count']
print(f'La cantidad total de turnos es: {count}')
end_time = time.time()  
elapsed_time = end_time - start_time
print(f"Tiempo total: {elapsed_time:.2f} segundos")


