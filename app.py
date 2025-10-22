from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import json
import logging
import traceback
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Adicionar o diretório atual ao path para importar o scraper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from scraper import setup_driver, scrape_products

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    try:
        logger.info("🔄 Iniciando nova requisição de scraping")
        
        data = request.get_json()
        search_term = data.get('search_term', '').strip()
        shipping_cost = float(data.get('shipping_cost', 0))
        
        logger.info(f"📝 Dados recebidos - Termo: '{search_term}', Frete: R$ {shipping_cost:.2f}")
        
        if not search_term:
            logger.warning("❌ Termo de busca vazio")
            return jsonify({'error': 'Termo de busca é obrigatório'}), 400
        
        print(f"🔍 Buscando por: {search_term}")
        print(f"🚚 Frete: R$ {shipping_cost:.2f}")
        
        # Setup driver and scrape
        logger.info("🚀 Configurando driver do Chrome...")
        try:
            driver = setup_driver()
            logger.info("✅ Driver configurado com sucesso")
        except Exception as e:
            logger.error(f"❌ Erro ao configurar driver: {str(e)}")
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return jsonify({'error': f'Erro ao configurar navegador: {str(e)}'}), 500
        
        try:
            logger.info(f"🔍 Iniciando scraping para '{search_term}'...")
            products = scrape_products(driver, search_term)
            logger.info(f"📊 Scraping concluído. {len(products)} produtos encontrados")
            
            # Adicionar preço de venda calculado para cada produto
            logger.info("💰 Calculando preços finais...")
            for i, product in enumerate(products):
                try:
                    # Extrair preço BRL e calcular preço de venda final em reais
                    brl_price_str = product.get('Preço (R$)', '0')
                    if brl_price_str != 'N/A':
                        brl_price = float(brl_price_str)
                        final_price_brl = brl_price + shipping_cost
                        product['Preço Final (R$)'] = f"{final_price_brl:.2f}"
                        logger.debug(f"Produto {i+1}: R$ {brl_price:.2f} + R$ {shipping_cost:.2f} = R$ {final_price_brl:.2f}")
                    else:
                        product['Preço Final (R$)'] = 'N/A'
                        logger.debug(f"Produto {i+1}: Preço N/A")
                except (ValueError, TypeError) as e:
                    product['Preço Final (R$)'] = 'N/A'
                    logger.warning(f"⚠️ Erro ao calcular preço do produto {i+1}: {str(e)}")
            
            # Save results with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save JSON
            json_filename = f'produtos_{search_term}_{timestamp}.json'
            logger.info(f"💾 Salvando resultados em {json_filename}...")
            
            try:
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(products, f, ensure_ascii=False, indent=4)
                logger.info("✅ Arquivo JSON salvo com sucesso")
            except Exception as e:
                logger.error(f"❌ Erro ao salvar JSON: {str(e)}")
                # Continua mesmo se não conseguir salvar o arquivo
            
            logger.info(f"🎉 Busca concluída com sucesso! {len(products)} produtos encontrados")
            
            return jsonify({
                'success': True,
                'products': products,
                'shipping_cost': shipping_cost,
                'count': len(products),
                'search_term': search_term,
                'json_file': json_filename
            })
            
        except Exception as e:
            logger.error(f"❌ Erro durante o scraping: {str(e)}")
            logger.error(f"📋 Traceback completo: {traceback.format_exc()}")
            return jsonify({'error': f'Erro durante a busca: {str(e)}'}), 500
            
        finally:
            try:
                driver.quit()
                logger.info("🔒 Driver fechado com sucesso")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao fechar driver: {str(e)}")
            
    except Exception as e:
        logger.error(f"💥 Erro crítico na aplicação: {str(e)}")
        logger.error(f"📋 Traceback completo: {traceback.format_exc()}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory('.', filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'Arquivo não encontrado'}), 404

@app.route('/logs')
def view_logs():
    """Endpoint para visualizar logs da aplicação"""
    try:
        log_lines = []
        if os.path.exists('app.log'):
            with open('app.log', 'r', encoding='utf-8') as f:
                log_lines = f.readlines()
        
        # Pegar as últimas 100 linhas
        recent_logs = log_lines[-100:] if len(log_lines) > 100 else log_lines
        
        return jsonify({
            'success': True,
            'logs': recent_logs,
            'total_lines': len(log_lines),
            'showing_lines': len(recent_logs)
        })
    except Exception as e:
        logger.error(f"Erro ao ler logs: {str(e)}")
        return jsonify({'error': f'Erro ao ler logs: {str(e)}'}), 500

@app.route('/logs/clear', methods=['POST'])
def clear_logs():
    """Endpoint para limpar logs da aplicação"""
    try:
        if os.path.exists('app.log'):
            with open('app.log', 'w') as f:
                f.write('')
            logger.info("📝 Logs limpos pelo usuário")
            return jsonify({'success': True, 'message': 'Logs limpos com sucesso'})
        else:
            return jsonify({'success': True, 'message': 'Arquivo de log não existe'})
    except Exception as e:
        logger.error(f"Erro ao limpar logs: {str(e)}")
        return jsonify({'error': f'Erro ao limpar logs: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print("🚀 Iniciando servidor do Scraper Compras Paraguai...")
    if debug:
        print(f"📱 Acesse: http://localhost:{port}")
    print("🛑 Para parar: Ctrl+C")
    
    app.run(debug=debug, host='0.0.0.0', port=port)