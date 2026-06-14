"""
台灣股市新聞情緒分析報告生成器
收集影響台灣股市的國內外新聞，進行情緒分析
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import json
import re
import os

# 目標輸出檔案
OUTPUT_FILE = "C:/Users/mosn8/stock-project/shared/news_analysis.txt"

# 情緒評分標準
SENTIMENT_SCORES = {
    "非常看好": 2.0,
    "看好": 1.0,
    "中性": 0.0,
    "看淡": -1.0,
    "非常看淡": -2.0
}

def fetch_taiwan_stock_news():
    """嘗試抓取台灣股市相關新聞"""
    news_items = []
    
    # 使用鉅亨網當日新聞
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # 嘗試抓取鉅亨網首頁新聞
        response = requests.get('https://news.cnyes.com/', headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # 嘗試找新聞標題
            headlines = soup.find_all('a', href=True)
            for h in headlines[:20]:
                text = h.get_text(strip=True)
                if len(text) > 10 and len(text) < 200:
                    news_items.append({
                        "source": "鉅亨網",
                        "title": text,
                        "url": h.get('href', '')
                    })
    except Exception as e:
        print(f"抓取鉅亨網新聞失敗: {e}")
    
    return news_items

def fetch_international_news():
    """抓取國際財經新聞"""
    news_items = []
    
    # 嘗試抓取 Yahoo Finance 國際新聞
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get('https://finance.yahoo.com/news/', headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            headlines = soup.find_all('h3', limit=15)
            for h in headlines:
                text = h.get_text(strip=True)
                if len(text) > 10:
                    news_items.append({
                        "source": "Yahoo Finance",
                        "title": text
                    })
    except Exception as e:
        print(f"抓取Yahoo Finance新聞失敗: {e}")
    
    return news_items

def get_market_data():
    """取得關鍵市場數據"""
    data = {}
    
    tickers = {
        "^TWII": "台灣加權指數",
        "^DJI": "道瓊工業平均",
        "^IXIC": "那斯達克",
        "^GSPC": "S&P 500",
        "^N225": "日經225",
        "^KS11": "韓國綜合",
        "000001.SS": "上證綜合",
        "DX-Y.NYB": "美元指數",
        "^TNX": "美國10年期公債殖利率"
    }
    
    for ticker, name in tickers.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                change = ((current - prev) / prev) * 100
                data[name] = {
                    "current": round(current, 2),
                    "change_pct": round(change, 2)
                }
        except Exception as e:
            print(f"取得 {name} 資料失敗: {e}")
    
    # 取得台積電相關數據
    try:
        tsmc = yf.Ticker("2330.TW")
        tsmc_hist = tsmc.history(period="5d")
        if not tsmc_hist.empty:
            current = tsmc_hist['Close'].iloc[-1]
            prev = tsmc_hist['Close'].iloc[-2] if len(tsmc_hist) > 1 else current
            change = ((current - prev) / prev) * 100
            data["台積電(2330)"] = {
                "current": round(current, 2),
                "change_pct": round(change, 2)
            }
    except Exception as e:
        print(f"取得台積電資料失敗: {e}")
    
    return data

def sentiment_analysis_keywords(text):
    """
    基於關鍵詞的新聞情緒分析
    回傳: (情緒標籤, 情緒分數, 影響方向)
    """
    text_lower = text.lower()
    
    # 非常正面的關鍵詞
    very_positive = ["大漲", "創新高", "強勁", "利多", "突破", "飆升", "暴漲", "多头", "buy", "bullish", "rally", "surge"]
    positive = ["上漲", "成長", "看好", "增加", "復甦", "樂觀", "漲", "紅", "佳", "優於預期"]
    
    # 非常負面的關鍵詞
    very_negative = ["大跌", "破底", "崩跌", "利空", "跳水", "暴跌", "空头", "sell", "bearish", "crash", "plunge"]
    negative = ["下跌", "衰退", "看淡", "減少", "警告", "虧損", "跌", "綠", "低於預期"]
    
    # 中性/風險關鍵詞
    risk_keywords = ["戰爭", "制裁", "關稅", "貿易戰", "升息", "通膨", "緊縮", "war", "sanction", "tariff", "trade war", "rate hike", "inflation"]
    
    score = 0
    reasons = []
    
    for kw in very_positive:
        if kw.lower() in text_lower:
            score += 2
            reasons.append(f"關鍵詞: {kw}")
    
    for kw in positive:
        if kw.lower() in text_lower:
            score += 1
            reasons.append(f"關鍵詞: {kw}")
    
    for kw in very_negative:
        if kw.lower() in text_lower:
            score -= 2
            reasons.append(f"關鍵詞: {kw}")
    
    for kw in negative:
        if kw.lower() in text_lower:
            score -= 1
            reasons.append(f"關鍵詞: {kw}")
    
    for kw in risk_keywords:
        if kw.lower() in text_lower:
            score -= 0.5
            reasons.append(f"風險關鍵詞: {kw}")
    
    # 轉換為情緒標籤
    if score >= 3:
        sentiment = "非常看好"
    elif score >= 1:
        sentiment = "看好"
    elif score <= -3:
        sentiment = "非常看淡"
    elif score <= -1:
        sentiment = "看淡"
    else:
        sentiment = "中性"
    
    # 影響方向
    if score > 0:
        direction = "偏多"
    elif score < 0:
        direction = "偏空"
    else:
        direction = "中性"
    
    return sentiment, score, direction, reasons

def generate_report():
    """生成完整分析報告"""
    
    report = []
    report.append("=" * 70)
    report.append("台灣股市新聞情緒分析報告")
    report.append(f"報告時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 70)
    report.append("")
    
    # 第一部分：市場數據概覽
    report.append("【一、主要市場數據概覽】")
    report.append("-" * 50)
    
    market_data = get_market_data()
    
    if market_data:
        # 排序：先台股，再美股，再亞股，再其他
        priority_order = ["台灣加權指數", "台積電(2330)", "道瓊工業平均", "那斯達克", "S&P 500", 
                         "日經225", "韓國綜合", "上證綜合", "美元指數", "美國10年期公債殖利率"]
        
        for name in priority_order:
            if name in market_data:
                d = market_data[name]
                arrow = "▲" if d["change_pct"] > 0 else "▼" if d["change_pct"] < 0 else "─"
                color = "+" if d["change_pct"] > 0 else "-" if d["change_pct"] < 0 else ""
                report.append(f"  {name}: {d['current']} ({arrow}{color}{abs(d['change_pct']):.2f}%)")
        
        for name, d in market_data.items():
            if name not in priority_order:
                arrow = "▲" if d["change_pct"] > 0 else "▼" if d["change_pct"] < 0 else "─"
                color = "+" if d["change_pct"] > 0 else "-" if d["change_pct"] < 0 else ""
                report.append(f"  {name}: {d['current']} ({arrow}{color}{abs(d['change_pct']):.2f}%)")
    else:
        report.append("  [無法取得市場數據]")
    
    report.append("")
    
    # 第二部分：新聞情緒分析
    report.append("【二、新聞情緒分析矩陣】")
    report.append("-" * 50)
    
    all_news = []
    
    # 收集新聞
    tw_news = fetch_taiwan_stock_news()
    intl_news = fetch_international_news()
    
    all_news.extend([(n, "台灣") for n in tw_news])
    all_news.extend([(n, "國際") for n in intl_news])
    
    if all_news:
        # 建立分析矩陣表格
        report.append("")
        report.append(f"{'來源':<10} {'新聞標題':<45} {'情緒':<10} {'方向':<8}")
        report.append("-" * 80)
        
        sentiment_counts = {"非常看好": 0, "看好": 0, "中性": 0, "看淡": 0, "非常看淡": 0}
        direction_counts = {"偏多": 0, "偏空": 0, "中性": 0}
        
        for news, region in all_news[:30]:  # 最多30則
            title = news.get("title", "")[:43]
            source = news.get("source", region)[:8]
            
            sentiment, score, direction, reasons = sentiment_analysis_keywords(title)
            
            sentiment_counts[sentiment] += 1
            direction_counts[direction] += 1
            
            # 縮短情緒標籤
            short_sentiment = sentiment[:4]
            short_direction = direction[:3]
            
            report.append(f"{source:<10} {title:<45} {short_sentiment:<10} {short_direction:<8}")
        
        report.append("")
        report.append("情緒分佈統計:")
        report.append(f"  非常看好: {sentiment_counts['非常看好']} 則")
        report.append(f"  看好: {sentiment_counts['看好']} 則")
        report.append(f"  中性: {sentiment_counts['中性']} 則")
        report.append(f"  看淡: {sentiment_counts['看淡']} 則")
        report.append(f"  非常看淡: {sentiment_counts['非常看淡']} 則")
    else:
        report.append("  [無法取得新聞資料]")
        sentiment_counts = {"非常看好": 0, "看好": 0, "中性": 0, "看淡": 0, "非常看淡": 0}
        direction_counts = {"偏多": 0, "偏空": 0, "中性": 0}
    
    report.append("")
    
    # 第三部分：關鍵影響因素分析
    report.append("【三、關鍵影響因素分析】")
    report.append("-" * 50)
    
    # 根據市場數據自動生成分析
    factors = []
    
    if "^TNX" in str(market_data):
        report.append("  [Fed利率政策]")
        report.append("    影響: 美國公債殖利率變化反映市場對Fed升息預期")
        report.append("    若殖利率上升 → 美元強 → 資金可能流出新興市場 → 對台股略偏空")
        report.append("")
    
    if "美元指數" in market_data:
        dx_data = market_data["美元指數"]
        if dx_data["change_pct"] > 0.5:
            report.append("  [美元走勢]")
            report.append("    現況: 美元強勢")
            report.append("    影響: 新台幣可能貶值，不利進口但有利出口")
            report.append("")
        elif dx_data["change_pct"] < -0.5:
            report.append("  [美元走勢]")
            report.append("    現況: 美元弱勢")
            report.append("    影響: 新台幣可能升值，有利資金流入")
            report.append("")
    
    # 台積電分析
    if "台積電(2330)" in market_data:
        tsmc_data = market_data["台積電(2330)"]
        if tsmc_data["change_pct"] > 2:
            report.append("  [台積電表現]")
            report.append(f"    台積電今日上漲 {tsmc_data['change_pct']:.2f}%")
            report.append("    影響: 半導體族群信心增強，指數空間向上")
            report.append("")
        elif tsmc_data["change_pct"] < -2:
            report.append("  [台積電表現]")
            report.append(f"    台積電今日下跌 {tsmc_data['change_pct']:.2f}%")
            report.append("    影響: 半導體族群承壓，指數動能減弱")
            report.append("")
    
    # 自動評估美股影響
    if "^IXIC" in str(market_data) and "^GSPC" in str(market_data):
        nasdaq = market_data.get("那斯達克", {}).get("change_pct", 0)
        sp500 = market_data.get("S&P 500", {}).get("change_pct", 0)
        
        report.append("  [美股氛圍]")
        if nasdaq > 1 and sp500 > 1:
            report.append(f"    美股全面上漲 (NASDAQ +{nasdaq:.2f}%, S&P500 +{sp500:.2f}%)")
            report.append("    影響: 正面，台股有望跟漲")
            report.append("")
        elif nasdaq < -1 or sp500 < -1:
            report.append(f"    美股普遍下跌 (NASDAQ {nasdaq:.2f}%, S&P500 {sp500:.2f}%)")
            report.append("    影響: 負面，台股恐承壓")
            report.append("")
        else:
            report.append(f"    美股區間震盪 (NASDAQ {nasdaq:.2f}%, S&P500 {sp500:.2f}%)")
            report.append("    影響: 中性，觀望氣氛濃")
            report.append("")
    
    # 第四部分：總結與操作建議
    report.append("【四、總結與做多策略影響】")
    report.append("-" * 50)
    
    # 計算整體情緒分數
    total_sentiment = (
        sentiment_counts["非常看好"] * 2 +
        sentiment_counts["看好"] * 1 +
        sentiment_counts["看淡"] * (-1) +
        sentiment_counts["非常看淡"] * (-2)
    )
    
    report.append("")
    report.append(f"  新聞情緒綜合評分: {total_sentiment}")
    
    # 市場趨勢評估
    bullish_signals = 0
    bearish_signals = 0
    
    if market_data:
        if market_data.get("台灣加權指數", {}).get("change_pct", 0) > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1
            
        if market_data.get("台積電(2330)", {}).get("change_pct", 0) > 0:
            bullish_signals += 2  # 台積電權重高
            
        if market_data.get("那斯達克", {}).get("change_pct", 0) > 0:
            bullish_signals += 1
        elif market_data.get("那斯達克", {}).get("change_pct", 0) < 0:
            bearish_signals += 1
    
    # 新聞情緒加權
    bullish_signals += sentiment_counts["非常看好"] + sentiment_counts["看好"]
    bearish_signals += sentiment_counts["非常看淡"] + sentiment_counts["看淡"]
    
    report.append("")
    report.append(f"  做多策略參考:")
    
    if bullish_signals > bearish_signals + 3:
        report.append("    訊號: 強烈偏多")
        report.append("    建議: 可適度建立多倉，順勢而為")
    elif bullish_signals > bearish_signals:
        report.append("    訊號: 輕微偏多")
        report.append("    建議: 謹慎做多，設定停損")
    elif bearish_signals > bullish_signals + 3:
        report.append("    訊號: 強烈偏空")
        report.append("    建議: 避免追多，清倉觀望")
    elif bearish_signals > bullish_signals:
        report.append("    訊號: 輕微偏空")
        report.append("    建議: 保守操作，等待回升")
    else:
        report.append("    訊號: 中性觀望")
        report.append("    建議: 區間操作，等待明確方向")
    
    report.append("")
    report.append("  風險提示:")
    report.append("    - 地緣政治風險(台海問題)可能突然影響市場")
    report.append("    - Fed利率決策及美元走勢需持續關注")
    report.append("    - 美中貿易談判進展為重要不確定因素")
    report.append("    - 本報告僅供參考，不構成投資建議")
    
    report.append("")
    report.append("=" * 70)
    report.append("報告結束")
    report.append(f"生成時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 70)
    
    return "\n".join(report)

if __name__ == "__main__":
    print("正在收集市場數據與新聞...")
    
    try:
        report_content = generate_report()
        
        # 寫入檔案
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"\n報告已成功生成並存檔至: {OUTPUT_FILE}")
        print("\n" + "=" * 50)
        print("【報告預覽】")
        print("=" * 50)
        print(report_content[:2000])  # 顯示前2000字
        
    except Exception as e:
        print(f"生成報告時發生錯誤: {e}")
        import traceback
        traceback.print_exc()