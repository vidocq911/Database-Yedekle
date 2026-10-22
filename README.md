# Database Yedekle (Windows)

Türkçe arayüzlü, SQL Server ve PostgreSQL veritabanlarını yerel diske yedeklemeyi ve rclone üzerinden Google Drive'a göndermeyi amaçlayan Windows masaüstü uygulaması.

## EXE indirme

1. GitHub deposunda **Actions** sekmesine gir.
2. **Build Windows EXE** iş akışını aç.
3. En son çalıştırmanın tamamlanmasını bekle (yeşil tik).
4. Sayfanın altındaki **Artifacts** bölümünden **Database-Yedekle-Windows** dosyasını indir.
5. ZIP içindeki `Database Yedekle.exe` dosyasını çıkar.

Her `main` dalı güncellemesinde otomatik derleme başlar. Derleme dosyası 30 gün saklanır.

## Gereksinimler

- SQL Server için Microsoft `sqlcmd`; PostgreSQL için `pg_dump` (otomatik tarama ayrıca `psql` kullanır).
- Google Drive aktarımı için `rclone` kurulu olmalı ve `rclone config` ile Google Drive remote'u oluşturulmalı. Varsayılan hedef `gdrive:DatabaseBackups`.
- Hedef bilgisayarda Python gerekmez; EXE derleme işlemi GitHub Actions Windows makinesinde yapılır.

## Önemli notlar

- Bu ilk sürüm/prototiptir; üretim veritabanlarında kullanmadan önce test veritabanıyla deneyin ve geri yükleme testi yapın.
- SQL Server `BACKUP DATABASE` komutu dosyayı SQL Server hizmetinin gördüğü/yazabildiği konuma yazar. Uzak SQL Server kullanılıyorsa yerel bilgisayarın klasör yolu sunucuda aynı anlama gelmez; uygun paylaşımlı UNC yolu veya farklı bir yedekleme yaklaşımı gerekir.
- Otomatik tarama yalnızca sınırlı yerel bağlantı noktalarını/örnekleri dener. Bulunmayan sunucular için **Manuel Ekle** kullanın.
- Veritabanı şifrelerini uygulama ayarlarına kaydetmez. Google hesabı şifresini uygulamaya girmeyin; rclone'un resmi OAuth akışını kullanın.
- Depo herkese açık olduğu için buraya parola, erişim anahtarı veya gerçek veritabanı bilgisi koymayın.
