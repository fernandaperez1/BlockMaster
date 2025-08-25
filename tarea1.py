import requests
import random
from collections import Counter
import copy
import time
import concurrent.futures

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
        if (0 <= x < len(board) and 0 <= y < len(board[0]) 
            and not visited[x][y] 
            and board[x][y] != '.' 
            and board[x][y] != 'X'  
            and board[x][y][-1] == color):
            
            visited[x][y] = True
            group.append((x, y))
            stack.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
    return group

def count_colors(board):
    colors_list = []
    for row in board:
        for block in row:
            if block != '.' and block != 'X':
                color = block[-1]
                colors_list.append(color)
    color_count = Counter(colors_list)
    return color_count

def generate_block(special_spawn_rate, color_probs):
    if random.random() < special_spawn_rate:
        r = random.random()
        if r < 0.40:  
            return "1" 
        elif r < 0.40 + 0.25:  
            return "2"  
        elif r < 0.40 + 0.25 + 0.20:  
            c = random.choice([cp['code'] for cp in color_probs])
            return f"3{c}" 
        else:  
            codes = [cp['code'] for cp in color_probs]
            c1, c2 = random.sample(codes, 2)
            return f"4{c1}{c2}"  
    else:
        r = random.random()
        acc = 0
        for cp in color_probs:
            acc += cp['p']
            if r < acc:
                return f"0{cp['code']}"
        return f"0{color_probs[-1]['code']}"

def simulate_gravity(board, color_probs, special_spawn_rate):
    rows = len(board)
    cols = len(board[0])

    for col in range(cols):
        start = rows - 1
        while start >= 0:
            end = start
            while end >= 0 and board[end][col] != 'X':
                end -= 1
            
            segment_blocks = []
            for row in range(end+1, start+1):
                if board[row][col] != '.' and board[row][col] != 'X':
                    segment_blocks.append(board[row][col])
            
            r = start
            for block in reversed(segment_blocks):
                board[r][col] = block
                r -= 1
            
            while r > end:
                board[r][col] = generate_block(special_spawn_rate, color_probs)
                r -= 1
            start = end - 1

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
            if not visited[row][col] and board[row][col] != '.' and board[row][col] != 'X':
                current_color = board[row][col][-1]
                connected_group = dfs(board, visited, row, col, current_color)
                if len(connected_group) >= min_size:
                    groups.append(connected_group)
    return groups

def simulate_move(board, group, color_probs, special_spawn_rate):
    temp = copy.deepcopy(board)
    sel_r, sel_c = group[0]
    sel_block = temp[sel_r][sel_c]
    
    def apply_special(r, c, block):
        if block[0] == '1':  
            for i in range(r-1, r+2):
                for j in range(c-1, c+2):
                    if 0 <= i < len(board) and 0 <= j < len(board[0]) and temp[i][j] != 'X':
                        temp[i][j] = '.'
        elif block[0] == '2':  
            for i in range(len(board)):
                if temp[i][c] != 'X':
                    temp[i][c] = '.'
            for j in range(len(board[0])):
                if temp[r][j] != 'X':
                    temp[r][j] = '.'
        elif block[0] == '3':  
            color_to_remove = block[-1]
            for i in range(len(board)):
                for j in range(len(board[0])):
                    if temp[i][j] != 'X' and temp[i][j][-1] == color_to_remove:
                        temp[i][j] = '.'
        elif block[0] == '4':  
            from_color = block[1]
            to_color = block[2]
            for i in range(len(board)):
                for j in range(len(board[0])):
                    if temp[i][j] != 'X' and temp[i][j][-1] == from_color:
                        temp[i][j] = f"0{to_color}"
    
    if sel_block[0] in '1234':
        apply_special(sel_r, sel_c, sel_block)
    
    for r, c in group:
        if (r, c) != (sel_r, sel_c):
            temp[r][c] = '.'
    
    temp = simulate_gravity(temp, color_probs, special_spawn_rate)
    return temp

