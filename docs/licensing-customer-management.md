# Database Yedekle — Lisanslama ve Müşteri Yönetimi

## Onaylanan ürün kuralları

- Deneme süresi: 7 gün; sayaç sunucuda, demo talebi yönetici tarafından onaylandığında başlar.
- Müşteri ilk ekranda müşteri numarası girmez. Kayıt gönderilince sunucu benzersiz müşteri numarası üretir ve ekranda gösterir.
- Müşteri numarası değişmez; yönetim panelinde de görünür ve müşteri aramalarında birincil anahtardır.
- Arama alanları: müşteri numarası, firma adı, yetkili kişi ve telefon.
- Aynı firma adının birden fazla kayıtta bulunmasına izin verilir; müşteri numarası her kaydı ayırt eder.
- Demo hakkı firma başına bir kez olacak şekilde yönetilir. Aynı ad tek başına kesin eşleşme kabul edilmez; telefon/e-posta ve yönetici incelemesi gibi kontrollerle olası mükerrer talepler işaretlenir.
- Lisans başına tek cihaz bağlanır. Cihaz değişikliği yalnızca yönetici panelinden serbest bırakılarak yapılabilir.
- Uygulama ilk aktivasyonda internete bağlanır; 168 saatte bir lisans doğrulaması yapar. Çevrimdışı tolerans 168 saattir.
- Yönetici paneli müşteri, demo talepleri, lisanslar, cihazlar, satışlar ve tahsilatları birbirine bağlı şekilde yönetir.
- Demo talepleri müşteri listesinde otomatik oluşur; onay/reddet işlemi panelden yapılır.
- Satış alanları: satış tarihi, toplam tutar, alınan tutar, kalan bakiye, ödeme yöntemi, vade tarihi ve notlar. Tahsilatlar ayrı kayıtlarla izlenir; durum ödenmedi/kısmi/ödendi/vadesi geçti olarak hesaplanır.
- Lisans anahtarları yalnızca sunucuda üretilir ve doğrulanır. İmza için özel anahtar ve servis rolü anahtarı masaüstü uygulamasına konulmaz.

## Güvenlik ve işletim notları

1. Müşteri numarası kimlik doğrulama sırrı değildir; yalnızca kayıt referansıdır.
2. Müşteri ve lisans tabloları doğrudan herkese açık API üzerinden okunamaz. RLS etkin olmalı; yazma ve yönetici işlemleri yetkili sunucu fonksiyonlarından geçmelidir.
3. Windows saatinin geri alınması deneme süresini uzatmamalıdır; demo başlangıç/bitiş zamanları sunucuda saklanır.
4. Yedi günlük çevrimdışı tolerans sırasında sunucuda iptal edilen lisansın cihazda hemen kapanamayacağı kabul edilir.
5. Firma başına tek demo kontrolü, sadece otomatik müşteri numarasıyla sağlanamaz. Telefon/e-posta normalizasyonu, ek doğrulama ve yönetici onayı gerekir. İstenirse vergi numarası gibi daha güçlü bir işletme tanımlayıcısı ayrıca toplanabilir; bu alan henüz zorunlu olarak belirlenmemiştir.
6. Bu belge gereksinimleri tanımlar. Canlı lisanslama için ayrı bir Supabase projesi, sunucu fonksiyonları, yönetici kimlik doğrulaması, Windows istemcisi entegrasyonu ve uçtan uca test gerekir.
