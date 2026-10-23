# Database Yedekle (Windows)

Türkçe arayüzlü Windows masaüstü uygulaması. Arayüz PySide6/Qt ile yeniden tasarlanmıştır; tutarlı koyu tema, modern tablolar ve SQL Server/PostgreSQL için ayrı vektör simgeleri kullanır. SQL Server ve PostgreSQL yedeklerini yerel diske, Google Drive, Dropbox, S3 uyumlu depolamaya (AWS S3/Cloudflare R2/MinIO) veya QNAP/SFTP hedefine gönderebilir.

## EXE indirme

1. GitHub deposunda **Actions** sekmesine gir.
2. **Build Windows EXE** iş akışını aç.
3. En son çalıştırmanın tamamlanmasını bekle (yeşil tik).
4. Sayfanın altındaki **Artifacts** bölümünden **Database-Yedekle-Windows** dosyasını indir.
5. ZIP içindeki `Database Yedekle.exe` dosyasını çıkar.

Her `main` dalı güncellemesinde otomatik derleme başlar. Derleme dosyası 30 gün saklanır.

## Gereksinimler

- `sqlcmd`, `pg_dump` ve `psql` Windows paketine eklenir. SQL Server için hedef sistemde uyumlu Microsoft ODBC Driver gerekir.
- S3 uyumlu hedefler için endpoint (isteğe bağlı), bucket, region ve erişim anahtarları uygulamada yapılandırılır.\n- Google Drive için uygulamanın geliştiricisi GitHub Actions secret `GOOGLE_OAUTH_CLIENT_JSON` içine Google Cloud Console'dan alınan OAuth **Desktop app** istemci JSON'unu eklemelidir. EXE bu yapılandırmayla derlenir; kullanıcı uygulamada **Google hesabını bağla** akışını tamamlar. Kullanıcının ayrıca rclone kurması gerekmez.
- Hedef bilgisayarda Python gerekmez; EXE derleme işlemi GitHub Actions Windows makinesinde yapılır.

## Önemli notlar

- Bu ilk sürüm/prototiptir; üretim veritabanlarında kullanmadan önce test veritabanıyla deneyin ve geri yükleme testi yapın.
- SQL Server `BACKUP DATABASE` komutu dosyayı SQL Server hizmetinin gördüğü/yazabildiği konuma yazar. Uzak SQL Server kullanılıyorsa yerel bilgisayarın klasör yolu sunucuda aynı anlama gelmez; uygun paylaşımlı UNC yolu veya farklı bir yedekleme yaklaşımı gerekir.
- Otomatik tarama yalnızca sınırlı yerel bağlantı noktalarını/örnekleri dener. Bulunmayan sunucular için **Manuel Ekle** kullanın.
- Google hesabı şifresini uygulamaya girmeyin; giriş Google'ın OAuth penceresinde yapılır. Uygulama yalnızca `drive.file` kapsamını ister. Google OAuth ekranı uygulamayı engelliyorsa Google Cloud Console'da OAuth Audience/Test users ayarlarını kontrol edin. Test modunda yalnızca eklenen test kullanıcıları bağlanabilir; herkese açık dağıtım için Google'ın doğrulama süreci gerekebilir.
- Depo herkese açık olduğu için buraya parola, erişim anahtarı veya gerçek veritabanı bilgisi koymayın.
