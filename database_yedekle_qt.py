import os,sys,json,shutil,subprocess,threading,webbrowser,urllib.request,urllib.error
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import Qt,Signal,QObject
from PySide6.QtGui import QColor,QPainter,QPen,QIcon,QPixmap
from PySide6.QtWidgets import *
APP="Database Yedekle"; BG="#0B1020"; PANEL="#111A2E"; PANEL2="#17233A"; LINE="#263650"; FG="#E8F0FF"; MUTED="#91A4C5"; CYAN="#22D3EE"; PURPLE="#8B5CF6"
SUPABASE="https://hkuoymftockxmynrcjwh.supabase.co"
def asset(name):
    for root in [Path(getattr(sys,"_MEIPASS",Path(__file__).parent)),Path(sys.executable).parent if getattr(sys,"frozen",False) else Path(__file__).parent]:
        p=root/name
        if p.exists(): return p
    return Path(name)
def cli(name):
    p=asset(name)
    return str(p) if p.exists() else shutil.which(name)
def db_icon(kind,size=40):
    pix=QPixmap(size,size); pix.fill(Qt.GlobalColor.transparent); p=QPainter(pix); p.setRenderHint(QPainter.RenderHint.Antialiasing)
    if kind=="SQL Server":
        p.setPen(QPen(QColor("#FFB4AE"),1.4));p.setBrush(QColor("#E7483D"));p.drawRoundedRect(5,8,size-10,size-16,5,5);p.drawEllipse(5,4,size-10,11);p.setBrush(Qt.BrushStyle.NoBrush);p.drawArc(5,size-15,size-10,11,0,180*16);p.drawArc(5,13,size-10,11,0,180*16)
    elif kind=="PostgreSQL":
        p.setPen(QPen(QColor("#B7DFFF"),1.7));p.setBrush(QColor("#336791"));p.drawEllipse(8,5,size-17,size-12);p.drawEllipse(3,13,13,12);p.drawEllipse(size-17,8,13,13);p.setBrush(Qt.BrushStyle.NoBrush);p.drawArc(size-23,15,16,17,230*16,190*16);p.setPen(QPen(QColor("#EAF7FF"),1.4));p.drawPoint(size-12,13)
    else:
        p.setPen(QPen(QColor(CYAN),1.5));p.setBrush(QColor("#164E63"));p.drawRoundedRect(4,5,size-8,size-10,7,7);p.setBrush(QColor(PURPLE));p.drawEllipse(size-18,size-18,12,12)
    p.end();return pix
class Bus(QObject):
    scan=Signal(list); done=Signal(str,bool)
class AddDialog(QDialog):
    def __init__(self,kind,parent=None):
        super().__init__(parent);self.setWindowTitle("Veritabanı bağlantısı ekle");self.setMinimumWidth(420);f=QFormLayout(self)
        self.kind=QComboBox();self.kind.addItems(["SQL Server","PostgreSQL"]);self.kind.setCurrentText(kind)
        self.host=QLineEdit("localhost");self.db=QLineEdit();self.user=QLineEdit();self.password=QLineEdit();self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.auth=QComboBox();self.auth.addItems(["Windows kimlik doğrulaması","Kullanıcı adı / parola"])
        f.addRow("Motor",self.kind);f.addRow("Sunucu / Host",self.host);f.addRow("Veritabanı",self.db);f.addRow("Kullanıcı",self.user);f.addRow("Parola",self.password);f.addRow("SQL Server girişi",self.auth)
        b=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);b.accepted.connect(self.accept);b.rejected.connect(self.reject);f.addRow(b)
class DemoDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle("Demo erişimi ve müşteri kaydı");self.setMinimumWidth(430);l=QVBoxLayout(self)
        h=QLabel("Demo talebi oluştur");h.setObjectName("pageTitle");l.addWidget(h);n=QLabel("Bilgilerini gönder; demo süresi onaydan sonra başlar.");n.setObjectName("muted");l.addWidget(n)
        f=QFormLayout();self.company=QLineEdit();self.person=QLineEdit();self.phone=QLineEdit();self.email=QLineEdit()
        f.addRow("Firma adı",self.company);f.addRow("Yetkili kişi",self.person);f.addRow("Telefon",self.phone);f.addRow("E-posta",self.email);l.addLayout(f)
        b=QDialogButtonBox();b.addButton("Talep gönder",QDialogButtonBox.ButtonRole.AcceptRole);b.addButton("Vazgeç",QDialogButtonBox.ButtonRole.RejectRole);b.accepted.connect(self.accept);b.rejected.connect(self.reject);l.addWidget(b)
