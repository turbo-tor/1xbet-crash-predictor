import os
import re
import math
import unicodedata
import sqlite3
import atexit
import tkinter as tk
from tkinter import messagebox
from contextlib import closing
from datetime import datetime

import pandas as pd
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# مكتبات لضبط الحروف العربية واتجاهاتها
import arabic_reshaper
from bidi.algorithm import get_display

matplotlib.rcParams['font.family'] = 'Arial'

# مسار ثابت لقاعدة البيانات: نفس فولدر هذا الملف مهما كان مكان التشغيل
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_data.db")
print("DB:", DB_PATH)

MIN_DATA = 5
WINDOW = 15

# حذف قاعدة البيانات تلقائياً عند إغلاق البرنامج
def cleanup_database():
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print("تم حذف قاعدة البيانات مؤقتاً عند الإغلاق.")
    except Exception as e:
        print("خطأ أثناء حذف قاعدة البيانات:", e)

atexit.register(cleanup_database)


def fix_arabic(text):
    """للرسوم البيانية (matplotlib): تشكيل الحروف + ترتيب الاتجاه."""
    return get_display(arabic_reshaper.reshape(text))


_EMOJI = "[\U0001F000-\U0001FFFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200d]"
_LEAD_EMOJI = re.compile(rf"^\s*({_EMOJI}+)\s*")
_TRAIL_EMOJI = re.compile(rf"\s*({_EMOJI}+)\s*$")

TK_NATIVE_ARABIC = True


def fix_ui_arabic(text):
    """لواجهة tkinter."""
    if TK_NATIVE_ARABIC:
        return text
    text = text or ""
    lead = trail = ""
    m = _LEAD_EMOJI.match(text)
    if m:
        lead, text = m.group(1), text[m.end():]
    m = _TRAIL_EMOJI.search(text)
    if m:
        trail, text = m.group(1), text[:m.start()]
    text = re.sub(f"{_EMOJI}+", "", text)
    shaped = get_display(arabic_reshaper.reshape(text)) if text else ""
    return (trail + " " if trail else "") + shaped + (" " + lead if lead else "")


# ----------------- قاعدة البيانات -----------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute("PRAGMA journal_mode=WAL;")  # تحسين الأداء ومنع قفل القاعدة
    return conn


