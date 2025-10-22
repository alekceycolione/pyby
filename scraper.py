
import logging
import requests
from bs4 import BeautifulSoup
import json
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ webdriver_manager não disponível: {str(e)}")
    ChromeDriverManager = None

# Configurar logging para o scraper
logger = logging.getLogger(__name__)

def setup_driver():
    logger.info("🔧 Configurando opções do Chrome...")
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
    
    # Tentar múltiplas estratégias para configurar o driver
    driver = None
    
    # Estratégia 1: webdriver-manager (se disponível)
    if ChromeDriverManager is not None:
        logger.info("📥 Tentativa 1: Instalando/configurando ChromeDriver via webdriver-manager...")
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("✅ ChromeDriver configurado via webdriver-manager")
            return driver
        except Exception as e:
            logger.warning(f"⚠️ Falha na tentativa 1: {str(e)}")
    else:
        logger.info("⏭️ Pulando tentativa 1: webdriver-manager não disponível")
    
    # Estratégia 2: Caminho padrão do Render
    logger.info("🔄 Tentativa 2: Usando caminho padrão do Render...")
    try:
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("✅ ChromeDriver configurado no caminho do Render")
        return driver
    except Exception as e:
        logger.warning(f"⚠️ Falha na tentativa 2: {str(e)}")
    
    # Estratégia 3: Caminho local (para desenvolvimento)
    logger.info("🔄 Tentativa 3: Usando caminho local...")
    try:
        service = Service("/opt/homebrew/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("✅ ChromeDriver configurado no caminho local")
        return driver
    except Exception as e:
        logger.warning(f"⚠️ Falha na tentativa 3: {str(e)}")
    
    # Estratégia 4: Sem service específico
    logger.info("🔄 Tentativa 4: Usando driver sem service específico...")
    try:
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("✅ ChromeDriver configurado sem service específico")
        return driver
    except Exception as e:
        logger.warning(f"⚠️ Falha na tentativa 4: {str(e)}")
    
    # Se todas as tentativas falharam, implementar fallback sem Selenium
    logger.error("❌ Todas as tentativas de configurar o ChromeDriver falharam")
    logger.info("🔄 Implementando fallback: scraping sem Selenium usando requests")
    
    # Retornar um objeto mock que simula o driver para o fallback
    class MockDriver:
        def __init__(self):
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
            logger.info("✅ Fallback configurado: usando requests em vez de Selenium")
        
        def get(self, url):
            logger.info(f"🌐 Fallback: Fazendo requisição HTTP para {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            self.page_source = response.text
            logger.info("✅ Fallback: Página carregada com sucesso")
        
        def quit(self):
            logger.info("🔒 Fallback: Fechando sessão requests")
            self.session.close()
        
        def find_element(self, by, value):
            # Método dummy para compatibilidade
            raise NoSuchElementException(f"Fallback mode: elemento {value} não encontrado")
        
        def find_elements(self, by, value):
            # Método dummy para compatibilidade
            return []
    
    return MockDriver()

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
    logger.info(f"🌐 Iniciando scraping para termo: '{search_term}'")
    base_url = "https://comprasparaguai.com.br"
    search_url = f"{base_url}/busca/?q={search_term}"
    
    logger.info(f"📍 Navegando para: {search_url}")
    try:
        driver.get(search_url)
        logger.info("✅ Página carregada com sucesso")
    except TimeoutException as e:
        logger.error(f"⏰ Timeout ao carregar página: {str(e)}")
        logger.error("A página demorou muito para carregar. Verifique a conexão com a internet.")
        raise
    except WebDriverException as e:
        logger.error(f"🚫 Erro do WebDriver ao carregar página: {str(e)}")
        logger.error("Possível problema com o navegador ou driver.")
        raise
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao carregar página: {str(e)}")
        logger.error(f"Tipo do erro: {type(e).__name__}")
        raise

    # Aceitar cookies, se presente (apenas para Selenium real)
    logger.info("🍪 Verificando banner de cookies...")
    try:
        # Verificar se é o MockDriver (fallback)
        if hasattr(driver, 'session'):
            logger.info("⏭️ Fallback mode: pulando verificação de cookies")
        else:
            cookie_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'ENTENDI')] | //button[contains(text(), 'Estou de Acordo')] | //*[@id='btn-cookie-allow']"))
            )
            cookie_button.click()
            logger.info("✅ Banner de cookies aceito")
        time.sleep(2) # Dar um tempo para o banner de cookies sumir
    except Exception as e:
        logger.info("ℹ️ Banner de cookies não encontrado ou já aceito")

    products_data = []
    
    # Rolar a página para carregar mais produtos (apenas para Selenium real)
    logger.info("📜 Iniciando scroll para carregar produtos...")
    if hasattr(driver, 'session'):
        logger.info("⏭️ Fallback mode: pulando scroll (usando HTML estático)")
    else:
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 5 # Ajustar conforme necessário
        
        while scroll_attempts < max_scroll_attempts:
            logger.debug(f"📜 Scroll tentativa {scroll_attempts + 1}/{max_scroll_attempts}")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # Esperar o conteúdo carregar
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logger.info("📜 Fim da página atingido")
                break
            last_height = new_height
            scroll_attempts += 1
        
        logger.info(f"📜 Scroll concluído após {scroll_attempts} tentativas")

    # Salvar o HTML da página para depuração
    logger.info("💾 Salvando HTML da página para debug...")
    try:
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger.info("✅ HTML salvo em debug_page.html")
    except Exception as e:
        logger.warning(f"⚠️ Erro ao salvar HTML de debug: {str(e)}")

    # Usar BeautifulSoup para parsear o HTML após o carregamento dinâmico
    logger.info("🍲 Parseando HTML com BeautifulSoup...")
    try:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        logger.info("✅ HTML parseado com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro ao parsear HTML com BeautifulSoup: {str(e)}")
        logger.error("Possível problema com o conteúdo HTML ou parser")
        # Tentar com parser alternativo
        try:
            logger.info("🔄 Tentando parser alternativo...")
            soup = BeautifulSoup(driver.page_source, 'lxml')
            logger.info("✅ HTML parseado com parser lxml")
        except Exception as e2:
            logger.error(f"❌ Erro também com parser lxml: {str(e2)}")
            try:
                logger.info("🔄 Tentando parser html.parser básico...")
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                logger.info("✅ HTML parseado com parser básico")
            except Exception as e3:
                logger.error(f"❌ Falha total no parsing: {str(e3)}")
                raise Exception("Não foi possível parsear o HTML com nenhum parser disponível")

    # Extrair dados dos produtos
    logger.info("🔍 Procurando produtos na página...")
    product_items = soup.find_all('div', class_='promocao-produtos-item')
    logger.info(f"📊 Encontrados {len(product_items)} itens de produto")

    if len(product_items) == 0:
        logger.warning("⚠️ Nenhum produto encontrado! Verificando estrutura da página...")
        # Tentar encontrar outros seletores possíveis
        alternative_selectors = [
            'div.produto-item',
            'div.product-item', 
            'div[class*="produto"]',
            'div[class*="product"]',
            'article',
            '.card'
        ]
        
        for selector in alternative_selectors:
            try:
                items = soup.select(selector)
                if items:
                    logger.info(f"🔍 Encontrados {len(items)} itens com seletor alternativo: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Seletor {selector} falhou: {str(e)}")

    for i, item in enumerate(product_items):
        logger.debug(f"🔍 Processando produto {i+1}/{len(product_items)}")
        try:
            name_tag = item.find('div', class_='promocao-item-nome')
            name = name_tag.a.text.strip() if name_tag and name_tag.a else 'N/A'
            logger.debug(f"📝 Nome: {name}")

            link_tag = item.find('div', class_='promocao-item-nome')
            link = link_tag.a['href'] if link_tag and link_tag.a and 'href' in link_tag.a.attrs else 'N/A'
            if link and not link.startswith('http'):
                link = base_url + link
            logger.debug(f"🔗 Link: {link}")

            price_usd = 'N/A'
            price_brl = 'N/A'

            # Extração do preço em dólar
            price_usd_element = item.select_one('.price-model span') or item.select_one('.promocao-item-preco-oferta strong')
            if price_usd_element:
                price_usd_text = price_usd_element.get_text(strip=True)
                match_usd = re.search(r'US\$\s*([\d\.,]+)', price_usd_text)
                if match_usd:
                    price_usd = clean_price(match_usd.group(1))
                    logger.debug(f"💵 Preço USD: {price_usd}")

            # Extração do preço em real
            price_brl_element = item.select_one('.promocao-item-preco-text')
            if price_brl_element:
                price_brl_text = price_brl_element.get_text(strip=True)
                match_brl = re.search(r'R\$\s*([\d\.,]+)', price_brl_text)
                if match_brl:
                    price_brl = clean_price(match_brl.group(1))
                    logger.debug(f"💰 Preço BRL: {price_brl}")

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
                    
                logger.debug(f"🖼️ Imagem: {image_url}")

            product_data = {
                'Nome': name,
                'Preço (US$)': price_usd,
                'Preço (R$)': price_brl,
                'Link': link,
                'Imagem': image_url
            }
            
            products_data.append(product_data)
            logger.debug(f"✅ Produto {i+1} processado com sucesso")
            
        except AttributeError as e:
            logger.error(f"❌ Erro de atributo ao extrair produto {i+1}: {str(e)}")
            logger.error("Possível mudança na estrutura HTML da página")
            continue
        except KeyError as e:
            logger.error(f"❌ Chave não encontrada ao extrair produto {i+1}: {str(e)}")
            logger.error("Elemento HTML esperado não possui o atributo necessário")
            continue
        except TypeError as e:
            logger.error(f"❌ Erro de tipo ao extrair produto {i+1}: {str(e)}")
            logger.error("Tipo de dados inesperado durante a extração")
            continue
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao extrair produto {i+1}: {str(e)}")
            logger.error(f"Tipo do erro: {type(e).__name__}")
            continue
    
    logger.info(f"🎯 Scraping finalizado. Total de {len(products_data)} produtos extraídos")
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

