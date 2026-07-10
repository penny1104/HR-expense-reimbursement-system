# -*- coding: utf-8 -*-
"""HR 智能小助手 - 規則與模糊相似度匹配引擎"""

FAQ_DATABASE = [
    {
        "id": "greeting",
        "category": "general",
        "question": "你好 / 您好",
        "synonyms": ["你好", "您好", "哈囉", "hello", "hi", "嗨", "小助手", "機器人"],
        "answer": "您好！我是 🤖 <b>HR 差旅報銷智能小助手</b>。<br>我能為您解答差旅報銷規定、發票 AI 辨識異常、填寫流程及進度追蹤等問題。<br>您可以直接輸入問題，或是點選快捷按鈕諮詢喔！"
    },
    {
        "id": "fill_process",
        "category": "process",
        "question": "如何填寫報銷單？",
        "synonyms": ["如何填寫", "怎麼填", "報銷流程", "報銷步驟", "填單", "申請步驟", "怎麼報銷"],
        "answer": "<strong>💡 報銷單填寫四部曲：</strong><br>"
                  "1. <b>選單</b>：至左側選單進入【差旅報銷中心】，點選已核准的出差申請單。<br>"
                  "2. <b>掃描</b>：點選明細行最左側的「掃描單據」按鈕，上傳您的發票/收據圖檔（系統將自動啟動 AI 進行 OCR 欄位填寫）。<br>"
                  "3. <b>核對</b>：系統會用框線顏色進行提示。<b>藍色框</b>代表資訊不全需要點選手動補齊，<b>紅色框</b>代表有錯誤或超支（此時需在下方填寫說明理由）。<br>"
                  "4. <b>送出</b>：核對無誤後，點選最下方的【列印並送出】即可列印並發送審核流程！"
    },
    {
        "id": "query_progress",
        "category": "process",
        "question": "報銷進度如何查詢？",
        "synonyms": ["進度", "查詢", "追蹤", "狀態", "簽核", "主管簽核", "會計審查", "退回", "駁回"],
        "answer": "<strong>🔍 報銷進度查詢指南：</strong><br>"
                  "您只需點選左側選單的 <b>【進度追蹤】</b> 即可看到所有送審單據的最新進程：<br>"
                  "- <b>主管/會計核准</b>：流程已通過，已進入財務撥款程序。<br>"
                  "- <b>駁回</b>：退回修改。點入後可以看見【審查意見】，請根據意見修正明細後重新點選「列印送出」即可！"
    },
    {
        "id": "ocr_border_meaning",
        "category": "invoice",
        "question": "OCR 辨識框線顏色意義（紅框、藍框說明）？",
        "synonyms": ["框線", "藍色框", "紅色框", "藍框", "紅框", "框線顏色", "邊框", "顏色意義", "框框", "為什麼是藍色", "為什麼是紅色"],
        "answer": "<strong>🎨 系統欄位框線顏色警示說明：</strong><br>"
                  "- <b>⚪ 無顏色 (預設白底)</b>：AI 成功完整辨識，且無任何合規疑慮，可直接通過。<br>"
                  "- <b>🔵 藍色框線 (待手動確認/補齊)</b>：AI 未成功辨識該欄位、或辨識資訊不完整（例如發票日期缺少『日』只辨識出年-月，此為保障財務資料真實性的防呆設計），請點選並手動補齊。<br>"
                  "- <b>🔴 紅色框線 (警告有誤)</b>：代表有錯誤或合規風險（例如金額超標、日期不在出差範圍內、消費地點不符等），請核對修改，或在下方填寫超額理由說明。"
    },
    {
        "id": "ocr_date_error",
        "category": "invoice",
        "question": "為什麼 AI 辨識發票沒有顯示日期（或日期不完整）？",
        "synonyms": ["日期不完整", "沒有日期", "缺日", "日期錯誤", "日期只顯示年月", "日期辨識失敗"],
        "answer": "<strong>📅 關於日期辨識不完整說明：</strong><br>"
                  "為了保障公司財務申報的<b>真實性與防範合規風險</b>，AI 辨識在遇到只辨識出年份與月份（例如 2026-05）而無法辨識出具體『日』的發票時，<b>不會自動為您補齊</b>（例如補成 01 號）。<br>"
                  "此時系統會以 <span class='badge bg-primary text-white'>藍色框線</span> 標示該日期欄位，請您點選該欄位，對照發票大圖手動點選補齊正確的日期即可。"
    },
    {
        "id": "tax_id_error",
        "category": "invoice",
        "question": "統一編號沒辨識出來怎麼辦？",
        "synonyms": ["統編", "統一編號", "統編沒出來", "沒辨識出統編", "統編錯誤"],
        "answer": "<strong>🏢 關於統一編號處理：</strong><br>"
                  "若發票上蓋章較為模糊導致 AI 未能自動帶入統編，該欄位會顯示為 <span class='badge bg-primary text-white'>藍色框線</span> 提示手動確認。<br>"
                  "請您對照原始發票，於該列「統一編號」輸入框手動輸入公司統編即可。若該單據確實無須統編，請輸入「無」或保持空白即可。"
    },
    {
        "id": "all_policy_limits",
        "category": "policy",
        "question": "各科目核銷上限？",
        "synonyms": ["各科目核銷上限", "額度規定", "報銷上限", "報銷額度", "費用規定", "核銷上限", "核銷標準", "限制"],
        "answer": "<strong>📋 公司常用差旅核銷限額一覽表：</strong><br>"
                  "<table class='table table-sm table-bordered mt-2 small' style='font-size:0.8rem;'>"
                  "<thead class='table-light'><tr><th>費用類別</th><th>平日上限</th><th>假日上限/說明</th></tr></thead>"
                  "<tbody>"
                  "<tr><td><b>住宿費</b></td><td>$3,500/晚</td><td>$4,500/晚</td></tr>"
                  "<tr><td><b>交通費</b></td><td>按實核銷</td><td>高鐵依標準車廂為費用標準</td></tr>"
                  "<tr><td><b>計程車</b></td><td>$800/筆</td><td>單趟上限 $800 元，超過需說明理由</td></tr>"
                  "<tr><td><b>早餐</b></td><td>$75/餐</td><td>不限平日假日</td></tr>"
                  "<tr><td><b>午餐</b></td><td>$150/餐</td><td>不限平日假日</td></tr>"
                  "<tr><td><b>晚餐</b></td><td>$150/餐</td><td>不限平日假日</td></tr>"
                  "<tr><td><b>雜費</b></td><td>實報實銷</td><td>郵資文具等核實報銷</td></tr>"
                  "</tbody>"
                  "</table>"
                  "<i>※ 超出上限仍可進行申報，但需在該列明細下方加填【超額說明】供主管審查。</i>"
    },
    {
        "id": "accommodation_limit",
        "category": "policy",
        "question": "住宿費的核銷上限與規定？",
        "synonyms": ["住宿", "住一晚", "住宿費", "飯店", "旅館", "住宿上限", "住宿規定", "住宿額度"],
        "answer": "<strong>🏨 住宿費核銷政策上限：</strong><br>"
                  "- <b>平日上限</b>：每晚 NT$ 3,500 元。<br>"
                  "- <b>假日上限</b>：每晚 NT$ 4,500 元。<br>"
                  "<i>※ 假日判定以該筆費用發生的「日期」星期六、星期日為基準（包含國定假日）。若超過額度，需在明細下方的「備註說明」中填寫合理理由（如：熱門展期房價上漲）。</i>"
    },
    {
        "id": "meals_limit",
        "category": "policy",
        "question": "伙食費的核銷上限與規定？",
        "synonyms": ["伙食", "吃東西", "早餐", "午餐", "晚餐", "便當", "吃飯", "餐飲", "伙食費", "請客", "伙食上限"],
        "answer": "<strong>🍽️ 伙食費每餐申報上限：</strong><br>"
                  "- <b>早餐上限</b>：每餐 NT$ 75 元。<br>"
                  "- <b>午餐上限</b>：每餐 NT$ 150 元。<br>"
                  "- <b>晚餐上限</b>：每餐 NT$ 150 元。<br>"
                  "<i>※ 請注意：伙食費申報需上傳含有對應餐點品名或商家蓋章的收據/統一發票。如果超出每餐規定上限，系統會以紅框提示，您需要在說明欄位內補充原因。</i>"
    },
    {
        "id": "transport_limit",
        "category": "policy",
        "question": "交通費的核銷上限與規定（計程車額度）？",
        "synonyms": ["交通", "搭車", "高鐵", "火車", "計程車", "計程車上限", "車資", "車費", "計程車規定", "交通費"],
        "answer": "<strong>🚗 交通費與計程車核銷規定：</strong><br>"
                  "- <b>高鐵、台鐵、客運</b>：按實報銷。高鐵依<b>標準車廂</b>票價為報銷標準，核銷時須提供購票證明或完整票根（電子票根請匯出 PDF 證明）。<br>"
                  "- <b>計程車 (Taxi)</b>：每單趟上限為 <b>NT$ 800 元</b>。<br>"
                  "<i>※ 如果計程車費超出 NT$ 800 元，需在備註說明填寫搭乘起訖點及原因（例如：長途公務行程或攜帶大型展覽設備）。</i>"
    },
    {
        "id": "misc_limit",
        "category": "policy",
        "question": "雜費的核銷上限與規定？",
        "synonyms": ["雜費", "郵資", "文具", "其他費用", "雜費上限", "雜費規定"],
        "answer": "<strong>📦 雜費核銷規定：</strong><br>"
                  "- <b>核銷規定</b>：採<b>實報實銷</b>，無設定固定金額上限。<br>"
                  "- <b>適用範圍</b>：郵資、寄送快遞、公務購買之文具及公務停車費等。<br>"
                  "<i>※ 申報時需在費用名稱明確說明用途，並附上收據憑證以利財務核銷。</i>"
    }
]

