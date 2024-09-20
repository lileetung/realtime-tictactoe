import asyncio
import websockets
import json
import uuid

# Game state
games = {}

class TicTacToe:
    def __init__(self):
        self.board = [" "] * 9
        self.current_player = "X"
        self.winner = None

    def make_move(self, position):
        if self.board[position] == " " and not self.winner:
            self.board[position] = self.current_player
            if self.check_winner():
                self.winner = self.current_player
            elif " " not in self.board:
                self.winner = "Tie"
            else:
                self.current_player = "O" if self.current_player == "X" else "X"
            return True
        return False

    def check_winner(self):
        win_combinations = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Rows
            [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Columns
            [0, 4, 8], [2, 4, 6]  # Diagonals
        ]
        return any(self.board[i] == self.board[j] == self.board[k] != " "
                   for i, j, k in win_combinations)

async def game_handler(websocket, path):
    game_id = path.split("/")[-1]
    
    if game_id == "new":
        game_id = str(uuid.uuid4())
        games[game_id] = {"game": TicTacToe(), "players": []}
        await websocket.send(json.dumps({"action": "new_game", "game_id": game_id}))
    
    if game_id not in games:
        await websocket.send(json.dumps({"action": "error", "message": "Game not found"}))
        return
    
    game = games[game_id]
    game["players"].append(websocket)
    player = "X" if len(game["players"]) == 1 else "O"
    
    try:
        await websocket.send(json.dumps({"action": "player_assign", "player": player}))
        if len(game["players"]) == 2:
            await broadcast(game_id, {"action": "game_start"})
        
        async for message in websocket:
            data = json.loads(message)
            if data["action"] == "move":
                if game["game"].current_player == player:
                    if game["game"].make_move(data["position"]):
                        if game["game"].winner:
                            await broadcast(game_id, {"action": "game_over", "board": game["game"].board, "winner": game["game"].winner})
                        else:
                            await broadcast(game_id, {"action": "update", "board": game["game"].board, "current_player": game["game"].current_player})
    finally:
        game["players"].remove(websocket)
        if not game["players"]:
            del games[game_id]

async def broadcast(game_id, message):
    if game_id in games:
        await asyncio.gather(
            *[player.send(json.dumps(message)) for player in games[game_id]["players"]]
        )

if __name__ == "__main__":
    start_server = websockets.serve(game_handler, "0.0.0.0", 8765)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
