import os, sys, json, shutil, subprocess, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from datetime import datetime, timedelta

APP = "Database Yedekle"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
BG = "#F3F6FA"
NAVY = "#183153"
BLUE = "#2563EB"
MUTED = "#607086"
GREEN = "#13805C"

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
        self.geometry("900x620")
        self.resizable(False, False)
        self.configure(bg=BG)
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

    def _style(self):
        s=ttk.Style(self)
        try:s.theme_use("clam")
        except tk.TclError:pass
        s.configure("TFrame",background=BG)
        s.configure("TLabel",background=BG,foreground=NAVY,font=("Segoe UI",10))
        s.configure("Muted.TLabel",foreground=MUTED,font=("Segoe UI",9))
        s.configure("Title.TLabel",font=("Segoe UI",16,"bold"),foreground=NAVY)
        s.configure("Section.TLabel",font=("Segoe UI",10,"bold"),foreground=NAVY)
        s.configure("TButton",font=("Segoe UI",9),padding=(7,4),background="#E6ECF4",foreground=NAVY)
        s.map("TButton",background=[("active","#D7E2F0")])
        s.configure("Primary.TButton",font=("Segoe UI",9,"bold"),padding=(9,5),background=BLUE,foreground="white")
        s.map("Primary.TButton",background=[("active","#1D4ED8")],foreground=[("active","white")])
        s.configure("Treeview",rowheight=22,font=("Segoe UI",9),background="white",fieldbackground="white")
        s.configure("Treeview.Heading",font=("Segoe UI",9,"bold"),background="#E8EEF6",foreground=NAVY,padding=7)
        s.configure("TNotebook",background=BG,borderwidth=0)
        s.configure("TNotebook.Tab",padding=(11,6),font=("Segoe UI",9,"bold"))
        s.map("TNotebook.Tab",background=[("selected","white")],foreground=[("selected",BLUE)])

    def _build(self):
        shell=ttk.Frame(self,padding=10); shell.pack(fill="both",expand=True)
        head=ttk.Frame(shell);head.pack(fill="x",pady=(0,7))
        ttk.Label(head,text="Database Yedekle",style="Title.TLabel").pack(anchor="w")
        ttk.Label(head,text="Veritabanı yedeklerini planla, sıkıştır ve Google Drive'a güvenle aktar.",style="Muted.TLabel").pack(anchor="w",pady=(3,0))
        self.tabs=ttk.Notebook(shell);self.tabs.pack(fill="both",expand=True)
        self.dbtab=ttk.Frame(self.tabs,padding=8);self.schedtab=ttk.Frame(self.tabs,padding=10);self.storagetab=ttk.Frame(self.tabs,padding=10)
        self.tabs.add(self.dbtab,text="  Veritabanları  ")
        self.tabs.add(self.schedtab,text="  Otomatik Yedekleme  ")
        self.tabs.add(self.storagetab,text="  Yedekleme Hedefi  ")
        self._build_db();self._build_schedule();self._build_storage()
        foot=ttk.Frame(shell);foot.pack(fill="x",pady=(7,0))
        ttk.Label(foot,textvariable=self.status,style="Muted.TLabel").pack(side="left",fill="x",expand=True)
        ttk.Button(foot,text="Google ile Bağlan",command=self.connect_google).pack(side="right",padx=(8,0))
        ttk.Button(foot,text="Şimdi Yedekle",style="Primary.TButton",command=self.start).pack(side="right")

    def _build_db(self):
        bar=ttk.Frame(self.dbtab);bar.pack(fill="x",pady=(0,10))
        ttk.Label(bar,text="Veritabanı türü").pack(side="left")
        ttk.Combobox(bar,textvariable=self.dbtype,values=["SQL Server","PostgreSQL"],state="readonly",width=16).pack(side="left",padx=8)
        ttk.Button(bar,text="Otomatik Ara",command=self.scan).pack(side="left",padx=4)
        ttk.Button(bar,text="Manuel Ekle",command=self.add_manual).pack(side="left",padx=4)
        ttk.Button(bar,text="Kaldır",command=self.remove).pack(side="left",padx=4)
        ttk.Label(self.dbtab,text="Yedekleme listesi",style="Section.TLabel").pack(anchor="w")
        ttk.Label(self.dbtab,text="Satıra çift tıklayarak dahil etme durumunu değiştir. Seçilen kayıtlar yedeklenir.",style="Muted.TLabel").pack(anchor="w",pady=(2,8))
        cols=("use","type","server","db","alias")
        self.tree=ttk.Treeview(self.dbtab,columns=cols,show="headings",selectmode="extended")
        for col,title,width in [("use","Dahil",55),("type","Tür",100),("server","Sunucu / Host",180),("db","Veritabanı",210),("alias","Yedek adı",190)]:
            self.tree.heading(col,text=title);self.tree.column(col,width=width,anchor="w")
        self.tree.pack(fill="both",expand=True)
        self.tree.bind("<Double-1>",self.toggle)
        actions=ttk.Frame(self.dbtab);actions.pack(fill="x",pady=(8,0))
        ttk.Button(actions,text="Tümünü Dahil Et",command=lambda:self.set_all(True)).pack(side="left")
        ttk.Button(actions,text="Hiçbirini Seçme",command=lambda:self.set_all(False)).pack(side="left",padx=6)
        ttk.Button(actions,text="Yedek Adını Düzenle",command=self.rename).pack(side="right")
        ttk.Label(self.dbtab,text="Arama sonuçları",style="Section.TLabel").pack(anchor="w",pady=(14,4))
        self.foundtree=ttk.Treeview(self.dbtab,columns=("pick","type","server","db"),show="headings",height=4,selectmode="extended")
        for col,title,width in [("pick","Ekle",50),("type","Tür",100),("server","Sunucu",180),("db","Bulunan veritabanı",250)]:
            self.foundtree.heading(col,text=title);self.foundtree.column(col,width=width,anchor="w")
        self.foundtree.pack(fill="x")
        fbtn=ttk.Frame(self.dbtab);fbtn.pack(fill="x",pady=(6,0))
        ttk.Button(fbtn,text="Bulunanları İşaretle",command=lambda:self.mark_found(True)).pack(side="left")
        ttk.Button(fbtn,text="İşaretlileri Listeye Ekle",style="Primary.TButton",command=self.add_found).pack(side="right")

    def _build_schedule(self):
        ttk.Label(self.schedtab,text="Yedekleme planı",style="Title.TLabel").pack(anchor="w")
        ttk.Label(self.schedtab,text="Seçtiğin veritabanları belirlenen aralıkta yedeklenir.",style="Muted.TLabel").pack(anchor="w",pady=(4,18))
        card=ttk.Frame(self.schedtab,padding=16);card.pack(fill="x")
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
        ttk.Combobox(targetrow,textvariable=self.target,values=["Yerel klasör","Google Drive","QNAP / SFTP"],state="readonly",width=20).pack(side="left",padx=8)
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
        ttk.Label(self.storagetab,text="Uzak klasör (örn. /share/Backups veya SFTP ana dizinine göre Backups)").pack(anchor="w",pady=(7,0))
        ttk.Entry(self.storagetab,textvariable=self.qnap_path).pack(fill="x",pady=(3,8))
        statusrow=ttk.Frame(self.storagetab);statusrow.pack(fill="x",pady=(2,8))
        ttk.Button(statusrow,text="Google hesabını bağla",command=self.connect_google).pack(side="left")
        ttk.Button(statusrow,text="Google bağlantısını kes / hesabı unut",command=self.disconnect_google).pack(side="left",padx=6)
        ttk.Button(statusrow,text="QNAP bağlantısını test et",command=self.test_sftp).pack(side="left",padx=6)
        ttk.Label(self.storagetab,text="Google belirteci bu Windows kullanıcısının AppData alanında tutulur. Ortak bilgisayarda bağlantıyı kes. QNAP parolası ayarlarda kaydedilir; hassas cihazlarda kullanımdan sonra temizle.",wraplength=760,style="Muted.TLabel").pack(anchor="w",pady=(4,0))

    def _config_dir(self):
        p=Path(os.getenv("APPDATA",str(Path.home())))/"DatabaseYedekle";p.mkdir(parents=True,exist_ok=True);return p

    def _load(self):
        try:
            d=json.loads((self._config_dir()/"settings.json").read_text(encoding="utf-8"))
            self.items=d.get("items",[]);self.local.set(d.get("local",self.local.get()));self.drive_folder.set(d.get("drive_folder","DatabaseBackups"))
            self.target.set(d.get("target","Google Drive"));self.qnap_host.set(d.get("qnap_host",""));self.qnap_port.set(d.get("qnap_port","22"));self.qnap_user.set(d.get("qnap_user",""));self.qnap_password.set("");self.qnap_path.set(d.get("qnap_path","/share/Backups"))
            self.auto.set(d.get("auto",False));self.interval.set(d.get("interval","Günlük"));self.shrink.set(d.get("shrink",False));self.refresh()
            try:self.last_run.set(json.loads((self._config_dir()/"last.json").read_text())["timestamp"])
            except Exception:pass
        except Exception:pass

    def save(self):
        try:
            d={"items":self.items,"local":self.local.get(),"drive_folder":self.drive_folder.get(),"auto":self.auto.get(),"interval":self.interval.get(),"shrink":self.shrink.get(),"target":self.target.get(),"qnap_host":self.qnap_host.get(),"qnap_port":self.qnap_port.get(),"qnap_user":self.qnap_user.get(),"qnap_path":self.qnap_path.get()}
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
        base=Path(sys.executable).parent if getattr(sys,"frozen",False) else Path(__file__).parent
        secrets=base/"client_secrets.json"
        if not secrets.exists():
            chosen=filedialog.askopenfilename(title="Google OAuth istemci JSON dosyasını seç",filetypes=[("JSON dosyaları","*.json"),("Tüm dosyalar","*.*")],parent=self)
            if not chosen: raise RuntimeError("Google bağlantısı için OAuth istemci JSON dosyası seçilmedi.")
            secrets=Path(chosen)
        creds=None
        if token.exists():
            try:creds=Credentials.from_authorized_user_file(str(token),SCOPES)
            except Exception:pass
        if creds and creds.expired and creds.refresh_token:creds.refresh(Request())
        if not creds or not creds.valid:
            flow=InstalledAppFlow.from_client_secrets_file(str(secrets),SCOPES)
            creds=flow.run_local_server(port=0)
            token.write_text(creds.to_json(),encoding="utf-8")
        return build("drive","v3",credentials=creds,cache_discovery=False)

    def connect_google(self):
        try:
            svc=self._config_credentials()
            email=svc.about().get(fields="user(emailAddress)").execute().get("user",{}).get("emailAddress","Google hesabı")
            messagebox.showinfo("Google Drive",f"Bağlandı: {email}")
            self.status.set("Google Drive bağlantısı hazır.")
        except Exception as e:messagebox.showerror("Google Drive bağlantısı",str(e))

    def disconnect_google(self):
        token=self._config_dir()/"google_token.json"
        try:
            if token.exists(): token.unlink()
            self.status.set("Google bağlantısı kaldırıldı; yerel belirteç silindi.")
            messagebox.showinfo("Google bağlantısı","Bu bilgisayardaki yerel Google belirteci silindi. Tam erişim iptali için Google Hesabı > Güvenlik > Üçüncü taraf bağlantıları bölümünden de uygulama erişimini kaldır.")
        except Exception as e: messagebox.showerror("Bağlantı kesilemedi",str(e))

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
            messagebox.showwarning("İstemci aracı bulunamadı",f"{client} bu bilgisayarda bulunamadı. Otomatik arama için ilgili komut satırı aracı gerekir. Kurulu SQL Server örnekleri ve istemci araçlarının algılanması sonraki iyileştirme adımıdır.")
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
