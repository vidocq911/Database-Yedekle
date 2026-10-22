import os, shutil, subprocess, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from pathlib import Path
from datetime import datetime

APP = "Database Yedekle"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP); self.geometry("820x590"); self.minsize(700,500)
        self.items=[]
        self.backup_dir=Path.home()/"DatabaseBackups"
        self.remote=tk.StringVar(value="gdrive:DatabaseBackups")
        self.dbtype=tk.StringVar(value="SQL Server")
        self._ui()

    def _ui(self):
        root=ttk.Frame(self,padding=12); root.pack(fill="both",expand=True)
        ttk.Label(root,text="Database Yedekle",font=("Segoe UI",18,"bold")).pack(anchor="w")
        ttk.Label(root,text="SQL Server / PostgreSQL yedeklerini yerel diske ve Google Drive'a aktarır.").pack(anchor="w",pady=(0,10))
        bar=ttk.Frame(root); bar.pack(fill="x")
        ttk.Label(bar,text="Veritabanı türü:").pack(side="left")
        ttk.Combobox(bar,textvariable=self.dbtype,values=["SQL Server","PostgreSQL"],state="readonly",width=18).pack(side="left",padx=6)
        ttk.Button(bar,text="Otomatik Ara",command=self.scan).pack(side="left",padx=4)
        ttk.Button(bar,text="Manuel Ekle",command=self.add).pack(side="left",padx=4)
        cols=("use","type","server","database","alias")
        self.tree=ttk.Treeview(root,columns=cols,show="headings",selectmode="browse",height=12)
        for c,t,w in [("use","Yedekle","70"),("type","Tür","105"),("server","Sunucu / Host","170"),("database","Veritabanı","190"),("alias","Yedek adı","190")]:
            self.tree.heading(c,text=t); self.tree.column(c,width=int(w),anchor="w")
        self.tree.pack(fill="both",expand=True,pady=8); self.tree.bind("<Double-1>",self.toggle)
        ttk.Label(root,text="İpucu: satıra çift tıklayarak yedeklemeyi açıp kapatabilirsin.").pack(anchor="w")
        f=ttk.Frame(root); f.pack(fill="x",pady=4)
        ttk.Label(f,text="Yerel klasör:").grid(row=0,column=0,sticky="w")
        self.local=tk.StringVar(value=str(self.backup_dir))
        ttk.Entry(f,textvariable=self.local).grid(row=0,column=1,sticky="ew",padx=6)
        ttk.Button(f,text="Gözat",command=self.browse).grid(row=0,column=2)
        ttk.Label(f,text="Google Drive hedefi (rclone remote:path):").grid(row=1,column=0,sticky="w",pady=4)
        ttk.Entry(f,textvariable=self.remote).grid(row=1,column=1,columnspan=2,sticky="ew",padx=6)
        f.columnconfigure(1,weight=1)
        self.log=tk.Text(root,height=6); self.log.pack(fill="x",pady=(5,0))
        ttk.Button(root,text="Seçilenleri Yedekle ve Drive'a Yükle",command=self.start).pack(anchor="e",pady=8)

    def say(self,s):
        self.log.insert("end",s+"\n"); self.log.see("end"); self.update_idletasks()

    def add(self):
        typ=self.dbtype.get()
        host=simpledialog.askstring("Sunucu","Sunucu/host (ör. localhost veya HOST\\INSTANCE):",parent=self)
        if not host:return
        db=simpledialog.askstring("Veritabanı","Veritabanı adı:",parent=self)
        if not db:return
        alias=simpledialog.askstring("Yedek adı","Dosya adı için takma ad:",initialvalue=db,parent=self) or db
        user=simpledialog.askstring("Kullanıcı (isteğe bağlı)","DB kullanıcı adı; boş bırakılırsa Windows/varsayılan kimlik doğrulama:",parent=self) or ""
        self.items.append({"use":True,"type":typ,"server":host,"db":db,"alias":alias,"user":user})
        self.refresh()

    def scan(self):
        typ=self.dbtype.get()
        if typ=="SQL Server":
            hosts=["localhost","localhost\\SQLEXPRESS"]
            tool="sqlcmd"
        else:
            hosts=["localhost"]
            tool="psql"
        if not shutil.which(tool):
            messagebox.showwarning("Eksik araç",f"{tool} bulunamadı. İlgili veritabanı istemci araçlarını kur veya Manuel Ekle kullan.")
            return
        found=0
        for host in hosts:
            try:
                if typ=="SQL Server":
                    p=subprocess.run([tool,"-S",host,"-E","-h","-1","-W","-Q","SET NOCOUNT ON; SELECT name FROM sys.databases WHERE database_id > 4"],capture_output=True,text=True,timeout=8)
                    names=[x.strip() for x in p.stdout.splitlines() if x.strip() and "rows affected" not in x.lower()]
                else:
                    p=subprocess.run([tool,"-h",host,"-U",os.getenv("PGUSER","postgres"),"-d","postgres","-Atc","SELECT datname FROM pg_database WHERE datistemplate=false"],capture_output=True,text=True,timeout=8)
                    names=[x.strip() for x in p.stdout.splitlines() if x.strip()]
                for db in names:
                    if not any(x["type"]==typ and x["server"]==host and x["db"]==db for x in self.items):
                        self.items.append({"use":True,"type":typ,"server":host,"db":db,"alias":db,"user":""}); found+=1
            except Exception as e:self.say(f"{host}: {e}")
        self.refresh(); self.say(f"Otomatik tarama tamamlandı. Eklenen kayıt: {found}")
        if not found:self.say("Veritabanı bulunamadı; bağlantı/izinleri kontrol et veya Manuel Ekle kullan.")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for i,x in enumerate(self.items):
            self.tree.insert("","end",iid=str(i),values=("☑" if x["use"] else "☐",x["type"],x["server"],x["db"],x["alias"]))

    def toggle(self,event):
        iid=self.tree.identify_row(event.y)
        if iid:
            self.items[int(iid)]["use"]=not self.items[int(iid)]["use"]; self.refresh()

    def browse(self):
        d=filedialog.askdirectory(initialdir=self.local.get())
        if d:self.local.set(d)

    def start(self):
        chosen=[x.copy() for x in self.items if x["use"]]
        if not chosen:messagebox.showinfo("Seçim yok","Önce yedeklenecek veritabanlarını seç.");return
        if not shutil.which("rclone"):
            messagebox.showerror("rclone bulunamadı","Google Drive aktarımı için rclone kurulu ve yapılandırılmış olmalı. Remote adını hedef alanına yaz (ör. gdrive:DatabaseBackups).")
            return
        threading.Thread(target=self.backup,args=(chosen,),daemon=True).start()

    def backup(self,items):
        folder=Path(self.local.get())/datetime.now().strftime("%Y-%m-%d")
        folder.mkdir(parents=True,exist_ok=True)
        for x in items:
            stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
            safe="".join(c if c.isalnum() or c in "-_." else "_" for c in x["alias"])
            try:
                if x["type"]=="SQL Server":
                    out=folder/f"{safe}_{stamp}.bak"
                    query=f"BACKUP DATABASE [{x['db'].replace(']', ']]')}] TO DISK = N'{str(out).replace(chr(39), chr(39)*2)}' WITH INIT, COMPRESSION"
                    cmd=["sqlcmd","-S",x["server"],"-Q",query,"-b"]
                    if x["user"]:
                        pw=simpledialog.askstring("DB şifresi",f"{x['db']} kullanıcı şifresi:",show="*",parent=self)
                        if pw is None:continue
                        cmd=["sqlcmd","-S",x["server"],"-U",x["user"],"-P",pw,"-Q",query,"-b"]
                else:
                    out=folder/f"{safe}_{stamp}.dump"
                    cmd=["pg_dump","-h",x["server"],"-Fc","-f",str(out),x["db"]]
                    if x["user"]:cmd[1:1]=["-U",x["user"]]
                self.say(f"Yedekleniyor: {x['db']}")
                p=subprocess.run(cmd,capture_output=True,text=True,timeout=3600)
                if p.returncode:raise RuntimeError((p.stderr or p.stdout or "Komut başarısız").strip())
                remote=self.remote.get().strip().rstrip("/")
                dest=f"{remote}/{datetime.now().strftime('%Y-%m-%d')}"
                p=subprocess.run(["rclone","copyto",str(out),f"{dest}/{out.name}"],capture_output=True,text=True,timeout=3600)
                if p.returncode:raise RuntimeError((p.stderr or p.stdout or "Drive yükleme başarısız").strip())
                self.say(f"OK: {out.name} -> {dest}")
            except Exception as e:self.say(f"HATA ({x['db']}): {e}")
        self.say("İşlem tamamlandı.")

if __name__=="__main__":
    App().mainloop()
