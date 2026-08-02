import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time
import urllib.parse

st.set_page_config(page_title="Prospectador Uni GRÁTIS - Sem Cartão", page_icon="🆓", layout="wide")

st.markdown("""
<style>
.big-title {font-size:30px; font-weight:900; color:#111827;}
.free-badge {background:#dcfce7; color:#166534; padding:8px 16px; border-radius:8px; font-weight:800;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-title">🆓 Prospectador Uni - Versão 100% GRÁTIS (Sem Cartão)</p>', unsafe_allow_html=True)
st.markdown('<span class="free-badge">✅ NÃO PRECISA DE API KEY • NÃO PRECISA DE CARTÃO</span>', unsafe_allow_html=True)
st.caption("Usa OpenStreetMap - Banco de dados gratuito com 30 milhões de comércios no Brasil")

col1, col2 = st.columns(2)
with col1:
    busca = st.text_input("O QUE buscar?", "pizzaria", help="Ex: pizzaria, dentista, academia, oficina")
with col2:
    localidade = st.text_input("ONDE?", "São José do Rio Preto, SP", help="Seja específico: Centro, São José do Rio Preto, SP")

col3, col4 = st.columns(2)
with col3:
    raio = st.slider("Raio de busca (metros)", 1000, 20000, 5000, step=500, help="5000m = 5km do centro")
with col4:
    termo_filtro = st.text_input("Filtrar nome que contém (opcional)", "", help="Ex: se buscar mercado e digitar 'atacadão', só vem atacadão")

buscar = st.button("🔍 BUSCAR GRÁTIS AGORA - SEM CHAVE", type="primary", use_container_width=True)

def geocodificar(local):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": local, "format": "json", "limit": 1, "countrycodes": "br"}
    headers = {"User-Agent": "ProspectadorUni/1.0"}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15).json()
        if r:
            return float(r[0]["lat"]), float(r[0]["lon"]), r[0]["display_name"]
    except Exception as e:
        st.error(f"Erro ao localizar: {e}")
    return None, None, None

def buscar_comercios(lat, lon, raio_m, termo):
    # Overpass API - grátis
    # Busca por shop, amenity, craft com o nome
    overpass_url = "https://overpass-api.de/api/interpreter"
    # Query precisa: procura tudo num raio que tenha shop ou amenity
    query = f"""
    [out:json][timeout:25];
    (
      nwr["shop"](around:{raio_m},{lat},{lon});
      nwr["amenity"](around:{raio_m},{lat},{lon});
      nwr["craft"](around:{raio_m},{lat},{lon});
      nwr["office"](around:{raio_m},{lat},{lon});
    );
    out center 100;
    """
    headers = {"User-Agent": "ProspectadorUni/1.0"}
    try:
        resp = requests.get(overpass_url, params={"data": query}, headers=headers, timeout=30)
        return resp.json().get("elements", [])
    except Exception as e:
        st.error(f"Erro Overpass: {e}")
        return []

if buscar:
    if not busca or not localidade:
        st.error("Preencha o que buscar e onde")
        st.stop()

    with st.status(f"🔎 Buscando '{busca}' em '{localidade}' de graça...", expanded=True) as status:
        st.write(f"📍 Localizando '{localidade}'...")
        lat, lon, nome_completo = geocodificar(localidade)
        if not lat:
            st.error(f"Não achei '{localidade}'. Tente: 'Centro, São José do Rio Preto, SP' ou 'São José do Rio Preto, SP'")
            st.stop()
        st.write(f"✅ Encontrado: {nome_completo} -> {lat}, {lon}")

        st.write(f"🎯 Buscando comércios num raio de {raio}m...")
        elementos = buscar_comercios(lat, lon, raio, busca)
        st.write(f"📦 {len(elementos)} comércios encontrados no raio, filtrando por '{busca}'...")

        resultados = []
        termo_lower = busca.lower()
        filtro_lower = termo_filtro.lower() if termo_filtro else ""

        for el in elementos:
            tags = el.get("tags", {})
            nome = tags.get("name", "")
            # Se não tem nome, ignora
            if not nome:
                continue
            
            # FILTRO DE PRECISÃO: tem que ter o termo buscado no nome OU no tipo de loja
            nome_lower = nome.lower()
            shop_type = tags.get("shop","") + " " + tags.get("amenity","") + " " + tags.get("craft","")
            shop_lower = shop_type.lower()

            # Verifica se o termo buscado está no nome ou tipo
            if termo_lower not in nome_lower and termo_lower not in shop_lower:
                # Também verifica tradução: pizzaria = pizza, etc
                if not (termo_lower in ["pizzaria","pizza"] and "pizza" in nome_lower):
                    # Se não bate, pula
                    if termo_lower not in str(tags).lower():
                        continue
            
            if filtro_lower and filtro_lower not in nome_lower:
                continue

            endereco_parts = []
            if tags.get("addr:street"): endereco_parts.append(tags.get("addr:street"))
            if tags.get("addr:housenumber"): endereco_parts.append(tags.get("addr:housenumber"))
            if tags.get("addr:city"): endereco_parts.append(tags.get("addr:city"))
            endereco = ", ".join(endereco_parts) if endereco_parts else tags.get("addr:full", nome_completo)

            telefone = tags.get("phone") or tags.get("contact:phone") or "Ver no Maps"
            whatsapp = tags.get("contact:whatsapp") or tags.get("whatsapp") or ""
            eh_whats = ""
            link_whats = ""
            if whatsapp or telefone:
                tel_limpo = whatsapp or telefone
                # Se tem whatsapp tag
                if whatsapp:
                    eh_whats = "✅ Tem WhatsApp cadastrado 📱"
                    link_whats = f"https://wa.me/{''.join(filter(str.isdigit, whatsapp))}"
                elif telefone != "Ver no Maps":
                    eh_whats = "☎️ Telefone listado - Clique para ver se é WhatsApp"
                    link_whats = f"https://wa.me/55{''.join(filter(str.isdigit, telefone))}"
                else:
                    eh_whats = "🔍 Clique em Localizar para ver telefone"
                    link_whats = ""

            lat_el = el.get("lat") or el.get("center", {}).get("lat")
            lon_el = el.get("lon") or el.get("center", {}).get("lon")
            link_maps = f"https://www.google.com/maps/search/?api=1&query={lat_el},{lon_el}" if lat_el else f"https://www.google.com/maps/search/{urllib.parse.quote(nome + ' ' + localidade)}"

            resultados.append({
                "Nome": nome,
                "Tipo": tags.get("shop") or tags.get("amenity") or tags.get("craft") or "comércio",
                "Endereço": endereco,
                "Telefone": telefone,
                "É WhatsApp?": eh_whats,
                "Link WhatsApp": link_whats,
                "Link Maps (Localizar)": link_maps
            })
        
        status.update(label=f"✅ Finalizado! {len(resultados)} resultados precisos para '{busca}'", state="complete", expanded=False)

    if resultados:
        st.success(f"Encontrei {len(resultados)} comércios que batem com '{busca}' em {raio}m de {localidade}")
        df = pd.DataFrame(resultados)
        st.dataframe(df, use_container_width=True, height=450, column_config={
            "Link Maps (Localizar)": st.column_config.LinkColumn("📍 Localizar"),
            "Link WhatsApp": st.column_config.LinkColumn("💬 WhatsApp"),
        })

        nome_arquivo = f"{busca.replace(' ','_')}_{localidade.replace(' ','_').replace(',','')}_GRATIS_{datetime.now().strftime('%d%m%Y')}.xlsx"
        df.to_excel(nome_arquivo, index=False)
        with open(nome_arquivo, "rb") as f:
            st.download_button(f"💾 BAIXAR EXCEL: {nome_arquivo}", f, file_name=nome_arquivo, type="primary", use_container_width=True)

        st.info("💡 Dica: Na coluna 'Link Maps (Localizar)' clique para abrir no Google Maps e ver telefone, WhatsApp e horário atualizado.")
    else:
        st.warning(f"Nenhum resultado para '{busca}' nesse raio. Tente aumentar o raio para 10000m ou buscar termo mais genérico como 'pizza' em vez de 'pizzaria gourmet'.")

st.divider()
st.markdown("""
### 🆚 Diferença entre versão Grátis vs Paga

| | **Grátis (esta aqui)** | **Paga (com cartão)** |
|---|---|---|
| **Precisa cartão?** | ❌ Não | ✅ Sim |
| **Precisa chave?** | ❌ Não | ✅ Sim |
| **Telefone automático?** | Às vezes (quando cadastrado) | ✅ Sempre |
| **Detector WhatsApp?** | Quando tem tag | ✅ Automático |
| **Precisão** | Muito boa | Perfeita |
| **Limite** | Ilimitado grátis | R$1200 grátis/mês |

**Para você sem cartão, use esta grátis. Ela já resolve 80% da prospecção!**
""")
