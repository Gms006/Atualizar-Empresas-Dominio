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

### 3. Configure as variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto:
```env
DOMINIO_PASSWORD=sua_senha_do_dominio
CAPTCHA_2CAPTCHA_KEY=sua_chave_do_2captcha
TEST_MODE=true  # opcional, processa somente as 3 primeiras empresas
MANUAL_LOGIN=true  # se verdadeiro, o script aguardará o login manual
```

## ⚙️ Configuração

### 🔑 Obter chave do 2Captcha
1. Acesse [2captcha.com](https://2captcha.com)
2. Crie uma conta e adicione fundos
3. Copie sua API key para o arquivo `.env`

### 🌐 Configurar Caminho do Sistema
No arquivo `script.py`, ajuste a constante `APP_SHORTCUT` caso o executável esteja em outro local.

### 🎯 Ajustar Componentes da Interface
Se a interface do sistema for diferente, edite os métodos da classe para localizar os elementos corretos utilizando **pywinauto** ou **pyautogui**.

## 🏃‍♂️ Execução

```bash
python script.py
```

Se a variável `TEST_MODE` estiver definida como `true`, somente as três primeiras empresas serão processadas.

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

### Aplicativo
- 🔒 Uso do aplicativo instalado no Windows
- 🔒 Janela identificada e controlada por pywinauto
- 🔒 Fechamento automático ao final

## 🐛 Solução de Problemas

### Script não inicia
```bash
# Verificar dependências
pip list | grep pywinauto
pip list | grep requests

# Reinstalar se necessário
pip install -r requirements.txt --force-reinstall
```



### Captcha não resolve
- Verifique saldo no 2Captcha
- Confirme se a chave está correta no `.env`
- Teste conexão: `curl "http://2captcha.com/res.php?key=SUA_CHAVE&action=getbalance"`

### Elementos não encontrados
- Inspecione a janela do sistema Domínio
- Ajuste os identificadores usados no código
- Use `pyautogui.screenshot('debug.png')` para auxiliar no debug

## ❓ FAQ

### O script exibe `TimeoutError` ao iniciar
Verifique se a constante `APP_SHORTCUT` aponta para o executável correto do Domínio e se a janela de login abre normalmente fora do script.  
Caso o sistema demore a iniciar, aumente o tempo de espera na função `init_app`.

### A senha não é inserida na janela de login
Confirme que o foco está no campo de senha e que o uso de área de transferência não está bloqueado.
Se necessário, altere o método de digitação para `keyboard.send_keys`.

### Posso fazer o login manualmente?
Defina `MANUAL_LOGIN=true` no arquivo `.env`. O script abrirá o Domínio e aguardará você concluir o login manualmente antes de continuar.

## 📞 Suporte

### Logs de Debug
Para debug avançado, adicione no início do script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
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
