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
    message = data.get("message", "")
    book_name = data.get("channel", "Inbox")

    # Book ID を取得
    books = requests.get(f"{BOOKSTACK_URL}/api/books", headers={
        "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
    }).json()

    book = next((b for b in books.get("data", []) if b["name"] == book_name), None)
    
    # Bookが存在しない場合は新規作成
    if not book:
        # 新しいBookを作成
        new_book_response = requests.post(f"{BOOKSTACK_URL}/api/books", headers={
            "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
        }, json={
            "name": book_name,
            "description": f"Created for channel: {book_name}"
        })
        
        if new_book_response.status_code not in [200, 201]:
            print(f"BookStack API Error: {new_book_response.status_code}")
            print(f"Response: {new_book_response.text}")
            return jsonify({"error": "Book creation failed", "details": new_book_response.text}), new_book_response.status_code
            
        book = new_book_response.json()

    # ページを作成
    page = requests.post(f"{BOOKSTACK_URL}/api/pages", headers={
        "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
    }, json={
        "book_id": book["id"],
        "name": message[:40],  # タイトルに使う（先頭40文字）
        "markdown": message
    })

    return jsonify(page.json()), page.status_code
