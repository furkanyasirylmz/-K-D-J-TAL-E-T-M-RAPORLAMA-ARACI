
# veriile2.py
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
            string_data, encoding='utf-8', sep=';', 
            on_bad_lines='skip', skipinitialspace=True
        )
        st.success("Dosya başarıyla yüklendi ve okundu.")
        
        # Sütun adlarındaki fazlalıkları temizliyoruz
        df.columns = df.columns.str.strip()
        
        if 'Etkinlik Kayıt Tarihi' in df.columns:
            # Tarih parse (karışık formatlara toleranslı)
            df['Etkinlik Kayıt Tarihi'] = pd.to_datetime(
                df['Etkinlik Kayıt Tarihi'], dayfirst=True, errors='coerce'
            )
            
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
                    "Ay Seçin", options=[all_months_option] + month_options, 
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
                        'Eğitim Adı', 
                        'Katılımcı Tam Adı',
                        'Etkinlik Kategorisi',
                        'Tamamlanma Durumu', 
                        'Etkinlik Kayıt Tarihi',
                        'Harcanan Süre'
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
