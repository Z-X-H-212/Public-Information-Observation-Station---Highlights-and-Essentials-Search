# ============================================================
#  公開資訊觀測站 精華版查詢 — Google Colab 版
#  使用方式：將此 cell 貼入 Colab 後直接執行
# ============================================================

# ── 1. 安裝套件 ──────────────────────────────────────────────
pip install -q requests beautifulsoup4 pandas ipywidgets

# ── 2. 匯入 ──────────────────────────────────────────────────
import requests
from bs4 import BeautifulSoup
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
import warnings
warnings.filterwarnings("ignore")

# ── 3. 常數 ───────────────────────────────────────────────────
BASE_URL  = "https://mopsov.twse.com.tw"
QUERY_URL = f"{BASE_URL}/mops/web/ajax_t146sb05"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer":      f"{BASE_URL}/mops/web/t146sb05",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin":       BASE_URL,
}

FORM_BASE = {
    "step":      "1",
    "firstin":   "true",
    "off":       "1",
    "keyword4":  "",
    "code1":     "",
    "TYPEK2":    "",
    "checkbtn":  "",
    "queryName": "co_id",
    "inpuType":  "co_id",
    "TYPEK":     "all",
}

# 全域儲存最後一次查詢結果
last_dfs: list[pd.DataFrame] = []

# ── 4. 查詢函式 ───────────────────────────────────────────────
def fetch_mops(co_id: str) -> list[pd.DataFrame]:
    """
    POST 至 MOPS，解析所有 HTML 表格，回傳 list[DataFrame]。
    """
    payload = {**FORM_BASE, "co_id": co_id.strip()}
    session = requests.Session()
    # 先取 cookies
    session.get(f"{BASE_URL}/mops/web/t146sb05",
                headers=HEADERS, timeout=15, verify=False)
    resp = session.post(QUERY_URL, data=payload,
                        headers=HEADERS, timeout=20, verify=False)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    dfs = []
    for tbl in soup.find_all("table"):
        rows = tbl.find_all("tr")
        if len(rows) < 2:
            continue
        data = [[c.get_text(strip=True) for c in r.find_all(["th", "td"])]
                for r in rows]
        # 統一每列欄數
        max_col = max(len(r) for r in data)
        data = [r + [""] * (max_col - len(r)) for r in data]
        header, *body = data
        if not any(header):
            continue
        df = pd.DataFrame(body, columns=header)
        df = df.loc[:, df.columns != ""].dropna(how="all").reset_index(drop=True)
        if not df.empty:
            dfs.append(df)
    return dfs

# ── 5. 美化 DataFrame 顯示 ────────────────────────────────────
def styled_html(df: pd.DataFrame, title: str = "") -> str:
    header_bg  = "#1565C0"
    row_even   = "#E3F2FD"
    row_odd    = "#FFFFFF"
    border_col = "#90CAF9"

    th_style = (
        f"background:{header_bg};color:white;padding:8px 12px;"
        f"font-size:13px;border:1px solid {border_col};white-space:nowrap;"
    )
    td_style_even = (
        f"padding:6px 12px;font-size:12px;border:1px solid {border_col};"
        f"background:{row_even};"
    )
    td_style_odd = (
        f"padding:6px 12px;font-size:12px;border:1px solid {border_col};"
        f"background:{row_odd};"
    )

    html = f"""
    <div style="margin:16px 0;">
      {"<h4 style='color:#1565C0;margin-bottom:6px;'>" + title + "</h4>" if title else ""}
      <div style="overflow-x:auto;">
      <table style="border-collapse:collapse;width:100%;font-family:'Noto Sans TC',sans-serif;">
        <thead><tr>
    """
    for col in df.columns:
        html += f"<th style='{th_style}'>{col}</th>"
    html += "</tr></thead><tbody>"
    for i, row in df.iterrows():
        td_style = td_style_even if i % 2 == 0 else td_style_odd
        html += "<tr>"
        for val in row:
            html += f"<td style='{td_style}'>{val}</td>"
        html += "</tr>"
    html += "</tbody></table></div></div>"
    return html

