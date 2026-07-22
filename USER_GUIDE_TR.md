# Parametric Process Studio — Kapsamlı Kullanım, Analiz ve Karar Rehberi

Bu rehber Parametric Process'in yalnızca hangi düğmesine basılacağını değil; bir planlama sorusunun nasıl modellenmesi, alternatiflerin nasıl üretilmesi, sonuçların nasıl okunması ve bulguların nasıl savunulabilir kararlara dönüştürülmesi gerektiğini açıklar.

## 1. Araç ne için kullanılmalıdır?

Parametric Process şu işlerde kullanılır:

- Gerçek QGIS parsel veya ada geometrilerinden parametrik kütle alternatifleri üretmek.
- BCR/KAKS, FAR/TAKS ve yükseklik gibi imar sınırlarını üretim sürecine katmak.
- GFA, karbon, rüzgâr, güneş, açık alan, yağmur suyu ve finans gibi çelişen hedefleri birlikte değerlendirmek.
- Pareto-optimal çözüm ailelerini bulmak ve tek bir puana erken kilitlenmeden alternatifleri karşılaştırmak.
- Tekrarlanabilir workflow'ları JSON olarak saklamak ve gözden geçirilen sonuçları QGIS'e geri yazmak.

Araç; ruhsat, statik, yangın, ulaşım, jeoteknik, ayrıntılı enerji veya CFD onayı değildir. Üretilen değerler erken tasarım ve karşılaştırmalı karar desteğidir; ilgili uzman analizleriyle doğrulanmalıdır.

## 2. Önce karar brifi yazın

Modeli açmadan önce aşağıdaki beş alanı doldurun:

1. **Karar birimi:** Tek parsel, ada, mahalle parçası veya senaryo.
2. **Sert kısıtlar:** Aşılamayacak BCR, FAR, yükseklik, minimum açık alan veya başka mevzuat koşulları.
3. **Amaçlar:** En çok 3–6 anlamlı performans hedefi ve her hedefin `min`/`max` yönü.
4. **Kabul eşikleri:** Bir adayın kısa listeye girmesi için gereken minimum/maksimum değerler.
5. **Karar sahibi:** Teknik ekip, idare, yatırımcı, jüri veya paydaş grubu ve beklenen çıktı biçimi.

Örnek karar cümlesi:

> Yasal BCR/FAR/yükseklik sınırlarını aşmadan, kabul edilebilir karbon ve açık alan düzeyinde yeterli GFA ve mikroiklim performansı sağlayan 3–5 uygulanabilir alternatifi belirle.

## 3. QGIS verisini hazırlama

### 3.1 Geometri

- Kaynak katman poligon olmalıdır.
- `Fix Geometries` ile kendini kesen veya geçersiz poligonları düzeltin.
- Boş, sıfır alanlı ve yinelenen geometrileri kaldırın.
- Çok parçalı geometrilerin analiz birimine uygun olup olmadığını kontrol edin.
- Kaynak katmanın bir yedeğini veya GeoPackage kopyasını alın.

### 3.2 Koordinat sistemi

Alan ve mesafe hesapları için bölgeye uygun, metre tabanlı projeksiyonlu CRS kullanın. Coğrafi koordinatlar derece cinsindedir ve metrik kararları bozabilir. Eklentinin görüntüleme için Web Mercator'a dönüştürmesi, kaynak analiz CRS'sini düzeltmenin yerine geçmez.

### 3.3 Kapsam

- İlk koşuda küçük ve temsil edici bir seçim kullanın.
- `scope=selected`, kalibrasyon ve güvenli pilot için uygundur.
- `scope=all`, parametreler doğrulandıktan sonra kontrollü toplu çalışma içindir.
- İlçe fiziği yorumlanacaksa gölge ve rüzgâr bağlamını temsil edecek komşu kütleleri dahil edin.

### 3.4 Kimlik ve geri yazım

QGIS senkronizasyonu feature ID ile eşleşir. Koşu sırasında kaynak objeleri silmeyin, ID düzenini değiştirmeyin veya başka bir katmanı aynı sanarak senkronize etmeyin.

