# -*- coding: utf-8 -*-
"""Football Pass Analyzer Pro - Android edition (Kivy).
Database tables and core fields are kept compatible with the v25/v26 SQLite schema.
"""
import os, sqlite3, json
from datetime import date, datetime
from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, Ellipse

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    def fa(s):
        try: return get_display(arabic_reshaper.reshape(str(s)))
        except Exception: return str(s)
except Exception:
    def fa(s): return str(s)

THEMES = {
    "Dark Green": {"bg":"101820","panel":"192630","panel2":"263B49","text":"F4F6F8","muted":"AAB7C2","accent":"35B47A","danger":"E06464","gold":"E5B84B"},
    "Black Gold": {"bg":"111111","panel":"1C1C1C","panel2":"292929","text":"F7F4EC","muted":"B8B2A5","accent":"D6AD52","danger":"E06B64","gold":"D6AD52"},
    "Light": {"bg":"F2F4F6","panel":"FFFFFF","panel2":"E7EBEF","text":"1D2730","muted":"65727D","accent":"16865B","danger":"C84646","gold":"B08020"},
    "Midnight Blue": {"bg":"0B1424","panel":"142238","panel2":"20334D","text":"F0F5FF","muted":"9EADC2","accent":"38B6C8","danger":"E16D79","gold":"55C7D3"},
}
POSITIONS = ["تعیین نشده","دروازه‌بان","دفاع میانی راست","دفاع میانی چپ","دفاع کناری راست","دفاع کناری چپ","هافبک دفاعی","هافبک میانی راست","هافبک میانی چپ","هافبک هجومی","وینگر راست","وینگر چپ","مهاجم راست","مهاجم چپ","مهاجم نوک"]

