import time
from collections import deque
import itertools
from itertools import product

class Sudoku:
    def __init__(self, sudoku):
        self.grid = sudoku
        self.recent_requests = deque()
        self.initial_grid = [row[:] for row in sudoku]

    def __str__(self):
        string_representation = "| - - - - - - - - - - - |\n"

        for i in range(9):
            string_representation += "| "
            for j in range(9):
                string_representation += str(self.grid[i][j])
                string_representation += " | " if j % 3 == 2 else " "

            if i % 3 == 2:
                string_representation += "\n| - - - - - - - - - - - |"
            string_representation += "\n"

        return string_representation

    def check_row(self, row, base_delay=0.01, interval=10, threshold=5):
        self._limit_calls(base_delay, interval, threshold)
        if sum(self.grid[row]) != 45 or len(set(self.grid[row])) != 9:
            return False
        return True

    def check_column(self, col, base_delay=0.01, interval=10, threshold=5):
        self._limit_calls(base_delay, interval, threshold)
        if sum([self.grid[row][col] for row in range(9)]) != 45 or len(set([self.grid[row][col] for row in range(9)])) != 9:
            return False
        return True

    def check_square(self, row, col, base_delay=0.01, interval=10, threshold=5):
        self._limit_calls(base_delay, interval, threshold)
        square = [self.grid[row + i][col + j] for i in range(3) for j in range(3)]
        if sum(square) != 45 or len(set(square)) != 9:
            return False
        return True

    def check(self, base_delay=0.01, interval=10, threshold=5):
        for row in range(9):
            if not self.check_row(row, base_delay, interval, threshold):
                return False
        for col in range(9):
            if not self.check_column(col, base_delay, interval, threshold):
                return False
        for i in range(3):
            for j in range(3):
                if not self.check_square(i * 3, j * 3, base_delay, interval, threshold):
                    return False
        return True

    def _limit_calls(self, base_delay=0.01, interval=10, threshold=5):
            """Limit the number of requests made to the Sudoku object."""
            if base_delay is None:
                base_delay = self.base_delay
            if interval is None:
                interval = self.interval
            if threshold is None:
                threshold = self.threshold

            current_time = time.time()
            self.recent_requests.append(current_time)
            num_requests = len(
                [t for t in self.recent_requests if current_time - t < interval]
            )

            if num_requests > threshold:
                delay = base_delay * (num_requests - threshold + 1)
                time.sleep(delay)

    def is_valid_partial(self, part):
        for row in part:
            seen_numbers = set()
            for num in row:
                if num != 0:
                    if num in seen_numbers:
                        return False
                    seen_numbers.add(num)

        for col in range(9):
            seen_numbers = set()
            for row in range(len(part)):
                num = part[row][col]
                if num != 0:
                    if num in seen_numbers:
                        return False
                    seen_numbers.add(num)

        return True


    def solve(self, grid):
        def generate_combinations(current_combo, remaining_positions):
            if not remaining_positions:
                all_combinations.append(tuple(current_combo))
                return
            for number in range(1, 10):
                current_combo.append(number)
                generate_combinations(current_combo, remaining_positions[1:])
                current_combo.pop()

        empty_positions = []
        for row in range(len(grid)):
            for col in range(9):
                if grid[row][col] == 0:
                    empty_positions.append((row, col))

        all_combinations = []
        generate_combinations([], empty_positions)

        solutions = []
        validation_count = 0

        def try_combination(combo):
            nonlocal validation_count
            for (pos, num) in zip(empty_positions, combo):
                row, col = pos
                grid[row][col] = num
                validation_count += 1

            if self.is_valid_partial(grid):
                solutions.append([row[:] for row in grid])

            for pos in empty_positions:
                row, col = pos
                grid[row][col] = 0

        for combo in all_combinations:
            try_combination(combo)

        return solutions, validation_count


if __name__ == "__main__":
    sudoku = Sudoku([
        [8, 2, 7, 1, 5, 4, 3, 9, 6],
        [9, 6, 5, 3, 2, 7, 1, 4, 8], 
        [3, 4, 1, 6, 8, 9, 7, 5, 2],
        [5, 0, 3, 4, 6, 8, 2, 7, 1], 
        [4, 7, 2, 5, 1, 3, 6, 8, 9], 
        [6, 1, 8, 9, 7, 2, 4, 3, 5], 
        [7, 0, 6, 2, 3, 5, 9, 1, 4], 
        [1, 5, 4, 7, 9, 6, 8, 2, 3], 
        [2, 3, 9, 8, 4, 1, 5, 6, 7]
    ])
    print("Initial Sudoku:")
    print(sudoku)

    solutions, validations = sudoku.solve(sudoku.grid)

    print("Solutions:")

    for i in range(len(solutions)):
        print(f"Solution {i + 1}:")
        print(Sudoku(solutions[i]))
        print()

    print(f"Validations: {validations}")


   