## 4. Üç çalışma alanı

### Parametric Cockpit

Tek parseli hızlı düzenlemek, tipoloji/setback/kat/yükseklik etkisini 3B görmek ve anlık metrik okumak için kullanılır. Bu yüzey keşif ve görsel doğrulama içindir.

### Evolutionary Studio

Çok sayıda alternatif üretmek, Pareto ön cephesini incelemek, PCP filtresi uygulamak, yakınsamayı izlemek, kümeleri karşılaştırmak ve adayları 3B önizlemek için kullanılır.

### Workflow Modeler

Kurumsal veya proje bazlı karar zincirini tekrarlanabilir bir DAG olarak tanımlamak için kullanılır. Girdi, kural, üretim, optimizasyon, analiz, sıralama, seçim ve QGIS çıktısı tek süreçte birleştirilir.

Önerilen öğrenme sırası:

1. Cockpit ile geometriyi ve metrik davranışını doğrulayın.
2. Evolutionary Studio ile objective ve parametre hassasiyetini öğrenin.
3. Kararlı süreci Workflow Modeler'da standartlaştırın.

## 5. Workflow Modeler kullanımı

### 5.1 Tek Tık Zincir

`Tek Tık Zincir` varsayılan olarak açıktır. Paletten bir bileşene tek kez basıldığında:

1. Yeni node tuvale eklenir.
2. Node anında seçilir ve Inspector açılır.
3. Uygun bir seçili/terminal node varsa yeni node ona otomatik bağlanır.

Kutunun herhangi bir yerine ilk basışta seçim gerçekleşir. İkinci tık gerekmez.

### 5.2 Manuel kullanım

- Serbest konum için bileşeni paletten tuvale sürükleyin.
- Özel bağlantı için kaynak çıkış portuna, sonra hedef giriş portuna basın.
- Bir kaynak birden fazla kola çıkabilir.
- Bir hedef node yalnız bir doğrudan giriş alır.
- Döngü oluşturulamaz.
- `Delete` seçili node veya bağlantıyı siler.
- `Escape` yarım kalmış bağlantıyı iptal eder.

### 5.3 Geçerli temel zincir

```text
QGIS Site Layer
  → Zoning Envelope
  → Evolutionary Solver
  → TOPSIS Ranker
  → Select Best
  → QGIS Output
```

### 5.4 Şablonlar

- **Balanced Urban Optimization:** Genel çok amaçlı planlama ve kısa liste üretimi.
- **PPUD Rule Chain:** Ada bölme, alt parsel ve kademeli kentsel doku üretimi.
- **District Performance:** Kütle alternatifleri üzerinde gölge, rüzgâr, konfor ve yağmur suyu bağlaşımı.
- **Blank:** Özel süreç; ilk node mutlaka QGIS Site Layer olmalıdır.

## 6. Node referansı

| Node | Neden kullanılır? | Kritik parametre/çıktı |
|---|---|---|
| QGIS Site Layer | Canlı poligon kapsamını okur | `scope=all/selected`, feature count, site area |
| Zoning Envelope | Yasal veya senaryo bazlı yapılaşma zarfını uygular | `max_bcr`, `max_far`, `max_height` |
| Shape Grammar | Ada geometrisinden alt parsel alternatifleri üretir | strategy, target frontage, minimum lot area |
| PPUD Fabric | Parsel → yapı → kademeli doku aşamalarını çalıştırır | typology, steps, climate feedback, seed |
| Evolutionary Solver | Çok amaçlı aday popülasyonu üretir | algorithm, population, generations, objectives, seed |
| District Physics | Komşuluk ölçeğinde birleşik çevresel performansı ölçer | shadow, canyon wind, comfort, stormwater |
| TOPSIS Ranker | Pareto adaylarını ideal/anti-ideal uzaklığa göre sıralar | göreli TOPSIS score/rank |
| Select Best | Belirli yönteme göre 1–10 aday seçer | topsis, PlanX score, lowest carbon, max GFA |
| QGIS Output | Seçilen çözümler için attribute update paketi üretir | `apply_mode=selected/all` |

