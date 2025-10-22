
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
import re
import os

def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Usar webdriver-manager para gerenciar o ChromeDriver automaticamente
    try:
        service = Service(ChromeDriverManager().install())
    except Exception:
        # Fallback para caminho local se webdriver-manager falhar
        service = Service("/opt/homebrew/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def clean_price(price_str):
    if not price_str: return 'N/A'
    # Remove thousand separators ("." or ",") and replace decimal comma (",") with dot (".")
    # Handles cases like '1.165,00' -> '1165.00' and '97,00' -> '97.00'
    # First, remove all dots (thousand separator in some locales)
    cleaned_price = price_str.replace('.', '')
    # Then, replace comma with dot (decimal separator in some locales)
    cleaned_price = cleaned_price.replace(',', '.')
    
    # Check if the cleaned price matches a pattern like '12345' (integer without decimal)
    # If so, and it's a dollar price, assume it should have two decimal places
    # This is a heuristic based on the observation that some dollar prices are missing decimal
    if re.fullmatch(r'\d+', cleaned_price) and len(cleaned_price) > 2: # e.g., '9700' should be '97.00'
        cleaned_price = cleaned_price[:-2] + '.' + cleaned_price[-2:]

    # Ensure it's a valid number format
    try:
        return str(float(cleaned_price))
    except ValueError:
        return 'N/A'

def scrape_products(driver, search_term):
    base_url = "https://comprasparaguai.com.br"
    search_url = f"{base_url}/busca/?q={search_term}"
    driver.get(search_url)

    # Aceitar cookies, se presente
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ENTENDI')] | //button[contains(text(), 'Estou de Acordo')] | //*[@id='btn-cookie-allow']"))
        ).click()
        time.sleep(2) # Dar um tempo para o banner de cookies sumir
    except Exception:
        pass # Elemento de cookie não encontrado ou já aceito

    products_data = []
    
    # Rolar a página para carregar mais produtos (se houver lazy loading)
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    max_scroll_attempts = 5 # Ajustar conforme necessário
    while scroll_attempts < max_scroll_attempts:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)  # Esperar o conteúdo carregar
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        scroll_attempts += 1

    # Salvar o HTML da página para depuração
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("HTML da página salvo em debug_page.html para depuração.")

    # Usar BeautifulSoup para parsear o HTML após o carregamento dinâmico
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Extrair dados dos produtos
    product_items = soup.find_all('div', class_='promocao-produtos-item')
    print(f"Encontrados {len(product_items)} itens de produto.")

    for item in product_items:
        try:
            name_tag = item.find('div', class_='promocao-item-nome')
            name = name_tag.a.text.strip() if name_tag and name_tag.a else 'N/A'

            link_tag = item.find('div', class_='promocao-item-nome')
            link = link_tag.a['href'] if link_tag and link_tag.a and 'href' in link_tag.a.attrs else 'N/A'
            if link and not link.startswith('http'):
                link = base_url + link

            price_usd = 'N/A'
            price_brl = 'N/A'

            # Extração do preço em dólar
            price_usd_element = item.select_one('.price-model span') or item.select_one('.promocao-item-preco-oferta strong')
            if price_usd_element:
                price_usd_text = price_usd_element.get_text(strip=True)
                match_usd = re.search(r'US\$\s*([\d\.,]+)', price_usd_text)
                if match_usd:
                    price_usd = clean_price(match_usd.group(1))

            # Extração do preço em real
            price_brl_element = item.select_one('.promocao-item-preco-text')
            if price_brl_element:
                price_brl_text = price_brl_element.get_text(strip=True)
                match_brl = re.search(r'R\$\s*([\d\.,]+)', price_brl_text)
                if match_brl:
                    price_brl = clean_price(match_brl.group(1))

            # Extração da URL da imagem
            image_url = 'N/A'
            img_tag = item.select_one('.promocao-item-img img')
            if img_tag:
                if 'data-src' in img_tag.attrs:
                    image_url = img_tag['data-src']
                elif 'src' in img_tag.attrs:
                    image_url = img_tag['src']
                
                # Corrigir URLs relativas ou incompletas
                if image_url and not image_url.startswith('http') and not image_url.startswith('//'):
                    image_url = 'https://media-production-bucket.us-southeast-1.linodeobjects.com' + image_url
                elif image_url.startswith('//'):
                    image_url = 'https:' + image_url
                
                # Se a URL da imagem ainda for 'N/A' ou vazia, garantir que não seja concatenada com o base_url
                if not image_url or 'N/A' in image_url:
                    image_url = 'N/A'

            products_data.append({
                'Nome': name,
                'Preço (US$)': price_usd,
                'Preço (R$)': price_brl,
                'Link': link,
                'Imagem': image_url
            })
        except Exception as e:
            print(f"Erro ao extrair produto: {e}")
            continue
    return products_data

def save_to_excel(data, filename='produtos.xlsx'):
    try:
        import pandas as pd
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False)
        print(f"Dados salvos em {filename}")
    except ImportError:
        print("Pandas não disponível. Salvando apenas em JSON.")
        save_to_json(data, filename.replace('.xlsx', '.json'))

def save_to_json(data, filename='produtos.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Dados salvos em {filename}")

if __name__ == '__main__':
    search_term = 'iphone' # Termo de busca padrão
    print(f"Iniciando a extração para: {search_term}")
    driver = setup_driver()
    try:
        products = scrape_products(driver, search_term)
        if products:
            save_to_excel(products)
            save_to_json(products)
            print(f"Total de {len(products)} produtos extraídos.")
        else:
            print("Nenhum produto encontrado.")
    finally:
        driver.quit()

