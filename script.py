import asyncio
import json
import csv
import time
import re
import requests
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import os
from typing import List, Dict, Optional

# Carrega variáveis do .env
load_dotenv()

class DominioAutomation:
    def __init__(self):
        self.password = os.getenv('DOMINIO_PASSWORD')
        self.captcha_key = os.getenv('CAPTCHA_2CAPTCHA_KEY')
        self.log_csv = []
        self.log_json = []
        self.page = None
        self.context = None
        self.browser = None
        
    async def init_browser(self):
        """Inicializa o navegador"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
    async def login(self):
        """Realiza login no sistema Domínio"""
        try:
            # Navegar para a página de login (substitua pela URL real)
            await self.page.goto("URL_DO_DOMINIO")
            
            # Preencher senha (usuário já preenchido)
            await self.page.fill('input[name="password"]', self.password)
            
            # Pressionar Alt + O para login
            await self.page.keyboard.press('Alt+o')
            
            # Aguardar carregamento completo
            await self.page.wait_for_load_state('networkidle')
            
            print("✅ Login realizado com sucesso")
            return True
            
        except Exception as e:
            print(f"❌ Erro no login: {e}")
            return False
    
    async def get_companies_list(self) -> List[str]:
        """Obtém lista de empresas cadastradas"""
        try:
            # Pressionar F8 para abrir Troca de Empresas
            await self.page.keyboard.press('F8')
            await asyncio.sleep(2)
            
            # Extrair lista de empresas (adapte seletor conforme interface)
            companies = await self.page.locator('select[name="empresas"] option').all_text_contents()
            
            print(f"📋 Encontradas {len(companies)} empresas")
            return companies
            
        except Exception as e:
            print(f"❌ Erro ao obter lista de empresas: {e}")
            return []
    
    async def select_company(self, company_name: str):
        """Seleciona uma empresa na lista"""
        try:
            # Selecionar empresa
            await self.page.select_option('select[name="empresas"]', company_name)
            await asyncio.sleep(1)
            
            # Confirmar seleção
            await self.page.click('button[name="confirmar"]')
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao selecionar empresa {company_name}: {e}")
            return False
    
    async def solve_captcha(self) -> bool:
        """Resolve hCaptcha usando 2Captcha"""
        try:
            # Localizar iframe do hCaptcha
            captcha_frame = await self.page.frame_locator('iframe[src*="hcaptcha"]')
            
            # Obter site key do hCaptcha
            site_key = await self.page.get_attribute('div[data-sitekey]', 'data-sitekey')
            
            # Enviar para 2Captcha
            captcha_data = {
                'key': self.captcha_key,
                'method': 'hcaptcha',
                'sitekey': site_key,
                'pageurl': self.page.url,
                'json': 1
            }
            
            response = requests.post('http://2captcha.com/in.php', data=captcha_data)
            result = response.json()
            
            if result['status'] != 1:
                print(f"❌ Erro ao enviar captcha: {result['error_text']}")
                return False
            
            captcha_id = result['request']
            
            # Aguardar resolução
            for _ in range(30):  # Máximo 30 tentativas (5 minutos)
                await asyncio.sleep(10)
                
                check_response = requests.get(f'http://2captcha.com/res.php?key={self.captcha_key}&action=get&id={captcha_id}&json=1')
                check_result = check_response.json()
                
                if check_result['status'] == 1:
                    # Inserir resposta do captcha
                    await self.page.evaluate(f'document.querySelector("textarea[name=h-captcha-response]").value = "{check_result["request"]}"')
                    await self.page.evaluate(f'document.querySelector("textarea[name=g-recaptcha-response]").value = "{check_result["request"]}"')
                    
                    print("✅ Captcha resolvido com sucesso")
                    return True
                elif check_result['status'] == 0 and check_result['request'] != 'CAPCHA_NOT_READY':
                    print(f"❌ Erro na resolução do captcha: {check_result['request']}")
                    return False
            
            print("❌ Timeout na resolução do captcha")
            return False
            
        except Exception as e:
            print(f"❌ Erro ao resolver captcha: {e}")
            return False
    
    async def update_company_data(self, company_name: str) -> Dict:
        """Atualiza dados cadastrais de uma empresa"""
        result = {
            'empresa': company_name,
            'cnpj': '',
            'status': 'Erro',
            'alteracoes': {},
            'socios_dominio': [],
            'socios_receita': [],
            'divergencia_societaria': False,
            'observacoes': ''
        }
        
        try:
            # Clicar em "Dados" (Alt + D)
            await self.page.keyboard.press('Alt+d')
            await asyncio.sleep(2)
            
            # Obter CNPJ da empresa
            cnpj_element = await self.page.locator('input[name="cnpj"]').first
            cnpj_raw = await cnpj_element.input_value()
            cnpj_clean = re.sub(r'[^\d]', '', cnpj_raw)
            result['cnpj'] = cnpj_clean
            
            # Clicar em "Atualizar Cadastro"
            await self.page.click('button:has-text("Atualizar Cadastro")')
            await asyncio.sleep(2)
            
            # Resolver captcha
            captcha_attempts = 0
            while captcha_attempts < 3:
                if await self.solve_captcha():
                    break
                captcha_attempts += 1
                
                # Verificar se apareceu erro de captcha
                if await self.page.locator('text="Captcha não validado"').is_visible():
                    print("⚠️ Captcha não validado, tentando novamente...")
                    await asyncio.sleep(2)
                    continue
                
            if captcha_attempts >= 3:
                result['status'] = 'Erro - Captcha não resolvido'
                return result
            
            # Clicar em "Importar"
            await self.page.click('button:has-text("Importar")')
            await asyncio.sleep(3)
            
            # Tratar possíveis erros
            if await self.page.locator('text="Página na Internet inválida"').is_visible():
                await self.handle_invalid_page_error()
            
            if await self.page.locator('text*="Sócio em mais de uma empresa"').is_visible():
                await self.page.keyboard.press('Alt+o')  # OK
                await asyncio.sleep(1)
            
            # Verificar quadro societário
            await self.verify_shareholders(result)
            
            # Se não há divergência, gravar alterações
            if not result['divergencia_societaria']:
                await self.save_changes()
                result['status'] = 'Atualizada com sucesso'
            else:
                result['status'] = 'Divergência no Quadro Societário'
                print(f"⚠️ Divergência societária encontrada em {company_name}")
            
            # Fechar aba de dados
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(1)
            
            return result
            
        except Exception as e:
            result['status'] = f'Erro: {str(e)}'
            result['observacoes'] = str(e)
            print(f"❌ Erro ao processar empresa {company_name}: {e}")
            return result
    
    async def handle_invalid_page_error(self):
        """Trata erro de página inválida"""
        try:
            # Copiar conteúdo após https://
            page_field = await self.page.locator('input[name="pagina_internet"]')
            page_value = await page_field.input_value()
            
            if page_value and 'https://' in page_value:
                content_after_https = page_value.split('https://', 1)[1]
                
                # Navegar para aba Observações
                await self.page.click('tab:has-text("Observações")')
                await asyncio.sleep(1)
                
                # Colar valor
                await self.page.fill('textarea[name="observacoes"]', content_after_https)
                
                # Voltar para aba principal
                await self.page.click('tab:has-text("Empresa")')
                await asyncio.sleep(1)
                
                print("✅ Erro de página inválida tratado")
                
        except Exception as e:
            print(f"❌ Erro ao tratar página inválida: {e}")
    
    async def verify_shareholders(self, result: Dict):
        """Verifica quadro societário contra ReceitaWS"""
        try:
            # Navegar para aba Quadro Societário
            await self.page.click('tab:has-text("Quadro Societário")')
            await asyncio.sleep(2)
            
            # Extrair sócios do Domínio
            shareholders_rows = await self.page.locator('table tbody tr').all()
            dominio_shareholders = []
            
            for row in shareholders_rows:
                name_cell = await row.locator('td').nth(0).text_content()
                if name_cell and name_cell.strip():
                    dominio_shareholders.append(name_cell.strip().upper())
            
            result['socios_dominio'] = dominio_shareholders
            
            # Consultar ReceitaWS
            if result['cnpj']:
                receita_shareholders = await self.get_receita_shareholders(result['cnpj'])
                result['socios_receita'] = receita_shareholders
                
                # Comparar sócios
                if self.compare_shareholders(dominio_shareholders, receita_shareholders):
                    result['divergencia_societaria'] = True
                    result['divergencias'] = self.get_shareholders_differences(dominio_shareholders, receita_shareholders)
            
            # Voltar para aba Empresa
            await self.page.click('tab:has-text("Empresa")')
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"❌ Erro ao verificar quadro societário: {e}")
            result['observacoes'] += f" Erro verificação societária: {e}"
    
    async def get_receita_shareholders(self, cnpj: str) -> List[str]:
        """Consulta sócios na ReceitaWS"""
        try:
            # Aguardar intervalo obrigatório de 30 segundos
            await asyncio.sleep(30)
            
            url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'qsa' in data:
                    return [socio['nome'].upper() for socio in data['qsa']]
            
            return []
            
        except Exception as e:
            print(f"❌ Erro ao consultar ReceitaWS: {e}")
            return []
    
    def compare_shareholders(self, dominio_list: List[str], receita_list: List[str]) -> bool:
        """Compara listas de sócios (True = há divergência)"""
        # Normalizar nomes (remover acentos, maiúsculas)
        dominio_normalized = [self.normalize_name(name) for name in dominio_list]
        receita_normalized = [self.normalize_name(name) for name in receita_list]
        
        return set(dominio_normalized) != set(receita_normalized)
    
    def normalize_name(self, name: str) -> str:
        """Normaliza nome removendo acentos e caracteres especiais"""
        # Remover acentos e converter para maiúsculas
        import unicodedata
        normalized = unicodedata.normalize('NFD', name)
        return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn').upper()
    
    def get_shareholders_differences(self, dominio_list: List[str], receita_list: List[str]) -> List[str]:
        """Retorna diferenças entre quadros societários"""
        differences = []
        
        dominio_normalized = [self.normalize_name(name) for name in dominio_list]
        receita_normalized = [self.normalize_name(name) for name in receita_list]
        
        # Sócios no Domínio mas não na Receita
        for name in dominio_normalized:
            if name not in receita_normalized:
                differences.append(f"{name} presente no Domínio mas ausente na ReceitaWS")
        
        # Sócios na Receita mas não no Domínio
        for name in receita_normalized:
            if name not in dominio_normalized:
                differences.append(f"{name} presente na ReceitaWS mas ausente no Domínio")
        
        return differences
    
    async def save_changes(self):
        """Grava alterações no sistema"""
        try:
            # Pressionar Alt + G (Gravar)
            await self.page.keyboard.press('Alt+g')
            await asyncio.sleep(2)
            
            # Verificar se há confirmação
            if await self.page.locator('text="Confirmar"').is_visible():
                await self.page.keyboard.press('Alt+s')  # Sim
                await asyncio.sleep(1)
            
            # Verificar se apareceu janela de alterações detectadas
            if await self.page.locator('text="alterações detectadas"').is_visible():
                await self.page.keyboard.press('Alt+g')  # Gravar novamente
                await asyncio.sleep(1)
            
            print("✅ Alterações gravadas com sucesso")
            
        except Exception as e:
            print(f"❌ Erro ao gravar alterações: {e}")
    
    def save_logs(self):
        """Salva logs em arquivos CSV e JSON"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Salvar CSV
        csv_filename = f"log_atualizacao_dominio_{timestamp}.csv"
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Empresa', 'CNPJ', 'Status', 'Alterações', 'Observações']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for entry in self.log_json:
                writer.writerow({
                    'Empresa': entry['empresa'],
                    'CNPJ': entry['cnpj'],
                    'Status': entry['status'],
                    'Alterações': len(entry['alteracoes']),
                    'Observações': entry['observacoes']
                })
        
        # Salvar JSON detalhado
        json_filename = f"log_detalhado_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(self.log_json, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"📊 Logs salvos: {csv_filename} e {json_filename}")
    
    async def run(self):
        """Executa o processo completo de automação"""
        try:
            await self.init_browser()
            
            # Login
            if not await self.login():
                print("❌ Falha no login. Encerrando processo.")
                return
            
            # Obter lista de empresas
            companies = await self.get_companies_list()
            if not companies:
                print("❌ Nenhuma empresa encontrada. Encerrando processo.")
                return
            
            print(f"🚀 Iniciando processamento de {len(companies)} empresas")
            
            # Processar cada empresa
            for i, company in enumerate(companies, 1):
                print(f"\n📋 Processando empresa {i}/{len(companies)}: {company}")
                
                # Selecionar empresa
                if await self.select_company(company):
                    # Atualizar dados
                    result = await self.update_company_data(company)
                    self.log_json.append(result)
                    
                    # Log de progresso
                    status_emoji = "✅" if result['status'] == 'Atualizada com sucesso' else "⚠️" if 'Divergência' in result['status'] else "❌"
                    print(f"{status_emoji} {company}: {result['status']}")
                else:
                    # Erro ao selecionar empresa
                    error_result = {
                        'empresa': company,
                        'cnpj': '',
                        'status': 'Erro - Não foi possível selecionar empresa',
                        'alteracoes': {},
                        'socios_dominio': [],
                        'socios_receita': [],
                        'divergencia_societaria': False,
                        'observacoes': 'Falha na seleção da empresa'
                    }
                    self.log_json.append(error_result)
                    print(f"❌ {company}: Erro na seleção")
            
            # Salvar logs
            self.save_logs()
            
            # Estatísticas finais
            successful = sum(1 for r in self.log_json if r['status'] == 'Atualizada com sucesso')
            divergent = sum(1 for r in self.log_json if 'Divergência' in r['status'])
            errors = len(self.log_json) - successful - divergent
            
            print(f"\n📊 Processo concluído:")
            print(f"   ✅ Atualizadas: {successful}")
            print(f"   ⚠️ Divergências: {divergent}")
            print(f"   ❌ Erros: {errors}")
            
        except Exception as e:
            print(f"❌ Erro crítico no processo: {e}")
            
        finally:
            if self.browser:
                await self.browser.close()

# Função principal
async def main():
    automation = DominioAutomation()
    await automation.run()

if __name__ == "__main__":
    asyncio.run(main())
