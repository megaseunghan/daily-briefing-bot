import re
import requests
import os
from datetime import datetime, timedelta
from google import genai

NOTION_KEY = os.environ.get("NOTION_KEY")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)
headers = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

today = datetime.now()
week_ago = today - timedelta(days=7)
today_str = today.strftime("%Y-%m-%d")
week_ago_str = week_ago.strftime("%Y-%m-%d")
first_day_of_month = today.replace(day=1).strftime("%Y-%m-%d")

STORES = [
    {
        "name": "행궁 테네스",
        "chat_id": "-5091670164",
        "dbs": {
            "pnl": "285ef865970a8017ba01d62e7d560fda",
            "survey": "2b5ef865970a80a4a3d1f0e84e98a17e",
            "sales": "301ef865970a80ef8c7cdfac92061b7b",
            "eval": "2e4ef865970a8027ab51e2e587b77176",
            "issue": "28fef865970a804caf13f74366f888fc",
            "meeting": "28fef865970a80219edff308c3b264c4"
        }
    },
    {
        "name": "신동 테네스",
        "chat_id": "-5117853372",
        "dbs": {
            "pnl": "2edef865970a8162a0b1ed6bee8d6878",
            "survey": "2b5ef865970a8088b267ec43bcf38836",
            "sales": "302ef865970a80b6b600d3c729b0c322",
            "eval": "302ef865970a80249b53c8d254adebea",
            "issue": "2edef865970a8123a784fa9d61cb93e2",
            "meeting": "2edef865970a816c842bc617b0aad335"
        }
    },
    {
        "name": "심금",
        "chat_id": "-5162270715",
        "dbs": {
            "pnl": "2edef865970a811886f8e1db38228849",
            "survey": "2b5ef865970a8057aed5ea0ac750e048",
            "sales": "302ef865970a80779bd9c89a66991958",
            "eval": "302ef865970a80b0abffde01de3c3efd",
            "issue": "2edef865970a81fd9f10e10e3363c916",
            "meeting": "2edef865970a81398a8ec4e39df28726"
        }
    },
    {
        "name": "팔달맥주",
        "chat_id": "-5175246647",
        "dbs": {
            "pnl": "2edef865970a81608fb3c8ce808cd539",
            "survey": "2b5ef865970a80b69bcee11f09160f6e",
            "sales": "302ef865970a804a9930daeafc203532",
            "eval": "302ef865970a8016ae5be3e950b56bd1",
            "issue": "2edef865970a81578442c56214d4ccd6",
            "meeting": "2edef865970a81fdae97fd4d817c560e"
        }
    }
]


def get_val(prop):
    if not prop or isinstance(prop, str): return "-"
    ptype = prop.get("type")
    if ptype == "number": return str(prop.get("number"))
    if ptype == "select" and prop.get("select"): return prop["select"].get("name")
    if ptype == "rich_text" and prop.get("rich_text"): return prop["rich_text"][0].get("plain_text", "")
    if ptype == "title" and prop.get("title"): return prop["title"][0].get("plain_text", "")
    if ptype == "formula":
        f_type = prop["formula"].get("type")
        return str(prop["formula"].get(f_type))
    if ptype == "date" and prop.get("date"): return prop["date"].get("start")
    return "-"


def get_array(prop):
    if not prop: return []
    ptype = prop.get("type")
    if ptype == "rollup":
        r_type = prop["rollup"].get("type")
        if r_type == "array" and prop["rollup"]["array"]:
            return [get_val(item) for item in prop["rollup"]["array"]]
    val = get_val(prop)
    return [val] if val != "-" else []


def star_to_num(val):
    if not val or val == "-": return "0"
    clean_val = str(val).replace('\ufe0f', '')
    count = clean_val.count("⭐")
    if count == 0:
        nums = re.findall(r'\d+', str(val))
        return nums[0] if nums else "0"
    return str(count)


def query_db(db_id, payload=None):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    res = requests.post(url, headers=headers, json=payload or {})
    return res.json().get("results", [])