def calculate_chinese_similarity(s1, s2):
    """計算中文字元相似度 (Jaccard Index)"""
    set1 = set(s1)
    set2 = set(s2)
    if not set1 or not set2:
        return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return float(intersection) / float(union)

def match_faq(query, session_context=None):
    """核心匹配邏輯 (關鍵字加分 + 模糊相似度比對 + 歷史對話 Context Boost + 智能引導)"""
    query_clean = query.lower().strip()
    if not query_clean:
        return {
            "answer": "您好！我是 HR 智能小助手。請問今天有什麼我可以幫您的？",
            "context": None,
            "suggestions": [FAQ_DATABASE[1]["question"], FAQ_DATABASE[6]["question"], FAQ_DATABASE[3]["question"]]
        }
    
    matches = []
    for faq in FAQ_DATABASE:
        score = 0.0
        
        # 1. 同義詞與關鍵字精確子字串匹配 (給予主要分數)
        matched_any_synonym = False
        for syn in faq["synonyms"]:
            syn_clean = syn.lower()
            if syn_clean in query_clean:
                score += 15.0
                matched_any_synonym = True
                if len(syn_clean) >= 3:
                    score += 5.0 # 長詞語額外加分
        
        # 2. 精確的題意匹配 (比對 User 輸入與 FAQ 主題的 Jaccard 相似度)
        sim = calculate_chinese_similarity(query_clean, faq["question"].lower())
        score += sim * 15.0
        
        # 3. 比對同義詞與輸入的相似度
        max_syn_sim = 0.0
        for syn in faq["synonyms"]:
            syn_sim = calculate_chinese_similarity(query_clean, syn.lower())
            if syn_sim > max_syn_sim:
                max_syn_sim = syn_sim
        score += max_syn_sim * 10.0
        
        # 4. 上下文關聯度判定 (Context Boost)
        if session_context and faq["category"] == session_context:
            score += 8.0 # 上下文範疇一致則大幅加分，維持多輪對話關聯性

        matches.append({
            "faq": faq,
            "score": score
        })
        
    # 排序匹配結果
    matches.sort(key=lambda x: x["score"], reverse=True)
    top_match = matches[0]
    
    # AI 判定閾值：
    # 閾值 >= 18: 精確高信心回覆
    if top_match["score"] >= 18.0:
        # 提供同類別或高分的其他 2 個問題作為建議
        suggestions = []
        for m in matches[1:]:
            if m["faq"]["id"] != top_match["faq"]["id"]:
                suggestions.append(m["faq"]["question"])
            if len(suggestions) >= 2:
                break
        return {
            "answer": top_match["faq"]["answer"],
            "context": top_match["faq"]["category"],
            "suggestions": suggestions
        }
        
    # 閾值 8.0 ~ 17.9: 模糊回覆，給出最接近的答案，並引導推薦
    elif top_match["score"] >= 8.0:
        suggestions = []
        for m in matches:
            suggestions.append(m["faq"]["question"])
            if len(suggestions) >= 3:
                break
        
        uncertain_reply = (
            f"您是不是想詢問：<b>「{top_match['faq']['question']}」</b>？<br><br>"
            f"{top_match['faq']['answer']}<br><br>"
            f"<i>💡 或者是您可能想了解：</i>"
        )
        return {
            "answer": uncertain_reply,
            "context": top_match["faq"]["category"],
            "suggestions": suggestions
        }
        
    # 閾值 < 8.0: 無法匹配，給出 Fallback 說明，引導點選三個核心熱門問題
    else:
        suggestions = [
            "如何填寫報銷單？",
            "各科目核銷上限？",
            "OCR 辨識出錯怎麼辦？"
        ]
        fallback_reply = (
            "抱歉，我目前還不太理解您的意思。🤔<br>"
            "您可以嘗試輸入<b>「住宿規定」、「如何報銷」、「發票紅框」</b>等關鍵字，"
            "或者直接點選下方的熱門問題指引諮詢喔！"
        )
        return {
            "answer": fallback_reply,
            "context": None,
            "suggestions": suggestions
        }
