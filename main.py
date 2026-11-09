import os
import random
import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

# 記憶體儲存遊戲狀態與全域戰績統計 (任務三)
games_db: Dict[str, dict] = {}
global_stats = {"played": 0, "wins": 0}

class NewGameRequest(BaseModel):
    hard_mode: Optional[bool] = False

class GuessRequest(BaseModel):
    game_id: str
    guess: str


@app.post("/api/new-game")
def start_new_game(req: NewGameRequest = None):
    """ 建立新一局遊戲，可帶入 hard_mode 設定 """
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    hard_mode = req.hard_mode if req else False
    
    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "hard_mode": hard_mode,
        "locked_greens": {}  # 任務四：Hard Mode 鎖定位置 {index: letter}
    }
    return {"game_id": game_id, "message": "New game started!", "hard_mode": hard_mode}


@app.post("/api/guess")
def process_guess(req: GuessRequest):
    """ 接收玩家猜測，進行字典庫檢查、Hard Mode 驗證與比對回傳 """
    game_id = req.game_id
    guess = req.guess.upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")
    
    if len(guess) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    # 任務二：後端字典庫驗證，若不在 WORD_BANK 中則回傳 HTTP 400
    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Not in word list (Invalid word).")

    game_data = games_db[game_id]
    target = game_data["target"]
    hard_mode = game_data["hard_mode"]
    locked_greens = game_data["locked_greens"]

    # 任務四：Hard Mode 邏輯驗證（先前已確定的綠色字母必須在對應位置保留）
    if hard_mode:
        for idx, letter in locked_greens.items():
            if guess[idx] != letter:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Hard Mode: Position {idx+1} must be '{letter}'."
                )

    feedback = ["absent"] * 5  
    target_letter_counts = {}

    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    # 1. 標記綠色 correct 並紀錄 Hard Mode 鎖定位置
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1
            if hard_mode:
                locked_greens[i] = guess[i]

    # 2. 標記黃色 present
    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts[guess[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    is_correct = (guess == target)
    
    # 更新勝負統計 (任務三)
    if game_data["status"] == "PLAYING":
        if is_correct:
            game_data["status"] = "WON"
            global_stats["played"] += 1
            global_stats["wins"] += 1
        else:
            # 假設此處如果判定次數已滿或需要累計場次 (可由前端送錯控制，或當作結束結算)
            pass

    # 任務一：若猜對或後端判斷結束，回傳 target_word
    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "target_word": target,  # 任務一規定：需正確回傳 target_word
        "stats": global_stats
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)