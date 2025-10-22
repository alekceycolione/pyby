from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import json
from datetime import datetime

# Import the scraper functions
from scraper import setup_driver, scrape_products

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    try:
        data = request.get_json()
        search_term = data.get('search_term', '').strip()
        shipping_cost = float(data.get('shipping_cost', 0))
        
        if not search_term:
            return jsonify({'error': 'Termo de busca é obrigatório'}), 400
        
        print(f"🔍 Buscando por: {search_term}")
        print(f"🚚 Frete: R$ {shipping_cost:.2f}")
        
        # Setup driver and scrape
        driver = setup_driver()
        try:
            products = scrape_products(driver, search_term)
            
            # Adicionar preço de venda calculado para cada produto
            for product in products:
                try:
                    # Extrair preço BRL e calcular preço de venda final em reais
                    brl_price_str = product.get('Preço (R$)', '0')
                    if brl_price_str != 'N/A':
                        brl_price = float(brl_price_str)
                        final_price_brl = brl_price + shipping_cost
                        product['Preço Final (R$)'] = f"{final_price_brl:.2f}"
                    else:
                        product['Preço Final (R$)'] = 'N/A'
                except (ValueError, TypeError):
                    product['Preço Final (R$)'] = 'N/A'
            
            # Save results with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save JSON
            json_filename = f'produtos_{search_term}_{timestamp}.json'
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=4)
            
            print(f"Busca concluída. {len(products)} produtos encontrados.")
            
            return jsonify({
                'success': True,
                'products': products,
                'shipping_cost': shipping_cost,
                'count': len(products),
                'search_term': search_term,
                'json_file': json_filename
            })
            
        finally:
            driver.quit()
            
    except Exception as e:
        print(f"Erro durante a busca: {str(e)}")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory('.', filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({'error': 'Arquivo não encontrado'}), 404

if __name__ == '__main__':
    print("🚀 Iniciando servidor do Scraper Compras Paraguai...")
    print("📱 Acesse: http://localhost:8080")
    print("🛑 Para parar: Ctrl+C")
    app.run(debug=True, host='0.0.0.0', port=8080)