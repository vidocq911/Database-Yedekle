# Google Drive OAuth kurulumu ve sorun giderme

Bu uygulama Google Drive'a yedek yüklemek için resmi Google Drive API Python istemcisini ve OAuth Desktop uygulama akışını kullanır. Databasement deposunda yerel Google Drive yedekleme kodu bulunmadığından, mevcut Python uygulamasındaki bu yerel entegrasyon korunur.

## Geliştirici kurulumu

1. Google Cloud Console'da proje oluştur veya mevcut projeyi seç.
2. Google Drive API'yi etkinleştir.
3. Google Auth Platform'da uygulama adı ve destek e-postasını ayarla.
4. Audience bölümünde uygulamayı kendi Google hesabınla test ediyorsan External/Testing seçip hesabını **Test users** listesine ekle.
5. Clients bölümünden **Desktop app** türünde OAuth istemcisi oluştur ve JSON dosyasını indir.
6. GitHub deposunun Actions secrets bölümünde `GOOGLE_OAUTH_CLIENT_JSON` secret'ını oluştur; JSON dosyasının tamamını secret değeri olarak koy.
7. `feature/licensing-customer-management` dalındaki Windows Actions iş akışı bu JSON'u derleme sırasında uygulama paketine ekler.

## Kullanıcı tarafı

1. EXE'yi aç ve **Yedekleme Hedefi** sekmesine geç.
2. Hedefi Google Drive seç.
3. **Google hesabını bağla** düğmesine bas ve Google'ın açtığı pencerede izin ver.
4. **Google bağlantısını kes / hesabı unut** düğmesi bu bilgisayardaki token dosyasını siler. Tam erişim iptali için Google Hesabı güvenlik ayarlarından uygulama erişimini de kaldır.

## Önemli: OAuth doğrulaması

Kod, Google'ın uygulama doğrulamasını atlatamaz. Uygulama Testing durumundaysa yalnızca Test users listesine eklenmiş hesaplarla çalışır. Genel müşterilere dağıtımda Google'ın OAuth doğrulama gereksinimleri ve uyarıları geçerlidir. Desktop OAuth istemci kimliği/secret'ı dağıtılan masaüstü uygulamasında gizli tutulamaz; güvenlik sınırı, istemci sırrını saklamaktan ziyade dar kapsamlı OAuth izinleri ve kullanıcı başına token saklamasıdır.

## Bu sürümde yapılan bağlantı düzeltmeleri

- Bağlantı testi artık `about.get` yerine `drive.file` izniyle uyumlu `files.list` çağrısını kullanır.
- Süresi dolmuş veya iptal edilmiş refresh token yenilenemezse eski token silinir ve yeniden OAuth girişi istenir.
- Bağlantı hatası; test kullanıcısı, istemci JSON'u veya Drive API kapsamı/proje ayarıyla ilgili olabilecek durumlar için yönlendirici açıklama verir.
- Token dosyası Windows kullanıcısının `%APPDATA%/DatabaseYedekle/google_token.json` konumunda tutulur; dosya paylaşılmamalıdır.
