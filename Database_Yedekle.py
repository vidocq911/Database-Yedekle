import os, sys, json, shutil, subprocess, threading, tkinter as tk, webbrowser, urllib.request, urllib.error
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from datetime import datetime, timedelta

APP = "Database Yedekle"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
BG = "#0B1020"
NAVY = "#E7EEFF"
BLUE = "#8B5CF6"
MUTED = "#91A0BC"
GREEN = "#34D399"
CARD = "#111A2E"
SUPABASE_URL = "https://hkuoymftockxmynrcjwh.supabase.co"

def tool(name):
    for p in [
        Path(getattr(sys, "_MEIPASS", "."))/name,
        Path(sys.executable).parent/name if getattr(sys, "frozen", False) else Path(__file__).parent/name,
    ]:
        if p.exists(): return str(p)
    return shutil.which(name)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Database Yedekle")
        # Fixed compact desktop layout; keep every tab within the 940x620 window.
        self.geometry("940x620")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._set_app_icon()
        self.items, self.found = [], []
        self.dbtype = tk.StringVar(value="SQL Server")
        self.local = tk.StringVar(value=str(Path.home()/"DatabaseBackups"))
        self.drive_folder = tk.StringVar(value="DatabaseBackups")
        self.target = tk.StringVar(value="Google Drive")
        self.qnap_host = tk.StringVar(value="")
        self.qnap_port = tk.StringVar(value="22")
        self.qnap_user = tk.StringVar(value="")
        self.qnap_password = tk.StringVar(value="")
        self.qnap_path = tk.StringVar(value="/share/Backups")
        self.s3_endpoint = tk.StringVar(value="")
        self.s3_bucket = tk.StringVar(value="")
        self.s3_region = tk.StringVar(value="us-east-1")
        self.s3_access_key = tk.StringVar(value="")
        self.s3_secret_key = tk.StringVar(value="")
        self.interval = tk.StringVar(value="Günlük")
        self.auto = tk.BooleanVar(value=False)
        self.shrink = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Hazır")
        self.last_run = tk.StringVar(value="Henüz yedek alınmadı")
        self.running = False
        self._style()
        self._build()
        self._load()
        self.after(3000, self._scheduler)

    def _set_app_icon(self):
        # Layered cyan/violet database mark, matched to the refreshed interface.
        try:
            from PIL import Image, ImageDraw, ImageTk
            im = Image.new("RGBA", (64, 64), "#0B1020")
            d = ImageDraw.Draw(im)
            d.polygon([(32, 4), (56, 18), (32, 32), (8, 18)], fill="#22D3EE", outline="#A5F3FC")
            d.line([(8, 18), (32, 32), (56, 18)], fill="#E0F2FE", width=2)
            d.polygon([(8, 18), (32, 32), (32, 42), (8, 28)], fill="#0E7490", outline="#22D3EE")
            d.polygon([(56, 18), (32, 32), (32, 42), (56, 28)], fill="#5B21B6", outline="#8B5CF6")
            d.polygon([(32, 18), (49, 28), (32, 38), (15, 28)], fill="#7C3AED", outline="#A78BFA")
            d.polygon([(15, 28), (32, 38), (32, 48), (15, 38)], fill="#4C1D95", outline="#8B5CF6")
            d.polygon([(49, 28), (32, 38), (32, 48), (49, 38)], fill="#312E81", outline="#6366F1")
            d.polygon([(32, 11), (49, 21), (32, 31), (15, 21)], fill="#22D3EE", outline="#A5F3FC")
            d.line([(15, 21), (32, 31), (49, 21)], fill="#E0F2FE", width=1)
            self._icon_image = ImageTk.PhotoImage(im)
            self.iconphoto(True, self._icon_image)
        except Exception:
            pass

    def _style(self):
        s=ttk.Style(self)
        try:s.theme_use("clam")
        except tk.TclError:pass
        # Premium dark dashboard palette inspired by Databasement's layered
        # cyan/violet visual identity; application name and functions stay ours.
        s.configure("TFrame",background=BG)
        s.configure("TLabel",background=BG,foreground=NAVY,font=("Segoe UI",10))
        s.configure("Muted.TLabel",background=BG,foreground=MUTED,font=("Segoe UI",9))
        s.configure("Title.TLabel",background=BG,font=("Segoe UI",17,"bold"),foreground=NAVY)
        s.configure("Section.TLabel",background=BG,font=("Segoe UI",11,"bold"),foreground=NAVY)
        s.configure("Eyebrow.TLabel",background=BG,foreground="#22D3EE",font=("Segoe UI",8,"bold"))
        s.configure("TButton",font=("Segoe UI",10),padding=(11,8),background="#202B43",foreground="#DCE7FF",borderwidth=0,relief="flat")
        s.map("TButton",background=[("active","#303D59"),("disabled","#182136")],foreground=[("active","#FFFFFF")])
        s.configure("Primary.TButton",font=("Segoe UI",10,"bold"),padding=(15,9),background="#7C3AED",foreground="white",borderwidth=0,relief="flat")
        s.map("Primary.TButton",background=[("active","#8B5CF6"),("pressed","#6D28D9")],foreground=[("active","white")])
        s.configure("Treeview",rowheight=32,font=("Segoe UI",10),background=CARD,fieldbackground=CARD,foreground="#DCE7FF",borderwidth=0,relief="flat")
        s.configure("Treeview.Heading",font=("Segoe UI",9,"bold"),background="#202B43",foreground="#AFC2E8",padding=10,relief="flat")
        s.map("Treeview",background=[("selected","#3730A3")],foreground=[("selected","#FFFFFF")])
        s.configure("TCombobox",fieldbackground=CARD,background="#202B43",foreground="#E7EEFF",arrowcolor="#22D3EE",padding=7)
        s.map("TCombobox",fieldbackground=[("readonly",CARD)],foreground=[("readonly","#E7EEFF")])
        s.configure("TEntry",fieldbackground=CARD,foreground="#E7EEFF",insertcolor="#FFFFFF",padding=7)
        s.configure("TCheckbutton",background=BG,foreground="#DCE7FF",font=("Segoe UI",10))
        s.map("TCheckbutton",background=[("active",BG)],foreground=[("active","#FFFFFF")])
        s.configure("TNotebook",background=BG,borderwidth=0,tabmargins=(0,0,0,0),padding=0)
        s.configure("TNotebook.Tab",padding=(13,8),font=("Segoe UI",9,"bold"),background="#151E32",foreground="#8393B3",borderwidth=0,relief="flat")
        s.map("TNotebook.Tab",
              background=[("selected",CARD),("active","#202B43")],
              foreground=[("selected","#22D3EE"),("active","#E7EEFF")],
              padding=[("selected",(13,8)),("!selected",(13,8))],
              relief=[("selected","flat"),("!selected","flat")])

    def _build(self):
        shell=ttk.Frame(self,padding=10); shell.pack(fill="both",expand=True)
        head=ttk.Frame(shell);head.pack(fill="x",pady=(0,7))
        logo=tk.Canvas(head,width=58,height=58,bg=BG,highlightthickness=0)
        logo.pack(side="left",padx=(0,12))
        # Layered isometric database mark: cyan edges with violet depth,
        # a visual nod to the upstream project's dimensional logo.
        logo.create_polygon(29,3,53,17,29,31,5,17,fill="#22D3EE",outline="#67E8F9",width=1)
        logo.create_polygon(5,17,29,31,29,39,5,25,fill="#0E7490",outline="#22D3EE",width=1)
        logo.create_polygon(53,17,29,31,29,39,53,25,fill="#5B21B6",outline="#8B5CF6",width=1)
        logo.create_polygon(29,15,47,25,29,35,11,25,fill="#7C3AED",outline="#A78BFA",width=1)
        logo.create_polygon(11,25,29,35,29,43,11,33,fill="#4C1D95",outline="#8B5CF6",width=1)
        logo.create_polygon(47,25,29,35,29,43,47,33,fill="#312E81",outline="#6366F1",width=1)
        logo.create_polygon(29,8,47,18,29,28,11,18,fill="#22D3EE",outline="#A5F3FC",width=1)
        logo.create_line(11,18,29,28,47,18,fill="#E0F2FE",width=1)
        headtext=ttk.Frame(head);headtext.pack(side="left",fill="x",expand=True)
        ttk.Label(headtext,text="DATABASE Yedekle  /  BACKUP CONTROL",style="Eyebrow.TLabel").pack(anchor="w",pady=(1,2))
        ttk.Label(headtext,text="Güvenli yedekleme merkezi",style="Title.TLabel").pack(anchor="w")
        ttk.Label(headtext,text="SQL SERVER • POSTGRESQL • DRIVE • DROPBOX • SFTP",style="Muted.TLabel").pack(anchor="w",pady=(3,0))
        ttk.Button(head,text="Demo / Müşteri Kaydı",command=self.open_demo_registration).pack(side="right",padx=(8,0),pady=(8,0))
        ttk.Button(head,text="Destek",command=lambda:webbrowser.open("mailto:oguzhanyilmaz8@gmail.com?subject=Database%20Yedekle%20Destek")).pack(side="right",pady=(8,0))
        self.tabs=ttk.Notebook(shell);self.tabs.pack(fill="both",expand=True)
        self.dbtab=ttk.Frame(self.tabs,padding=5);self.schedtab=ttk.Frame(self.tabs,padding=6);self.storagetab=ttk.Frame(self.tabs,padding=6)
        self.tabs.add(self.dbtab,text="  Veritabanları  ")
        self.tabs.add(self.schedtab,text="  Otomatik Yedekleme  ")
        self.tabs.add(self.storagetab,text="  Yedekleme Hedefi  ")
        self._build_db();self._build_schedule();self._build_storage()
        foot=ttk.Frame(shell);foot.pack(fill="x",pady=(5,0))
        ttk.Label(foot,textvariable=self.status,style="Muted.TLabel").pack(side="left",fill="x",expand=True)
        ttk.Button(foot,text="Lisans",command=self.manage_license).pack(side="right",padx=(8,0))
        ttk.Button(foot,text="Google ile Bağlan",command=self.connect_google).pack(side="right",padx=(8,0))
        ttk.Button(foot,text="Şimdi Yedekle",style="Primary.TButton",command=self.start).pack(side="right")

    def manage_license(self):
        from license_manager import activate, check_cached_license
        try:
            payload = check_cached_license()
            expiry = payload.get("expires_at") or "Süresiz"
            due = payload.get("_client_online_check_due", False)
            msg = f"Aktif lisans. Bitiş: {expiry}"
            if due: msg += "\nÇevrimiçi doğrulama zamanı geldi."
            if not messagebox.askyesno("Lisans", msg + "\n\nYeniden doğrulansın mı?", parent=self): return
        except Exception as e:
            if not messagebox.askyesno("Lisans", str(e) + "\n\nLisans anahtarını girmek ister misin?", parent=self): return
        key = simpledialog.askstring("Lisans etkinleştirme", "Lisans anahtarı:", parent=self)
        if not key: return
        try:
            payload = activate(key)
            messagebox.showinfo("Lisans", "Lisans doğrulandı. Bitiş: " + str(payload.get("expires_at") or "Süresiz"), parent=self)
        except Exception as e:
            messagebox.showerror("Lisans", str(e), parent=self)
    def _draw_db_icon(self):
        if not hasattr(self, "db_icon"): return
        self.db_icon.delete("all")
        if self.dbtype.get() == "SQL Server":
            c = "#E7483D"
            self.db_icon.create_oval(3,3,31,12,fill=c,outline="#FFB4AE",width=1)
            self.db_icon.create_rectangle(3,7,31,25,fill=c,outline="")
            self.db_icon.create_arc(3,20,31,30,start=180,extent=180,style="arc",outline="#FFB4AE",width=2)
            self.db_icon.create_arc(3,11,31,20,start=0,extent=180,style="arc",outline="#FFD4D0",width=1)
            self.db_icon.create_line(4,16,30,16,fill="#FFD4D0",width=1)
        else:
            c = "#336791"
            self.db_icon.create_oval(5,5,25,25,fill=c,outline="#A7D5F4",width=1)
            self.db_icon.create_oval(2,8,10,17,fill=c,outline="#A7D5F4",width=1)
            self.db_icon.create_oval(20,5,31,16,fill=c,outline="#A7D5F4",width=1)
            self.db_icon.create_arc(14,14,27,32,start=270,extent=150,style="arc",outline="#A7D5F4",width=4)
            self.db_icon.create_oval(20,9,23,12,fill="white",outline="")
            self.db_icon.create_oval(21,10,22,11,fill="#17243A",outline="")

    def open_demo_registration(self):
        win=tk.Toplevel(self)
        win.title("Demo erişimi ve müşteri kaydı")
        win.configure(bg=BG)
        win.resizable(False,False)
        win.transient(self); win.grab_set()
        outer=ttk.Frame(win,padding=24); outer.pack(fill="both",expand=True)
        ttk.Label(outer,text="Database Yedekle",style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer,text="Ücretsiz demo talep et veya müşteri kaydını oluştur.",style="Muted.TLabel").pack(anchor="w",pady=(4,18))
        fields={}
        for key,label in [("company_name","Firma adı"),("contact_person","Yetkili kişi"),("phone","Telefon"),("email","E-posta (isteğe bağlı)")]:
            ttk.Label(outer,text=label,style="Section.TLabel").pack(anchor="w",pady=(5,3))
            var=tk.StringVar()
            ttk.Entry(outer,textvariable=var,width=48,font=("Segoe UI",10)).pack(fill="x",ipady=5)
            fields[key]=var
        ttk.Label(outer,text="Demo süresi, talep yönetici tarafından onaylandıktan sonra başlar.",wraplength=410,style="Muted.TLabel").pack(anchor="w",pady=(12,14))
        result=tk.StringVar(value="")
        ttk.Label(outer,textvariable=result,wraplength=410).pack(anchor="w",pady=(0,8))
        def submit():
            payload={k:v.get().strip() for k,v in fields.items()}
            if len(payload["company_name"])<2 or len(payload["contact_person"])<2 or len(payload["phone"])<7:
                messagebox.showwarning("Eksik bilgi","Firma adı, yetkili kişi ve geçerli telefon zorunludur.",parent=win);return
            button.configure(state="disabled",text="Gönderiliyor…")
            try:
                data=json.dumps(payload).encode("utf-8")
                req=urllib.request.Request(SUPABASE_URL+"/functions/v1/demo-request",data=data,headers={"Content-Type":"application/json","Accept":"application/json"},method="POST")
                with urllib.request.urlopen(req,timeout=20) as response:
                    body=json.loads(response.read().decode("utf-8"))
                message=body.get("message","Talep alındı.")
                messagebox.showinfo("Talep alındı",message,parent=win)
                win.destroy()
            except urllib.error.HTTPError as exc:
                try:
                    raw=exc.read().decode("utf-8",errors="replace")
                    parsed=json.loads(raw)
                    message=parsed.get("error") or parsed.get("message") or f"Sunucu HTTP {exc.code} yanıtı verdi."
                except Exception:
                    message=f"Sunucu HTTP {exc.code} yanıtı verdi. Demo talebi servisini kontrol edin."
                result.set(message);button.configure(state="normal",text="Demo talebi gönder")
            except Exception as exc:
                result.set("Sunucuya ulaşılamadı: "+str(exc))
                button.configure(state="normal",text="Demo talebi gönder")
        button=ttk.Button(outer,text="Demo talebi gönder",style="Primary.TButton",command=submit)
        button.pack(fill="x")
        win.update_idletasks()
        win.geometry(f"+{self.winfo_rootx()+80}+{self.winfo_rooty()+60}")

    def _build_db(self):
        bar=ttk.Frame(self.dbtab);bar.pack(fill="x",pady=(0,10))
        ttk.Label(bar,text="VERİTABANI MOTORU",style="Section.TLabel").pack(side="left",padx=(0,12))
        self.db_icon=tk.Canvas(bar,width=34,height=34,bg=BG,highlightthickness=0)
        self.db_icon.pack(side="left",padx=(0,5))
        self._draw_db_icon()
        db_combo=ttk.Combobox(bar,textvariable=self.dbtype,values=["SQL Server","PostgreSQL"],state="readonly",width=18,font=("Segoe UI",10))
        db_combo.pack(side="left",padx=(0,12))
        db_combo.bind("<<ComboboxSelected>>",lambda _e:self._draw_db_icon())
        ttk.Button(bar,text="Otomatik Ara",command=self.scan).pack(side="left",padx=4)
        ttk.Button(bar,text="Manuel Ekle",command=self.add_manual).pack(side="left",padx=4)
        ttk.Button(bar,text="Kaldır",command=self.remove).pack(side="left",padx=4)
        panes=ttk.Panedwindow(self.dbtab,orient="vertical")
        panes.pack(fill="both",expand=True,pady=(0,2))
        main=ttk.Frame(panes,padding=(0,0,0,5)); found=ttk.Frame(panes,padding=(0,5,0,0))
        panes.add(main,weight=3); panes.add(found,weight=2)
        ttk.Label(main,text="Yedekleme listesi",style="Section.TLabel").pack(anchor="w")
        ttk.Label(main,text="Satıra çift tıklayarak dahil etme durumunu değiştir. Seçilen kayıtlar yedeklenir.",style="Muted.TLabel").pack(anchor="w",pady=(2,8))
        cols=("use","type","server","db","alias")
        wrap=ttk.Frame(main);wrap.pack(fill="both",expand=True)
        self.tree=ttk.Treeview(wrap,columns=cols,show="headings",selectmode="extended")
        vs=ttk.Scrollbar(wrap,orient="vertical",command=self.tree.yview);hs=ttk.Scrollbar(wrap,orient="horizontal",command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set,xscrollcommand=hs.set)
        for col,title,width in [("use","Dahil",60),("type","Tür",115),("server","Sunucu / Host",190),("db","Veritabanı",230),("alias","Yedek adı",190)]:
            self.tree.heading(col,text=title);self.tree.column(col,width=width,anchor="w",stretch=col in ("server","db","alias"))
        self.tree.grid(row=0,column=0,sticky="nsew");vs.grid(row=0,column=1,sticky="ns");hs.grid(row=1,column=0,sticky="ew")
        wrap.rowconfigure(0,weight=1);wrap.columnconfigure(0,weight=1)
        self.tree.bind("<Double-1>",self.toggle)
        actions=ttk.Frame(main);actions.pack(fill="x",pady=(7,0))
        ttk.Button(actions,text="Tümünü Dahil Et",command=lambda:self.set_all(True)).pack(side="left")
        ttk.Button(actions,text="Hiçbirini Seçme",command=lambda:self.set_all(False)).pack(side="left",padx=6)
        ttk.Button(actions,text="Yedek Adını Düzenle",command=self.rename).pack(side="right")
        ttk.Label(found,text="Arama sonuçları",style="Section.TLabel").pack(anchor="w",pady=(0,4))
        fwrap=ttk.Frame(found);fwrap.pack(fill="both",expand=True)
        self.foundtree=ttk.Treeview(fwrap,columns=("pick","type","server","db"),show="headings",selectmode="extended")
        fvs=ttk.Scrollbar(fwrap,orient="vertical",command=self.foundtree.yview);fhs=ttk.Scrollbar(fwrap,orient="horizontal",command=self.foundtree.xview)
        self.foundtree.configure(yscrollcommand=fvs.set,xscrollcommand=fhs.set)
        for col,title,width in [("pick","Ekle",55),("type","Tür",115),("server","Sunucu",190),("db","Bulunan veritabanı",250)]:
            self.foundtree.heading(col,text=title);self.foundtree.column(col,width=width,anchor="w",stretch=col in ("server","db"))
        self.foundtree.grid(row=0,column=0,sticky="nsew");fvs.grid(row=0,column=1,sticky="ns");fhs.grid(row=1,column=0,sticky="ew")
        fwrap.rowconfigure(0,weight=1);fwrap.columnconfigure(0,weight=1)
        fbtn=ttk.Frame(found);fbtn.pack(fill="x",pady=(6,0))
        ttk.Button(fbtn,text="Bulunanları İşaretle",command=lambda:self.mark_found(True)).pack(side="left")
        ttk.Button(fbtn,text="İşaretlileri Listeye Ekle",style="Primary.TButton",command=self.add_found).pack(side="right")

    def _build_schedule(self):
        ttk.Label(self.schedtab,text="Yedekleme planı",style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.schedtab,text="Seçtiğin veritabanları belirlenen aralıkta yedeklenir.",style="Muted.TLabel").pack(anchor="w",pady=(3,10))
        card=ttk.Frame(self.schedtab,padding=12);card.pack(fill="x")
        ttk.Checkbutton(card,text="Otomatik yedeklemeyi etkinleştir",variable=self.auto,command=self.save).grid(row=0,column=0,sticky="w",columnspan=2,pady=(0,16))
        ttk.Label(card,text="Yedekleme sıklığı").grid(row=1,column=0,sticky="w",pady=7)
        ttk.Combobox(card,textvariable=self.interval,values=["Günlük","Haftalık","Aylık","3 aylık"],state="readonly",width=18).grid(row=1,column=1,sticky="w",padx=12)
        ttk.Label(card,text="Bir sonraki kontrol",style="Muted.TLabel").grid(row=2,column=0,sticky="w",pady=7)
        ttk.Label(card,text="Uygulama açıkken dakikada bir kontrol edilir.",style="Muted.TLabel").grid(row=2,column=1,sticky="w",padx=12)
        ttk.Label(card,text="Son otomatik yedek",style="Muted.TLabel").grid(row=3,column=0,sticky="w",pady=7)
        ttk.Label(card,textvariable=self.last_run).grid(row=3,column=1,sticky="w",padx=12)
        ttk.Label(self.schedtab,text="Not: Bu sürümde zamanlama yalnızca uygulama açıkken çalışır. Windows açılışında otomatik başlatma ayrı kurulum adımı gerektirir.",wraplength=760,style="Muted.TLabel").pack(anchor="w",pady=16)
        ttk.Separator(self.schedtab).pack(fill="x",pady=8)
        ttk.Checkbutton(self.schedtab,text="SQL Server yedeğinden önce veritabanını küçült (ileri seviye / riskli)",variable=self.shrink,command=self._shrink_warning).pack(anchor="w",pady=8)
        ttk.Label(self.schedtab,text="Öneri: Dosya boyutunu azaltmak için önce sıkıştırılmış yedeği kullan. Shrink işlemi veritabanı performansını etkileyebilir.",wraplength=760,style="Muted.TLabel").pack(anchor="w")

    def _build_storage(self):
        ttk.Label(self.storagetab,text="Yedekleme hedefi",style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.storagetab,text="Yedekler seçtiğin hedefe doğrudan gönderilir; aracı sunucu yoktur.",style="Muted.TLabel").pack(anchor="w",pady=(4,10))
        targetrow=ttk.Frame(self.storagetab);targetrow.pack(fill="x",pady=(0,10))
        ttk.Label(targetrow,text="Hedef").pack(side="left")
        ttk.Combobox(targetrow,textvariable=self.target,values=["Yerel klasör","Google Drive","Dropbox","QNAP / SFTP","S3 uyumlu depolama"],state="readonly",width=20).pack(side="left",padx=8)
        ttk.Label(self.storagetab,text="Yerel yedek klasörü",style="Section.TLabel").pack(anchor="w")
        row=ttk.Frame(self.storagetab);row.pack(fill="x",pady=(4,10))
        ttk.Entry(row,textvariable=self.local).pack(side="left",fill="x",expand=True)
        ttk.Button(row,text="Klasör seç…",command=self.browse).pack(side="left",padx=(8,0))
        ttk.Label(self.storagetab,text="Google Drive klasör adı").pack(anchor="w")
        ttk.Entry(self.storagetab,textvariable=self.drive_folder).pack(fill="x",pady=(3,8))
        ttk.Label(self.storagetab,text="Uzak QNAP / SFTP bağlantısı",style="Section.TLabel").pack(anchor="w",pady=(4,4))
        grid=ttk.Frame(self.storagetab);grid.pack(fill="x")
        for col, (label,var,width,show) in enumerate([("Sunucu / IP",self.qnap_host,28,None),("Port",self.qnap_port,7,None),("Kullanıcı",self.qnap_user,18,None),("Parola",self.qnap_password,18,"*")]):
            cell=ttk.Frame(grid);cell.grid(row=0,column=col,padx=(0,6),sticky="ew")
            ttk.Label(cell,text=label).pack(anchor="w")
            ttk.Entry(cell,textvariable=var,width=width,show=show).pack(fill="x")
            grid.columnconfigure(col,weight=1)
        ttk.Label(self.storagetab,text="Uzak klasör (örn. /share/Backups veya SFTP ana dizinine göre Backups)").pack(anchor="w",pady=(5,0))
        ttk.Entry(self.storagetab,textvariable=self.qnap_path).pack(fill="x",pady=(2,5))
        statusrow=ttk.Frame(self.storagetab);statusrow.pack(fill="x",pady=(1,5))
        ttk.Button(statusrow,text="Google hesabını bağla",command=self.connect_google).pack(side="left")
        ttk.Button(statusrow,text="Google bağlantısını kes / hesabı unut",command=self.disconnect_google).pack(side="left",padx=6)
        ttk.Button(statusrow,text="Dropbox hesabını bağla",command=self.connect_dropbox).pack(side="left",padx=6)
        ttk.Button(statusrow,text="Dropbox bağlantısını kes",command=self.disconnect_dropbox).pack(side="left",padx=6)
        ttk.Button(statusrow,text="QNAP bağlantısını test et",command=self.test_sftp).pack(side="left",padx=6)
        ttk.Label(self.storagetab,text="S3 uyumlu depolama (AWS S3 / Cloudflare R2 / MinIO)").pack(anchor="w",pady=(8,2))
        s3grid=ttk.Frame(self.storagetab);s3grid.pack(fill="x")
        for col,(label,var,width,show) in enumerate([("Endpoint URL",self.s3_endpoint,22,None),("Bucket",self.s3_bucket,14,None),("Region",self.s3_region,10,None),("Access key",self.s3_access_key,15,None),("Secret key",self.s3_secret_key,15,"*")]):
            cell=ttk.Frame(s3grid);cell.grid(row=0,column=col,padx=(0,4),sticky="ew")
            ttk.Label(cell,text=label).pack(anchor="w");ttk.Entry(cell,textvariable=var,width=width,show=show).pack(fill="x")
            s3grid.columnconfigure(col,weight=1)
        ttk.Label(self.storagetab,text="Google belirteci bu Windows kullanıcısının AppData alanında tutulur. Ortak bilgisayarda bağlantıyı kes. QNAP parolası ayarlarda kaydedilir; hassas cihazlarda kullanımdan sonra temizle.",wraplength=760,style="Muted.TLabel").pack(anchor="w",pady=(4,0))

    def _config_dir(self):
        p=Path(os.getenv("APPDATA",str(Path.home())))/"DatabaseYedekle";p.mkdir(parents=True,exist_ok=True);return p

    def _load(self):
        try:
            d=json.loads((self._config_dir()/"settings.json").read_text(encoding="utf-8"))
            self.items=d.get("items",[]);self.local.set(d.get("local",self.local.get()));self.drive_folder.set(d.get("drive_folder","DatabaseBackups"))
            self.target.set(d.get("target","Google Drive"));self.s3_endpoint.set(d.get("s3_endpoint",""));self.s3_bucket.set(d.get("s3_bucket",""));self.s3_region.set(d.get("s3_region","us-east-1"));self.s3_access_key.set("");self.s3_secret_key.set("");self.qnap_host.set(d.get("qnap_host",""));self.qnap_port.set(d.get("qnap_port","22"));self.qnap_user.set(d.get("qnap_user",""));self.qnap_password.set("");self.qnap_path.set(d.get("qnap_path","/share/Backups"))
            self.auto.set(d.get("auto",False));self.interval.set(d.get("interval","Günlük"));self.shrink.set(d.get("shrink",False));self.refresh()
            try:self.last_run.set(json.loads((self._config_dir()/"last.json").read_text())["timestamp"])
            except Exception:pass
        except Exception:pass

    def save(self):
        try:
            d={"items":self.items,"local":self.local.get(),"drive_folder":self.drive_folder.get(),"auto":self.auto.get(),"interval":self.interval.get(),"shrink":self.shrink.get(),"target":self.target.get(),"s3_endpoint":self.s3_endpoint.get(),"s3_bucket":self.s3_bucket.get(),"s3_region":self.s3_region.get(),"qnap_host":self.qnap_host.get(),"qnap_port":self.qnap_port.get(),"qnap_user":self.qnap_user.get(),"qnap_path":self.qnap_path.get()}
            (self._config_dir()/"settings.json").write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception as e:self.status.set("Ayar kaydedilemedi: "+str(e))

    def _shrink_warning(self):
        if self.shrink.get() and not messagebox.askyesno("İşlem riski","SQL Server shrink indeks parçalanmasına ve performans kaybına yol açabilir. Yalnızca disk alanını geri kazanmak gerekiyorsa etkinleştir. Devam?"):
            self.shrink.set(False)
        self.save()

    def _config_credentials(self):
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        token=self._config_dir()/"google_token.json"
        # OAuth istemci yapılandırması uygulamayla birlikte paketlenir.
        # _MEIPASS, PyInstaller --add-data ile eklenen dosyaların geçici konumudur.
        candidates = []
        if getattr(sys, "frozen", False):
            candidates.append(Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "client_secrets.json")
            candidates.append(Path(sys.executable).parent / "client_secrets.json")
        else:
            candidates.append(Path(__file__).parent / "client_secrets.json")
        secrets = next((p for p in candidates if p.is_file()), None)
        if secrets is None:
            raise RuntimeError(
                "Bu uygulama paketi Google Drive bağlantısı için yapılandırılmamış. "
                "Uygulamanın geliştiricisi Google OAuth Desktop istemci ayarlarını "
                "build işlemine eklemeli. Kullanıcının ayrıca JSON dosyası bulması gerekmemeli."
            )
        creds=None
        if token.exists():
            try:
                creds=Credentials.from_authorized_user_file(str(token),SCOPES)
            except Exception:
                creds=None
        # Expired/revoked tokens must not permanently block sign-in. If refresh
        # fails (e.g. invalid_grant), discard the stale token and authorize again.
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds=None
                try: token.unlink(missing_ok=True)
                except OSError: pass
        if not creds or not creds.valid:
            flow=InstalledAppFlow.from_client_secrets_file(str(secrets),SCOPES)
            # Explicit offline access ensures a refresh token can be issued.
            # Consent may be shown again; this is preferable to saving a token
            # that expires and leaves unattended scheduled backups broken.
            creds=flow.run_local_server(port=0,access_type="offline",prompt="consent")
            token.write_text(creds.to_json(),encoding="utf-8")
        return build("drive","v3",credentials=creds,cache_discovery=False)

    def connect_google(self):
        try:
            svc=self._config_credentials()
            # drive.file does not grant the broader account metadata scope needed
            # by about.get(). Validate with a Drive files.list call instead.
            svc.files().list(q="trashed=false",pageSize=1,fields="files(id,name)").execute()
            messagebox.showinfo(
                "Google Drive",
                "Google Drive bağlantısı doğrulandı. Yedekler uygulamanın erişebildiği "
                "Drive alanına yüklenebilir.",
                parent=self,
            )
            self.status.set("Google Drive bağlantısı doğrulandı.")
        except Exception as e:
            detail=str(e)
            low=detail.lower()
            if "access_denied" in low or "access blocked" in low or "app_not_configured_for_user" in low:
                detail += (
                    "\\n\\nGoogle OAuth izin ekranı uygulamayı engelliyor olabilir. "
                    "Google Cloud Console > Google Auth Platform > Audience bölümünde "
                    "uygulama Testing durumundaysa hesabını Test users listesine ekle. "
                    "Genel kullanıcılara dağıtmak için Google'ın doğrulama süreci gerekir."
                )
            elif "invalid_client" in low or "client_secret" in low or "client id" in low:
                detail += (
                    "\\n\\nGitHub Actions secret GOOGLE_OAUTH_CLIENT_JSON içinde "
                    "Google Cloud Console'dan alınmış OAuth Client ID türü Desktop app "
                    "JSON dosyası bulunmalı."
                )
            elif "insufficient" in low or "403" in low:
                detail += (
                    "\\n\\nDrive API'nin Google Cloud projesinde etkin olduğunu ve "
                    "uygulamanın drive.file iznini istediğini kontrol et."
                )
            messagebox.showerror("Google Drive bağlantısı",detail,parent=self)

    def disconnect_google(self):
        token=self._config_dir()/"google_token.json"
        try:
            if token.exists(): token.unlink()
            self.status.set("Google bağlantısı kaldırıldı; yerel belirteç silindi.")
            messagebox.showinfo("Google bağlantısı","Bu bilgisayardaki yerel Google belirteci silindi. Tam erişim iptali için Google Hesabı > Güvenlik > Üçüncü taraf bağlantıları bölümünden de uygulama erişimini kaldır.")
        except Exception as e: messagebox.showerror("Bağlantı kesilemedi",str(e))

    def _dropbox_app_key(self):
        candidates=[]
        if getattr(sys,"frozen",False):
            candidates += [Path(getattr(sys,"_MEIPASS",Path(sys.executable).parent))/"dropbox_app_key.txt",Path(sys.executable).parent/"dropbox_app_key.txt"]
        else:
            candidates += [Path(__file__).parent/"dropbox_app_key.txt"]
        for path in candidates:
            try:
                value=path.read_text(encoding="utf-8-sig").strip()
                if value:return value
            except OSError:pass
        raise RuntimeError("Dropbox bağlantısı bu EXE için henüz yapılandırılmamış. Geliştirici Dropbox App Key değerini DROPBOX_APP_KEY secret alanına ekleyip yeniden derlemeli.")

    def _dropbox_client(self,interactive=False):
        import dropbox
        app_key=self._dropbox_app_key()
        token_path=self._config_dir()/"dropbox_token.json"
        token_data={}
        try:token_data=json.loads(token_path.read_text(encoding="utf-8"))
        except Exception:pass
        refresh=token_data.get("refresh_token")
        if not refresh and interactive:
            flow=dropbox.DropboxOAuth2FlowNoRedirect(app_key,token_access_type="offline")
            auth_url=flow.start()
            webbrowser.open(auth_url)
            code=simpledialog.askstring("Dropbox bağlantısı","Tarayıcıda Dropbox'a giriş yapıp izin ver. Gösterilen yetkilendirme kodunu buraya yapıştır:",parent=self)
            if not code:raise RuntimeError("Dropbox bağlantısı iptal edildi.")
            result=flow.finish(code.strip())
            refresh=result.refresh_token
            token_path.write_text(json.dumps({"refresh_token":refresh},indent=2),encoding="utf-8")
        if not refresh:
            raise RuntimeError("Dropbox hesabı bağlı değil. Önce Yedekleme Hedefi sekmesinden Dropbox hesabını bağla.")
        client=dropbox.Dropbox(oauth2_refresh_token=refresh,app_key=app_key)
        client.users_get_current_account()
        return client

    def connect_dropbox(self):
        try:
            self._dropbox_client(interactive=True)
            self.status.set("Dropbox bağlantısı doğrulandı.")
            messagebox.showinfo("Dropbox","Dropbox hesabı başarıyla bağlandı.",parent=self)
        except Exception as e:
            messagebox.showerror("Dropbox bağlantısı",str(e),parent=self)

    def disconnect_dropbox(self):
        try:
            token=self._config_dir()/"dropbox_token.json"
            token.unlink(missing_ok=True)
            self.status.set("Dropbox bağlantısı kesildi.")
            messagebox.showinfo("Dropbox","Bu bilgisayardaki Dropbox yenileme belirteci silindi.",parent=self)
        except Exception as e:messagebox.showerror("Dropbox",str(e),parent=self)

    def _sftp_connect(self):
        import paramiko
        host=self.qnap_host.get().strip()
        if not host: raise RuntimeError("QNAP sunucu adresini gir.")
        try: port=int(self.qnap_port.get().strip() or "22")
        except ValueError: raise RuntimeError("SFTP portu sayısal olmalı.")
        transport=paramiko.Transport((host,port))
        transport.connect(username=self.qnap_user.get().strip(),password=self.qnap_password.get())
        return paramiko.SFTPClient.from_transport(transport),transport

    def test_sftp(self):
        try:
            client,transport=self._sftp_connect()
            client.listdir(self.qnap_path.get().strip() or ".")
            client.close();transport.close()
            self.status.set("QNAP / SFTP bağlantısı başarılı.")
            messagebox.showinfo("QNAP bağlantısı","SFTP bağlantısı başarılı; uzak klasör okunabiliyor.")
        except Exception as e: messagebox.showerror("QNAP bağlantısı başarısız",str(e))

    def scan(self):
        typ=self.dbtype.get()
        client="sqlcmd" if typ=="SQL Server" else "psql"
        exe=tool(client)
        if not exe:
            if typ == "SQL Server":
                detail = (
                    "SQL Server komut satırı aracı (sqlcmd) bu uygulama paketinde bulunamadı.\n\n"
                    "Otomatik tarama ve SQL Server yedekleme için bu araç gerekir. Bu sürümde araç EXE içine henüz gömülü değil.\n\n"
                    "Şimdilik Manuel Ekle ile sunucu/veritabanı kaydı oluşturabilirsin; yedek almak için sqlcmd kurulumu yine gerekir.\n\n"
                    "Microsoft'un resmi kurulum sayfasını açayım mı?"
                )
                url = "https://learn.microsoft.com/sql/tools/sqlcmd/sqlcmd-utility"
            else:
                detail = (
                    "PostgreSQL komut satırı araçları (psql / pg_dump) bu uygulama paketinde bulunamadı.\n\n"
                    "psql otomatik tarama, pg_dump yedek alma için gerekir. Bu sürümde araçlar EXE içine henüz gömülü değil.\n\n"
                    "Şimdilik Manuel Ekle ile veritabanı kaydı oluşturabilirsin; yedek almak için istemci araçları yine gerekir.\n\n"
                    "PostgreSQL'in resmi indirme sayfasını açayım mı?"
                )
                url = "https://www.postgresql.org/download/windows/"
            if messagebox.askyesno("Veritabanı aracı gerekli", detail, parent=self):
                webbrowser.open(url)
            self.status.set(f"Otomatik arama yapılamadı: {client} bulunamadı.")
            return
        self.status.set("Yerel veritabanları taranıyor…")
        hosts=["localhost",".","(local)",r"localhost\SQLEXPRESS",r".\SQLEXPRESS"] if typ=="SQL Server" else ["localhost","127.0.0.1"]
        threading.Thread(target=self._scan_worker,args=(typ,exe,hosts),daemon=True).start()

    def _scan_worker(self,typ,exe,hosts):
        found=[]
        for host in hosts:
            try:
                if typ=="SQL Server":
                    cmd=[exe,"-S",host,"-E","-h","-1","-W","-Q","SET NOCOUNT ON; SELECT name FROM sys.databases WHERE database_id > 4","-b"]
                else:
                    cmd=[exe,"-h",host,"-U",os.getenv("PGUSER","postgres"),"-d","postgres","-Atc","SELECT datname FROM pg_database WHERE datistemplate=false"]
                p=subprocess.run(cmd,capture_output=True,text=True,timeout=8,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                if p.returncode==0:
                    for db in [x.strip() for x in p.stdout.splitlines() if x.strip()]:
                        if not any(i["type"]==typ and i["server"]==host and i["db"]==db for i in found):
                            found.append({"use":True,"type":typ,"server":host,"db":db,"alias":db,"user":""})
            except Exception:pass
        self.after(0,lambda:self.show_found(found))

    def show_found(self,items):
        self.found=items;self.foundtree.delete(*self.foundtree.get_children())
        for i,x in enumerate(items):self.foundtree.insert("","end",iid=str(i),values=("✓",x["type"],x["server"],x["db"]))
        self.status.set(f"Arama tamamlandı: {len(items)} veritabanı bulundu.")
        if not items:messagebox.showinfo("Sonuç yok","Veritabanı bulunamadı. Servis ve yetkileri kontrol et; sunucu adını biliyorsan Manuel Ekle kullan.")

    def mark_found(self,val):
        for i,x in enumerate(self.found):x["use"]=val;self.foundtree.set(str(i),"pick","✓" if val else "—")

    def add_found(self):
        ids=self.foundtree.selection()
        chosen=[self.found[int(i)] for i in ids] if ids else [x for x in self.found if x.get("use",True)]
        for x in chosen:
            if not any(y["type"]==x["type"] and y["server"]==x["server"] and y["db"]==x["db"] for y in self.items):self.items.append(x.copy())
        self.refresh();self.save();self.status.set(f"{len(chosen)} kayıt yedekleme listesine eklendi.")

    def add_manual(self):
        typ=self.dbtype.get()
        host=simpledialog.askstring("Bağlantı bilgisi","Sunucu / host (örn. localhost veya .\\SQLEXPRESS):",parent=self)
        if not host:return
        db=simpledialog.askstring("Bağlantı bilgisi","Veritabanı adı:",parent=self)
        if not db:return
        alias=simpledialog.askstring("Yedek adı","Yedek dosyasında kullanılacak ad:",initialvalue=db,parent=self) or db
        user=simpledialog.askstring("Veritabanı kullanıcısı","Kullanıcı adı (Windows kimlik doğrulaması için boş bırak):",parent=self) or ""
        self.items.append({"use":True,"type":typ,"server":host,"db":db,"alias":alias,"user":user})
        self.refresh();self.save()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,x in enumerate(self.items):self.tree.insert("","end",iid=str(i),values=("✓" if x.get("use",True) else "—",x["type"],x["server"],x["db"],x.get("alias",x["db"])))

    def toggle(self,event):
        iid=self.tree.identify_row(event.y)
        if iid:
            x=self.items[int(iid)];x["use"]=not x.get("use",True);self.refresh();self.save()

    def set_all(self,val):
        for x in self.items:x["use"]=val
        self.refresh();self.save()

    def remove(self):
        ids=sorted((int(i) for i in self.tree.selection()),reverse=True)
        if not ids:messagebox.showinfo("Seçim gerekli","Kaldırılacak satırı seç.");return
        for i in ids:del self.items[i]
        self.refresh();self.save()

    def rename(self):
        ids=self.tree.selection()
        if len(ids)!=1:messagebox.showinfo("Seçim gerekli","Yedek adını değiştirmek için bir satır seç.");return
        x=self.items[int(ids[0])]
        name=simpledialog.askstring("Yedek adı","Yeni yedek adı:",initialvalue=x.get("alias",x["db"]),parent=self)
        if name and name.strip():x["alias"]=name.strip();self.refresh();self.save()

    def browse(self):
        d=filedialog.askdirectory(initialdir=self.local.get())
        if d:self.local.set(d);self.save()

    def start(self):
        chosen=[x.copy() for x in self.items if x.get("use",True)]
        if not chosen:messagebox.showinfo("Yedekleme listesi boş","Önce Veritabanları sekmesinde kayıt ekle ve dahil et.");return
        if self.running:return
        self.save();self.running=True
        threading.Thread(target=self._backup_worker,args=(chosen,),daemon=True).start()

    def _scheduler(self):
        try:
            if self.auto.get() and not self.running:
                last=None
                try:last=datetime.fromisoformat(json.loads((self._config_dir()/"last.json").read_text())["timestamp"])
                except Exception:pass
                days={"Günlük":1,"Haftalık":7,"Aylık":30,"3 aylık":90}.get(self.interval.get(),1)
                if last is None or datetime.now()-last>=timedelta(days=days):
                    chosen=[x.copy() for x in self.items if x.get("use",True)]
                    if chosen:
                        self.running=True
                        threading.Thread(target=self._backup_worker,args=(chosen,),daemon=True).start()
        finally:self.after(60000,self._scheduler)

    def _backup_worker(self,items):
        try:
            service=None; sftp=None; transport=None; remote_day=None
            target=self.target.get()
            outdir=Path(self.local.get())/datetime.now().strftime("%Y-%m-%d");outdir.mkdir(parents=True,exist_ok=True)
            if target=="Google Drive":
                service=self._config_credentials()
                root=self._drive_folder(service,self.drive_folder.get().strip() or "DatabaseBackups")
                remote_day=self._drive_folder(service,datetime.now().strftime("%Y-%m-%d"),root)
            elif target=="Dropbox":
                service=self._dropbox_client(interactive=False)
                remote_day="/"+(self.drive_folder.get().strip() or "DatabaseBackups").strip("/")+"/"+datetime.now().strftime("%Y-%m-%d")
                try:service.files_create_folder_v2(remote_day)
                except Exception as e:
                    if "conflict" not in str(e).lower(): raise
            elif target=="S3 uyumlu depolama":
                import boto3
                if not self.s3_bucket.get().strip() or not self.s3_access_key.get().strip() or not self.s3_secret_key.get().strip():
                    raise RuntimeError("S3 için Bucket, Access key ve Secret key alanlarını doldur.")
                service=boto3.client("s3",endpoint_url=self.s3_endpoint.get().strip() or None,region_name=self.s3_region.get().strip() or "us-east-1",aws_access_key_id=self.s3_access_key.get().strip(),aws_secret_access_key=self.s3_secret_key.get().strip())
                remote_day=datetime.now().strftime("%Y-%m-%d")
            elif target=="QNAP / SFTP":
                sftp,transport=self._sftp_connect()
                remote_root=self.qnap_path.get().strip() or "."
                try:sftp.stat(remote_root)
                except IOError:raise RuntimeError("QNAP üzerindeki uzak klasör bulunamadı. QNAP'ta oluştur veya doğru yolu gir.")
                remote_day=remote_root.rstrip("/")+"/"+datetime.now().strftime("%Y-%m-%d")
                try:sftp.mkdir(remote_day)
                except IOError:pass
            for x in items:
                self.after(0,lambda db=x["db"]:self.status.set("Yedekleniyor: "+db))
                stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
                safe="".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in x.get("alias",x["db"]))
                if x["type"]=="SQL Server":
                    exe=tool("sqlcmd")
                    if not exe:raise RuntimeError("sqlcmd bulunamadı; SQL Server istemci araçları gerekli.")
                    if self.shrink.get():
                        q=f"USE [{x['db'].replace(']', ']]')}]; DBCC SHRINKDATABASE (N'{x['db'].replace(chr(39),chr(39)*2)}');"
                        p=subprocess.run([exe,"-S",x["server"],"-E","-Q",q,"-b"],capture_output=True,text=True,timeout=3600,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                        if p.returncode:raise RuntimeError("Shrink başarısız: "+(p.stderr or p.stdout))
                    out=outdir/f"{safe}_{stamp}.bak"
                    q=f"BACKUP DATABASE [{x['db'].replace(']', ']]')}] TO DISK = N'{str(out).replace(chr(39),chr(39)*2)}' WITH INIT, COMPRESSION"
                    cmd=[exe,"-S",x["server"],"-Q",q,"-b"]
                else:
                    exe=tool("pg_dump")
                    if not exe:raise RuntimeError("pg_dump bulunamadı; PostgreSQL istemci araçları gerekli.")
                    out=outdir/f"{safe}_{stamp}.dump";cmd=[exe,"-h",x["server"],"-Fc","-f",str(out),x["db"]]
                    if x.get("user"):cmd[1:1]=["-U",x["user"]]
                p=subprocess.run(cmd,capture_output=True,text=True,timeout=3600,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                if p.returncode:raise RuntimeError((p.stderr or p.stdout or "Yedek komutu başarısız").strip())
                if target=="Google Drive":
                    from googleapiclient.http import MediaFileUpload
                    service.files().create(body={"name":out.name,"parents":[remote_day]},media_body=MediaFileUpload(str(out),resumable=True),fields="id").execute()
                    self.after(0,lambda n=out.name:self.status.set("Google Drive'a yüklendi: "+n))
                elif target=="Dropbox":
                    import dropbox
                    with out.open("rb") as source:
                        service.files_upload(source.read(),remote_day+"/"+out.name,mode=dropbox.files.WriteMode.overwrite)
                    self.after(0,lambda n=out.name:self.status.set("Dropbox'a yüklendi: "+n))
                elif target=="S3 uyumlu depolama":
                    key="/".join(part.strip("/") for part in [self.drive_folder.get() or "DatabaseBackups",remote_day,out.name])
                    service.upload_file(str(out),self.s3_bucket.get().strip(),key)
                    self.after(0,lambda n=out.name:self.status.set("S3 depolamaya yüklendi: "+n))
                elif target=="QNAP / SFTP":
                    sftp.put(str(out),remote_day+"/"+out.name)
                    self.after(0,lambda n=out.name:self.status.set("QNAP'a yüklendi: "+n))
                else:
                    self.after(0,lambda n=out.name:self.status.set("Yerel yedek oluşturuldu: "+n))
            now=datetime.now().isoformat(timespec="seconds")
            (self._config_dir()/"last.json").write_text(json.dumps({"timestamp":now}),encoding="utf-8")
            self.after(0,lambda:self.last_run.set(now))
            self.after(0,lambda:self.status.set("Yedekleme tamamlandı."))
        except Exception as e:self.after(0,lambda err=str(e):messagebox.showerror("Yedekleme başarısız",err))
        finally:
            try:
                if sftp: sftp.close()
                if transport: transport.close()
            except Exception: pass
            self.running=False

    def _drive_folder(self,service,name,parent=None):
        safe=name.replace("'","\\'")
        q="mimeType='application/vnd.google-apps.folder' and name='"+safe+"' and trashed=false"
        if parent:q+=" and '"+parent+"' in parents"
        res=service.files().list(q=q,spaces="drive",fields="files(id,name)",pageSize=100).execute()
        if res.get("files"):return res["files"][0]["id"]
        body={"name":name,"mimeType":"application/vnd.google-apps.folder"}
        if parent:body["parents"]=[parent]
        return service.files().create(body=body,fields="id").execute()["id"]

if __name__=="__main__":
    App().mainloop()
