import os
import json
import base64
import requests
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
DATA_FILE = "data.json"

def get_github_data():
    """GitHub 저장소에서 data.json 가져오기"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f), None
        return [], None

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        file_info = res.json()
        content = base64.b64decode(file_info["content"]).decode("utf-8")
        return json.loads(content), file_info["sha"]
    return [], None

def save_github_data(data):
    """GitHub 저장소에 data.json 영구 저장하기"""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    _, sha = get_github_data()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    content_str = json.dumps(data, ensure_ascii=False, indent=2)
    b64_content = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")

    payload = {
        "message": "Update household ledger data",
        "content": b64_content
    }
    if sha:
        payload["sha"] = sha

    res = requests.put(url, headers=headers, json=payload)
    return res.status_code in [200, 201]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>부부 가계부</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-800 pb-12">
    <div class="max-w-md mx-auto p-4">
        <!-- 헤더 -->
        <div class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 mb-4 flex justify-between items-center">
            <div>
                <h1 class="text-xl font-bold text-gray-900">가계부</h1>
                <p class="text-xs text-gray-400 mt-1">실시간 GitHub 영구 보존 연동</p>
            </div>
            <button onclick="loadData()" class="p-2 text-gray-500 hover:text-blue-600 active:scale-95 transition">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
            </button>
        </div>

        <!-- 이번 달 요약 카드 -->
        <div class="grid grid-cols-2 gap-3 mb-4">
            <div class="bg-emerald-50 border border-emerald-100 rounded-2xl p-4">
                <span class="text-xs text-emerald-600 font-semibold">총 수입</span>
                <p id="total-income" class="text-lg font-bold text-emerald-700 mt-1">0원</p>
            </div>
            <div class="bg-rose-50 border border-rose-100 rounded-2xl p-4">
                <span class="text-xs text-rose-600 font-semibold">총 지출</span>
                <p id="total-expense" class="text-lg font-bold text-rose-700 mt-1">0원</p>
            </div>
        </div>

        <!-- 입력 폼 -->
        <div class="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 mb-5">
            <form id="tx-form" onsubmit="handleSubmit(event)" class="space-y-3">
                <div class="flex gap-2">
                    <button type="button" id="btn-expense" onclick="setType('expense')" class="flex-1 py-2 rounded-xl text-sm font-bold bg-rose-500 text-white transition shadow-sm">지출</button>
                    <button type="button" id="btn-income" onclick="setType('income')" class="flex-1 py-2 rounded-xl text-sm font-bold bg-gray-100 text-gray-500 transition">수입</button>
                </div>

                <div class="grid grid-cols-2 gap-2">
                    <input type="date" id="date" required class="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-blue-500 bg-gray-50" />
                    <input type="number" id="amount" placeholder="금액" required class="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-blue-500 bg-gray-50" />
                </div>

                <div class="grid grid-cols-2 gap-2">
                    <input type="text" id="user" placeholder="작성자(남편/아내)" required class="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-blue-500 bg-gray-50" />
                    <input type="text" id="category" placeholder="카테고리(식비 등)" required class="border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-blue-500 bg-gray-50" />
                </div>

                <input type="text" id="desc" placeholder="내용 (선택)" class="w-full border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-blue-500 bg-gray-50" />

                <button type="submit" id="submit-btn" class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-sm shadow-md active:scale-95 transition">
                    기록 저장하기
                </button>
            </form>
        </div>

        <!-- 내역 리스트 -->
        <div class="space-y-2">
            <div class="flex justify-between items-center px-1">
                <span class="text-xs font-semibold text-gray-400">내역 목록</span>
                <span id="list-count" class="text-xs text-gray-400">0건</span>
            </div>
            <div id="tx-list" class="space-y-2">
                <div class="text-center py-8 text-gray-400 text-sm">불러오는 중...</div>
            </div>
        </div>
    </div>

    <script>
        let currentType = 'expense';
        let txData = [];

        document.getElementById('date').valueAsDate = new Date();

        function setType(type) {
            currentType = type;
            const bExp = document.getElementById('btn-expense');
            const bInc = document.getElementById('btn-income');
            if(type === 'expense') {
                bExp.className = 'flex-1 py-2 rounded-xl text-sm font-bold bg-rose-500 text-white transition shadow-sm';
                bInc.className = 'flex-1 py-2 rounded-xl text-sm font-bold bg-gray-100 text-gray-500 transition';
            } else {
                bInc.className = 'flex-1 py-2 rounded-xl text-sm font-bold bg-emerald-500 text-white transition shadow-sm';
                bExp.className = 'flex-1 py-2 rounded-xl text-sm font-bold bg-gray-100 text-gray-500 transition';
            }
        }

        async function loadData() {
            try {
                const res = await fetch('/api/data');
                txData = await res.json();
                render();
            } catch(e) {
                alert('데이터 불러오기 실패');
            }
        }

        function render() {
            let inc = 0, exp = 0;
            const listEl = document.getElementById('tx-list');
            listEl.innerHTML = '';

            txData.slice().reverse().forEach((item, idx) => {
                const amt = parseInt(item.amount);
                if(item.type === 'income') inc += amt;
                else exp += amt;

                const originalIndex = txData.length - 1 - idx;
                const card = document.createElement('div');
                card.className = 'bg-white border border-gray-100 rounded-xl p-4 shadow-sm flex items-center justify-between';
                card.innerHTML = `
                    <div class="flex flex-col">
                        <div class="flex items-center gap-2">
                            <span class="px-2 py-0.5 rounded text-[11px] font-semibold ${item.type === 'income' ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}">${item.category}</span>
                            <span class="text-xs font-semibold text-gray-700">${item.user}</span>
                            <span class="text-xs text-gray-400">${item.date}</span>
                        </div>
                        <span class="text-xs text-gray-500 mt-1">${item.desc || '-'}</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <span class="font-bold text-sm ${item.type === 'income' ? 'text-emerald-600' : 'text-rose-600'}">
                            ${item.type === 'income' ? '+' : '-'}${amt.toLocaleString()}원
                        </span>
                        <button onclick="deleteItem(${originalIndex})" class="text-gray-300 hover:text-red-500 text-xs">삭제</button>
                    </div>
                `;
                listEl.appendChild(card);
            });

            if(txData.length === 0) {
                listEl.innerHTML = '<div class="text-center py-8 text-gray-400 text-sm">기록된 내역이 없습니다.</div>';
            }

            document.getElementById('total-income').innerText = inc.toLocaleString() + '원';
            document.getElementById('total-expense').innerText = exp.toLocaleString() + '원';
            document.getElementById('list-count').innerText = txData.length + '건';
        }

        async function handleSubmit(e) {
            e.preventDefault();
            const btn = document.getElementById('submit-btn');
            btn.innerText = '저장 중...';
            btn.disabled = true;

            const newItem = {
                date: document.getElementById('date').value,
                amount: document.getElementById('amount').value,
                user: document.getElementById('user').value,
                category: document.getElementById('category').value,
                desc: document.getElementById('desc').value,
                type: currentType
            };

            const updatedList = [...txData, newItem];

            try {
                const res = await fetch('/api/data', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: jsonStringify(updatedList)
                });
                if(res.ok) {
                    txData = updatedList;
                    document.getElementById('amount').value = '';
                    document.getElementById('desc').value = '';
                    render();
                } else {
                    alert('저장에 실패했습니다.');
                }
            } catch(err) {
                alert('네트워크 오류');
            } finally {
                btn.innerText = '기록 저장하기';
                btn.disabled = false;
            }
        }

        function jsonStringify(obj) {
            return JSON.stringify(obj);
        }

        async function deleteItem(idx) {
            if(!confirm('삭제하시겠습니까?')) return;
            const updatedList = txData.filter((_, i) => i !== idx);
            const res = await fetch('/api/data', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: jsonStringify(updatedList)
            });
            if(res.ok) {
                txData = updatedList;
                render();
            }
        }

        loadData();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/data", methods=["GET"])
def get_data():
    data, _ = get_github_data()
    return jsonify(data)

@app.route("/api/data", methods=["POST"])
def update_data():
    new_data = request.get_json()
    success = save_github_data(new_data)
    if success:
        return jsonify({"status": "success"}), 200
    return jsonify({"status": "error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