def init_db():
    with closing(get_conn()) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction REAL,
                actual REAL,
                error REAL
            )
        ''')
        conn.commit()


init_db()


def build_insert(conn, values):
    data = dict(values)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for cid, name, ctype, notnull, dflt, pk in conn.execute("PRAGMA table_info(results)").fetchall():
        if name in data or pk or not notnull or dflt is not None:
            continue
        ctype = (ctype or "").upper()
        if any(k in name.lower() for k in ("time", "date", "created")):
            data[name] = now
        elif any(k in ctype for k in ("INT", "REAL", "FLOA", "DOUB", "NUM")):
            data[name] = 0
        else:
            data[name] = ""
    names = list(data.keys())
    sql = (f"INSERT INTO results ({', '.join(chr(34) + n + chr(34) for n in names)}) "
           f"VALUES ({', '.join('?' * len(names))})")
    return sql, [data[n] for n in names]


_SEPARATORS = ",،٫٬/ز"


def parse_actual(text):
    chars = [ch for ch in (text or "")
             if unicodedata.category(ch) != "Cf" and not ch.isspace()]
    text = "".join(chars).lower()
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    for sep in _SEPARATORS:
        text = text.replace(sep, ".")
    text = text.rstrip("x×")
    if not re.fullmatch(r"\d+(\.\d+)?", text):
        raise ValueError("not a number")
    value = float(text)
    if not math.isfinite(value) or value < 1.0:
        raise ValueError("below 1.00")
    return value


def save_record(prediction_text, actual_text):
    try:
        actual = parse_actual(actual_text)
    except ValueError:
        detail = "input=" + ascii(actual_text)
        return False, "الرقم غير مقروء، اكتب مثل 1.77", detail
    try:
        prediction = float(prediction_text)
    except (TypeError, ValueError):
        prediction = 1.40
    error = abs(prediction - actual)

    try:
        with closing(get_conn()) as conn:
            sql, params = build_insert(
                conn, {"prediction": prediction, "actual": actual, "error": error})
            conn.execute(sql, params)
            conn.commit()
        return True, "", ""
    except sqlite3.Error as e:
        return False, "خطأ في قاعدة البيانات", str(e)


def export_to_csv():
    try:
        with closing(get_conn()) as conn:
            df = pd.read_sql("SELECT * FROM results", conn)
        filename = os.path.join(
            os.path.dirname(DB_PATH),
            f"crash_academic_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        return filename
    except Exception as e:
        print("فشل التصدير:", e)
        return None


def reset_database():
    with closing(get_conn()) as conn:
        conn.execute("DELETE FROM results")
        conn.execute("DELETE FROM sqlite_sequence WHERE name='results'")
        conn.commit()


# ----------------- التوقع والمقاييس وتطوير Pandas -----------------
def generate_prediction():
    try:
        with closing(get_conn()) as conn:
            df = pd.read_sql("SELECT actual FROM (SELECT id, actual FROM results ORDER BY id DESC LIMIT 30) ORDER BY id ASC", conn)
            df_signed = pd.read_sql(
                "SELECT actual - prediction AS signed_error FROM results "
                "WHERE prediction IS NOT NULL ORDER BY id DESC LIMIT 10", conn)
    except Exception as e:
        print("خطأ في قراءة البيانات:", e)
        return 1.40, "بداية الجلسة 🟢", "#10b981"

    if len(df) < MIN_DATA:
        if len(df) > 0:
            fallback_val = float(df['actual'].iloc[-1])
            return (round(max(1.00, fallback_val), 2), "تجميع بيانات أولية 🟡", "#fbbf24")
        return 1.40, "جاهز للبدء 🟢", "#10b981"

    recent_df = df.tail(WINDOW)
    std_dev = recent_df['actual'].std()

    # تقييم مرن لحالة الجولات
    if pd.isna(std_dev) or std_dev < 0.8:
        confidence, color = "استقرار جيد 🟢", "#10b981"
    elif std_dev < 1.8:
        confidence, color = "تذبذب مقبولة 🟡", "#f59e0b"
    else:
        confidence, color = "تذبذب عالي 🔴", "#ef4444"

    # تحسين التخمين بزيادة وزن القيم الأخيرة (أكثر استجابة للاتجاه الحالي)
    ema_value = recent_df['actual'].ewm(span=3, adjust=False).mean().iloc[-1]
    recent_mean = recent_df['actual'].mean()
    base_prediction = (ema_value * 0.70) + (recent_mean * 0.30)

    correction_factor = 0.0
    if not df_signed.empty:
        avg_signed = df_signed['signed_error'].mean()
        if not pd.isna(avg_signed):
            correction_factor = avg_signed * 0.12

    prediction = max(1.00, base_prediction + correction_factor)
    return round(prediction, 2), confidence, color


def analyze_market_decision_pandas():
    """تطوير شروط Pandas لتكون أكثر مرونة في إعطاء إشارة الدخول بعد 30 جولة"""
    try:
        with closing(get_conn()) as conn:
            df = pd.read_sql("SELECT prediction, actual, error FROM results ORDER BY id ASC", conn)
        
        total_rounds = len(df)
        if total_rounds < 30:
            return False, f"جولات غير كافية ({total_rounds}/30)", "#ef4444"
        
        recent = df.tail(15)
        std_dev = recent['actual'].std()
        errors = recent['error'].dropna()
        win_rate = (errors <= 0.40).sum() / len(errors) * 100 if len(errors) > 0 else 0
        
        # شروط مرنة ومحدثة لظهور اللون الأخضر بشكل أفضل
        if std_dev <= 1.8 and win_rate >= 35.0:
            return True, f"فرصة مناسبة (نجاح: {win_rate:.1f}%)", "#10b981" # أخضر
        else:
            return False, f"تذبذب عالي (نجاح: {win_rate:.1f}%)", "#ef4444" # أحمر
    except Exception as e:
        return False, "خطأ في تحليل المعطيات", "#ef4444"

def analyze_market_decision_pandas():
    """تطوير في Pandas لقياس المعطيات والتحقق من حالة الدخول بعد 30 جولة"""
    try:
        with closing(get_conn()) as conn:
            df = pd.read_sql("SELECT prediction, actual, error FROM results ORDER BY id ASC", conn)
        
        total_rounds = len(df)
        if total_rounds < 30:
            return False, f"جولات غير كافية ({total_rounds}/30)", "#ef4444"
        
        recent = df.tail(15)
        std_dev = recent['actual'].std()
        errors = recent['error'].dropna()
        win_rate = (errors <= 0.30).sum() / len(errors) * 100 if len(errors) > 0 else 0
        
        # شروط الدخول بناءً على تحليل المعطيات والنتائج
        if std_dev <= 1.3 and win_rate >= 45.0:
            return True, f"فرصة ممتازة (نجاح: {win_rate:.1f}%)", "#10b981" # أخضر
        else:
            return False, f"تذبذب عالي (نجاح: {win_rate:.1f}%)", "#ef4444" # أحمر
    except Exception as e:
        return False, "خطأ في تحليل المعطيات", "#ef4444"


def walk_forward_prediction(prior):
    if not prior:
        return 1.40
    if len(prior) < MIN_DATA:
        return round(max(1.00, prior[-1]), 2)
    recent = pd.Series(prior[-WINDOW:])
    ema = recent.ewm(span=5, adjust=False).mean().iloc[-1]
    return round(max(1.00, 0.65 * ema + 0.35 * recent.median()), 2)


def import_rounds(text):
    values, bad = [], []
    for token in re.split(r"[\s;]+", text or ""):
        if not token:
            continue
        try:
            values.append(parse_actual(token))
        except ValueError:
            bad.append(token)
    if not values:
        return 0, bad
    with closing(get_conn()) as conn:
        history = [r[0] for r in conn.execute(
            "SELECT actual FROM results ORDER BY id ASC").fetchall()]
        for v in values:
            pred = walk_forward_prediction(history)
            sql, params = build_insert(conn, {"prediction": pred, "actual": v, "error": abs(pred - v)})
            conn.execute(sql, params)
            history.append(v)
        conn.commit()
    return len(values), bad


def calculate_academic_metrics():
    try:
        with closing(get_conn()) as conn:
            df = pd.read_sql("SELECT prediction, actual, error FROM results ORDER BY id ASC", conn)

        total_all = len(df)
        if total_all == 0:
            return "0.0%", "0.00", 0

        recent_df = df.tail(WINDOW)
        errors = recent_df['error'].dropna()
        if len(errors) == 0:
            return "0.0%", "0.00", total_all

        win_rate = (errors <= 0.30).sum() / len(errors) * 100
        mae = errors.mean()
        return f"{win_rate:.1f}%", f"{mae:.2f}", total_all
    except Exception as e:
        print("خطأ في حساب المقاييس:", e)
        return "0.0%", "0.00", 0


# ----------------- الثيمات -----------------
themes = {
    "اللون الحالي (داكن مميز)": {
        "bg": "#111827", "panel_bg": "#1f2937", "fg": "#35d39a",
        "text": "white", "chart_bg": "#1f2937", "menu_bg": "#374151", "menu_fg": "white",
        "chart_text": "white"
    },
    "الثيم الأسود الكامل 🖤": {
        "bg": "#000000", "panel_bg": "#121212", "fg": "#00ffcc",
        "text": "#ffffff", "chart_bg": "#121212", "menu_bg": "#222222", "menu_fg": "#00ffcc",
        "chart_text": "white"
    },
    "الثيم الأبيض النظيف 🤍": {
        "bg": "#f3f4f6", "panel_bg": "#ffffff", "fg": "#047857",
        "text": "#111827", "chart_bg": "#ffffff", "menu_bg": "#e5e7eb", "menu_fg": "#111827",
        "chart_text": "black"
    }
}

current_theme_key = "اللون الحالي (داكن مميز)"

root = tk.Tk()
root.title("Crash Academic Simulation & Analytics Suite")
root.geometry("900x680+200+60")


def apply_theme(theme_name):
    global current_theme_key
    current_theme_key = theme_name
    t = themes[theme_name]

    root.configure(bg=t["bg"])
    top_frame.configure(bg=t["bg"])
    metrics_frame.configure(bg=t["panel_bg"])
    chart_frame.configure(bg=t["chart_bg"])
    btn_frame_main.configure(bg=t["bg"])

    lbl_title.configure(bg=t["bg"], fg=t["fg"])
    lbl_theme_title.configure(bg=t["bg"], fg=t["text"])
    theme_menu.config(bg=t["menu_bg"], fg=t["menu_fg"],
                      activebackground=t["fg"], activeforeground=t["bg"])

    lbl_win_rate.configure(bg=t["panel_bg"])
    lbl_mae.configure(bg=t["panel_bg"])
    lbl_samples.configure(bg=t["panel_bg"], fg=t["text"])
    lbl_db.configure(bg=t["bg"], fg=t["text"])

    update_dashboard()


top_frame = tk.Frame(root)
top_frame.pack(fill="x", pady=10, padx=15)

lbl_title = tk.Label(top_frame, text="ACADEMIC SIMULATION DASHBOARD", font=("Arial", 15, "bold"))
lbl_title.pack(side="left")

theme_var = tk.StringVar(value=current_theme_key)
theme_menu = tk.OptionMenu(top_frame, theme_var, *themes.keys(), command=apply_theme)
theme_menu.config(font=("Arial", 10, "bold"), bd=0, relief="flat")
theme_menu.pack(side="right")

lbl_theme_title = tk.Label(top_frame, text=fix_ui_arabic("🎨 الثيم:"), font=("Arial", 10, "bold"))
lbl_theme_title.pack(side="right", padx=5)

metrics_frame = tk.Frame(root, bd=1, relief="solid")
metrics_frame.pack(fill="x", padx=15, pady=5)

lbl_win_rate = tk.Label(metrics_frame, font=("Arial", 11, "bold"), fg="#35d39a")
lbl_win_rate.pack(side="left", padx=20, pady=8)

lbl_mae = tk.Label(metrics_frame, font=("Arial", 11, "bold"), fg="#fbbf24")
lbl_mae.pack(side="left", padx=20, pady=8)

lbl_samples = tk.Label(metrics_frame, font=("Arial", 11, "bold"))
lbl_samples.pack(side="right", padx=20, pady=8)

chart_frame = tk.Frame(root)
chart_frame.pack(fill="both", expand=True, padx=15, pady=10)


def plot_charts():
    for widget in chart_frame.winfo_children():
        widget.destroy()

    t = themes[current_theme_key]
    try:
        with closing(get_conn()) as conn:
            df = pd.read_sql("SELECT prediction, actual FROM results ORDER BY id ASC", conn)

        if len(df) < 2:
            tk.Label(chart_frame,
                     text=fix_arabic("سجل على الأقل نتيجتين لعرض الرسوم البيانية الإحصائية"),
                     font=("Arial", 12), bg=t["chart_bg"], fg=t["text"]).pack(expand=True)
            return

        txt = t["chart_text"]
        fig = Figure(figsize=(8, 4.2), facecolor=t["chart_bg"])
        ax1, ax2 = fig.subplots(1, 2)

        low_count = len(df[df['actual'] < 1.50])
        mid_count = len(df[(df['actual'] >= 1.50) & (df['actual'] <= 3.00)])
        high_count = len(df[df['actual'] > 3.00])

        counts = [low_count, mid_count, high_count]
        labels = [fix_arabic('أقل من 1.50'), fix_arabic('1.50 - 3.00'), fix_arabic('أعلى من 3.00')]
        colors = ['#ef4444', '#f59e0b', '#10b981']

        valid = [(c, l, col) for c, l, col in zip(counts, labels, colors) if c > 0]
        if valid:
            ax1.pie([v[0] for v in valid], labels=[v[1] for v in valid],
                    colors=[v[2] for v in valid], autopct='%1.1f%%',
                    textprops={'color': txt, 'fontsize': 9}, startangle=90)
        ax1.set_title(fix_arabic("توزيع نطاقات العينات"), color=txt, fontsize=11, fontweight='bold')
        ax1.set_facecolor(t["chart_bg"])

        recent = df.tail(WINDOW)
        indices = list(range(len(recent)))
        width = 0.35

        ax2.set_facecolor(t["chart_bg"])
        ax2.bar([i - width / 2 for i in indices], recent['actual'], width,
                label=fix_arabic('الفعلي'), color='#35d39a')
        if recent['prediction'].notnull().any():
            ax2.bar([i + width / 2 for i in indices], recent['prediction'].fillna(0), width,
                    label=fix_arabic('التوقع'), color='#6366f1')

        ax2.set_title(fix_arabic("مقارنة التوقع بالفعلي (آخر 15)"), color=txt,
                      fontsize=11, fontweight='bold')
        ax2.tick_params(colors=txt, labelsize=8)
        ax2.legend(facecolor=t["panel_bg"], edgecolor='none', labelcolor=txt, fontsize=8)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    except Exception as e:
        print("خطأ في الرسم البياني:", e)


def update_dashboard():
    w_rate, mae_v, count_v = calculate_academic_metrics()
    lbl_win_rate.config(text=fix_ui_arabic(f"نسبة النجاح (آخر {WINDOW}): {w_rate}"))
    lbl_mae.config(text=fix_ui_arabic(f"متوسط الخطأ (MAE): {mae_v}"))
    lbl_samples.config(text=fix_ui_arabic(f"عدد الجولات المسجلة: {count_v}"))
    plot_charts()


def quick_log_current():
    prediction, _, _ = generate_prediction()

    top = tk.Toplevel(root)
    top.title(fix_ui_arabic("تسجيل سريع"))
    top.geometry("280x170+500+300")
    top.configure(bg="#1f2937")
    top.attributes("-topmost", True)

    tk.Label(top, text=fix_ui_arabic(f"التوقع الحالي: {prediction}"), font=("Arial", 11, "bold"),
             bg="#1f2937", fg="#35d39a").pack(pady=10)
    tk.Label(top, text=fix_ui_arabic("أدخل الرقم الفعلي للطيارة:"), font=("Arial", 10),
             bg="#1f2937", fg="white").pack()

    entry_actual = tk.Entry(top, font=("Arial", 14), justify="center")
    entry_actual.pack(pady=5)
    entry_actual.focus_set()

    def confirm_save(event=None):
        ok, msg, detail = save_record(str(prediction), entry_actual.get())
        if ok:
            top.destroy()
            update_dashboard()
        else:
            messagebox.showerror(fix_ui_arabic("خطأ"), fix_ui_arabic(msg) + "\n" + detail, parent=top)

    entry_actual.bind("<Return>", confirm_save)
    tk.Button(top, text=fix_ui_arabic("حفظ وسجل"), command=confirm_save, bg="#10b981", fg="white",
              font=("Arial", 10, "bold"), width=12).pack(pady=5)


btn_frame_main = tk.Frame(root)
btn_frame_main.pack(fill="x", padx=15, pady=10)

tk.Button(btn_frame_main, text=fix_ui_arabic("🚀 فتح النافذة العائمة"), command=lambda: open_floating(),
          bg="#2563eb", fg="white", font=("Arial", 10, "bold"), pady=5).pack(side="left", padx=5)
tk.Button(btn_frame_main, text=fix_ui_arabic("⚡ تسجيل سريع للتوقع"), command=quick_log_current,
          bg="#059669", fg="white", font=("Arial", 10, "bold"), pady=5).pack(side="left", padx=5)


def reset_and_refresh():
    if messagebox.askyesno(fix_ui_arabic("تأكيد التصفير"),
                           fix_ui_arabic("هل أنت متأكد من مسح جميع السجلات لبدء جلسة تجريبية جديدة؟")):
        reset_database()
        update_dashboard()


tk.Button(btn_frame_main, text=fix_ui_arabic("🗑️ جلسة جديدة (تصفير)"), command=reset_and_refresh,
          bg="#dc2626", fg="white", font=("Arial", 10, "bold"), pady=5).pack(side="right", padx=5)


def open_import_window():
    win = tk.Toplevel(root)
    win.title(fix_ui_arabic("استيراد جولات"))
    win.geometry("360x350+300+200")
    win.configure(bg="#1f2937")
    win.attributes("-topmost", True)

    tk.Label(win, text=fix_ui_arabic("الصق الأرقام بالترتيب (رقم في كل سطر أو بينهم مسافة):"),
             bg="#1f2937", fg="white", font=("Arial", 10), wraplength=330).pack(pady=8)
    box = tk.Text(win, height=10, width=38, font=("Arial", 12))
    box.pack(padx=10)
    box.focus_set()
    status = tk.Label(win, text="", bg="#1f2937", fg="#35d39a", font=("Arial", 9), wraplength=330)
    status.pack(pady=4)

    def do_import():
        try:
            saved, bad = import_rounds(box.get("1.0", tk.END))
        except sqlite3.Error as e:
            status.config(text=fix_ui_arabic("خطأ في قاعدة البيانات: ") + str(e), fg="#ef4444")
            return
        if saved == 0:
            status.config(text=fix_ui_arabic("مفيش أرقام صالحة"), fg="#ef4444")
            return
        msg = fix_ui_arabic(f"تم استيراد {saved} جولة ✅")
        if bad:
            msg += "\n" + fix_ui_arabic("تم تجاهل:") + " " + " ".join(bad[:10])
        status.config(text=msg, fg="#35d39a")
        box.delete("1.0", tk.END)
        update_dashboard()

    tk.Button(win, text=fix_ui_arabic("استيراد"), command=do_import, bg="#10b981", fg="white",
              font=("Arial", 10, "bold"), width=12).pack(pady=6)


tk.Button(btn_frame_main, text=fix_ui_arabic("📊 تحديث التحليلات"), command=update_dashboard,
          bg="#7c3aed", fg="white", font=("Arial", 10, "bold"), pady=5).pack(side="left", padx=5)
tk.Button(btn_frame_main, text=fix_ui_arabic("📥 استيراد جولات"), command=open_import_window,
          bg="#0891b2", fg="white", font=("Arial", 10, "bold"), pady=5).pack(side="left", padx=5)

lbl_db = tk.Label(root, text=f"DB: {DB_PATH}", font=("Arial", 8), anchor="w")
lbl_db.pack(fill="x", padx=15, pady=(0, 6))


def open_floating():
    floating = tk.Toplevel(root)
    floating.title("Quick Recorder")
    floating.geometry("320x480+850+180")
    floating.configure(bg="#202938")
    floating.attributes("-topmost", True)
    floating.resizable(False, False)

    title = tk.Label(floating, text="QUICK RECORDER", font=("Arial", 14, "bold"),
                     bg="#202938", fg="#35d39a")
    title.pack(pady=8)

    confidence_label = tk.Label(floating, text=fix_ui_arabic("حالة السوق: جاري التحليل..."),
                                bg="#202938", fg="#fbbf24", font=("Arial", 10, "bold"))
    confidence_label.pack(pady=2)

    tk.Label(floating, text=fix_ui_arabic("التوقع التلقائي (بعد 30 جولة)"), bg="#202938",
             fg="white", font=("Arial", 11)).pack()

    prediction_entry = tk.Entry(floating, font=("Arial", 15, "bold"), justify="center",
                                state="readonly", readonlybackground="#e5e7eb")
    prediction_entry.pack(pady=5)

    # زر اتخاذ القرار (أحمر يتحول للأخضر بناءً على قياس Pandas بعد 30 جولة)
    decision_btn = tk.Button(floating, text=fix_ui_arabic("🔴 جاري التحليل (أقل من 30 جولة)"), 
                             bg="#00ffcc", fg="white", font=("Arial", 12, "bold"), width=28, state="disabled")
    decision_btn.pack(pady=6)

    def refresh_ui_prediction():
        prediction, conf_text, conf_color = generate_prediction()
        prediction_entry.config(state="normal")
        prediction_entry.delete(0, tk.END)
        prediction_entry.insert(0, f"{prediction:.2f}")
        prediction_entry.config(
            readonlybackground="#d1fae5" if "🟢" in conf_text else "#fef3c7", state="readonly")
        confidence_label.config(text=fix_ui_arabic(f"حالة السوق: {conf_text}"), fg=conf_color)

        # تحديث زر قرار الدخول باستخدام Pandas
        can_enter, decision_text, decision_color = analyze_market_decision_pandas()
        decision_btn.config(text=fix_ui_arabic(f"هل تدخل؟ {decision_text}"), bg=decision_color)

    refresh_ui_prediction()

    tk.Label(floating, text=fix_ui_arabic("الرقم الفعلي للطيارة"), bg="#202938", fg="white",
             font=("Arial", 11)).pack()
    actual_entry = tk.Entry(floating, font=("Arial", 15), justify="center")
    actual_entry.pack(pady=5)
    actual_entry.focus_set()

    def save(event=None):
        ok, msg, detail = save_record(prediction_entry.get(), actual_entry.get())
        if ok:
            actual_entry.delete(0, tk.END)
            refresh_ui_prediction()
            update_dashboard()
            status_label.config(text=fix_ui_arabic("تم الحفظ ✅"), fg="#35d39a")
        else:
            status_label.config(text=fix_ui_arabic(msg) + " ❌\n" + detail,
                                fg="#ef4444", wraplength=300)

    def manual_refresh():
        refresh_ui_prediction()
        status_label.config(text=fix_ui_arabic("تم تحديث التوقع 🔄"), fg="#35d39a")

    def export_data():
        file = export_to_csv()
        if file:
            status_label.config(text=fix_ui_arabic("تم التصدير 📁") + "\n" + os.path.basename(file),
                                fg="#35d39a")
        else:
            status_label.config(text=fix_ui_arabic("فشل التصدير ❌"), fg="#ef4444")

    actual_entry.bind("<Return>", save)

    btn_frame = tk.Frame(floating, bg="#202938")
    btn_frame.pack(pady=10)

    tk.Button(btn_frame, text=fix_ui_arabic("حفظ"), command=save, bg="#20a878", fg="white",
              font=("Arial", 10, "bold"), width=8).pack(side="left", padx=3)
    tk.Button(btn_frame, text=fix_ui_arabic("تحديث"), command=manual_refresh, bg="#d97706",
              fg="white", font=("Arial", 10, "bold"), width=8).pack(side="left", padx=3)
    tk.Button(btn_frame, text=fix_ui_arabic("تصدير"), command=export_data, bg="#4b5563",
              fg="white", font=("Arial", 10, "bold"), width=8).pack(side="left", padx=3)

    status_label = tk.Label(floating, text="", bg="#202938", fg="#35d39a", font=("Arial", 9))
    status_label.pack(pady=2)

    def start_move(event):
        floating._x = event.x_root - floating.winfo_x()
        floating._y = event.y_root - floating.winfo_y()

    def move(event):
        floating.geometry(f"+{event.x_root - floating._x}+{event.y_root - floating._y}")

    title.bind("<Button-1>", start_move)
    title.bind("<B1-Motion>", move)


apply_theme("اللون الحالي (داكن مميز)")
root.mainloop()