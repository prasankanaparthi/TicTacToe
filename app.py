# app.py
from flask import Flask, render_template, jsonify, request
from uuid import uuid4
from game_logic import TicTacToeGame, MinimaxAI
from typing import Dict
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

# In-memory games store (simple). Format: games[g_id] = TicTacToeGame()
games: Dict[str, TicTacToeGame] = {}

# Default AI difficulty: 'hard' (supports 'easy','medium','hard')
DEFAULT_AI_MODE = "hard"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/new", methods=["POST"])
def api_new():
    """
    Create a new game. Optional JSON body: {"starting_player": "X" or "O", "ai_mode": "easy|medium|hard"}
    Returns: {"game_id": "...", "state": {...}}
    """
    body = request.get_json(silent=True) or {}
    starting = body.get("starting_player", "X")
    ai_mode = body.get("ai_mode", DEFAULT_AI_MODE)

    g = TicTacToeGame(starting_player=starting)
    g_id = str(uuid4())
    games[g_id] = {
        "game": g,
        "ai_mode": ai_mode,
        "ai": MinimaxAI(ai_player=("O" if starting == "X" else "X"),
                        human_player=("X" if starting == "X" else "O"))
    }  # we store some meta alongside the game

    return jsonify({"game_id": g_id, "state": serialize_game_state(g)})

@app.route("/api/state/<game_id>", methods=["GET"])
def api_state(game_id):
    entry = games.get(game_id)
    if not entry:
        return jsonify({"error": "game not found"}), 404
    return jsonify({"state": serialize_game_state(entry["game"])})

@app.route("/api/move/<game_id>", methods=["POST"])
def api_move(game_id):
    """
    Human makes a move.
    Body: {"index": 0-8}
    Returns: {"state": {...}, "ok": true/false}
    """
    entry = games.get(game_id)
    if not entry:
        return jsonify({"error": "game not found"}), 404

    body = request.get_json(silent=True) or {}
    idx = body.get("index")
    if idx is None or not isinstance(idx, int) or not 0 <= idx <= 8:
        return jsonify({"error": "invalid index"}), 400

    game: TicTacToeGame = entry["game"]
    # Only allow move if it's the human's turn (we infer human player from ai object)
    ai_obj: MinimaxAI = entry["ai"]
    human_player = ai_obj.human_player

    if game.current_player != human_player:
        return jsonify({"error": "not human's turn", "state": serialize_game_state(game)}), 400

    ok = game.make_move(idx)
    return jsonify({"ok": bool(ok), "state": serialize_game_state(game)})

@app.route("/api/ai_move/<game_id>", methods=["POST"])
def api_ai_move(game_id):
    """
    Ask the server to make an AI move for the current game (if it's AI's turn).
    Returns updated state and the move the AI made.
    """
    entry = games.get(game_id)
    if not entry:
        return jsonify({"error": "game not found"}), 404

    game: TicTacToeGame = entry["game"]
    ai_obj: MinimaxAI = entry["ai"]
    ai_mode = entry.get("ai_mode", DEFAULT_AI_MODE)

    if game.is_over():
        return jsonify({"error": "game already finished", "state": serialize_game_state(game)}), 400

    if game.current_player != ai_obj.ai_player:
        return jsonify({"error": "not AI's turn", "state": serialize_game_state(game)}), 400

    move = ai_obj.choose_move(game.board, mode=ai_mode)
    game.make_move(move)
    return jsonify({"move": move, "state": serialize_game_state(game)})

@app.route("/api/reset/<game_id>", methods=["POST"])
def api_reset(game_id):
    entry = games.get(game_id)
    if not entry:
        return jsonify({"error": "game not found"}), 404
    starting = request.get_json(silent=True) or {}
    start_player = starting.get("starting_player", "X")
    entry["game"].reset(starting_player=start_player)
    return jsonify({"state": serialize_game_state(entry["game"])})

# Helper to turn TicTacToeGame into JSON-able dict
def serialize_game_state(game: TicTacToeGame):
    return {
        "board": game.board.to_list(),
        "current_player": game.current_player,
        "winner": game.game_result(),  # 'X'/'O'/'Tie'/None
        "available_moves": game.available_moves(),
        "history": game.history
    }

if __name__ == "__main__":
    # Use debug only during development
    app.run(debug=True)