# ── 6. 查詢回呼 ───────────────────────────────────────────────
def on_query(btn):
    global last_dfs
    co_id = txt_input.value.strip()
    if not co_id:
        with out:
            clear_output()
            display(HTML("<p style='color:red;'>⚠️ 請輸入股票代號或公司簡稱</p>"))
        return

    btn.disabled = True
    btn.description = "查詢中…"
    with out:
        clear_output()
        display(HTML(f"<p style='color:#555;'>🔍 正在查詢「{co_id}」，請稍候…</p>"))

    try:
        dfs = fetch_mops(co_id)
        last_dfs = dfs
    except Exception as e:
        with out:
            clear_output()
            display(HTML(f"<p style='color:red;'>❌ 查詢失敗：{e}</p>"))
        btn.disabled = False
        btn.description = "🔍  查詢"
        return

    with out:
        clear_output()
        if not dfs:
            display(HTML(
                f"<p style='color:orange;'>⚠️「{co_id}」查無資料，"
                "請確認代號是否正確</p>"
            ))
        else:
            display(HTML(
                f"<p style='color:green;font-weight:bold;'>"
                f"✅ 「{co_id}」查詢完成，共取得 {len(dfs)} 張表格</p>"
            ))
            for i, df in enumerate(dfs):
                display(HTML(styled_html(df, title=f"表格 {i+1}")))
                print(f"\n[表格 {i+1}] DataFrame：")
                display(df)

    btn.disabled = False
    btn.description = "🔍  查詢"

# ── 7. 匯出回呼 ───────────────────────────────────────────────
def on_export(btn):
    if not last_dfs:
        with out:
            display(HTML("<p style='color:orange;'>⚠️ 尚無查詢結果可匯出</p>"))
        return
    co_id = txt_input.value.strip() or "result"
    filename = f"mops_{co_id}.xlsx"
    try:
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            for i, df in enumerate(last_dfs):
                df.to_excel(writer, sheet_name=f"表格{i+1}", index=False)
        from google.colab import files
        files.download(filename)
        with out:
            display(HTML(f"<p style='color:green;'>📥 已下載：{filename}</p>"))
    except Exception as e:
        with out:
            display(HTML(f"<p style='color:red;'>❌ 匯出失敗：{e}</p>"))

# ── 8. 建立 UI ────────────────────────────────────────────────
display(HTML("""
<div style="background:linear-gradient(135deg,#1565C0,#0D47A1);
            padding:20px 28px;border-radius:12px;margin-bottom:16px;
            font-family:'Noto Sans TC',sans-serif;">
  <h2 style="color:white;margin:0;">📊 公開資訊觀測站 精華版查詢</h2>
  <p style="color:#BBDEFB;margin:6px 0 0;">
    Taiwan Stock Exchange MOPS — Company Information Query
  </p>
</div>
"""))

txt_input = widgets.Text(
    value="2330",
    placeholder="輸入股票代號或公司簡稱，例如：2330 或 台積電",
    description="股票代號：",
    layout=widgets.Layout(width="420px"),
    style={"description_width": "90px"},
)

btn_query = widgets.Button(
    description="🔍  查詢",
    button_style="primary",
    layout=widgets.Layout(width="120px", height="36px"),
)

btn_export = widgets.Button(
    description="📥  匯出 Excel",
    button_style="success",
    layout=widgets.Layout(width="140px", height="36px"),
)

btn_query.on_click(on_query)
btn_export.on_click(on_export)

out = widgets.Output()

display(widgets.HBox([txt_input, btn_query, btn_export],
                     layout=widgets.Layout(align_items="center", gap="10px")))
display(HTML("<hr style='border:1px solid #e0e0e0;margin:12px 0;'>"))
display(out)