class App(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle(APP);self.resize(1020,700);self.setMinimumSize(900,600);self.setWindowIcon(QIcon(db_icon("app",64)))
        self.bus=Bus();self.bus.scan.connect(self.scanned);self.bus.done.connect(self.backup_result);self.items=[];self.found=[]
        self.cfgdir=Path(os.getenv("APPDATA",str(Path.home())))/"DatabaseYedekle";self.cfgdir.mkdir(parents=True,exist_ok=True);self.cfgfile=self.cfgdir/"config.json"
        try:self.cfg=json.loads(self.cfgfile.read_text(encoding="utf-8"))
        except Exception:self.cfg={}
        self.build();self.style();self.statusBar().showMessage("Hazır")
    def build(self):
        root=QWidget();root.setObjectName("root");outer=QVBoxLayout(root);outer.setContentsMargins(18,14,18,12);outer.setSpacing(14)
        head=QHBoxLayout();logo=QLabel();logo.setPixmap(db_icon("app",54));head.addWidget(logo)
        brand=QVBoxLayout();ey=QLabel("DATABASE YEDEKLE  /  BACKUP CONTROL");ey.setObjectName("eyebrow");title=QLabel("Güvenli yedekleme merkezi");title.setObjectName("title");sub=QLabel("SQL SERVER  •  POSTGRESQL  •  CLOUD STORAGE");sub.setObjectName("muted")
        brand.addWidget(ey);brand.addWidget(title);brand.addWidget(sub);head.addLayout(brand);head.addStretch()
        support=QPushButton("Destek");support.clicked.connect(lambda:webbrowser.open("mailto:oguzhanyilmaz8@gmail.com?subject=Database%20Yedekle%20Destek"));demo=QPushButton("Demo / Müşteri Kaydı");demo.clicked.connect(self.demo)
        head.addWidget(support);demo.setMinimumWidth(142);head.addWidget(demo);outer.addLayout(head)
        body=QHBoxLayout();body.setSpacing(14);side=QFrame();side.setObjectName("sidebar");side.setFixedWidth(188);sl=QVBoxLayout(side);sl.setContentsMargins(10,12,10,10);sl.setSpacing(6)
        cap=QLabel("ÇALIŞMA ALANI");cap.setObjectName("eyebrow");sl.addWidget(cap);self.nav=[];self.stack=QStackedWidget()
        for i,t in enumerate(["Veritabanları","Otomatik yedekleme","Yedekleme hedefi"]):
            b=QPushButton(["▦","◷","⇧"][i]+"    "+t);b.setObjectName("nav");b.setCheckable(True);b.clicked.connect(lambda checked=False,j=i:self.navigate(j));sl.addWidget(b);self.nav.append(b)
        sl.addStretch();sl.addWidget(QLabel("DURUM"));self.side_status=QLabel("Henüz yedek alınmadı");self.side_status.setObjectName("muted");self.side_status.setWordWrap(True);sl.addWidget(self.side_status)
        body.addWidget(side);body.addWidget(self.stack,1);outer.addLayout(body,1)
        foot=QHBoxLayout();self.status=QLabel("Hazır");self.status.setObjectName("muted");foot.addWidget(self.status);foot.addStretch()
        lic=QPushButton("Lisans");lic.clicked.connect(self.license);foot.addWidget(lic);self.go=QPushButton("Şimdi yedekle");self.go.setObjectName("primary");self.go.clicked.connect(self.backup);foot.addWidget(self.go);outer.addLayout(foot);self.setCentralWidget(root)
        self.dbpage=QWidget();self.db_ui();self.stack.addWidget(self.dbpage);self.schedpage=QWidget();self.schedule_ui();self.stack.addWidget(self.schedpage);self.storepage=QWidget();self.storage_ui();self.stack.addWidget(self.storepage);self.navigate(0)
        self.load_cfg()
    def card(self,title,desc=""):
        w=QFrame();w.setObjectName("card");l=QVBoxLayout(w);l.setContentsMargins(17,15,17,15);l.setSpacing(10);h=QLabel(title);h.setObjectName("section");l.addWidget(h)
        if desc:d=QLabel(desc);d.setObjectName("muted");d.setWordWrap(True);l.addWidget(d)
        return w,l
    def table(self,heads):
        t=QTableWidget(0,len(heads));t.setHorizontalHeaderLabels(heads);t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows);t.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection);t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);t.verticalHeader().hide();t.setShowGrid(False);t.setAlternatingRowColors(True);t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);return t
    def db_ui(self):
        o=QVBoxLayout(self.dbpage);o.setContentsMargins(0,0,0,0);o.setSpacing(12)
        title_row=QVBoxLayout();h=QLabel("Veritabanı bağlantıları");h.setObjectName("pageTitle");title_row.addWidget(h);d=QLabel("Yedeklenecek kaynakları seç veya sunucularda otomatik arama yap.");d.setObjectName("muted");title_row.addWidget(d);o.addLayout(title_row)
        top=QHBoxLayout();top.setSpacing(8);self.kind=QComboBox();self.kind.addItems(["SQL Server","PostgreSQL"]);self.kind.setMinimumWidth(125);self.kind.currentTextChanged.connect(self.kind_changed);self.kind_icon=QLabel();self.kind_icon.setFixedSize(34,34);top.addWidget(self.kind_icon);top.addWidget(self.kind)
        for text,fn in [("Tara",self.scan_db),("＋ Bağlantı ekle",self.add_db),("Kaldır",self.remove_db)]:
            b=QPushButton(text);b.clicked.connect(fn)
            if text=="Tara": self.scan_button=b
            if text.startswith("＋"): b.setObjectName("primary")
            top.addWidget(b)
        top.addStretch();o.addLayout(top);split=QSplitter(Qt.Orientation.Vertical);split.setChildrenCollapsible(False)
        c,l=self.card("Yedekleme listesi","Satıra çift tıklayarak yedeklemeye dahil etme durumunu değiştir.");self.tbl=self.table(["Dahil","Motor","Sunucu / Host","Veritabanı","Yedek adı"]);self.tbl.cellDoubleClicked.connect(self.toggle);l.addWidget(self.tbl);split.addWidget(c)
        c,l=self.card("Arama sonuçları","Bulunan veritabanlarını seçip yedekleme listesine ekle.");self.results=self.table(["Motor","Sunucu","Bulunan veritabanı"]);l.addWidget(self.results)
        row=QHBoxLayout();self.host_filter=QLineEdit();self.host_filter.setPlaceholderText("Sunucu adı/IP; boşsa localhost");row.addWidget(self.host_filter,1);b=QPushButton("Seçilenleri ekle");b.setObjectName("primary");b.clicked.connect(self.add_found);row.addWidget(b);l.addLayout(row);split.addWidget(c);split.setSizes([270,230]);o.addWidget(split,1);self.kind_changed(self.kind.currentText())
    def schedule_ui(self):
        o=QVBoxLayout(self.schedpage);o.setContentsMargins(0,0,0,0);h=QLabel("Otomatik yedekleme");h.setObjectName("pageTitle");o.addWidget(h)
        c,l=self.card("Yedekleme planı","Seçtiğin veritabanları uygulama açıkken belirlenen aralıkta yedeklenir.");self.auto=QCheckBox("Otomatik yedeklemeyi etkinleştir");l.addWidget(self.auto)
        row=QHBoxLayout();row.addWidget(QLabel("Yedekleme sıklığı"));self.interval=QComboBox();self.interval.addItems(["Saatlik","Günlük","Haftalık"]);row.addWidget(self.interval);row.addStretch();l.addLayout(row)
        self.shrink=QCheckBox("SQL Server yedeğinden önce veritabanını küçült (ileri seviye / riskli)");l.addWidget(self.shrink)
        note=QLabel("Öneri: SQL Server için sıkıştırılmış yedek kullan. Shrink işlemi performansı etkileyebilir.");note.setObjectName("muted");note.setWordWrap(True);l.addWidget(note)
        b=QPushButton("Planı kaydet");b.setObjectName("primary");b.clicked.connect(self.save_cfg);l.addWidget(b,0,Qt.AlignmentFlag.AlignLeft);o.addWidget(c);o.addStretch()
    def storage_ui(self):
        o=QVBoxLayout(self.storepage);o.setContentsMargins(0,0,0,0);h=QLabel("Yedekleme hedefi");h.setObjectName("pageTitle");o.addWidget(h)
        c,l=self.card("Depolama sağlayıcısı","Yedekler seçilen hedefe doğrudan gönderilir; aracı sunucu kullanılmaz.")
        row=QHBoxLayout();row.addWidget(QLabel("Hedef"));self.target=QComboBox();self.target.addItems(["Yerel klasör","Google Drive","Dropbox","S3 uyumlu depolama","QNAP / SFTP"]);self.target.currentTextChanged.connect(self.target_changed);row.addWidget(self.target);row.addStretch();l.addLayout(row)
        self.pages=QStackedWidget();self.pages.setMinimumHeight(250);l.addWidget(self.pages,1)
        w=QWidget();g=QGridLayout(w);self.local=QLineEdit(str(Path.home()/"DatabaseBackups"));b=QPushButton("Klasör seç");b.clicked.connect(self.browse);g.addWidget(QLabel("Yerel yedek klasörü"),0,0);g.addWidget(self.local,1,0);g.addWidget(b,1,1);self.pages.addWidget(w)
        self.pages.addWidget(self.notice("Google Drive","Google OAuth Desktop istemci bilgisi ve izinler yapılandırılmış olmalıdır."))
        self.pages.addWidget(self.notice("Dropbox","Dropbox OAuth uygulama anahtarıyla bağlantı kurulmalıdır."))
        w=QWidget();g=QGridLayout(w);self.endpoint=QLineEdit();self.endpoint.setPlaceholderText("Endpoint URL (AWS S3 için boş bırakılabilir)");self.bucket=QLineEdit();self.region=QLineEdit("us-east-1");self.access=QLineEdit();self.secret=QLineEdit();self.secret.setEchoMode(QLineEdit.EchoMode.Password);self.remote_folder=QLineEdit("DatabaseBackups")
        g.addWidget(QLabel("Endpoint"),0,0);g.addWidget(QLabel("Bucket"),0,1);g.addWidget(self.endpoint,1,0);g.addWidget(self.bucket,1,1);g.addWidget(QLabel("Region"),2,0);g.addWidget(QLabel("Access key"),2,1);g.addWidget(self.region,3,0);g.addWidget(self.access,3,1);g.addWidget(QLabel("Secret key"),4,0);g.addWidget(self.secret,5,0,1,2);g.addWidget(QLabel("Bulut klasörü"),6,0);g.addWidget(self.remote_folder,7,0,1,2);self.pages.addWidget(w)
        w=QWidget();g=QGridLayout(w);self.shost=QLineEdit();self.sport=QLineEdit("22");self.suser=QLineEdit();self.spass=QLineEdit();self.spass.setEchoMode(QLineEdit.EchoMode.Password);self.spath=QLineEdit("/share/Backups")
        for pos,lab,widget in [(0,"Sunucu / IP",self.shost),(1,"Port",self.sport),(2,"Kullanıcı",self.suser),(3,"Parola",self.spass),(4,"Uzak klasör",self.spath)]:
            g.addWidget(QLabel(lab),pos//3*2,pos%3);g.addWidget(widget,pos//3*2+1,pos%3)
        self.pages.addWidget(w)
        row=QHBoxLayout();save=QPushButton("Ayarları kaydet");save.setObjectName("primary");save.clicked.connect(self.save_cfg);test=QPushButton("Bağlantıyı test et");test.clicked.connect(self.test_target);row.addWidget(save);row.addWidget(test);row.addStretch();l.addLayout(row);o.addWidget(c,1);self.target_changed(self.target.currentText())
    def notice(self,title,desc):
        w=QWidget();l=QVBoxLayout(w);h=QLabel(title);h.setObjectName("section");d=QLabel(desc);d.setObjectName("muted");d.setWordWrap(True);l.addWidget(h);l.addWidget(d);l.addStretch();return w
    def style(self):
        self.setStyleSheet("""
        *{font-family:'Segoe UI';font-size:10pt} QMainWindow,QWidget#root{background:#080D19;color:#EDF3FF}
        QFrame#sidebar{background:#0E1628;border:1px solid #1D2A42;border-radius:18px} QFrame#card{background:#101A2D;border:1px solid #263752;border-radius:16px}
        QLabel{color:#E8F0FF;background:transparent} QLabel#title{font-size:23pt;font-weight:750} QLabel#pageTitle{font-size:20pt;font-weight:750;padding:2px 0 4px 0} QLabel#section{font-size:12pt;font-weight:700}
        QLabel#eyebrow{color:#22D3EE;font-size:8pt;font-weight:700;letter-spacing:1px} QLabel#muted{color:#91A4C5;font-size:9pt}
        QPushButton{color:#E8F0FF;background:#19263D;border:1px solid #2A3B58;border-radius:9px;padding:9px 11px;font-weight:650} QPushButton:hover{background:#263954;border-color:#456184} QPushButton:pressed{background:#101A2D}
        QPushButton#primary{background:#6D45E8;color:white;border:1px solid #8B73FF;border-radius:10px;padding:11px 17px} QPushButton#primary:hover{background:#805FF0}
        QPushButton#nav{text-align:left;background:transparent;border:0;padding:12px 10px;color:#A6B7D4} QPushButton#nav:hover{background:#17233A} QPushButton#nav:checked{background:#1A2C43;color:#22D3EE;border-left:3px solid #22D3EE}
        QLineEdit,QComboBox{background:#0B1425;color:#EDF3FF;border:1px solid #2B3D5A;border-radius:8px;padding:8px 10px;selection-background-color:#5B21B6;min-height:18px}
        QLineEdit:focus,QComboBox:focus{border:1px solid #22D3EE} QComboBox QAbstractItemView{background:#111A2E;color:#E8F0FF;selection-background-color:#3730A3}
        QCheckBox{spacing:9px;color:#D9E5FA;padding:5px 0} QCheckBox::indicator{width:17px;height:17px} QCheckBox::indicator:unchecked{background:#0D172A;border:1px solid #4A5D7B;border-radius:4px} QCheckBox::indicator:checked{background:#7C3AED;border:1px solid #A78BFA;border-radius:4px}
        QTableWidget{background:#0B1425;alternate-background-color:#101C30;color:#E2EBFC;border:1px solid #263752;border-radius:11px;gridline-color:transparent;selection-background-color:#293D62;selection-color:white;outline:0}
        QTableWidget::item{padding:11px 9px;border-bottom:1px solid #1A2940} QHeaderView::section{background:#17253D;color:#C9D8F0;border:0;border-bottom:1px solid #2C405F;padding:13px 10px;font-weight:700}
        QScrollBar:vertical{background:#0D172A;width:10px;margin:4px 2px;border-radius:5px} QScrollBar::handle:vertical{background:#344765;min-height:24px;border-radius:5px} QScrollBar::handle:vertical:hover{background:#52698F} QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}
        QScrollBar:horizontal{background:#0D172A;height:10px;margin:2px 4px;border-radius:5px} QScrollBar::handle:horizontal{background:#344765;min-width:24px;border-radius:5px} QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal{width:0}
        QSplitter::handle{background:#263650;height:5px} QStatusBar{background:#0F172A;color:#91A4C5;border-top:1px solid #263650} QDialog{background:#111A2E}
        """)
    def navigate(self,i):
        self.stack.setCurrentIndex(i)
        for j,b in enumerate(self.nav):b.setChecked(i==j)
    def kind_changed(self,t):self.kind_icon.setPixmap(db_icon(t,38))
    def target_changed(self,t):self.pages.setCurrentIndex({"Yerel klasör":0,"Google Drive":1,"Dropbox":2,"S3 uyumlu depolama":3,"QNAP / SFTP":4}.get(t,0))
    def refresh(self):
        self.tbl.setRowCount(len(self.items))
        for r,x in enumerate(self.items):
            vals=["✓" if x.get("use",True) else "—",x["type"],x["server"],x["db"],x.get("alias",x["db"])]
            for c,v in enumerate(vals):self.tbl.setItem(r,c,QTableWidgetItem(v))
        self.results.setRowCount(len(self.found))
        for r,x in enumerate(self.found):
            for c,k in enumerate(["type","server","db"]):self.results.setItem(r,c,QTableWidgetItem(x[k]))
    def add_db(self):
        d=AddDialog(self.kind.currentText(),self)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        if not d.db.text().strip():QMessageBox.warning(self,"Eksik bilgi","Veritabanı adı gerekli.");return
        self.items.append({"use":True,"type":d.kind.currentText(),"server":d.host.text().strip() or "localhost","db":d.db.text().strip(),"alias":d.db.text().strip(),"user":d.user.text().strip(),"password":d.password.text(),"auth":d.auth.currentText()});self.refresh()
    def remove_db(self):
        for r in sorted({i.row() for i in self.tbl.selectedIndexes()},reverse=True):self.items.pop(r)
        self.refresh()
    def toggle(self,r,c):
        if r<len(self.items):self.items[r]["use"]=not self.items[r].get("use",True);self.refresh()
    def scan_db(self):
        typ=self.kind.currentText();exe=cli("sqlcmd.exe" if typ=="SQL Server" else "psql.exe")
        if not exe:QMessageBox.warning(self,"Araç bulunamadı",f"{'sqlcmd.exe' if typ=='SQL Server' else 'psql.exe'} bulunamadı.");return
        host=self.host_filter.text().strip() or "localhost";self.scan_button.setEnabled(False);self.status.setText("Veritabanları aranıyor…")
        threading.Thread(target=self.scan_worker,args=(typ,exe,host.split(",")),daemon=True).start()
    def scan_worker(self,typ,exe,hosts):
        out=[]
        for host in hosts:
            try:
                cmd=[exe,"-S",host,"-E","-h","-1","-W","-Q","SET NOCOUNT ON; SELECT name FROM sys.databases WHERE database_id > 4","-b"] if typ=="SQL Server" else [exe,"-h",host,"-U",os.getenv("PGUSER","postgres"),"-d","postgres","-Atc","SELECT datname FROM pg_database WHERE datistemplate=false"]
                p=subprocess.run(cmd,capture_output=True,text=True,timeout=12,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                if p.returncode==0:
                    for db in p.stdout.splitlines():
                        if db.strip():out.append({"type":typ,"server":host.strip(),"db":db.strip(),"use":True,"alias":db.strip(),"user":""})
            except Exception:pass
        self.bus.scan.emit(out)
    def scanned(self,rows):
        self.found=rows;self.refresh();self.scan_button.setEnabled(True);self.status.setText(f"Arama tamamlandı · {len(rows)} veritabanı bulundu")
    def add_found(self):
        for r in sorted({i.row() for i in self.results.selectedIndexes()}):
            x=self.found[r]
            if not any(y["type"]==x["type"] and y["server"]==x["server"] and y["db"]==x["db"] for y in self.items):self.items.append(dict(x))
        self.refresh()
    def browse(self):
        p=QFileDialog.getExistingDirectory(self,"Yedek klasörü seç",self.local.text())
        if p:self.local.setText(p)
    def load_cfg(self):
        self.local.setText(self.cfg.get("local_path",str(Path.home()/"DatabaseBackups")));self.target.setCurrentText(self.cfg.get("target","Yerel klasör"));self.interval.setCurrentText(self.cfg.get("interval","Günlük"));self.auto.setChecked(self.cfg.get("auto",False));self.shrink.setChecked(self.cfg.get("shrink",False));self.endpoint.setText(self.cfg.get("endpoint",""));self.bucket.setText(self.cfg.get("bucket",""));self.region.setText(self.cfg.get("region","us-east-1"));self.access.setText(self.cfg.get("access",""));self.remote_folder.setText(self.cfg.get("remote_folder","DatabaseBackups"));self.shost.setText(self.cfg.get("shost",""));self.sport.setText(self.cfg.get("sport","22"));self.suser.setText(self.cfg.get("suser",""));self.spath.setText(self.cfg.get("spath","/share/Backups"))
    def save_cfg(self):
        self.cfg.update({"local_path":self.local.text(),"target":self.target.currentText(),"interval":self.interval.currentText(),"auto":self.auto.isChecked(),"shrink":self.shrink.isChecked(),"endpoint":self.endpoint.text(),"bucket":self.bucket.text(),"region":self.region.text(),"access":self.access.text(),"remote_folder":self.remote_folder.text(),"shost":self.shost.text(),"sport":self.sport.text(),"suser":self.suser.text(),"spath":self.spath.text()})
        self.cfgfile.write_text(json.dumps(self.cfg,ensure_ascii=False,indent=2),encoding="utf-8");self.status.setText("Ayarlar kaydedildi")
    def test_target(self):
        try:
            if self.target.currentText()=="Yerel klasör":Path(self.local.text()).mkdir(parents=True,exist_ok=True)
            elif self.target.currentText()=="S3 uyumlu depolama":
                import boto3;boto3.client("s3",endpoint_url=self.endpoint.text().strip() or None,region_name=self.region.text() or "us-east-1",aws_access_key_id=self.access.text(),aws_secret_access_key=self.secret.text()).head_bucket(Bucket=self.bucket.text())
            elif self.target.currentText()=="QNAP / SFTP":
                import paramiko;t=paramiko.Transport((self.shost.text(),int(self.sport.text() or 22)));t.connect(username=self.suser.text(),password=self.spass.text());t.close()
            else:QMessageBox.information(self,"OAuth gerekli","Bu hedef için OAuth kimlik bilgileri bu derlemede doğrulanmadı.");return
            QMessageBox.information(self,"Bağlantı başarılı","Hedef erişimi doğrulandı.")
        except Exception as e:QMessageBox.critical(self,"Bağlantı başarısız",str(e))
    def backup(self):
        chosen=[dict(x) for x in self.items if x.get("use",True)]
        if not chosen:QMessageBox.warning(self,"Seçim gerekli","Önce yedeklenecek veritabanı ekle.");return
        self.save_cfg();self.go.setEnabled(False);self.status.setText("Yedekleme sürüyor…")
        # Capture UI values on the main thread before worker starts.
        opts={"target":self.target.currentText(),"local":self.local.text(),"endpoint":self.endpoint.text(),"bucket":self.bucket.text(),"region":self.region.text(),"access":self.access.text(),"secret":self.secret.text(),"folder":self.remote_folder.text(),"shost":self.shost.text(),"sport":self.sport.text(),"suser":self.suser.text(),"spass":self.spass.text(),"spath":self.spath.text()}
        threading.Thread(target=self.backup_worker,args=(chosen,opts),daemon=True).start()
    def backup_worker(self,items,o):
        try:
            folder=Path(o["local"]);folder.mkdir(parents=True,exist_ok=True)
            for x in items:
                name="".join(c if c.isalnum() or c in "-_." else "_" for c in x["db"]);stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
                if x["type"]=="SQL Server":
                    exe=cli("sqlcmd.exe");out=folder/f"{name}_{stamp}.bak"
                    if not exe:raise RuntimeError("sqlcmd.exe bulunamadı.")
                    db=x["db"].replace("]","]]");path=str(out).replace("'","''");query=f"BACKUP DATABASE [{db}] TO DISK=N'{path}' WITH COPY_ONLY, COMPRESSION, INIT"
                    cmd=[exe,"-S",x["server"],"-E","-Q",query,"-b"]
                    p=subprocess.run(cmd,capture_output=True,text=True,timeout=3600,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                else:
                    exe=cli("pg_dump.exe");out=folder/f"{name}_{stamp}.dump"
                    if not exe:raise RuntimeError("pg_dump.exe bulunamadı.")
                    env=os.environ.copy()
                    if x.get("password"):env["PGPASSWORD"]=x["password"]
                    cmd=[exe,"-h",x["server"],"-U",x.get("user") or os.getenv("PGUSER","postgres"),"-d",x["db"],"-F","c","-f",str(out)]
                    p=subprocess.run(cmd,capture_output=True,text=True,timeout=3600,env=env,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                if p.returncode:raise RuntimeError((p.stderr or p.stdout or "Yedekleme başarısız")[-1200:])
                if o["target"]=="S3 uyumlu depolama":
                    import boto3;c=boto3.client("s3",endpoint_url=o["endpoint"] or None,region_name=o["region"] or "us-east-1",aws_access_key_id=o["access"],aws_secret_access_key=o["secret"])
                    c.upload_file(str(out),o["bucket"],"/".join([o["folder"] or "DatabaseBackups",datetime.now().strftime("%Y-%m-%d"),out.name]))
                elif o["target"]=="QNAP / SFTP":
                    import paramiko;t=paramiko.Transport((o["shost"],int(o["sport"] or 22)));t.connect(username=o["suser"],password=o["spass"]);s=paramiko.SFTPClient.from_transport(t)
                    try:
                        remote=o["spath"].rstrip("/")+"/"+datetime.now().strftime("%Y-%m-%d")
                        try:s.mkdir(remote)
                        except IOError:pass
                        s.put(str(out),remote+"/"+out.name)
                    finally:s.close();t.close()
                elif o["target"] in ("Google Drive","Dropbox"):raise RuntimeError(f"{o['target']} OAuth integration needs to be ported into the Qt UI; choose local, S3 or SFTP for this build.")
            self.bus.done.emit(f"{len(items)} veritabanı yedeklendi.",True)
        except Exception as e:self.bus.done.emit(str(e),False)
    def backup_result(self,msg,ok):
        self.go.setEnabled(True);self.status.setText(msg);self.side_status.setText(msg)
        (QMessageBox.information if ok else QMessageBox.critical)(self,"Yedekleme sonucu",msg)
    def demo(self):
        d=DemoDialog(self)
        if d.exec()!=QDialog.DialogCode.Accepted:return
        k=asset("supabase_anon_key.txt")
        if not k.exists():QMessageBox.warning(self,"Demo servisi yapılandırılmamış","GitHub Actions secret SUPABASE_ANON_KEY eksik.");return
        key=k.read_text(encoding="utf-8").strip();payload=json.dumps({"company":d.company.text().strip(),"name":d.person.text().strip(),"phone":d.phone.text().strip(),"email":d.email.text().strip()}).encode()
        req=urllib.request.Request(SUPABASE+"/functions/v1/demo-request",data=payload,headers={"Content-Type":"application/json","apikey":key,"Authorization":"Bearer "+key},method="POST")
        try:
            with urllib.request.urlopen(req,timeout=20):QMessageBox.information(self,"Talep gönderildi","Demo talebin gönderildi.")
        except urllib.error.HTTPError as e:QMessageBox.critical(self,"Talep gönderilemedi",f"HTTP {e.code}\n{e.read().decode('utf-8','replace')[:700]}")
        except Exception as e:QMessageBox.critical(self,"Talep gönderilemedi",str(e))
    def license(self):
        try:
            from license_manager import activate,check_cached_license
            from PySide6.QtWidgets import QInputDialog
            try:
                p=check_cached_license()
                if QMessageBox.question(self,"Lisans",f"Aktif lisans: {p.get('expires_at') or 'Süresiz'}\nYeniden doğrulansın mı?")!=QMessageBox.StandardButton.Yes:return
            except Exception as e:
                if QMessageBox.question(self,"Lisans",str(e)+"\n\nLisans anahtarı girmek ister misin?")!=QMessageBox.StandardButton.Yes:return
            key,ok=QInputDialog.getText(self,"Lisans","Lisans anahtarı:")
            if ok and key:QMessageBox.information(self,"Lisans",str(activate(key).get("expires_at") or "Süresiz"))
        except Exception as e:QMessageBox.critical(self,"Lisans",str(e))
    def closeEvent(self,event):
        try:self.save_cfg()
        except Exception:pass
        super().closeEvent(event)
def main():
    app=QApplication(sys.argv);app.setApplicationName(APP);app.setStyle("Fusion");w=App();w.show();sys.exit(app.exec())
if __name__=="__main__":main()
