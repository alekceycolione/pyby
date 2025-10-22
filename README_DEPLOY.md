# 🚀 Deploy no Render - Scraper Compras Paraguai

## 📋 Pré-requisitos

1. **Conta no Render**: Crie uma conta gratuita em [render.com](https://render.com)
2. **Repositório Git**: Seu código deve estar em um repositório Git (GitHub, GitLab, etc.)

## 🔧 Arquivos de Configuração Criados

✅ **requirements.txt** - Dependências Python
✅ **Procfile** - Comando de inicialização
✅ **runtime.txt** - Versão do Python
✅ **render.yaml** - Configuração do serviço Render
✅ **Dockerfile** - Para containerização (opcional)
✅ **.dockerignore** - Arquivos a ignorar no Docker

## 📤 Passos para Deploy

### 1. Preparar o Repositório
```bash
# Adicionar todos os arquivos ao Git
git add .
git commit -m "Preparar para deploy no Render"
git push origin main
```

### 2. Criar Serviço no Render

1. Acesse [render.com](https://render.com) e faça login
2. Clique em **"New +"** → **"Web Service"**
3. Conecte seu repositório Git
4. Configure o serviço:
   - **Name**: `scraper-compras-paraguai`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

### 3. Configurar Variáveis de Ambiente

No painel do Render, adicione estas variáveis:
- `FLASK_ENV` = `production`
- `PORT` = `10000` (automático no Render)

### 4. Deploy Automático

O Render fará o deploy automaticamente. Aguarde alguns minutos.

## 🌐 Acesso à Aplicação

Após o deploy, sua aplicação estará disponível em:
`https://scraper-compras-paraguai.onrender.com`

## ⚠️ Limitações do Plano Gratuito

- **Sleep Mode**: Aplicação "dorme" após 15 minutos de inatividade
- **Tempo de Build**: Limitado a 90 segundos
- **Recursos**: CPU e RAM limitados
- **Selenium**: Pode ter problemas de performance

## 🔧 Troubleshooting

### Problema: Chrome/Selenium não funciona
**Solução**: O Render pode ter limitações com Selenium. Considere:
1. Usar um serviço de scraping externo
2. Implementar cache para reduzir requisições
3. Upgrade para plano pago

### Problema: Timeout no Build
**Solução**: 
1. Otimizar requirements.txt
2. Usar imagem Docker mais leve
3. Remover dependências desnecessárias

### Problema: Aplicação não inicia
**Verificar**:
1. Logs no painel do Render
2. Variáveis de ambiente
3. Comando de start no Procfile

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs no painel do Render
2. Teste localmente primeiro
3. Consulte a documentação do Render

## 🎯 Próximos Passos

1. **Monitoramento**: Configure alertas no Render
2. **Domínio Customizado**: Adicione seu próprio domínio
3. **SSL**: Configurado automaticamente pelo Render
4. **Backup**: Configure backup dos dados extraídos