def run_store_briefing(store):
    dbs = store["dbs"]
    msg = f"<b>[ 🏢 {store['name']} 데일리 브리핑 : {today_str} ]</b>\n\n"

    # 1. 손익 요약
    pnl_payload = {"filter": {"property": "날짜", "date": {"on_or_after": first_day_of_month}},
                   "sorts": [{"property": "날짜", "direction": "descending"}], "page_size": 1}
    pnl_data = query_db(dbs["pnl"], pnl_payload)
    msg += "📊 <b>1. 손익 요약 (이번 달)</b>\n"
    msg += "<blockquote>"
    if pnl_data:
        props = pnl_data[0]["properties"]
        labels = sorted([get_val(v) for k, v in props.items() if "(LABEL)" in k])
        for label in labels:
            for ln in label.split('\n'):
                ln = re.sub(r'^\s*\d+\.\s*', '▪️ ', ln)
                ln = re.sub(r'^\s*\d+-\d+\.\s*', 'ㅤㅤ└ ', ln)
                msg += f"{ln}\n"
    else:
        msg += "- 이번 달 데이터 없음\n"
    msg += "</blockquote>\n"

    # 2. 고객 설문
    survey_payload = {"filter": {"property": "응답일시", "date": {"on_or_after": week_ago_str}},
                      "sorts": [{"property": "응답일시", "direction": "ascending"}]}
    survey_data = query_db(dbs["survey"], survey_payload)
    msg += "💬 <b>2. 고객 설문 핵심 피드백</b>\n"
    msg += "<blockquote>"
    if survey_data:
        msg += "<b>(가이드: 맛 / 친절 / 가격)</b>\n──────────────────\n"
        for idx, item in enumerate(survey_data):
            p = item["properties"]
            page_url = item.get("url")
            gender, age = get_val(p.get("성별")), get_val(p.get("연령대"))
            t, k, pr = star_to_num(get_val(p.get("맛/구성 평가"))), star_to_num(get_val(p.get("직원 친절도 평가"))), star_to_num(
                get_val(p.get("가격 대비 만족도 평가")))
            improve, rev_val = get_val(p.get("개선 사항")), get_val(p.get("재방문 의사 여부"))
            will_revisit = "O" if "있다" in rev_val or rev_val == "예" else "X"
            msg += f"<a href='{page_url}'><b>{idx + 1}. {gender}/{age} [재방문:{will_revisit}]</b></a>\nㅤ점수: {t} / {k} / {pr}\n"
            if improve != "-" and improve.strip(): msg += f"ㅤ⚠️ 건의: {improve[:20]}...\n"
            msg += "\n"
    else:
        msg += "- 최근 7일 설문 데이터 없음\n"
    msg += "</blockquote>\n"

    # 3. 주간 매출 일치율
    sales_data = query_db(dbs["sales"], {"page_size": 1})
    msg += "📈 <b>3. 주간 매출 일치율</b>\n"
    msg += "<blockquote>"
    if sales_data:
        p = sales_data[0]["properties"]
        mr = get_val(p.get('매출 일치율'))
        msg += f"총합: {mr}%\n"
        a_n, a_s, e_s = get_array(p.get('실제 날짜')), get_array(p.get('실제 매출액')), get_array(p.get('예상 매출액'))
        for i in range(len(a_n)):
            dt = str(a_n[i])[:10]
            if week_ago_str <= dt <= today_str:
                actual = int(''.join(filter(str.isdigit, str(a_s[i])))) if i < len(a_s) else 0
                expected = int(''.join(filter(str.isdigit, str(e_s[i])))) if i < len(e_s) else 0
                diff = actual - expected
                diff_s = f"🔺+{diff:,}" if diff > 0 else f"🔻{diff:,}"
                msg += f"• {dt[5:].replace('-', '/')} | 실 {actual:,} ↔ 예 {expected:,} ({diff_s})\n"
    msg += "</blockquote>\n"

    # 4. 종합 평가
    eval_data = query_db(dbs["eval"], {"page_size": 1})
    msg += "⭐ <b>4. 종합 평가</b>\n"
    msg += "<blockquote>"
    if eval_data:
        msg += f"{get_val(eval_data[0]['properties'].get('View')).strip()}\n"
    else:
        msg += "- 데이터 없음\n"
    msg += "</blockquote>\n"

    # 5. 주간 이슈
    issue_data = query_db(dbs["issue"], {"filter": {"property": "입력 날짜", "date": {"on_or_after": week_ago_str}},
                                         "sorts": [{"property": "입력 날짜", "direction": "ascending"}]})
    msg += "⚠️ <b>5. 주간 이슈</b>\n"
    msg += "<blockquote>"
    if issue_data:
        for idx, item in enumerate(issue_data):
            p = item["properties"]
            msg += f"{idx + 1}. <b>{get_val(p.get('Log'))}</b>\n"
            for ln in get_val(p.get('이슈')).split('\n'):
                if ln.strip(): msg += f"ㅤㅤ▪️ {re.sub(r'^[-*]\s*', '', ln.strip())}\n"
    else:
        msg += "- 이슈 없음\n"
    msg += "</blockquote>\n"

    # 6. 회의 리마인드
    meeting_data = query_db(dbs["meeting"],
                            {"sorts": [{"property": "입력 날짜", "direction": "descending"}], "page_size": 1})
    msg += "📝 <b>6. 회의 리마인드</b>\n"
    msg += "<blockquote>"
    if meeting_data:
        p = meeting_data[0]["properties"]
        msg += f"<b>[{get_val(p.get('입력 날짜'))}] {get_val(p.get('Log'))}</b>\n"
        for ln in get_val(p.get('내용')).split('\n'):
            if ln.strip(): msg += f"ㅤㅤ▪️ {re.sub(r'^[-*]\s*', '', ln.strip())}\n"
    else:
        msg += "- 회의록 없음\n"
    msg += "</blockquote>\n"

    # 7. AI 요약 (필요시 주석 해제)
    try:
        prompt = f"""너는 다수의 F&B 매장을 운영하는 20대 후반 점장이야. 
    아래 일일 브리핑 데이터를 보고, 오늘 아침 회의에서 직원들과 당장 짚어야 할 '핵심 피드백 및 액션 플랜'을 정확히 5가지만 뽑아줘.

    [분석 기준]
    1. 종합평가 데이터는 아예 제외할 것.
    2. 손익(인건비/원가 비중 등)과 실/예상 매출 차액에서 튀는 지표가 있다면 날카롭게 지적할 것.
    3. 최근 이슈 중 오늘 당장 처리해야 하거나(예: 발주 누락, 시설 보수), 전 직원이 숙지해야 할 사항을 우선할 것.

    [출력 형식]
    - 반드시 '- (내용)' 형태의 개조식으로 딱 5줄만 출력할 것.
    - 부연 설명이나 인사말 절대 금지.
    - 오글거리지 않고, 짧고 직관적인 실무자 말투를 사용할 것. 
    (말투 예시: "- 인건비 비율 25% 초과. 파트타임 스케줄 효율화 방안 논의 필요")

    {msg}"""
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        msg += f"🤖 <b>오늘 회의 핵심 5줄 요약 (AI)</b>\n<blockquote>{response.text.strip()}</blockquote>"
    except Exception as e:
        print(f"AI Error: {e}")

    # 전송
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": store["chat_id"], "text": msg, "parse_mode": "HTML"})


# === 5. 요일/시간별 실행 로직 ===
if __name__ == "__main__":
    now_kst = datetime.utcnow() + timedelta(hours=9)
    weekday = now_kst.weekday()
    hour = now_kst.hour

    targets = []
    if weekday == 3 and hour == 10:  # 목 10시
        targets = ["신동 테네스"]
    elif weekday == 4:  # 금요일
        if hour == 12:
            targets = ["행궁 테네스"]
        elif hour == 13:
            targets = ["심금"]
    elif weekday == 6 and hour == 13:  # 일 13시
        targets = ["팔달맥주"]

    for store in STORES:
        if store["name"] in targets:
            try:
                run_store_briefing(store)
                print(f"{store['name']} 전송 완료")
            except Exception as e:
                print(f"{store['name']} 실패: {e}")
