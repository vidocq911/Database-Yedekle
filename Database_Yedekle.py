import os, sys, shutil, subprocess, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from datetime import datetime

APP = "Database Yedekle"

def bundled_tool(name):
    candidates=[]
    if getattr(sys,"frozen",False):
        candidates.append(Path(getattr(sys,"_MEIPASS","."))/name)
        candidates.append(Path(sys.executable).parent/name)
    found=shutil.which(name)
    if found: candidates.append(Path(found))
    for p in candidates:
        if p.exists(): return str(p)
    return None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP); self.geometry("1120x720"); self.minsize(900,600)
        self.items=[]; self.discovered=[]
        self.backup_dir=Path.home()/"DatabaseBackups"
        self.remote=tk.StringVar(value="gdrive:DatabaseBackups")
        self.dbtype=tk.StringVar(value="SQL Server")
        self.status=tk.StringVar(value="Hazır — veritabanlarını arayabilir veya manuel ekleyebilirsin.")
        self._style(); self._ui()

    def _style(self):
        s=ttk.Style(self)
        try:s.theme_use("clam")
        except tk.TclError:pass
        s.configure("Title.TLabel",font=("Segoe UI",19,"bold"),foreground="#17365D")
        s.configure("Sub.TLabel",font=("Segoe UI",10),foreground="#526579")
        s.configure("Primary.TButton",font=("Segoe UI",10,"bold"),padding=(12,8))
        s.configure("Treeview",rowheight=29,font=("Segoe UI",10))
        s.configure("Treeview.Heading",font=("Segoe UI",10,"bold"))
        s.configure("TLabelframe.Label",font=("Segoe UI",10,"bold"))

    def _ui(self):
        root=ttk.Frame(self,padding=16); root.pack(fill="both",expand=True)
        header=ttk.Frame(root);header.pack(fill="x",pady=(0,12))
        ttk.Label(header,text="Database Yedekle",style="Title.TLabel").pack(anchor="w")
        ttk.Label(header,text="Veritabanlarını bul, seçimlerini düzenle ve yedeklerini güvenle sakla.",style="Sub.TLabel").pack(anchor="w",pady=(3,0))
        toolbar=ttk.Frame(root);toolbar.pack(fill="x",pady=(0,10))
        ttk.Label(toolbar,text="Veritabanı türü").pack(side="left")
        ttk.Combobox(toolbar,textvariable=self.dbtype,values=["SQL Server","PostgreSQL"],state="readonly",width=16).pack(side="left",padx=(8,12))
        ttk.Button(toolbar,text="🔎  Otomatik Ara",style="Primary.TButton",command=self.scan).pack(side="left",padx=(0,8))
        ttk.Button(toolbar,text="＋  Manuel Ekle",command=self.add).pack(side="left",padx=(0,8))
        ttk.Button(toolbar,text="−  Seçileni Kaldır",command=self.remove).pack(side="left")
        paned=ttk.Panedwindow(root,orient="horizontal");paned.pack(fill="both",expand=True)
        left=ttk.Labelframe(paned,text="Yedekleme listem",padding=8);right=ttk.Labelframe(paned,text="Otomatik arama sonuçları",padding=8)
        paned.add(left,weight=3);paned.add(right,weight=2);self.paned=paned;self.right=right
        ttk.Label(left,text="Listede çift tıklayarak yedekleme seçimini açıp kapatabilirsin.",style="Sub.TLabel").pack(anchor="w",pady=(0,7))
        cols=("use","type","server","db","alias")
        self.tree=ttk.Treeview(left,columns=cols,show="headings",selectmode="extended")
        for c,t,w in [("use","Yedekle",70),("type","Tür",100),("server","Sunucu / Host",150),("db","Veritabanı",150),("alias","Yedek dosyası adı",150)]:
            self.tree.heading(c,text=t);self.tree.column(c,width=w,anchor="w")
        self.tree.pack(fill="both",expand=True);self.tree.bind("<Double-1>",self.toggle)
        actions=ttk.Frame(left);actions.pack(fill="x",pady=(8,0))
        ttk.Button(actions,text="Tümünü Seç",command=lambda:self.set_all(True)).pack(side="left")
        ttk.Button(actions,text="Seçimi Temizle",command=lambda:self.set_all(False)).pack(side="left",padx=6)
        ttk.Button(actions,text="Adı Düzenle",command=self.rename).pack(side="right")
        ttk.Label(right,text="Bulunan veritabanlarını burada görebilir, işaretleyip listeye ekleyebilirsin.",style="Sub.TLabel",wraplength=310).pack(anchor="w",pady=(0,8))
        self.found_tree=ttk.Treeview(right,columns=("pick","type","server","db"),show="headings",selectmode="extended",height=12)
        for c,t,w in [("pick","Ekle",48),("type","Tür",85),("server","Sunucu",110),("db","Veritabanı",135)]:
            self.found_tree.heading(c,text=t);self.found_tree.column(c,width=w,anchor="w")
        self.found_tree.pack(fill="both",expand=True);self.found_tree.bind("<Double-1>",self.toggle_found)
        found_actions=ttk.Frame(right);found_actions.pack(fill="x",pady=(8,0))
        ttk.Button(found_actions,text="Bulunanların Tümünü İşaretle",command=lambda:self.mark_found(True)).pack(fill="x",pady=2)
        ttk.Button(found_actions,text="İşaretlileri Listeye Ekle →",style="Primary.TButton",command=self.add_found).pack(fill="x",pady=2)
        opts=ttk.Labelframe(root,text="Yedekleme ve Google Drive",padding=10);opts.pack(fill="x",pady=(10,0))
        ttk.Label(opts,text="Yerel klasör").grid(row=0,column=0,sticky="w",padx=(0,8),pady=3)
        self.local=tk.StringVar(value=str(self.backup_dir))
        ttk.Entry(opts,textvariable=self.local).grid(row=0,column=1,sticky="ew",pady=3)
        ttk.Button(opts,text="Gözat…",command=self.browse).grid(row=0,column=2,padx=(8,0))
        ttk.Label(opts,text="Drive hedefi").grid(row=1,column=0,sticky="w",padx=(0,8),pady=3)
        ttk.Entry(opts,textvariable=self.remote).grid(row=1,column=1,sticky="ew",pady=3)
        ttk.Label(opts,text="Örn. gdrive:DatabaseBackups  •  rclone remote önceden yapılandırılmış olmalı",style="Sub.TLabel").grid(row=1,column=2,sticky="w",padx=(8,0))
        opts.columnconfigure(1,weight=1)
        bottom=ttk.Frame(root);bottom.pack(fill="x",pady=(10,0))
        ttk.Label(bottom,textvariable=self.status).pack(side="left",fill="x",expand=True)
        ttk.Button(bottom,text="Yedeklemeyi Başlat  →",style="Primary.TButton",command=self.start).pack(side="right")

    def say(self,s):
        self.status.set(s); self.update_idletasks()

    def add(self):
        typ=self.dbtype.get()
        host=simpledialog.askstring("Manuel veritabanı","Sunucu/host (örn. localhost veya .\\SQLEXPRESS):",parent=self)
        if not host:return
        db=simpledialog.askstring("Manuel veritabanı","Veritabanı adı:",parent=self)
        if not db:return
        alias=simpledialog.askstring("Yedek dosyası adı","Yedek dosyası adı:",initialvalue=db,parent=self) or db
        user=simpledialog.askstring("Kullanıcı (isteğe bağlı)","Veritabanı kullanıcı adı. Boşsa Windows/varsayılan kimlik doğrulama kullanılır:",parent=self) or ""
        self._add_item({"use":True,"type":typ,"server":host,"db":db,"alias":alias,"user":user})
        self.say(f"{db} listeye eklendi.")

    def _add_item(self,x):
        if not any(a["type"]==x["type"] and a["server"].lower()==x["server"].lower() and a["db"].lower()==x["db"].lower() for a in self.items):
            self.items.append(x);self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,x in enumerate(self.items):
            self.tree.insert("","end",iid=str(i),values=("✓" if x["use"] else "—",x["type"],x["server"],x["db"],x["alias"]))

    def toggle(self,event):
        iid=self.tree.identify_row(event.y)
        if iid:
            self.items[int(iid)]["use"]=not self.items[int(iid)]["use"];self.refresh()

    def set_all(self,val):
        for x in self.items:x["use"]=val
        self.refresh()

    def remove(self):
        ids=sorted((int(i) for i in self.tree.selection()),reverse=True)
        if not ids:
            messagebox.showinfo("Seçim gerekli","Kaldırmak istediğin satırı seç.");return
        for i in ids:del self.items[i]
        self.refresh();self.say(f"{len(ids)} kayıt listeden kaldırıldı.")

    def rename(self):
        ids=self.tree.selection()
        if len(ids)!=1:
            messagebox.showinfo("Tek kayıt seç","Adını değiştirmek için listeden bir kayıt seç.");return
        x=self.items[int(ids[0])]
        new=simpledialog.askstring("Yedek dosyası adı","Yeni dosya adı:",initialvalue=x["alias"],parent=self)
        if new and new.strip():x["alias"]=new.strip();self.refresh()

    def scan(self):
        self.discovered=[];self.found_tree.delete(*self.found_tree.get_children())
        typ=self.dbtype.get();tool="sqlcmd" if typ=="SQL Server" else "psql"
        toolpath=bundled_tool(tool)
        if not toolpath:
            messagebox.showwarning("İstemci aracı bulunamadı",
                f"{tool} bu bilgisayarda bulunamadı.\n\nOtomatik arama için {tool} gerekli. SQL Server kurulu olsa bile yönetim aracı ayrı kurulmuş olabilir.\n\nSunucu ve veritabanı adını biliyorsan 'Manuel Ekle' seçeneğini kullanabilirsin.")
            self.say(f"Otomatik arama yapılamadı: {tool} kurulu değil.");return
        hosts=["localhost",".","(local)","localhost\\SQLEXPRESS",".\\SQLEXPRESS"]
        if typ=="PostgreSQL":hosts=["localhost","127.0.0.1"]
        self.say("Yerel sunucular taranıyor…")
        threading.Thread(target=self._scan_worker,args=(typ,toolpath,hosts),daemon=True).start()

    def _scan_worker(self,typ,tool,hosts):
        found=[]
        for host in hosts:
            try:
                if typ=="SQL Server":
                    cmd=[tool,"-S",host,"-E","-h","-1","-W","-Q","SET NOCOUNT ON; SELECT name FROM sys.databases WHERE database_id > 4","-b"]
                    p=subprocess.run(cmd,capture_output=True,text=True,timeout=8,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    names=[z.strip() for z in p.stdout.splitlines() if z.strip() and "rows affected" not in z.lower()]
                else:
                    cmd=[tool,"-h",host,"-U",os.getenv("PGUSER","postgres"),"-d","postgres","-Atc","SELECT datname FROM pg_database WHERE datistemplate=false"]
                    p=subprocess.run(cmd,capture_output=True,text=True,timeout=8,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                    names=[z.strip() for z in p.stdout.splitlines() if z.strip()]
                if p.returncode==0:
                    for db in names:
                        if not any(x["server"].lower()==host.lower() and x["db"].lower()==db.lower() and x["type"]==typ for x in found):
                            found.append({"use":True,"type":typ,"server":host,"db":db,"alias":db,"user":""})
            except Exception:pass
        self.after(0,lambda:self._show_found(found,typ))

    def _show_found(self,found,typ):
        self.discovered=found;self.found_tree.delete(*self.found_tree.get_children())
        for i,x in enumerate(found):
            self.found_tree.insert("","end",iid=str(i),values=("✓",x["type"],x["server"],x["db"]))
        self.say(f"Arama tamamlandı: {len(found)} veritabanı bulundu.")
        if not found:
            self.say("Veritabanı bulunamadı. Servis/izinleri kontrol et veya Manuel Ekle kullan.")
    def toggle_found(self,event):
        iid=self.found_tree.identify_row(event.y)
        if iid:
            x=self.discovered[int(iid)];x["use"]=not x["use"]
            self.found_tree.set(iid,"pick","✓" if x["use"] else "—")
    def mark_found(self,val):
        for x in self.discovered:x["use"]=val
        for i,x in enumerate(self.discovered):self.found_tree.set(str(i),"pick","✓" if val else "—")
    def add_found(self):
        selected=set(self.found_tree.selection())
        chosen=[x for i,x in enumerate(self.discovered) if x.get("use") and (not selected or str(i) in selected)]
        if not chosen:
            messagebox.showinfo("Seçim gerekli","Eklemek istediğin bulunan veritabanlarını işaretle.");return
        for x in chosen:self._add_item(x.copy())
        self.say(f"{len(chosen)} bulunan veritabanı yedekleme listesine eklendi.")

    def browse(self):
        d=filedialog.askdirectory(initialdir=self.local.get())
        if d:self.local.set(d)

    def start(self):
        chosen=[x.copy() for x in self.items if x["use"]]
        if not chosen:
            messagebox.showinfo("Yedekleme listesi boş","Önce yedeklenecek veritabanlarını seç veya ekle.");return
        rclone=bundled_tool("rclone.exe") or bundled_tool("rclone")
        if not rclone:
            messagebox.showerror("rclone bulunamadı","Google Drive aktarımı için rclone kurulu olmalı ve Google Drive remote'u yapılandırılmalı. Yerel yedekleme bu araçtan bağımsız olarak da yapılabilir; önce yerel yedekleme seçeneğini eklememiz gerekiyor.")
            return
        threading.Thread(target=self.backup,args=(chosen,rclone),daemon=True).start()

    def backup(self,items,rclone):
        folder=Path(self.local.get())/datetime.now().strftime("%Y-%m-%d")
        folder.mkdir(parents=True,exist_ok=True)
        for x in items:
            stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
            safe="".join(c if c.isalnum() or c in "-_." else "_" for c in x["alias"])
            try:
                if x["type"]=="SQL Server":
                    out=folder/f"{safe}_{stamp}.bak"
                    query=f"BACKUP DATABASE [{x['db'].replace(']', ']]')}] TO DISK = N'{str(out).replace(chr(39), chr(39)*2)}' WITH INIT, COMPRESSION"
                    cmd=[bundled_tool("sqlcmd") or "sqlcmd","-S",x["server"],"-Q",query,"-b"]
                    if x["user"]:
                        pw=simpledialog.askstring("DB şifresi",f"{x['db']} kullanıcı şifresi:",show="*",parent=self)
                        if pw is None:continue
                        cmd=["sqlcmd","-S",x["server"],"-U",x["user"],"-P",pw,"-Q",query,"-b"]
                else:
                    out=folder/f"{safe}_{stamp}.dump"
                    cmd=[bundled_tool("pg_dump") or "pg_dump","-h",x["server"],"-Fc","-f",str(out),x["db"]]
                    if x["user"]:cmd[1:1]=["-U",x["user"]]
                self.after(0,lambda db=x["db"]:self.say(f"Yedekleniyor: {db}"))
                p=subprocess.run(cmd,capture_output=True,text=True,timeout=3600,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                if p.returncode:raise RuntimeError((p.stderr or p.stdout or "Komut başarısız").strip())
                remote=self.remote.get().strip().rstrip("/")
                if not remote:raise RuntimeError("Google Drive hedefi boş.")
                dest=f"{remote}/{datetime.now().strftime('%Y-%m-%d')}"
                p=subprocess.run([rclone,"copyto",str(out),f"{dest}/{out.name}"],capture_output=True,text=True,timeout=3600,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                if p.returncode:raise RuntimeError((p.stderr or p.stdout or "Drive yükleme başarısız").strip())
                self.after(0,lambda n=out.name,d=dest:self.say(f"Tamamlandı: {n} → {d}"))
            except Exception as e:self.after(0,lambda db=x["db"],err=str(e):self.say(f"HATA ({db}): {err}"))
        self.after(0,lambda:self.say("İşlem tamamlandı."))

if __name__=="__main__":
    App().mainloop()
