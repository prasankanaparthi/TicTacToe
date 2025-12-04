#!/usr/bin/env python3
"""
game_logic.py

Complete Tic-Tac-Toe game logic module.

Classes:
- Board: low-level board representation and utilities.
- TicTacToeGame: higher-level game management (turns, moves, undo, serialize).
- MinimaxAI: AI engine (easy/random, medium/depth-limited, hard/full minimax with alpha-beta).

Run this file to try a simple command-line demo where you play vs AI.
"""

from __future__ import annotations
import math
import random
import json
from typing import List, Optional, Tuple


# -------------------------
# Board: low-level utilities
# -------------------------
class Board:
    def __init__(self, cells: Optional[List[str]] = None):
        # Use 'X', 'O', or '' for empty
        self.cells: List[str] = cells[:] if cells is not None else [""] * 9

    def copy(self) -> "Board":
        return Board(self.cells)

    def available_moves(self) -> List[int]:
        return [i for i, v in enumerate(self.cells) if v == ""]

    def make_move(self, index: int, player: str) -> bool:
        """Place player's mark at index (0-8). Returns True if move succeeded."""
        if 0 <= index < 9 and self.cells[index] == "":
            self.cells[index] = player
            return True
        return False

    def undo_move(self, index: int) -> None:
        self.cells[index] = ""

    def is_full(self) -> bool:
        return "" not in self.cells

    def winner(self) -> Optional[str]:
        """Return 'X' or 'O' if there's a winner, 'Tie' if full with no winner, else None."""
        wins = [
            (0,1,2),(3,4,5),(6,7,8),
            (0,3,6),(1,4,7),(2,5,8),
            (0,4,8),(2,4,6)
        ]
        for a,b,c in wins:
            if self.cells[a] != "" and self.cells[a] == self.cells[b] == self.cells[c]:
                return self.cells[a]
        if self.is_full():
            return "Tie"
        return None

    def __str__(self) -> str:
        def cell(i):
            v = self.cells[i]
            return v if v != "" else str(i+1)
        rows = [
            f" {cell(0)} | {cell(1)} | {cell(2)} ",
            "---+---+---",
            f" {cell(3)} | {cell(4)} | {cell(5)} ",
            "---+---+---",
            f" {cell(6)} | {cell(7)} | {cell(8)} ",
        ]
        return "\n".join(rows)

    def to_list(self) -> List[str]:
        return self.cells[:]

    def to_json(self) -> str:
        return json.dumps(self.cells)

    @classmethod
    def from_json(cls, s: str) -> "Board":
        cells = json.loads(s)
        return cls(cells)


# -------------------------
# TicTacToeGame: game state
# -------------------------
class TicTacToeGame:
    def __init__(self, starting_player: str = "X"):
        if starting_player not in ("X", "O"):
            raise ValueError("starting_player must be 'X' or 'O'")
        self.board = Board()
        self.current_player = starting_player
        self.history: List[Tuple[int,str]] = []  # list of (index, player) for undo
        self.winner_cache: Optional[str] = None

    def reset(self, starting_player: str = "X") -> None:
        self.board = Board()
        self.current_player = starting_player
        self.history.clear()
        self.winner_cache = None

    def make_move(self, index: int) -> bool:
        """Attempt to make a move for current player at index. Returns True if successful."""
        if self.board.winner() is not None:
            return False  # game already finished
        ok = self.board.make_move(index, self.current_player)
        if ok:
            self.history.append((index, self.current_player))
            self.winner_cache = self.board.winner()
            # swap player for next turn only if game not finished
            if self.winner_cache is None:
                self.current_player = "O" if self.current_player == "X" else "X"
        return ok

    def undo(self) -> Optional[Tuple[int,str]]:
        """Undo last move. Returns undone (index, player) or None."""
        if not self.history:
            return None
        index, player = self.history.pop()
        self.board.undo_move(index)
        self.winner_cache = self.board.winner()
        # Set current player to the player who just moved (so they can move again)
        self.current_player = player
        return (index, player)

    def game_result(self) -> Optional[str]:
        """Return 'X' or 'O' if winner, 'Tie' if draw, else None."""
        return self.board.winner()

    def is_over(self) -> bool:
        return self.game_result() is not None

    def available_moves(self) -> List[int]:
        return self.board.available_moves()

    def serialize(self) -> str:
        """Return JSON string capturing the board and current player."""
        return json.dumps({
            "board": self.board.to_list(),
            "current_player": self.current_player,
            "history": self.history
        })

    @classmethod
    def deserialize(cls, s: str) -> "TicTacToeGame":
        data = json.loads(s)
        game = cls(starting_player=data.get("current_player", "X"))
        game.board = Board(data.get("board", [""]*9))
        game.history = data.get("history", [])
        game.winner_cache = game.board.winner()
        return game


