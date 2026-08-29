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
    if not GITHUB_TOKEN or not GITHUB_REPO:
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f), None
            except:
                return [], None
        return [], None

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            file_info = res.json()
            content = base64.b64decode(file_info["content"]).decode("utf-8")
            return json.loads(content), file_info["sha"]
    except:
        pass
    return [], None

def save_github_data(data):
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
        "message": "Update ledger data",
        "content": b64_content
    }
    if sha:
        payload["sha"] = sha

    try:
        res = requests.put(url, headers=headers, json=payload)
        return res.status_code in [200, 201]
    except:
        return False

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>가계부</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 15px; background-color: #f4f6f8; }
        .container { max-width: 500px; margin: 0 auto; background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h2 { text-align: center; margin-top: 0; color: #333; }
        .summary { display: flex; justify-content: space-between; margin-bottom: 20px; padding: 12px; background: #eef2f6; border-radius: 8px; font-weight: bold; }
        .form-group { margin-bottom: 12px; }
        label { display: block; font-size: 13px; color: #666; margin-bottom: 4px; }
        input, select { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 6px; box-sizing: border-box; font-size: 14px; }
        .type-btns { display: flex; gap: 8px; margin-bottom: 12px; }
        .type-btn { flex: 1; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .btn-exp { background: #ff4d4f; color: white; }
        .btn-inc { background: #e0e0e0; color: #333; }
        .btn-submit { width: 100%; padding: 12px; background: #1890ff; color: white; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; }
        .list-title { margin-top: 25px; font-size: 15px; font-weight: bold; color: #333; border-bottom: 1px solid #eee; padding-bottom: 8px; }
        .item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f0f0f0; }
        .item-info { font-size: 13px; color: #555; }
        .item-amt { font-weight: bold; font-size: 14px; }
        .amt-exp { color: #ff4d4f; }
        .amt-inc { color: #52c41a; }
        .btn-del { border: none; background: none; color: #999; cursor: pointer; font-size: 12px; margin-left: 8px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>가계부</h2>
        <div class="summary">
            <span style="color:#52c41a">수입: <span id="tot-inc">0</span>원</span>
            <span style="color:#ff4d4f">지출: <span id="tot-exp">0</span>원</span>
        </div>

        <div class="type-btns">
            <button type="button" id="b-exp" class="type-btn btn-exp" onclick="setType('expense')">지출</button>
            <button type="button" id="b-inc" class="type-btn btn-inc" onclick="setType('income')">수입</button>
        </div>

        <form id="f" onsubmit="save(event)">
            <div class="form-group">
                <label>날짜</label>
                <input type="date" id="date" required>
            </div>
            <div class="form-group">
                <label>작성자</label>
                <input type="text" id="user" placeholder="남편 / 아내" required>
            </div>
            <div class="form-group">
                <label>카테고리</label>
                <input type="text" id="category" placeholder="식비, 생활용품 등" required>
            </div>
            <div class="form-group">
                <label>금액</label>
                <input type="number" id="amount" placeholder="금액 입력" required>
            </div>
            <div class="form-group">
                <label>메모</label>
                <input type="text" id="desc" placeholder="메모 (선택사항)">
            </div>
            <button type="submit" id="s-btn" class="btn-submit">등록하기</button>
        </form>

        <div class="list-title">내역 목록</div>
        <div id="list"></div>
    </div>

    <script>
        let curType = 'expense';
        let records = [];
        document.getElementById('date').valueAsDate = new Date();

        function setType(t) {
            curType = t;
            if(t === 'expense') {
                document.getElementById('b-exp').className = 'type-btn btn-exp';
                document.getElementById('b-exp').style.background = '#ff4d4f';
                document.getElementById('b-exp').style.color = 'white';
                document.getElementById('b-inc').className = 'type-btn btn-inc';
                document.getElementById('b-inc').style.background = '#e0e0e0';
                document.getElementById('b-inc').style.color = '#333';
            } else {
                document.getElementById('b-inc').className = 'type-btn btn-exp';
                document.getElementById('b-inc').style.background = '#52c41a';
                document.getElementById('b-inc').style.color = 'white';
                document.getElementById('b-exp').className = 'type-btn btn-inc';
                document.getElementById('b-exp').style.background = '#e0e0e0';
                document.getElementById('b-exp').style.color = '#333';
            }
        }

        async function load() {
            try {
                const res = await fetch('/api/data');
                records = await res.json();
                render();
            } catch(e){}
        }

        function render() {
            let inc = 0, exp = 0;
            const l = document.getElementById('list');
            l.innerHTML = '';

            records.slice().reverse().forEach((r, idx) => {
                const amt = parseInt(r.amount);
                if(r.type === 'income') inc += amt;
                else exp += amt;

                const origIdx = records.length - 1 - idx;
                const d = document.createElement('div');
                d.className = 'item';
                d.innerHTML = `
                    <div class="item-info">
                        <strong>[${r.category}]</strong> ${r.user} (${r.date})<br>
                        ${r.desc || ''}
                    </div>
                    <div>
                        <span class="item-amt ${r.type === 'income' ? 'amt-inc' : 'amt-exp'}">
                            ${r.type === 'income' ? '+' : '-'}${amt.toLocaleString()}원
                        </span>
                        <button class="btn-del" onclick="del(${origIdx})">✕</button>
                    </div>
                `;
                l.appendChild(d);
            });

            document.getElementById('tot-inc').innerText = inc.toLocaleString();
            document.getElementById('tot-exp').innerText = exp.toLocaleString();
        }

        async function save(e) {
            e.preventDefault();
            const btn = document.getElementById('s-btn');
            btn.innerText = '저장 중...';
            btn.disabled = true;

            const item = {
                date: document.getElementById('date').value,
                user: document.getElementById('user').value,
                category: document.getElementById('category').value,
                amount: document.getElementById('amount').value,
                desc: document.getElementById('desc').value,
                type: curType
            };

            records.push(item);
            await fetch('/api/data', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(records)
            });

            document.getElementById('amount').value = '';
            document.getElementById('desc').value = '';
            btn.innerText = '등록하기';
            btn.disabled = false;
            render();
        }

        async function del(idx) {
            if(!confirm('삭제하시겠습니까?')) return;
            records.splice(idx, 1);
            await fetch('/api/data', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(records)
            });
            render();
        }

        load();
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
    save_github_data(new_data)
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
