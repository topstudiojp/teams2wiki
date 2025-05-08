from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

BOOKSTACK_URL = os.getenv("BOOKSTACK_URL")
BOOKSTACK_TOKEN_ID = os.getenv("BOOKSTACK_TOKEN_ID")
BOOKSTACK_TOKEN_SECRET = os.getenv("BOOKSTACK_TOKEN_SECRET")

@app.route("/teams-to-bookstack", methods=["POST"])
def handle_post():
    data = request.json
    text = data.get("text", "")
    
    # 形式: "本文 @チャンネル"
    if "@" not in text:
        return jsonify({"error": "Invalid format. Use: message @channel"}), 400

    message, channel = map(str.strip, text.split("@", 1))
    book_name = channel or "Inbox"

    # Bookを取得
    books = requests.get(f"{BOOKSTACK_URL}/api/books", headers={
        "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
    }).json()

    book = next((b for b in books.get("data", []) if b["name"] == book_name), None)

    if not book:
        new_book_response = requests.post(f"{BOOKSTACK_URL}/api/books", headers={
            "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
        }, json={
            "name": book_name,
            "description": f"{book_name} チャンネルからの送信"
        })
        book = new_book_response.json()

    # ページ作成
    page_payload = {
        "name": "Teamsメッセージ",
        "markdown": message
    }

    page = requests.post(f"{BOOKSTACK_URL}/api/books/{book['id']}/pages", headers={
        "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
    }, json=page_payload).json()

    return jsonify({
        "name": page["name"],
        "url": page["url"]
    })
