import os
import requests
from aiohttp import web
from botbuilder.core import (
    BotFrameworkAdapterSettings,
    BotFrameworkAdapter,
    TurnContext,
)
from botbuilder.core.integration import aiohttp_error_middleware
from botbuilder.core.teams import TeamsActivityHandler, TeamsMessagingExtensionsAction

# 環境変数
BOOKSTACK_URL = os.getenv("BOOKSTACK_URL")
BOOKSTACK_TOKEN_ID = os.getenv("BOOKSTACK_TOKEN_ID")
BOOKSTACK_TOKEN_SECRET = os.getenv("BOOKSTACK_TOKEN_SECRET")
MICROSOFT_APP_ID = os.getenv("MICROSOFT_APP_ID")！
MICROSOFT_APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD")

class TeamsBookStackBot(TeamsActivityHandler):
    async def on_teams_messaging_extension_submit_action(
        self, turn_context: TurnContext, action: TeamsMessagingExtensionsAction
    ):
        try:
            # メッセージ本文取得
            payload = action.message_payload or {}
            body = payload.get("body", {})
            channel_info = payload.get("channelData", {}).get("channel", {})

            message = body.get("plainText") or body.get("content") or "（本文なし）"
            channel_name = channel_info.get("name") or channel_info.get("id") or "Inbox"

            # BookStack Books 取得
            books_resp = requests.get(
                f"{BOOKSTACK_URL}/api/books",
                headers={"Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"},
            )
            books_resp.raise_for_status()
            books = books_resp.json().get("data", [])
            book = next((b for b in books if b.get("name") == channel_name), None)

            # 未存在なら作成
            if not book:
                create_resp = requests.post(
                    f"{BOOKSTACK_URL}/api/books",
                    headers={"Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"},
                    json={
                        "name": channel_name,
                        "description": f"Teamsチャンネル「{channel_name}」からの送信",
                    },
                )
                create_resp.raise_for_status()
                book = create_resp.json().get("data", create_resp.json())

            # ページ作成
            page_resp = requests.post(
                f"{BOOKSTACK_URL}/api/pages",
                headers={"Authorization": f"Token {BOOKSTACK_TOKEN_ID}:{BOOKSTACK_TOKEN_SECRET}"},
                json={
                    "book_id": book.get("id"),
                    "name": message[:40],
                    "markdown": message,
                },
            )
            page_resp.raise_for_status()
            page = page_resp.json().get("data", page_resp.json())

            # Teams へのレスポンス
            return {
                "composeExtension": {
                    "type": "result",
                    "attachmentLayout": "list",
                    "attachments": [
                        {
                            "contentType": "application/vnd.microsoft.card.hero",
                            "content": {
                                "title": "BookStackへ送信完了",
                                "text": f"ページ『{page.get('name')}』を作成しました。",
                                "buttons": [
                                    {
                                        "type": "openUrl",
                                        "title": "開く",
                                        "value": page.get("url"),
                                    }
                                ],
                            },
                        }
                    ],
                }
            }

        except Exception as e:
            return {
                "composeExtension": {
                    "type": "message",
                    "text": f"エラーが発生しました: {e}"
                }
            }

# Bot とサーバー起動設定
if __name__ == "__main__":
    settings = BotFrameworkAdapterSettings(MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD)
    adapter = BotFrameworkAdapter(settings)
    bot = TeamsBookStackBot()

    app = web.Application(middlewares=[aiohttp_error_middleware])
    # Bot Framework メッセージ受信用
    app.router.add_post(
        "/api/messages", 
        lambda req: adapter.process_activity(
            req, bot.on_turn, req.headers.get("Authorization", ""),
        ),
    )
    # Compose Extension アクション受信用
    app.router.add_post(
        "/teams-to-bookstack", 
        lambda req: adapter.process_activity(
            req, bot.on_turn, req.headers.get("Authorization", ""),
        ),
    )

    port = int(os.getenv("PORT", 3978))
    web.run_app(app, host="0.0.0.0", port=port)
