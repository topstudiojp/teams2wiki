from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

BOOKSTACK_URL = os.getenv("BOOKSTACK_URL")
BOOKSTACK_TOKEN_ID = os.getenv("BOOKSTACK_TOKEN_ID")
BOOKSTACK_TOKEN_SECRET = os.getenv("BOOKSTACK_TOKEN_SECRET")

@app.route("/api/messages", methods=["POST"])
def dummy_messages():
    return jsonify({"status": "received"}), 200


@app.route("/teams-to-bookstack", methods=["POST"])
def handle_compose_action():
    try:
        data = request.json
        payload = data.get("messagePayload", {})
        body = payload.get("body", {})
        channel_info = payload.get("channelData", {}).get("channel", {})

        message = body.get("plainText") or body.get("content") or "（本文なし）"
        channel_name = channel_info.get("name") or channel_info.get("id") or "Inbox"

        # Book取得
        books_response = requests.get(f"{BOOKSTACK_URL}/api/books", headers={
            "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
        })
        if books_response.status_code != 200:
            return jsonify({"error": "Failed to fetch books", "details": books_response.text}), 500

        books = books_response.json().get("data", [])
        book = next((b for b in books if b["name"] == channel_name), None)

        # なければ作成
        if not book:
            create_response = requests.post(f"{BOOKSTACK_URL}/api/books", headers={
                "Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"
            }, json={
                "name": channel_name,
                "description": f"Teamsチャンネル「{channel_name}」からの送信"
            })
            if create_response.status_code != 200:
                return jsonify({"error": "Failed to create book", "details": create_response.text}), 500
            book = create_response.json()

        # ページ作成（先頭40文字をタイトルに）
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

        # Teamsへの応答
        return jsonify({
            "composeExtension": {
                "type": "result",
                "attachmentLayout": "list",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.hero",
                        "content": {
                            "title": "BookStackへ送信完了",
                            "text": f"ページ「{page['name']}」を作成しました。",
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

    except Exception as e:
        return jsonify({"error": "Unexpected error", "details": str(e)}), 500
