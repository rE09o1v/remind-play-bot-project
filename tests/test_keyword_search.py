'''
フリーワード検索テスト用スクリプト

このスクリプトを実行すると、コンソールから検索キーワードを入力し、
`YTDLSource.search` を使って YouTube の上位 5 件を取得して表示します。

実行例:
    (venv) $ python test_keyword_search.py
    検索キーワード> lo-fi hip hop
    1. Lofi Hip Hop Radio - Beats to Relax/Study to - https://www.youtube.com/watch?v=5qap5aO4i9A
    2. ...
'''

import asyncio
from typing import List

# cogs.music をインポートすると discord.py なども読み込まれます。
# requirements.txt をインストール済みであることを前提とします。
from cogs.music import YTDLSource


async def search_and_print(term: str) -> None:
    """YTDLSource.search を呼び出して結果を表示"""
    results: List[dict] = await YTDLSource.search(term)
    if not results:
        print("検索結果なし")
        return

    print(f"検索結果 ({len(results)}件):")
    for idx, entry in enumerate(results, start=1):
        title = entry.get("title", "<titleなし>")
        url = entry.get("webpage_url", "<urlなし>")
        print(f"{idx}. {title} - {url}")


def main():
    term = input("検索キーワード> ")
    # asyncio.run は Python 3.7+
    asyncio.run(search_and_print(term))


if __name__ == "__main__":
    main()
