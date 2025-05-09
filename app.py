from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

BOOKSTACK_URL = os.getenv("BOOKSTACK_URL")
BOOKSTACK_TOKEN_ID = os.getenv("BOOKSTACK_TOKEN_ID")
BOOKSTACK_TOKEN_SECRET = os.getenv("BOOKSTACK_TOKEN_SECRET")

@app.route("/teams-to-bookstack", methods=["POST"])
def handle_compose_action():
    data = request.json
    message = data.get("message", "")
    channel = data.get("channel", "Inbox")

    books_response = requests.get(f"{BOOKSTACK_URL}/api/books", headers={
        "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
    })

    if books_response.status_code != 200:
        return jsonify({"error": "Failed to fetch books", "details": books_response.text}), 500

    books = books_response.json()
    book = next((b for b in books.get("data", []) if b["name"] == channel), None)

    if not book:
        new_book_response = requests.post(f"{BOOKSTACK_URL}/api/books", headers={
            "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
        }, json={
            "name": channel,
            "description": f"{channel} チャンネルからの送信"
        })

        if new_book_response.status_code != 200:
            return jsonify({"error": "Failed to create book", "details": new_book_response.text}), 500

        book = new_book_response.json()

    page_response = requests.post(f"{BOOKSTACK_URL}/api/pages", headers={
        "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
    }, json={
        "book_id": book["id"],
        "name": message[:40],
        "markdown": message
    })

    if page_response.status_code != 200:
        return jsonify({"error": "Failed to create page", "details": page_response.text}), 500

    page = page_response.json()

    return jsonify({
        "composeExtension": {
            "type": "result",
            "attachmentLayout": "list",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.hero",
                    "content": {
                        "title": "BookStackへ送信完了",
                        "text": f"ページ: {page['name']} を作成しました。",
                        "buttons": [
                            {
                                "type": "openUrl",
                                "title": "開く",
                                "value": page["url"]
                            }
                        ]
                    }
                }
            ]
        }
    })