### Shape Grammar stratejileri

- **frontage:** Yol cephesi ve hedef parsel genişliği önemliyse.
- **grid:** Düzenli ve ölçülebilir parsel ağı isteniyorsa.
- **perimeter:** Çevre blok ve iç avlu mantığı aranıyorsa.
- **organic:** Düzensiz mevcut dokuya uyum gerekiyorsa.
- **radial:** Meydan, odak veya merkez etrafında dağılım isteniyorsa.
- **hybrid:** Birden fazla morfolojik ilke birlikte deneniyorsa.

## 7. Optimizasyon stratejisi

### 7.1 Algoritma seçimi

| Algoritma | Uygun kullanım |
|---|---|
| NSGA-II | 2–4 hedefte dengeli ve anlaşılır varsayılan başlangıç |
| SPEA-2 | Çözüm yoğunluğu ve arşiv ayrıştırması önemliyse |
| NSGA-III | Dört veya daha fazla hedef bulunan many-objective çalışma |
| MOEA/D | Hedef uzayını alt problemlere ayrıştırarak kapsam arama |

### 7.2 Koşu bütçesi

- **Keşif:** population 16–24, generations 5–10.
- **Kalibrasyon:** population 30–50, generations 15–30.
- **Nihai analiz:** Birden fazla seed ile kararlılık kontrolü; gerekli ölçekte daha yüksek bütçe.

Yüksek değer her zaman daha iyi değildir. Önce küçük koşuyla veri, objective yönü ve kısıt hatalarını bulun.

### 7.3 Seed

Aynı seed ve aynı girdiler karşılaştırılabilir koşu üretir. Parametre kalibrasyonunda seed'i sabit tutun. Nihai kararda en az 2–3 farklı seed kullanarak aday sıralamasının dayanıklılığını ölçün.

### 7.4 Crossover ve mutation

- Crossover mevcut iyi özellikleri birleştirir.
- Mutation yeni çözüm bölgelerini keşfeder.
- Çözümler erken benzeşiyorsa mutation oranını küçük adımlarla artırın.
- Sonuçlar aşırı oynaksa population/generations artırıp mutation'ı azaltarak kıyaslayın.
- Her deneyde tek ana parametreyi değiştirin.

### 7.5 Objective yönleri

Genel olarak büyütülen hedefler: `planx_score`, `gfa`, `wind_ventilation`, `solar_radiation_kwh`, `pollution_dispersion`, `sky_view_factor`, `daylight_index`, `roi_percentage`, `pv_yield_mwh`, `open_space_ratio`.

Genel olarak küçültülen hedefler: `carbon_kg`, `runoff_m3`, `constraint_penalty`.

UTCI veya konfor skorlarında metriğin uygulamadaki tanımını kontrol edin. Ham sıcaklık değeri ile normalize edilmiş konfor skorunu karıştırmayın.

## 8. Sonuçları okuma

### 8.1 Uygunluk önce gelir

Önce `constraint_penalty`, BCR, FAR ve height değerlerini kontrol edin. Uygun olmayan bir aday yüksek GFA veya yüksek birleşik puan nedeniyle doğrudan seçilmemelidir.

### 8.2 Pareto ön cephesi

Pareto-optimal aday, başka bir hedefi kötüleştirmeden tek bir hedefte iyileştirilemeyen çözümdür. Pareto Rank 1 “mutlak en iyi” anlamına gelmez; takas açısından baskılanmayan aday demektir.

Scatter grafiğinde dirsek noktaları, küçük bir fedakârlık karşılığında büyük performans kazanımı sağlayan adayları gösterebilir.

### 8.3 Parallel Coordinates Plot

Her çizgi bir çözüm, her dikey eksen bir değişken veya metriktir. Brush ile kabul aralıklarını işaretleyin. Aynı anda bütün kritik aralıklardan geçen çizgiler kısa listenin çekirdeğidir.