def simulate_score_score_target(board, group):
    sel_r, sel_c = group[0]
    sel_block = board[sel_r][sel_c]

    if sel_block[0] == '0': 
        return len(group) ** 2

    elif sel_block[0] == '1':  
        count = 0
        for i in range(sel_r-1, sel_r+2):
            for j in range(sel_c-1, sel_c+2):
                if 0 <= i < len(board) and 0 <= j < len(board[0]) and board[i][j] != 'X':
                    count += 1
        return count ** 2

    elif sel_block[0] == '2': 
        count = 0
        for j in range(len(board[0])):  
            if board[sel_r][j] != 'X':
                count += 1
        for i in range(len(board)): 
            if board[i][sel_c] != 'X':
                count += 1
        count -= 1  
        return count ** 2

    elif sel_block[0] == '3': 
        color_to_remove = sel_block[-1]
        count = 0
        for i in range(len(board)):
            for j in range(len(board[0])):
                block = board[i][j]
                if block != 'X' and block != '.' and block.endswith(color_to_remove):
                    count += 1
        return count ** 2

    elif sel_block[0] == '4': 
        return 0
        
def simulate_score_color_target(board, group, remaining):
    sel_r, sel_c = group[0]
    sel_block = board[sel_r][sel_c]
    
    if sel_block[0] == '0':  
        count = 0
        for r, c in group:
            block_color = board[r][c][-1]
            if block_color in remaining and remaining[block_color] > 0:
                count += 1
        return count

    elif sel_block[0] == '1': 
        count = 0
        for i in range(sel_r-1, sel_r+2):
            for j in range(sel_c-1, sel_c+2):
                if 0 <= i < len(board) and 0 <= j < len(board[0]) and board[i][j] != 'X':
                    block_color = board[i][j][-1]
                    if block_color in remaining and remaining[block_color] > 0:
                        count += 1
        return count

    elif sel_block[0] == '2': 
        count = 0
        for j in range(len(board[0])):  
            if board[sel_r][j] != 'X':
                block_color = board[sel_r][j][-1]
                if block_color in remaining and remaining[block_color] > 0:
                    count += 1
        for i in range(len(board)): 
            if board[i][sel_c] != 'X':
                block_color = board[i][sel_c][-1]
                if block_color in remaining and remaining[block_color] > 0:
                    count += 1
        count -= 1  
        return count

    elif sel_block[0] == '3':  
        color_to_remove = sel_block[-1]
        if color_to_remove in remaining and remaining[color_to_remove] > 0:
            count = 0
            for i in range(len(board)):
                for j in range(len(board[0])):
                    if board[i][j] != 'X' and board[i][j][-1] == color_to_remove:
                        count += 1
            return count
        return 0

    elif sel_block[0] == '4': 
        return 1

def find_best_move_color_target(board, color_probs, special_spawn_rate, remaining=None):
    best_move = None
    best_score = -1
    rows, cols = len(board), len(board[0])

    all_groups = get_all_groups(board, min_size=1)

    for r in range(rows):
        for c in range(cols):
            block = board[r][c]
            if block[0] in '1234':  # es una bomba o conversor
                in_group = False
                for group in all_groups:
                    if (r, c) in group:
                        in_group = True
                        break
                if not in_group:
                    all_groups.append([(r, c)])

    for group in all_groups:
        sel_r, sel_c = group[0]
        sel_block = board[sel_r][sel_c]

        score = simulate_score_color_target(board, group, remaining)

        if sel_block[0] == '3' and sel_block[-1] in remaining and remaining[sel_block[-1]] > 0:
            score *= 1.5  

        if sel_block[0] == '4' and sel_block[2] in remaining and remaining[sel_block[2]] > 0:
            score *= 1.3

        simulated_board = simulate_move(board, group, color_probs, special_spawn_rate)

        future_groups = get_all_groups(simulated_board, min_size=1)
        best_future = 0
        for future_group in future_groups:
            puntaje = simulate_score_color_target(simulated_board, future_group, remaining)
            if puntaje > best_future:
                best_future = puntaje

        total_score = score + 0.6 * best_future 

        if len(group) == 1 and sel_block[0] == '0':
            total_score *= 0.8

        if total_score > best_score:
            best_score = total_score
            best_move = group

    return best_move[0]

def find_best_move_score_target(board, color_probs, special_spawn_rate):
    best_move = None
    best_score = -1

    all_groups = get_all_groups(board, min_size=3)
    if len(all_groups) == 0:
        all_groups = get_all_groups(board, min_size=1)

    rows, cols = len(board), len(board[0])
    bomb_groups = []
    for r in range(rows):
        for c in range(cols):
            if board[r][c][0] in '1234': 
                bomb_groups.append([(r, c)])
    
    possible_moves = all_groups + bomb_groups

    for group in possible_moves:
        current_score = simulate_score_score_target(board, group)
        simulated_future_board = simulate_move(board, group, color_probs, special_spawn_rate)

        future_groups = get_all_groups(simulated_future_board, min_size=3)
        if len(future_groups) == 0:
            future_groups = get_all_groups(simulated_future_board, min_size=1)

        if len(future_groups) > 0:
            best_future = -1
            for future_group in future_groups:
                puntaje = simulate_score_score_target(simulated_future_board, future_group)
                if puntaje > best_future:
                    best_future = puntaje
        else:
            best_future = 0

        total_score = current_score + 0.8 * best_future
        if total_score > best_score:
            best_score = total_score
            best_move = group

    return best_move[0]

