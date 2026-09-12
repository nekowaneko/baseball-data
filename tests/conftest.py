#測試共用設定：路徑、fixture 讀取、以及封鎖真實網路連線
import json
import os
import socket
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_DIR = os.path.join(ROOT, 'tests', 'fixtures')
if ROOT not in sys.path:  #讓測試能以 core.xxx 匯入專案模組
    sys.path.insert(0, ROOT)


#全測試期間封鎖對外連線，任何嘗試都直接失敗（驗收項 V17）
@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError('測試期間不得連線外部服務')

    monkeypatch.setattr(socket.socket, 'connect', refuse)
    monkeypatch.setattr(socket.socket, 'connect_ex', refuse)
    monkeypatch.setattr(socket, 'create_connection', refuse)


#fixture 根目錄
@pytest.fixture(scope='session')
def fixtures_dir():
    return FIXTURES_DIR


#讀取 MHT fixture 的主文件 HTML，依分頁名稱取用並快取
@pytest.fixture(scope='session')
def page():
    from core import mht

    cache = {}

    def get(name):
        if name not in cache:
            path = os.path.join(FIXTURES_DIR, 'mht', f'short-stop-{name}.mht')
            with open(path, 'rb') as f:
                cache[name] = mht.main_page(f.read())
        return cache[name]

    return get


#讀取 JSON fixture
@pytest.fixture(scope='session')
def load_json():
    def get(name):
        with open(os.path.join(FIXTURES_DIR, name), encoding='utf-8') as f:
            return json.load(f)

    return get


#讀取 config/ 設定檔（便宜批次的產出，只讀不改）
@pytest.fixture(scope='session')
def load_config():
    def get(name):
        with open(os.path.join(ROOT, 'config', name), encoding='utf-8') as f:
            return json.load(f)

    return get