### 8.4 Yakınsama ve standart sapma

- Ortalama performans iyileşip sonra dengeleniyorsa yakınsama işareti vardır.
- Standart sapma ilk nesillerde sıfıra yaklaşıyorsa çeşitlilik erken kaybolmuş olabilir.
- Ortalama ve maksimum hâlâ hızla değişiyorsa daha fazla generation gerekebilir.
- Tek koşunun yakınsaması, farklı seedlerde aynı kararın çıkacağı anlamına gelmez.

### 8.5 Radar

Radar grafik tek adayın normalize edilmiş profilini gösterir. Farklı metrik birimleri nedeniyle şekil karşılaştırması yapılır; alanın büyük olması tek başına mutlak kalite kanıtı değildir.

### 8.6 K-Means ve PCA

Kümeler benzer çözüm ailelerini ayırır. Yalnız en yüksek puanlı kümeden aday almak yerine farklı anlamlı kümelerden temsilci seçmek seçenek çeşitliliğini korur.

### 8.7 TOPSIS

TOPSIS puanı, adayın tanımlı ideal çözüme yakın ve anti-ideal çözüme uzak olmasını ölçen göreli bir sıralamadır.

- Puan yalnız aynı aday kümesi içinde anlamlıdır.
- Objective yönü veya aday kümesi değişirse puan yeniden hesaplanmalıdır.
- Küçük tercih/ağırlık değişiminde sıra ters dönüyorsa karar kırılgandır.
- TOPSIS, Pareto ve ham metrik kontrolünün yerine geçmez.

## 9. Karar protokolü

1. **Uygunluk kapısı:** İhlalli adayları ayırın.
2. **Pareto filtresi:** Baskın olmayan adayları belirleyin.
3. **PCP eşikleri:** Kurumsal kabul aralıklarını uygulayın.
4. **Çeşitlilik:** Farklı çözüm kümelerinden temsilci alın.
5. **Kısa liste:** Genellikle 3–5 aday tutun.
6. **Tercih senaryoları:** Yoğunluk, iklim, düşük karbon ve finans senaryolarını ayrı sıralayın.
7. **Duyarlılık:** Seed, sınır ve kritik varsayımları değiştirin.
8. **3B ve QGIS doğrulaması:** Komşuluk, erişim, cephe, mülkiyet ve servis ilişkilerini inceleyin.
9. **Uzman kontrolü:** Gerekli disiplinlere aktarın.
10. **Karar kaydı:** Seçim gerekçesi, elenen alternatifler, koşullar ve riskleri yazın.

### Örnek bulgu → karar → aksiyon zincirleri

| Bulgu | Karar | Aksiyon |
|---|---|---|
| GFA yüksek; karbon ve runoff kötü | Yoğunluk koşullu kabul | Tipoloji/malzeme değiştir, açık alan ve geçirgenlik eşiği ekle |
| Rüzgâr zayıf; kanyon oranı yüksek | Kütle sürekliliğini kır | Setback, kademe ve rüzgâr koridoru varyantı üret |
| TOPSIS sırası küçük değişimde ters dönüyor | Karar kırılgan | Tek kazanan seçme; veri ve paydaş tercihi topla |
| Farklı seedlerde aynı aile üstte | Çözüm görece dayanıklı | Detay tasarım ve uzman doğrulamasına geçir |

## 10. İyileştirme ve sorun çözme

| Belirti | Muhtemel neden | Yapılacak işlem |
|---|---|---|
| Workflow çalışmıyor | Bağlantısız node, yanlış kök, döngü veya çoklu giriş | İlk validation mesajını çöz, temel zincire dön |
| Uygun aday yok | Kısıtlar fiziksel olarak çelişkili | Mevzuat verisini doğrula, karar uzayını kontrol et |
| Tüm adaylar benzer | Mutation düşük, aralık dar, erken yakınsama | Mutation/population artır, genotype sınırlarını gözden geçir |
| Sonuç her koşuda değişiyor | Bütçe düşük veya problem çok modlu | Seed sabitle, bütçeyi büyüt, çoklu seed testi yap |
| TOPSIS anlamsız | Min/max yönü yanlış veya aday kümesi zayıf | Objective yönü ve Pareto filtresini denetle |
| 3B iyi fakat metrik kötü | Görsel beğeni ile ölçülen hedef farklı | Varsayımı aç, objective/kısıtı gerekçeli biçimde düzelt |
| Tarayıcı yavaş | Çok özellik veya yüksek arama bütçesi | Selected scope ve kademeli ölçek kullan |

