from pathlib import Path

import httpx


class Poem:
    def __init__(self):
        self._token_url = "https://v2.jinrishici.com/token"
        self._poem_url = "https://v2.jinrishici.com/sentence"
        self._token = self._init_token()

    def _init_token(self) -> str:
        token_path = Path("./poem_token")
        if not token_path.exists():
            token = self._get_token()
            with token_path.open("w") as f:
                f.write(token)
            return token

        with token_path.open() as f:
            return f.read().strip()

    def _get_token(self) -> str:
        res = httpx.get(self._token_url)
        assert res.status_code == 200, f"poem 请求token失败: {res.status_code}"
        j = res.json()
        assert j["status"] == "success", f"poem 请求token失败: {j['status']}"
        return j["data"]

    def get_poem(self) -> str:
        assert self._token, "poem 无可用token"
        res = httpx.get(self._poem_url, headers={"X-User-Token": self._token})
        assert res.status_code == 200, f"poem 获取诗句失败: {res.status_code}"
        j = res.json()
        assert j["status"] == "success", f"poem 获取诗句失败: {j['status']}"
        return j["data"]["content"]


poem = Poem()