def color_dfs(board, visited, r, c, color):
    stack = [(r, c)]
    group = []
    rows, cols = len(board), len(board[0])

    while stack:
        x, y = stack.pop()
        if visited[x][y]:
            continue
        visited[x][y] = True

        if board[x][y] != '.' and board[x][y] != 'X' and board[x][y][0] == '0' and board[x][y][-1] == color:
            group.append((x, y))

            for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < rows and 0 <= ny < cols and not visited[nx][ny]:
                    stack.append((nx, ny))

    return group

def find_largest_group(board, color):
    rows, cols = len(board), len(board[0])
    visited = []
    for _ in range(rows):
        visited_row = []
        for _ in range(cols):
            visited_row.append(False)
        visited.append(visited_row)
    largest_group = []

    for r in range(rows-1, -1, -1):
        for c in range(cols):
            if not visited[r][c] and board[r][c] != '.' and board[r][c] != 'X' and board[r][c][0] == '0' and board[r][c][-1] == color:
                group = color_dfs(board, visited, r, c, color)
                if len(group) > len(largest_group):
                    largest_group = group

    return largest_group


def remove_group(board, r, c):
    rows, cols = len(board), len(board[0])
    color_block = board[r][c]
    
    if color_block is None or color_block == "." or color_block[0] != '0':
        return 0

    color = color_block[-1]
    stack = [(r, c)]
    visited = set()
    removed = 0

    while stack:
        x, y = stack.pop()
        if (x, y) in visited:
            continue
        if 0 <= x < rows and 0 <= y < cols and board[x][y] != '.' and board[x][y] != 'X' and board[x][y][0] == '0' and board[x][y][-1] == color:
            visited.add((x, y))
            board[x][y] = "."
            removed += 1
            stack.extend([(x-1, y), (x+1, y), (x, y-1), (x, y+1)])

    return removed

def simulate_move_group_target(board, r, c, target_color, min_group_size, color_probs, special_spawn_rate):
    rows, cols = len(board), len(board[0])
    new_board = []
    for row in board:
        new_row = []
        for cell in row:
            new_row.append(cell)
        new_board.append(new_row)
    cell = new_board[r][c]

    def clear_cell(i, j):
        if 0 <= i < rows and 0 <= j < cols and new_board[i][j] != 'X':
            new_board[i][j] = '.'

    def apply_special(r0, c0, block):
        t = block[0]
        if t == '1':  
            for i in range(r0-1, r0+2):
                for j in range(c0-1, c0+2):
                    clear_cell(i, j)
            new_board[r0][c0] = '.'

        elif t == '2':  
            for i in range(rows):
                clear_cell(i, c0)
            for j in range(cols):
                clear_cell(r0, j)
            new_board[r0][c0] = '.'

        elif t == '3':  
            color_to_remove = block[-1]
            for i in range(rows):
                for j in range(cols):
                    if new_board[i][j] != 'X' and new_board[i][j] != '.' and new_board[i][j][-1] == color_to_remove:
                        new_board[i][j] = '.'
            new_board[r0][c0] = '.'

        elif t == '4':  
            from_c, to_c = block[1], block[2]
            for i in range(rows):
                for j in range(cols):
                    if new_board[i][j] != '.' and new_board[i][j] != 'X' and new_board[i][j][0] == '0' and new_board[i][j][-1] == from_c:
                        new_board[i][j] = f'0{to_c}'
            new_board[r0][c0] = '.'  

    if cell == '.' or cell == 'X':
        pass
    elif cell[0] in ('1','2','3','4'):
        apply_special(r, c, cell)
    else:
        remove_group(new_board, r, c)

    simulate_gravity(new_board, color_probs, special_spawn_rate)

    largest_group = find_largest_group(new_board, target_color)
    return len(largest_group), new_board