## 11. QGIS'e güvenli senkronizasyon

1. Önce `Preview Best in 3D` ile fenotipi kontrol edin.
2. Workflow'u JSON olarak dışa aktarın.
3. Kaynak katmanın yedeğini alın.
4. İlk denemede `apply_mode=selected` kullanın.
5. Tek özellikte yazılan alanları ve değerleri kontrol edin.
6. Toplu senkronizasyondan sonra attribute diff ve mekânsal görünümü inceleyin.
7. QGIS düzenleme oturumunu yalnız kontrol tamamlandıktan sonra commit edin.

Geri yazılan alanlar çözüm tipolojisi ve kat sayısından FAR, BCR, GFA, karbon, runoff, açık alan, rüzgâr, güneş ve Pareto kimliğine kadar karar denetimini destekleyen değerleri içerir.

## 12. Tekrar üretilebilirlik kaydı

Her önemli koşuda aşağıdakileri arşivleyin:

- Veri dosyası veya anlık görüntü kimliği.
- Katman adı, CRS ve seçim kapsamı.
- Plugin sürümü.
- Workflow JSON.
- Algoritma, population, generations, crossover, mutation ve seed.
- Objective listesi ve min/max yönleri.
- Zoning eşikleri ve kaynakları.
- Pareto/PCP filtreleri ve TOPSIS tercih senaryosu.
- Kısa liste, elenen adaylar ve karar gerekçesi.
- CSV/JSON raporları ve gerekli 3B ekran görüntüleri.

## 13. Nihai checklist

- [ ] Geometri ve CRS doğrulandı.
- [ ] Sert imar koşulları resmi kaynağıyla doğrulandı.
- [ ] Objective yönleri ve birimleri kontrol edildi.
- [ ] Küçük keşif koşusu hatasız tamamlandı.
- [ ] En az iki seed/duyarlılık koşusu karşılaştırıldı.
- [ ] Pareto, PCP ve ham tablo birlikte okundu.
- [ ] Farklı çözüm ailelerinden kısa liste oluşturuldu.
- [ ] TOPSIS sıralaması ham metriklerle denetlendi.
- [ ] 3B ve QGIS mekânsal doğrulama yapıldı.
- [ ] Workflow JSON ve sonuçlar arşivlendi.
- [ ] Karar gerekçesi, riskler ve sonraki uzman analizleri kaydedildi.

## 14. Temel sözlük

- **Genotype:** Tasarımı üreten karar değişkenleri.
- **Phenotype:** Karar değişkenlerinden oluşan gözlenebilir 3B/mekânsal çözüm.
- **Pareto optimal:** Başka bir hedefi kötüleştirmeden iyileştirilemeyen aday.
- **Dominance:** Bir adayın tüm hedeflerde en az eşit, en az birinde daha iyi olması.
- **Convergence:** Popülasyonun kaliteli çözüm bölgesine yaklaşması.
- **Diversity:** Farklı çözüm ailelerinin korunması.
- **Seed:** Rastgele üretimin tekrarlanabilir başlangıcı.
- **TOPSIS:** İdeal ve anti-ideal çözüme göre göreli çok ölçütlü sıralama.
- **DAG:** Döngü içermeyen yönlü workflow grafiği.

Son ilke: Model sonucu karar değildir. İyi karar; model çıktısı, mevzuat, saha bilgisi, paydaş önceliği ve uzman doğrulamasının belgelenmiş birleşimidir.