# -------------------------
# Minimax AI implementation
# -------------------------
class MinimaxAI:
    def __init__(self, ai_player: str = "O", human_player: Optional[str] = None):
        if ai_player not in ("X", "O"):
            raise ValueError("ai_player must be 'X' or 'O'")
        self.ai_player = ai_player
        self.human_player = human_player if human_player in ("X", "O") else ("O" if ai_player == "X" else "X")

    def choose_move(self, board: Board, mode: str = "hard", depth_limit: Optional[int] = None) -> int:
        """
        mode: 'easy' -> random legal move
              'medium' -> depth-limited minimax (depth_limit must be int)
              'hard' -> full minimax with alpha-beta (optimal)
        """
        moves = board.available_moves()
        if not moves:
            raise ValueError("No moves left")

        if mode == "easy":
            return random.choice(moves)

        if mode == "medium":
            # if no depth_limit provided, set to 2 or 3 based on emptiness
            if depth_limit is None:
                depth_limit = 3 if len(moves) >= 6 else 6
            best_score = -math.inf
            best_move = random.choice(moves)
            for m in moves:
                board.make_move(m, self.ai_player)
                score = self._minimax(board, False, depth_limit - 1, -math.inf, math.inf)
                board.undo_move(m)
                if score > best_score:
                    best_score = score
                    best_move = m
            return best_move

        # hard mode (full depth minimax with alpha-beta)
        best_score = -math.inf
        best_move = random.choice(moves)
        for m in moves:
            board.make_move(m, self.ai_player)
            score = self._minimax(board, False, None, -math.inf, math.inf)
            board.undo_move(m)
            if score > best_score:
                best_score = score
                best_move = m
        return best_move

    def _minimax(self, board: Board, is_ai_turn: bool, depth: Optional[int], alpha: float, beta: float) -> float:
        """
        Returns heuristic score from perspective of self.ai_player.
        +1 => ai win, -1 => human win, 0 => tie.
        If depth is not None, it's a depth-limited search.
        """
        winner = board.winner()
        if winner == self.ai_player:
            return 1.0
        elif winner == self.human_player:
            return -1.0
        elif winner == "Tie":
            return 0.0

        if depth is not None and depth <= 0:
            # heuristic: count two-in-a-row opportunities (simple)
            return self._heuristic(board)

        if is_ai_turn:
            value = -math.inf
            for m in board.available_moves():
                board.make_move(m, self.ai_player)
                value = max(value, self._minimax(board, False, None if depth is None else depth-1, alpha, beta))
                board.undo_move(m)
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return value
        else:
            value = math.inf
            for m in board.available_moves():
                board.make_move(m, self.human_player)
                value = min(value, self._minimax(board, True, None if depth is None else depth-1, alpha, beta))
                board.undo_move(m)
                beta = min(beta, value)
                if alpha >= beta:
                    break
            return value

    def _heuristic(self, board: Board) -> float:
        """
        Basic heuristic for depth-limited evaluation:
        +0.1 for each line where AI could win (no opponent marks),
        -0.1 for each line where human could win.
        """
        score = 0.0
        lines = [
            (0,1,2),(3,4,5),(6,7,8),
            (0,3,6),(1,4,7),(2,5,8),
            (0,4,8),(2,4,6)
        ]
        for a,b,c in lines:
            line = [board.cells[a], board.cells[b], board.cells[c]]
            if self.human_player not in line:
                # only ai and empties
                ai_count = line.count(self.ai_player)
                if ai_count == 2:
                    score += 0.5
                elif ai_count == 1:
                    score += 0.1
            if self.ai_player not in line:
                human_count = line.count(self.human_player)
                if human_count == 2:
                    score -= 0.5
                elif human_count == 1:
                    score -= 0.1
        return score


# -------------------------
# Simple CLI demo / usage
# -------------------------
def human_vs_ai_cli(ai_mode: str = "hard"):
    print("Tic-Tac-Toe CLI — You are X (enter 1-9).")
    game = TicTacToeGame(starting_player="X")
    ai = MinimaxAI(ai_player="O", human_player="X")

    while not game.is_over():
        print(game.board)
        if game.current_player == "X":
            # Human
            try:
                raw = input("Your move (1-9) or 'u' to undo: ").strip().lower()
                if raw == "u":
                    undone = game.undo()
                    if undone:
                        print(f"Undid move {undone}")
                    else:
                        print("Nothing to undo.")
                    continue
                idx = int(raw) - 1
                if idx not in range(9):
                    print("Choose 1-9")
                    continue
                if not game.make_move(idx):
                    print("Invalid move (occupied or game over).")
            except ValueError:
                print("Invalid input.")
        else:
            # AI turn
            move = ai.choose_move(game.board, mode=ai_mode)
            print(f"AI ({ai.ai_player}) plays at {move+1}")
            game.make_move(move)

    # final board and result
    print(game.board)
    res = game.game_result()
    if res == "Tie":
        print("Result: Tie")
    else:
        print(f"Result: {res} wins")


if __name__ == "__main__":
    # Run an interactive demo: human (X) vs AI (O) in hard mode by default.
    print("Running CLI demo. Press Ctrl+C to quit.")
    try:
        human_vs_ai_cli(ai_mode="hard")
    except KeyboardInterrupt:
        print("\nExiting demo.")