def find_best_move_group_target(board, color_probs, special_spawn_rate, min_group_size, locked_target_color=None):
    rows, cols = len(board), len(board[0])

    target_color = locked_target_color
    if target_color is None:
        counts = Counter()
        for row in board:
            for cell in row:
                if cell not in ('.', 'X') and cell[0] == '0':
                    color = cell[-1]
                    counts[color] += 1

        if not counts:
            for i in range(rows):
                for j in range(cols):
                    if board[i][j] not in ('.','X'):
                        return i, j, None
            return 0, 0, None

        pmap = {}
        for cp in color_probs:
            code = cp['code']
            prob = cp['p']
            pmap[code] = prob

        best = None
        best_pair = None
        for c, cnt in counts.items():
            score = (cnt, pmap.get(c, 0.0))
            if best is None or score > best:
                best = score
                best_pair = c
        target_color = best_pair

    largest_group = find_largest_group(board, target_color)
    current_size = len(largest_group)
    if current_size >= min_group_size and current_size > 0:
        r0, c0 = largest_group[0]
        return r0, c0, None

    group_set = set(largest_group)

    candidates = []
    frontier_seen = set()
    for (gr, gc) in largest_group:
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = gr + dr, gc + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in group_set and (nr, nc) not in frontier_seen:
                cell = board[nr][nc]
                if cell not in ('.','X'):
                    if cell[0] in ('0','1','2','3','4'):
                        candidates.append((nr, nc))
                        frontier_seen.add((nr, nc))

    if not candidates:
        for i in range(rows):
            for j in range(cols):
                cell = board[i][j]
                if cell not in ('.','X') and cell[0] in ('0','1','2','3','4'):
                    candidates.append((i, j))

    best_move = None
    best_size = -1
    best_delta = -10**9 

    def tie_break_key(r, c):
        t = board[r][c][0]
        if t == '4':
            power = 4
        elif t == '3':
            power = 3
        elif t == '2':
            power = 2
        elif t == '1':
            power = 1
        else:  
            power = 0
        return (r, power)

    for (r, c) in candidates:
        size_after, _ = simulate_move_group_target(
            board, r, c, target_color, min_group_size, color_probs, special_spawn_rate
        )
        delta = size_after - current_size

        if (delta > best_delta) or (delta == best_delta and size_after > best_size) or (delta == best_delta and size_after == best_size and tie_break_key(r, c) > tie_break_key(*best_move) if best_move else True):
            best_delta = delta
            best_size = size_after
            best_move = (r, c)
    
    print(f"[DEBUG] Color objetivo {target_color}, mejor grupo tras simulación: {best_size}, celda {best_move}")

    if best_move is None:
        for i in range(rows):
            for j in range(cols):
                if board[i][j] not in ('.','X'):
                    return i, j, target_color
        return 0, 0, target_color

    return best_move[0], best_move[1], target_color

def play_game(game):
    print(f"Playing game {game['id']}")
    status = get_status(game['id'])
    goal_type = game['goal_type']
    goal_params = game['goal_params']
    special_spawn_rate = game['special_spawn_rate']
    if goal_type == "color_target":
        remaining = goal_params['color_requirements']
    if goal_type == "group_target":
        min_group_size = goal_params['min_group_size']
        locked_target_color = None

    while status['status'] == 'in_progress':
        board_str = status['board_string']
        board = board_to_matrix(board_str)
        color_probs = game['colors']

        if goal_type == "score_target":
            row, col = find_best_move_score_target(board, color_probs, special_spawn_rate)
        if goal_type == "color_target":
            row, col = find_best_move_color_target(board, color_probs, special_spawn_rate, remaining)
        if goal_type == "group_target":
            row, col, locked_target_color = find_best_move_group_target(board, color_probs, special_spawn_rate, min_group_size, locked_target_color)

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

def run_all_games():
    start_time = time.time()
    games = get_games()
    count = 0
    turns = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(games)) as executor:
        future_to_game = {executor.submit(play_game, game): game for game in games}

        for future in concurrent.futures.as_completed(future_to_game):
            game = future_to_game[future]
            try:
                future.result() 
                status = get_status(game['id'])
                turns.append({f'game {game["id"]}': status['turn_count']})
                count += status['turn_count']
            except Exception as e:
                print(f"Error en juego {game['id']}: {e}")

    print(f'La cantidad total de turnos es: {count}')
    print(turns)
    end_time = time.time()  
    elapsed_time = end_time - start_time
    print(f"Tiempo total: {elapsed_time:.2f} segundos")

run_all_games()