class Store:
    def __init__(self, path):
        self.path = path
        self.init()
    def connect(self):
        c = sqlite3.connect(self.path); c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        return c
    def init(self):
        with self.connect() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS matches(
                id INTEGER PRIMARY KEY, title TEXT NOT NULL, match_date TEXT NOT NULL,
                opponent TEXT DEFAULT '', notes TEXT DEFAULT '')""")
            c.execute("""CREATE TABLE IF NOT EXISTS players(
                id INTEGER PRIMARY KEY, name TEXT NOT NULL, number TEXT DEFAULT '',
                position TEXT NOT NULL DEFAULT 'تعیین نشده', UNIQUE(name,number))""")
            c.execute("""CREATE TABLE IF NOT EXISTS match_players(
                match_id INTEGER, player_id INTEGER, PRIMARY KEY(match_id,player_id),
                FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE,
                FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE)""")
            c.execute("""CREATE TABLE IF NOT EXISTS player_list_order(
                player_id INTEGER PRIMARY KEY, sort_order INTEGER NOT NULL,
                FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE)""")
            c.execute("""CREATE TABLE IF NOT EXISTS matrix_player_order(
                match_id INTEGER NOT NULL, player_id INTEGER NOT NULL, sort_order INTEGER NOT NULL,
                PRIMARY KEY(match_id,player_id),
                FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE,
                FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE)""")
            c.execute("""CREATE TABLE IF NOT EXISTS passes(
                id INTEGER PRIMARY KEY, match_id INTEGER NOT NULL, passer_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL, outcome TEXT NOT NULL, length TEXT NOT NULL,
                created_at TEXT NOT NULL, start_x REAL, start_y REAL, end_x REAL, end_y REAL,
                pass_type TEXT NOT NULL DEFAULT 'رو به جلو', minute INTEGER, video_time TEXT,
                video_path TEXT, quantity INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE,
                FOREIGN KEY(passer_id) REFERENCES players(id), FOREIGN KEY(receiver_id) REFERENCES players(id))""")
            pcols = {r[1] for r in c.execute("PRAGMA table_info(passes)")}
            for n,d in [("start_x","REAL"),("start_y","REAL"),("end_x","REAL"),("end_y","REAL"),
                        ("pass_type","TEXT NOT NULL DEFAULT 'رو به جلو'"),("minute","INTEGER"),
                        ("video_time","TEXT"),("video_path","TEXT"),("quantity","INTEGER NOT NULL DEFAULT 1")]:
                if n not in pcols: c.execute(f"ALTER TABLE passes ADD COLUMN {n} {d}")
            mcols = {r[1] for r in c.execute("PRAGMA table_info(matches)")}
            if "watched" not in mcols: c.execute("ALTER TABLE matches ADD COLUMN watched INTEGER NOT NULL DEFAULT 0")
            c.execute("""CREATE TABLE IF NOT EXISTS player_positions(
                match_id INTEGER NOT NULL, player_id INTEGER NOT NULL, x REAL NOT NULL, y REAL NOT NULL,
                PRIMARY KEY(match_id,player_id), FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE,
                FOREIGN KEY(player_id) REFERENCES players(id) ON DELETE CASCADE)""")
            c.execute("""CREATE TABLE IF NOT EXISTS match_events(
                id INTEGER PRIMARY KEY, match_id INTEGER NOT NULL, minute INTEGER NOT NULL DEFAULT 0,
                title TEXT NOT NULL, description TEXT DEFAULT '', video_time TEXT DEFAULT '',
                video_path TEXT DEFAULT '', created_at TEXT NOT NULL,
                FOREIGN KEY(match_id) REFERENCES matches(id) ON DELETE CASCADE)""")
            if not c.execute("SELECT id FROM matches LIMIT 1").fetchone():
                c.execute("INSERT INTO matches(title,match_date,opponent,notes) VALUES(?,?,?,?)",
                          ("مسابقه اول", date.today().isoformat(), "", "مسابقه پیش‌فرض"))

class FLabel(Label):
    def __init__(self, **kw):
        kw.setdefault("halign", "right"); kw.setdefault("valign", "middle")
        kw.setdefault("size_hint_y", None); kw.setdefault("height", dp(38))
        super().__init__(**kw)
        self.bind(size=self._sync)
    def _sync(self, *_): self.text_size = (self.width-dp(12), None)

class AnalyzerApp(App):
    def build(self):
        self.title = "Football Pass Analyzer Pro"
        self.db = Store(os.path.join(self.user_data_dir, "football_pass_analyzer.db"))
        self.prefs_path = os.path.join(self.user_data_dir, "preferences.json")
        try:
            self.prefs = json.load(open(self.prefs_path, encoding="utf-8"))
        except Exception: self.prefs = {}
        self.theme_name = self.prefs.get("theme", "Dark Green")
        if self.theme_name not in THEMES: self.theme_name = "Dark Green"
        self.active_match = None
        Window.clearcolor = self.rgb("bg")
        self.sm = ScreenManager()
        self.root_box = BoxLayout(orientation="vertical", spacing=dp(5), padding=dp(8))
        with self.root_box.canvas.before:
            self.bg_color = Color(*self.rgb("bg")); self.bg_rect = Rectangle(pos=self.root_box.pos, size=self.root_box.size)
        self.root_box.bind(pos=self._bg_update, size=self._bg_update)
        self.header = FLabel(text=fa("تحلیل‌گر پاس فوتبال | نسخه اندروید"), bold=True, font_size="19sp", height=dp(48), color=self.rgb("gold"))
        self.root_box.add_widget(self.header)
        self.nav = GridLayout(cols=5, size_hint_y=None, height=dp(94), spacing=dp(4))
        self.root_box.add_widget(self.nav)
        self.root_box.add_widget(self.sm)
        self.nav_items = [
            ("dashboard","داشبورد"),("quick","ثبت پاس"),("players","بازیکنان"),("matches","مسابقات"),("matrix","ماتریس"),
            ("network","شبکه پاس"),("compare","مقایسه"),("timeline","خط زمانی"),("pitch","زمین"),("settings","تنظیمات")]
        for key,title in self.nav_items:
            b=self.btn(title, small=True); b.bind(on_release=lambda _b,k=key:self.show(k)); self.nav.add_widget(b)
            sc=Screen(name=key); self.sm.add_widget(sc)
        self.refresh_all()
        self.show("dashboard")
        return self.root_box

    def _bg_update(self,*_): self.bg_rect.pos=self.root_box.pos; self.bg_rect.size=self.root_box.size
    def rgb(self,key):
        h=THEMES[self.theme_name][key]; return tuple(int(h[i:i+2],16)/255 for i in (0,2,4))+(1,)
    def btn(self, title, small=False, primary=False):
        b=Button(text=fa(title), size_hint_y=None, height=dp(42 if not small else 36),
                 background_normal="", background_color=self.rgb("accent" if primary else "panel2"),
                 color=self.rgb("bg" if primary else "text"), font_size="13sp")
        return b
    def label(self, text, height=38, color=None, bold=False):
        return FLabel(text=fa(text), height=dp(height), color=color or self.rgb("text"), bold=bold, font_size="14sp")
    def inp(self, hint="", text="", multiline=False):
        return TextInput(hint_text=fa(hint), text=str(text), multiline=multiline, size_hint_y=None,
                         height=dp(42 if not multiline else 82), background_color=self.rgb("panel2"),
                         foreground_color=self.rgb("text"), hint_text_color=self.rgb("muted"),
                         cursor_color=self.rgb("accent"), padding=(dp(10),dp(10)))
    def spin(self, values):
        return Spinner(text=fa(values[0]), values=[fa(x) for x in values], size_hint_y=None, height=dp(42),
                       background_normal="", background_color=self.rgb("panel2"), color=self.rgb("text"))
    def popup(self, message, title="پیام"):
        box=BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        box.add_widget(self.label(message, height=75))
        b=self.btn("باشه",primary=True); box.add_widget(b)
        p=Popup(title=fa(title), content=box, size_hint=(.88,.32)); b.bind(on_release=p.dismiss); p.open()
    def content(self, key, title):
        sc=self.sm.get_screen(key); sc.clear_widgets()
        outer=BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(8))
        outer.add_widget(self.label(title, height=42, color=self.rgb("gold"), bold=True))
        sv=ScrollView(do_scroll_x=True); body=GridLayout(cols=1, spacing=dp(6), size_hint_y=None, padding=dp(3))
        body.bind(minimum_height=body.setter("height")); sv.add_widget(body); outer.add_widget(sv)
        sc.add_widget(outer); return body
    def addrow(self, body, widget): body.add_widget(widget)
    def show(self,key):
        self.sm.current=key
        builders={"dashboard":self.page_dashboard,"quick":self.page_quick,"players":self.page_players,
                  "matches":self.page_matches,"matrix":self.page_matrix,"network":self.page_network,
                  "compare":self.page_compare,"timeline":self.page_timeline,"pitch":self.page_pitch,"settings":self.page_settings}
        builders[key]()
    def match_id(self):
        if self.active_match is None:
            with self.db.connect() as c: r=c.execute("SELECT id FROM matches ORDER BY id LIMIT 1").fetchone()
            self.active_match=r["id"] if r else None
        return self.active_match
    def match_selector(self, body):
        with self.db.connect() as c: rows=c.execute("SELECT id,title,match_date FROM matches ORDER BY match_date DESC,id DESC").fetchall()
        vals=[f"{r['id']} | {r['title']} | {r['match_date']}" for r in rows]
        sp=self.spin(vals or ["مسابقه‌ای وجود ندارد"])
        if self.active_match:
            for v in vals:
                if v.startswith(str(self.active_match)+" |"): sp.text=fa(v)
        def changed(obj, value):
            try: self.active_match=int(value.split("|")[0].strip())
            except: pass
            self.refresh_all()
            self.show(self.sm.current)
        sp.bind(text=changed); self.addrow(body,self.label("مسابقه فعال")); self.addrow(body,sp)
    def refresh_all(self):
        with self.db.connect() as c:
            r=c.execute("SELECT id FROM matches ORDER BY match_date DESC,id DESC LIMIT 1").fetchone()
        if self.active_match is None and r: self.active_match=r["id"]
    def stats(self):
        mid=self.match_id()
        if not mid:return (0,0,0,0,[])
        with self.db.connect() as c:
            total=c.execute("SELECT COALESCE(SUM(quantity),0) FROM passes WHERE match_id=?",(mid,)).fetchone()[0]
            ok=c.execute("SELECT COALESCE(SUM(quantity),0) FROM passes WHERE match_id=? AND outcome='صحیح'",(mid,)).fetchone()[0]
            bad=total-ok; rate=round(ok*100/total,1) if total else 0
            rows=c.execute("""SELECT p.name,SUM(ps.quantity) total,
              SUM(CASE WHEN ps.outcome='صحیح' THEN ps.quantity ELSE 0 END) ok,
              SUM(CASE WHEN ps.outcome='غلط' THEN ps.quantity ELSE 0 END) bad
              FROM passes ps JOIN players p ON p.id=ps.passer_id WHERE ps.match_id=?
              GROUP BY p.id ORDER BY total DESC""",(mid,)).fetchall()
        return total,ok,bad,rate,rows
    def page_dashboard(self):
        b=self.content("dashboard","نمای کلی عملکرد تیم"); self.match_selector(b)
        total,ok,bad,rate,rows=self.stats()
        for x in [f"کل پاس‌ها: {total}",f"پاس صحیح: {ok}",f"پاس غلط: {bad}",f"درصد موفقیت: {rate}%"]:
            self.addrow(b,self.label(x, height=44,bold=True))
        self.addrow(b,self.label("عملکرد بازیکنان",color=self.rgb("gold"),bold=True))
        for r in rows:self.addrow(b,self.label(f"{r['name']} | کل: {r['total']} | صحیح: {r['ok']} | غلط: {r['bad']}"))
    def page_quick(self):
        b=self.content("quick","ثبت سریع پاس"); self.match_selector(b)
        with self.db.connect() as c: players=c.execute("SELECT id,name,number FROM players ORDER BY name").fetchall()
        opts=[f"{p['id']} | {p['number']} - {p['name']}" for p in players]
        if not opts: opts=["بازیکنی ثبت نشده"]
        self.addrow(b,self.label("پاس‌دهنده")); passer=self.spin(opts); self.addrow(b,passer)
        self.addrow(b,self.label("پاس‌گیرنده")); receiver=self.spin(opts); self.addrow(b,receiver)
        self.addrow(b,self.label("نتیجه")); outcome=self.spin(["صحیح","غلط"]); self.addrow(b,outcome)
        self.addrow(b,self.label("طول پاس")); length=self.spin(["کوتاه","بلند"]); self.addrow(b,length)
        self.addrow(b,self.label("جهت پاس")); typ=self.spin(["رو به جلو","رو به عقب","عرضی","عمقی"]); self.addrow(b,typ)
        self.addrow(b,self.label("تعداد")); qty=self.inp("تعداد", "1"); self.addrow(b,qty)
        self.addrow(b,self.label("دقیقه مسابقه")); minute=self.inp("دقیقه","0"); self.addrow(b,minute)
        def save(*_):
            try:
                if not self.match_id() or not players: raise ValueError("ابتدا بازیکن و مسابقه ثبت کن.")
                pid=int(passer.text.split("|")[0]); rid=int(receiver.text.split("|")[0])
                if pid==rid: raise ValueError("پاس‌دهنده و گیرنده باید متفاوت باشند.")
                q=max(1,min(999,int(qty.text))); mn=max(0,min(150,int(minute.text or 0)))
                with self.db.connect() as c:
                    c.execute("INSERT OR IGNORE INTO match_players(match_id,player_id) VALUES(?,?)",(self.match_id(),pid))
                    c.execute("INSERT OR IGNORE INTO match_players(match_id,player_id) VALUES(?,?)",(self.match_id(),rid))
                    c.execute("""INSERT INTO passes(match_id,passer_id,receiver_id,outcome,length,created_at,pass_type,minute,quantity)
                      VALUES(?,?,?,?,?,?,?,?,?)""",(self.match_id(),pid,rid,outcome.text,length.text,datetime.now().isoformat(timespec="seconds"),typ.text,mn,q))
                qty.text="1"; self.popup("پاس با موفقیت ثبت شد."); self.refresh_all()
            except Exception as e:self.popup(str(e),"خطا")
        x=self.btn("ثبت پاس",primary=True); x.bind(on_release=save); self.addrow(b,x)
    def page_players(self):
        b=self.content("players","مدیریت بازیکنان")
        name=self.inp("نام بازیکن"); number=self.inp("شماره پیراهن"); pos=self.spin(POSITIONS)
        for w in [self.label("نام"),name,self.label("شماره"),number,self.label("پست"),pos]:self.addrow(b,w)
        def add(*_):
            if not name.text.strip():return self.popup("نام بازیکن را وارد کن.")
            try:
                with self.db.connect() as c:c.execute("INSERT INTO players(name,number,position) VALUES(?,?,?)",(name.text.strip(),number.text.strip(),pos.text))
                name.text="";number.text="";self.page_players()
            except sqlite3.IntegrityError:self.popup("این بازیکن قبلاً ثبت شده است.")
        z=self.btn("افزودن بازیکن",primary=True);z.bind(on_release=add);self.addrow(b,z)
        with self.db.connect() as c: rows=c.execute("SELECT id,name,number,position FROM players ORDER BY id DESC").fetchall()
        for r in rows:
            self.addrow(b,self.label(f"#{r['id']} | {r['number']} | {r['name']} | {r['position']}"))
            d=self.btn(f"حذف بازیکن #{r['id']}");d.bind(on_release=lambda _,pid=r["id"]:self.delete_player(pid));self.addrow(b,d)
    def delete_player(self,pid):
        with self.db.connect() as c:
            used=c.execute("SELECT 1 FROM passes WHERE passer_id=? OR receiver_id=? LIMIT 1",(pid,pid)).fetchone()
            if used:return self.popup("این بازیکن در سوابق پاس استفاده شده و قابل حذف نیست.")
            c.execute("DELETE FROM players WHERE id=?",(pid,))
        self.page_players()
    def page_matches(self):
        b=self.content("matches","مدیریت مسابقات")
        title=self.inp("عنوان مسابقه"); opp=self.inp("نام حریف"); dt=self.inp("تاریخ YYYY-MM-DD",date.today().isoformat())
        for w in [self.label("عنوان مسابقه"),title,self.label("حریف"),opp,self.label("تاریخ"),dt]:self.addrow(b,w)
        def add(*_):
            try:
                datetime.strptime(dt.text.strip(),"%Y-%m-%d")
                if not title.text.strip():raise ValueError("عنوان مسابقه الزامی است.")
                with self.db.connect() as c:c.execute("INSERT INTO matches(title,match_date,opponent) VALUES(?,?,?)",(title.text.strip(),dt.text.strip(),opp.text.strip()))
                self.refresh_all();self.page_matches()
            except Exception as e:self.popup(str(e),"خطا")
        z=self.btn("ایجاد مسابقه",primary=True);z.bind(on_release=add);self.addrow(b,z)
        with self.db.connect() as c:rows=c.execute("SELECT id,title,match_date,opponent FROM matches ORDER BY match_date DESC").fetchall()
        for r in rows:
            self.addrow(b,self.label(f"#{r['id']} | {r['match_date']} | {r['title']} | {r['opponent']}"))
            d=self.btn(f"انتخاب مسابقه #{r['id']}");d.bind(on_release=lambda _,mid=r["id"]:self.select_match(mid));self.addrow(b,d)
    def select_match(self,mid):self.active_match=mid;self.refresh_all();self.show("dashboard")
    def page_matrix(self):
        b=self.content("matrix","ماتریس پاس");self.match_selector(b);mid=self.match_id()
        with self.db.connect() as c:
            ps=c.execute("SELECT id,name FROM players ORDER BY name").fetchall()
            for p in ps:
                cells=[]
                for q in ps:
                    r=c.execute("SELECT COALESCE(SUM(CASE WHEN outcome='صحیح' THEN quantity ELSE 0 END),0) ok,COALESCE(SUM(CASE WHEN outcome='غلط' THEN quantity ELSE 0 END),0) bad FROM passes WHERE match_id=? AND passer_id=? AND receiver_id=?",(mid,p["id"],q["id"])).fetchone()
                    cells.append(f"{r['ok']}/{r['bad']}")
                self.addrow(b,self.label(p["name"]+" → "+" | ".join(cells),height=48))
    def page_network(self):
        b=self.content("network","شبکه پاس تیم");self.match_selector(b)
        with self.db.connect() as c:
            rows=c.execute("""SELECT a.name an,b.name bn,
            SUM(CASE WHEN ps.outcome='صحیح' THEN ps.quantity ELSE 0 END) ok,
            SUM(CASE WHEN ps.outcome='غلط' THEN ps.quantity ELSE 0 END) bad
            FROM passes ps JOIN players a ON a.id=ps.passer_id JOIN players b ON b.id=ps.receiver_id
            WHERE ps.match_id=? GROUP BY a.id,b.id ORDER BY 3 DESC""",(self.match_id(),)).fetchall()
        for r in rows:self.addrow(b,self.label(f"{r['an']} → {r['bn']} | صحیح {r['ok']} | غلط {r['bad']}"))
        if not rows:self.addrow(b,self.label("هنوز داده‌ای برای شبکه پاس ثبت نشده است."))
    def page_compare(self):
        b=self.content("compare","مقایسه بازیکنان");self.match_selector(b)
        _,_,_,_,rows=self.stats()
        for r in rows:
            rate=round(r["ok"]*100/r["total"],1) if r["total"] else 0
            self.addrow(b,self.label(f"{r['name']} | کل {r['total']} | صحیح {r['ok']} | غلط {r['bad']} | موفقیت {rate}%"))
    def page_timeline(self):
        b=self.content("timeline","خط زمانی مسابقه");self.match_selector(b)
        with self.db.connect() as c: rows=c.execute("SELECT minute,title,description,video_time FROM match_events WHERE match_id=? ORDER BY minute,id",(self.match_id(),)).fetchall()
        for r in rows:self.addrow(b,self.label(f"{r['minute']}' | {r['title']} | {r['description']} | {r['video_time']}"))
        if not rows:self.addrow(b,self.label("رویدادی برای این مسابقه ثبت نشده است. در نسخه دسکتاپ نیز فرم ثبت رویداد وجود ندارد."))
    def page_pitch(self):
        b=self.content("pitch","تحلیل زمین فوتبال")
        self.addrow(b,self.label("نمای شماتیک زمین؛ برای نقشه حرارتی واقعی باید مختصات پاس‌ها ثبت شوند.",height=62))
        pitch=Widget(size_hint_y=None,height=dp(230))
        with pitch.canvas:
            Color(0.10,0.38,0.25,1); Rectangle(pos=pitch.pos,size=pitch.size)
            Color(1,1,1,.8); Line(rectangle=(pitch.x+8,pitch.y+8,pitch.width-16,pitch.height-16),width=1.3)
            Line(points=[pitch.center_x,pitch.y+8,pitch.center_x,pitch.top-8],width=1.2)
            Ellipse(pos=(pitch.center_x-dp(35),pitch.center_y-dp(35)),size=(dp(70),dp(70)),width=1)
            Line(rectangle=(pitch.x+8,pitch.center_y-dp(58),dp(55),dp(116)),width=1)
            Line(rectangle=(pitch.right-dp(63),pitch.center_y-dp(58),dp(55),dp(116)),width=1)
        self.addrow(b,pitch)
        with self.db.connect() as c:n=c.execute("SELECT COUNT(*) FROM passes WHERE match_id=? AND start_x IS NOT NULL AND start_y IS NOT NULL",(self.match_id(),)).fetchone()[0]
        self.addrow(b,self.label(f"پاس‌های دارای مختصات شروع: {n}"))
    def page_settings(self):
        b=self.content("settings","تنظیمات و پوسته‌ها")
        sp=self.spin(list(THEMES.keys()));sp.text=fa(self.theme_name);self.addrow(b,self.label("انتخاب پوسته"));self.addrow(b,sp)
        def change(*_):
            self.theme_name=next((k for k in THEMES if fa(k)==sp.text),sp.text)
            self.prefs["theme"]=self.theme_name
            json.dump(self.prefs,open(self.prefs_path,"w",encoding="utf-8"),ensure_ascii=False)
            self.bg_color.rgba=self.rgb("bg");Window.clearcolor=self.rgb("bg")
            self.popup("پوسته ذخیره شد. برای اعمال کامل در همه بخش‌ها صفحه را دوباره باز کن.")
        z=self.btn("ذخیره پوسته",primary=True);z.bind(on_release=change);self.addrow(b,z)
        self.addrow(b,self.label("اطلاعات در حافظه داخلی برنامه ذخیره می‌شود. برای انتقال اطلاعات به گوشی دیگر، از فایل پایگاه داده نسخه پشتیبان تهیه کن.",height=90))

if __name__ == "__main__":
    AnalyzerApp().run()
