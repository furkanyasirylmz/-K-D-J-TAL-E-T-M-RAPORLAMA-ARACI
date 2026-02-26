# veriile2.py

import re
import streamlit as st
import pandas as pd
from io import StringIO

st.title("Dijital Eğitim Raporlama Aracı")
st.write("Yeni CSV dosyanızı yükleyin ve tarih aralığını seçerek raporu alın.")

uploaded_file = st.file_uploader("CSV dosyanızı yükleyin", type=['csv'])

if uploaded_file is not None:
    string_data = StringIO(uploaded_file.getvalue().decode("utf-8"))
    try:
        # Dosyayı NOKTALI VİRGÜL (;) ayırıcısıyla okuyoruz.
        df = pd.read_csv(
            string_data,
            encoding='utf-8',
            sep=';',
            on_bad_lines='skip',
            skipinitialspace=True
        )
        st.success("Dosya başarıyla yüklendi ve okundu.")

        # Sütun adlarındaki fazlalıkları temizle
        df.columns = df.columns.str.strip()

        # =========================================================
        # 1) GELEN BAŞLIKLARI HEP AYNI "HEDEF" BAŞLIKLARA ÇEVİR
        #    (Senin istediğin standardize başlıklar)
        # =========================================================
        # CSV'de farklı kaynaklardan gelebilecek muhtemel adlar:
        incoming_to_target = {
            # İsim
            'Ad Soyad': 'Ad Soyad',
            'Ad Soyad.1': 'Ad Soyad',          # varsa birleştir
            'Katılımcı Adı': 'Ad Soyad',

            # Eğitim adı
            'Eğitim Adı': 'Eğitim Adı',
            'Etkinlik Adı': 'Eğitim Adı',
            'Eğitim/Konu': 'Eğitim Adı',

            # Kategori
            'Kategori': 'Kategori',
            'Eğitim Kategorisi': 'Kategori',
            'Etkinlik Kategorisi': 'Kategori',

            # Kayıt tarihi
            'Kayıt Tarihi': 'Kayıt Tarihi',
            'Etkinlik Kayıt Tarihi': 'Kayıt Tarihi',
            'Tarih': 'Kayıt Tarihi',
            'Tarih/Saat': 'Kayıt Tarihi',

            # Tamamlanma durumu
            'Tamamlanma Durumu': 'Tamamlanma Durumu',
            'Etkinlik Tamamlanma Durumu': 'Tamamlanma Durumu',
            'Durum': 'Tamamlanma Durumu',

            # Süre
            'Eğitimde Geçirilen Süre': 'Eğitimde Geçirilen Süre',
            'Etkinlikte Harcanan Zaman': 'Eğitimde Geçirilen Süre',
            'Süre': 'Eğitimde Geçirilen Süre',
        }

        # Yalnızca var olanları rename et
        available_map = {c: incoming_to_target[c] for c in df.columns if c in incoming_to_target}
        if available_map:
            df.rename(columns=available_map, inplace=True)

        # "Ad Soyad.1" varsa ve "Ad Soyad" boş olan yerler için yedekse doldur
        if 'Ad Soyad.1' in df.columns and 'Ad Soyad' in df.columns:
            df['Ad Soyad'] = df['Ad Soyad'].astype(str)
            df['Ad Soyad'] = df['Ad Soyad'].where(
                df['Ad Soyad'].str.strip().ne(''),
                df['Ad Soyad.1'].astype(str)
            )

        # Artık hedef başlık setimiz şu olmalı (en azından mevcut olanlar):
        target_headers = [
            'Ad Soyad', 'Eğitim Adı', 'Kategori',
            'Kayıt Tarihi', 'Tamamlanma Durumu', 'Eğitimde Geçirilen Süre'
        ]

        # =========================================================
        # 2) KODU BOZMAMAK İÇİN "ETKİNLİK ..." ALIAS SÜTUNLARINI DA OLUŞTUR
        #    (Kodun geri kalanı bu isimleri kullanıyor)
        # =========================================================
        # Hedef -> Kodun beklediği iç isimler (alias)
        target_to_internal_alias = {
            'Kayıt Tarihi': 'Etkinlik Kayıt Tarihi',
            'Eğitim Adı': 'Etkinlik Adı',
            'Kategori': 'Etkinlik Kategorisi',
            'Tamamlanma Durumu': 'Etkinlik Tamamlanma Durumu',
            'Eğitimde Geçirilen Süre': 'Etkinlikte Harcanan Zaman',
            # 'Ad Soyad' aynı kullanılacak
        }

        # Hedef sütun mevcutsa karşılığı olan Etkinlik ... isminde bir alias sütunu oluştur
        for src, alias in target_to_internal_alias.items():
            if src in df.columns:
                df[alias] = df[src]

        # =========================================================
        # 3) TARİH NORMALİZASYONU (Senin gönderdiğin blok, iç isimle çalışır)
        # =========================================================
        if 'Etkinlik Kayıt Tarihi' in df.columns:
            # --- Türkçe ay adları haritası ---
            TR_MONTHS = {
                'ocak': '01', 'şubat': '02', 'mart': '03', 'nisan': '04', 'mayıs': '05', 'haziran': '06',
                'temmuz': '07', 'ağustos': '08', 'eylül': '09', 'ekim': '10', 'kasım': '11', 'aralık': '12'
            }

            # --- "Perşembe, 6 Şubat 2025, 10:03 AM" --> "2025-02-06 10:03 AM" normalize eden fonksiyon ---
            def normalize_tr_datetime(x: str):
                if pd.isna(x):
                    return None
                s = str(x).strip().replace('\xa0', ' ')  # olası NBSP temizliği

                # Türkçe AM/PM varyasyonlarını normalize et
                s = (s.replace('ÖÖ', 'AM').replace('ÖS', 'PM')
                       .replace('öğleden önce', 'AM').replace('öğleden sonra', 'PM')
                       .replace('öö', 'AM').replace('ös', 'PM'))

                # Başındaki gün adını ve virgülü temizle (ör. "Perşembe, ")
                s = re.sub(r'^[A-Za-zÇĞİÖŞÜçğıöşü\s]+,\s*', '', s)

                # Şablon: "6 Şubat 2025, 10:03 AM" veya "6 Şubat 2025, 16:03"
                m = re.match(
                    r'^\s*(?P<gun>\d{1,2})\s+(?P<ay>[A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(?P<yil>\d{4}),\s*'
                    r'(?P<saat>\d{1,2}:\d{2}(?::\d{2})?)\s*(?P<ampm>(AM|PM))?\s*$',
                    s, flags=re.I
                )

                if m:
                    day = int(m.group('gun'))
                    mon_name = m.group('ay').lower()
                    mon_num = TR_MONTHS.get(mon_name)
                    year = m.group('yil')
                    timepart = m.group('saat')
                    ampm = m.group('ampm')  # olabilir ya da olmayabilir

                    if mon_num:
                        iso_like = f"{year}-{mon_num}-{day:02d} {timepart}"
                        if ampm:
                            iso_like += f" {ampm.upper()}"  # AM/PM varsa ekle
                        return iso_like

                # Eşleşmezse orijinali döndür (sonraki parse denemeleri için)
                return s

            # --- UYGULAMA: normalize et ve çok aşamalı parse yap ---
            tmp = df['Etkinlik Kayıt Tarihi'].apply(normalize_tr_datetime)

            # 12-saat (saniyeli)
            dt = pd.to_datetime(tmp, format='%Y-%m-%d %I:%M:%S %p', errors='coerce')

            # 12-saat (saniyesiz)
            mask = dt.isna()
            if mask.any():
                dt2 = pd.to_datetime(tmp[mask], format='%Y-%m-%d %I:%M %p', errors='coerce')
                dt.loc[mask] = dt2

            # 24-saat (saniyeli)
            mask = dt.isna()
            if mask.any():
                dt3 = pd.to_datetime(tmp[mask], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                dt.loc[mask] = dt3

            # 24-saat (saniyesiz)
            mask = dt.isna()
            if mask.any():
                dt4 = pd.to_datetime(tmp[mask], format='%Y-%m-%d %H:%M', errors='coerce')
                dt.loc[mask] = dt4

            # Son atama
            df['Etkinlik Kayıt Tarihi'] = dt

            # (İsteğe bağlı) parse edilemeyenleri uyarı olarak göster
            if df['Etkinlik Kayıt Tarihi'].isna().any():
                kalan = tmp[df['Etkinlik Kayıt Tarihi'].isna()].head(5).tolist()
                st.warning(f"Tarih formatı çözülemeyen kayıt örnekleri: {kalan}")

            # --- yıl/ay listeleri ---
            years = sorted(
                df['Etkinlik Kayıt Tarihi'].dt.year.dropna().unique().astype(int).tolist()
            )
            months = {
                1: 'Ocak', 2: 'Şubat', 3: 'Mart', 4: 'Nisan', 5: 'Mayıs', 6: 'Haziran',
                7: 'Temmuz', 8: 'Ağustos', 9: 'Eylül', 10: 'Ekim', 11: 'Kasım', 12: 'Aralık'
            }

            col1, col2 = st.columns(2)
            with col1:
                default_year_index = len(years) - 1 if len(years) > 0 else 0
                selected_year = st.selectbox("Yıl Seçin", options=years, index=default_year_index)
            with col2:
                all_months_option = 'Tüm Aylar'
                month_options = list(months.values())
                selected_months = st.multiselect(
                    "Ay Seçin",
                    options=[all_months_option] + month_options,
                    default=all_months_option
                )

            selected_month_numbers = []
            if all_months_option in selected_months:
                selected_month_numbers = list(months.keys())
            else:
                for month_name in selected_months:
                    for num, name in months.items():
                        if name == month_name:
                            selected_month_numbers.append(num)

            if st.button("Rapor Oluştur"):
                # Tarih aralığı filtresi (ay ve yıl)
                df_filtered = df[
                    (df['Etkinlik Kayıt Tarihi'].dt.year == selected_year) &
                    (df['Etkinlik Kayıt Tarihi'].dt.month.isin(selected_month_numbers))
                ].copy()

                if df_filtered.empty:
                    st.warning("Seçilen tarih aralığında veri bulunamadı.")
                else:
                    # ---- YENİDEN ADLANDIRMA (Ad/Soyad hariç) ----
                    df_filtered.rename(columns={
                        'Etkinlik Adı': 'Eğitim Adı',
                        'Etkinlik Tamamlanma Durumu': 'Tamamlanma Durumu',
                        'Etkinlikte Harcanan Zaman': 'Harcanan Süre'
                    }, inplace=True)

                    # ---- KATILIMCI TAM ADI OLUŞTURMA (Ad Soyad / Ad Soyad.1) ----
                    # Öncelik: 'Ad Soyad' -> boşsa ve varsa 'Ad Soyad.1' ile doldur.
                    if 'Ad Soyad' in df_filtered.columns:
                        kat_fullname = df_filtered['Ad Soyad'].astype(str)
                        if 'Ad Soyad.1' in df_filtered.columns:
                            kat_fullname = kat_fullname.where(
                                kat_fullname.str.strip().ne(''),
                                df_filtered['Ad Soyad.1'].astype(str)
                            )
                    elif 'Ad Soyad.1' in df_filtered.columns:
                        kat_fullname = df_filtered['Ad Soyad.1'].astype(str)
                    else:
                        # veriile2.py akışını bozmadan anlaşılır bir hata
                        st.error("İsim sütunu bulunamadı. Dosyada 'Ad Soyad' bekleniyor.")
                        st.stop()

                    df_filtered['Katılımcı Tam Adı'] = kat_fullname.str.strip()

                    # ---- SÜRE FİLTRESİ ve DÖNÜŞÜM ----
                    if 'Harcanan Süre' not in df_filtered.columns:
                        st.error("Dosyada 'Etkinlikte Harcanan Zaman' sütunu bulunamadı.")
                        st.stop()

                    # '-' veya boş süreleri dışarıda bırak
                    df_filtered = df_filtered[
                        df_filtered['Harcanan Süre'].astype(str).str.strip().ne('-') &
                        df_filtered['Harcanan Süre'].notna()
                    ]

                    # Saat:Dakika:Saniye -> toplam saniye
                    def convert_to_seconds(time_str):
                        try:
                            parts = str(time_str).split(':')
                            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                            return h * 3600 + m * 60 + s
                        except (ValueError, IndexError):
                            return 0

                    df_filtered['Harcanan Süre'] = df_filtered['Harcanan Süre'].apply(convert_to_seconds)

                    # ---- İSTATİSTİKLER ----
                    tamamlanan_egitim_baslik_sayisi = df_filtered[
                        df_filtered['Tamamlanma Durumu'] == 'Tamamlandı'
                    ]['Eğitim Adı'].nunique()

                    devam_eden_egitim_baslik_sayisi = df_filtered[
                        df_filtered['Tamamlanma Durumu'] != 'Tamamlandı'
                    ]['Eğitim Adı'].nunique()

                    tamamlanan_etkilesim_sayisi = df_filtered[
                        df_filtered['Tamamlanma Durumu'] == 'Tamamlandı'
                    ].shape[0]

                    devam_eden_etkilesim_sayisi = df_filtered[
                        df_filtered['Tamamlanma Durumu'] != 'Tamamlandı'
                    ].shape[0]

                    toplam_katilimci_sayisi = df_filtered['Katılımcı Tam Adı'].nunique()
                    toplam_etkilesim_sayisi = df_filtered.shape[0]

                    toplam_saniye = df_filtered['Harcanan Süre'].sum()
                    toplam_saat = int(toplam_saniye // 3600)
                    toplam_dakika = int((toplam_saniye % 3600) // 60)

                    # ---- GÖRSELLEŞTİRME ----
                    st.markdown("---")
                    st.subheader(f"Eğitim İstatistikleri: {', '.join(selected_months) if selected_months else 'Yok'} {selected_year}")

                    col1_m, col2_m = st.columns(2)
                    with col1_m:
                        st.metric("Tamamlanan Dijital Eğitim Sayısı", tamamlanan_egitim_baslik_sayisi)
                    with col2_m:
                        st.metric("Devam Eden Dijital Eğitim Sayısı", devam_eden_egitim_baslik_sayisi)

                    col3_m, col4_m = st.columns(2)
                    with col3_m:
                        st.metric("Tamamlanan Katılımcı Sayısı", tamamlanan_etkilesim_sayisi)
                    with col4_m:
                        st.metric("Devam Eden Katılımcı Sayısı", devam_eden_etkilesim_sayisi)

                    st.metric("Toplam Katılımcı Sayısı", toplam_katilimci_sayisi)
                    st.metric("Toplam Eğitim Süresi", f"{toplam_saat} saat {toplam_dakika} dakika")

                    st.markdown("---")
                    st.subheader("En Çok Tercih Edilen 25 Eğitim")

                    top_25_egitim = (
                        df_filtered.groupby(['Eğitim Adı', 'Etkinlik Kategorisi'])
                        .size()
                        .reset_index(name='Katılım Sayısı')
                        .sort_values(by='Katılım Sayısı', ascending=False)
                        .head(25)
                    )
                    st.dataframe(top_25_egitim)

                    st.markdown("---")
                    st.subheader("Filtrelenmiş Veri Tablosu")
                    column_order = [
                        'Eğitim Adı', 'Katılımcı Tam Adı', 'Etkinlik Kategorisi',
                        'Tamamlanma Durumu', 'Etkinlik Kayıt Tarihi', 'Harcanan Süre'
                    ]
                    # Sürpriz sütun eksikliklerine karşı emniyet
                    column_order = [c for c in column_order if c in df_filtered.columns]
                    df_display = df_filtered[column_order]
                    st.dataframe(df_display)

        else:
            st.error("Hata: Dosyanızdaki sütun başlıkları eşleşmiyor. Lütfen sütun başlıklarını kontrol edin.")

    except Exception as e:
        st.error(f"Dosya işlenirken bir hata oluştu: {e}")
        st.warning("Lütfen dosya formatının doğru olduğundan (noktalı virgül ile ayrılmış CSV) emin olun.")
``
