# 🤖 Automação Sistema Domínio

Script Python para automação completa de atualização cadastral e verificação do quadro societário no sistema Domínio.

## 📋 Funcionalidades

- ✅ **Login automático** no sistema Domínio
- 🏢 **Processamento em lote** de todas as empresas cadastradas
- 🔄 **Atualização automática** dos dados cadastrais
- 🤖 **Resolução de captcha** via 2Captcha
- 👥 **Verificação do quadro societário** contra ReceitaWS
- 📊 **Logs detalhados** em CSV e JSON
- ⚠️ **Tratamento robusto de erros**

## 🚀 Instalação

### 1. Clone ou baixe o projeto
```bash
git clone [url-do-repositorio]
cd dominio-automation
```

### 2. Instale as dependências
```bash
pip install -r requirements.txt
```

### 3. Instale o navegador Chromium
```bash
playwright install chromium
```

### 4. Configure as variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto:
```env
DOMINIO_PASSWORD=sua_senha_do_dominio
CAPTCHA_2CAPTCHA_KEY=sua_chave_do_2captcha
```

## ⚙️ Configuração

### 🔑 Obter chave do 2Captcha
1. Acesse [2captcha.com](https://2captcha.com)
2. Crie uma conta e adicione fundos
3. Copie sua API key para o arquivo `.env`

### 🌐 Configurar URL do Sistema
No arquivo `dominio_automation.py`, linha 35:
```python
await self.page.goto("URL_DO_DOMINIO")  # Substitua pela URL real
```

### 🎯 Ajustar Seletores (se necessário)
Caso a interface do sistema seja diferente, ajuste os seletores CSS nas seguintes funções:
- `login()` - Campos de login
- `get_companies_list()` - Lista de empresas
- `select_company()` - Seleção de empresa
- `update_company_data()` - Campos de dados

## 🏃‍♂️ Execução

```bash
python dominio_automation.py
```

### 📊 Logs Gerados
O script gera dois tipos de log:

**1. CSV Resumido** (`log_atualizacao_dominio_YYYYMMDD_HHMMSS.csv`)
```csv
Empresa,CNPJ,Status,Alterações,Observações
LOC E LOG LOCAÇÕES,03163171000804,Atualizada com sucesso,3,
EXEMPLO LTDA,12345678000123,Divergência no Quadro Societário,0,Sócio ausente na ReceitaWS
```

**2. JSON Detalhado** (`log_detalhado_YYYYMMDD_HHMMSS.json`)
```json
{
  "empresa": "LOC E LOG LOCAÇÕES",
  "cnpj": "03163171000804",
  "status": "Atualizada com sucesso",
  "alteracoes": {
    "Razão Social": {"de": "LOC E LOG LTDA", "para": "LOC E LOG LOCAÇÕES"}
  },
  "socios_dominio": ["HERMES CARRIJO COELHO"],
  "socios_receita": ["HERMES CARRIJO COELHO"],
  "divergencia_societaria": false
}
```

## 🔧 Tratamento de Erros

### ❌ Captcha não validado
- **Ação**: Retry automático até 3 tentativas
- **Log**: Registra falha se não conseguir resolver

### ⚠️ Página da Internet inválida
- **Ação**: Copia URL para campo "Observações"
- **Log**: Continua processamento normalmente

### 👥 Sócio em múltiplas empresas
- **Ação**: Pressiona OK e continua
- **Log**: Registra como processada normalmente

### 🔍 Divergência no Quadro Societário
- **Ação**: **NÃO altera** os dados
- **Log**: Registra divergência detalhada

## 📈 Limite de API

### ReceitaWS (Versão Gratuita)
- **Limite**: 3 consultas por minuto
- **Intervalo**: 30 segundos entre chamadas
- **Implementação**: Aguarda automaticamente

### 2Captcha
- **Custo**: ~$0.001 por captcha
- **Tempo**: 10-60 segundos por resolução
- **Implementação**: Polling automático

## 🛡️ Segurança

### Dados Sensíveis
- ✅ Senha armazenada em `.env` (não versionado)
- ✅ Chave 2Captcha em `.env` (não versionado)
- ✅ Logs locais (não enviados para nuvem)

### Navegador
- 🔒 Usa Chromium controlado (não headless para debug)
- 🔒 Contexto isolado por sessão
- 🔒 Fechamento automático ao final

## 🐛 Solução de Problemas

### Script não inicia
```bash
# Verificar dependências
pip list | grep playwright
pip list | grep requests

# Reinstalar se necessário
pip install -r requirements.txt --force-reinstall
```

### Erro de navegador
```bash
# Reinstalar navegador
playwright install chromium --force
```

### Captcha não resolve
- Verifique saldo no 2Captcha
- Confirme se a chave está correta no `.env`
- Teste conexão: `curl "http://2captcha.com/res.php?key=SUA_CHAVE&action=getbalance"`

### Seletores não funcionam
- Inspecione a interface do sistema Domínio
- Ajuste os seletores CSS no código
- Use `await self.page.screenshot(path="debug.png")` para debug

## 📞 Suporte

### Logs de Debug
Para debug avançado, adicione no início do script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Modo Headless
Para execução em servidor, altere na linha 22:
```python
self.browser = await playwright.chromium.launch(headless=True)
```

## ⚖️ Responsabilidades

- 🔒 Use apenas em sistemas que você tem autorização
- 📊 Mantenha logs em local seguro
- 🔄 Faça backup dos dados antes de executar
- ⚠️ Monitore execução para evitar problemas

## 🔄 Versão
**v1.0.0** - Versão inicial completa

---

**Desenvolvido para automação profissional do sistema Domínio**  
*Script otimizado para eficiência e segurança*
