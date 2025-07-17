import csv
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List

import logging
from colorama import Fore, Style, init as colorama_init

import requests
from dotenv import load_dotenv
from pywinauto import Application, keyboard
import pyautogui
import pyperclip

APP_SHORTCUT = r"C:\\Contabil\\contabil.exe /registro"

class DominioConsultaSocietaria:
    """Consulta simplificada do quadro societ\u00e1rio no Dom\u00ednio."""

    def __init__(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
        colorama_init(autoreset=True)
        self.logger = logging.getLogger(__name__)

        load_dotenv()
        self.password = os.getenv("DOMINIO_PASSWORD", "")
        self.test_mode = os.getenv("TEST_MODE", "false").lower() in ("1", "true", "yes")
        self.manual_login = os.getenv("MANUAL_LOGIN", "false").lower() in ("1", "true", "yes")
        self.app: Application | None = None
        self.main_window = None
        self.log_json: List[Dict] = []

    # --------------------------------------------------------------
    # Inicializa\u00e7\u00e3o e login
    # --------------------------------------------------------------
    def init_app(self) -> None:
        """Abre o aplicativo Dom\u00ednio."""
        self.logger.info(Fore.YELLOW + "Abrindo aplicativo Dom\u00ednio" + Style.RESET_ALL)
        # inicia o Dom\u00ednio sem aguardar ocioso para evitar travamentos
        self.app = Application(backend="win32").start(APP_SHORTCUT, wait_for_idle=False)
        time.sleep(2)  # pequena pausa para a janela ser criada

        # conecta na janela principal, que pode demorar alguns segundos para surgir
        self.app.connect(title_re=".*Dom\u00ednio.*", timeout=60)
        self.main_window = self.app.window(title_re=".*Dom\u00ednio.*")
        self.main_window.wait("visible", timeout=60)
        self.logger.info(Fore.GREEN + "Aplicativo aberto" + Style.RESET_ALL)

    def login(self) -> tuple[bool, str]:
        """Realiza login automatico ou aguarda login manual."""
        self.logger.info(Fore.YELLOW + "Realizando login" + Style.RESET_ALL)
        try:
            if not self.main_window:
                return False, "Janela principal não encontrada"
            self.main_window.wait("ready", timeout=30)
            self.main_window.set_focus()

            if self.manual_login:
                self.logger.info("Aguardando login manual")
                input()
                return True, "Login manual realizado"

            try:
                password_edit = self.main_window.child_window(
                    auto_id="1007", class_name="Edit"
                )
                password_edit.wait("ready", timeout=5)
                password_edit.click_input()
                pyperclip.copy(self.password)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.5)
            except Exception as exc:  # pragma: no cover - depende da UI
                self.logger.error("Erro ao inserir senha: %s", exc)
                try:
                    self.main_window.set_focus()
                    keyboard.send_keys(self.password)
                except Exception as exc2:  # pragma: no cover - depende da UI
                    self.logger.error("Falha no fallback de digitação: %s", exc2)
                    return False, f"Erro ao digitar senha: {exc2}"

            self.main_window.set_focus()
            keyboard.send_keys("%o")  # Alt+O
            time.sleep(2)

            # conecta novamente à janela principal aberta apos o login
            self.app.connect(title_re=".*Domínio.*", timeout=60)
            self.main_window = self.app.window(title_re=".*Domínio.*")
            self.main_window.wait("ready")
            self.main_window.set_focus()

            self.logger.info(Fore.GREEN + "Login realizado" + Style.RESET_ALL)

            return True, ""
        except Exception as exc:
            screenshot = "login_error.png"
            try:
                pyautogui.screenshot(screenshot)
            except Exception as scr_exc:  # pragma: no cover - captura opcional
                self.logger.error("Falha ao salvar screenshot: %s", scr_exc)
            self.logger.error(
                "Erro no login: %s. Screenshot salvo em %s", exc, screenshot
            )
            return False, f"Erro no login: {exc}"

    # --------------------------------------------------------------
    # Processamento das empresas
    # --------------------------------------------------------------
    def get_companies_list(self) -> tuple[List[str], str]:
        try:
            self.logger.debug("Obtendo lista de empresas")
            self.main_window.set_focus()
            keyboard.send_keys("{F8}")
            time.sleep(2)
            # the list of empresas is hosted inside a custom control identified
            # by auto_id 1011 (class_name "pbdw190"), so we iterate over its
            # children to read the names
            list_box = self.main_window.child_window(auto_id="1011")
            companies = [child.window_text() for child in list_box.children()]
            self.main_window.set_focus()
            keyboard.send_keys("{ESC}")
            self.logger.info("%d empresas encontradas", len(companies))
            return companies, ""
        except Exception as exc:
            self.logger.error("Falha ao obter empresas: %s", exc)
            return [], str(exc)

    def select_company(self, name: str) -> tuple[bool, str]:
        try:
            self.logger.debug("Selecionando empresa %s", name)
            self.main_window.set_focus()
            keyboard.send_keys("{F8}")
            time.sleep(1)
            # seleciona a empresa procurando entre os filhos do controle
            list_box = self.main_window.child_window(auto_id="1011")
            for item in list_box.children():
                if item.window_text().strip().upper() == name.upper():
                    item.click_input()
                    break
            else:
                self.main_window.set_focus()
                keyboard.send_keys("{ESC}")
                self.logger.warning("Empresa %s não encontrada", name)
                return False, f"Empresa {name} não encontrada"
            self.main_window.set_focus()
            keyboard.send_keys("%o")
            time.sleep(1)
            self.logger.info("Empresa %s selecionada", name)
            return True, ""
        except Exception as exc:
            self.main_window.set_focus()
            keyboard.send_keys("{ESC}")
            self.logger.error("Falha ao selecionar empresa %s: %s", name, exc)
            return False, str(exc)

    # --------------------------------------------------------------
    # Consulta de quadro societ\u00e1rio
    # --------------------------------------------------------------
    def check_company_shareholders(self, company: str) -> Dict:
        result: Dict[str, object] = {
            "empresa": company,
            "cnpj": "",
            "socios_receita": [],
            "observacoes": "",
        }
        try:
            self.logger.debug("Verificando sócios da empresa %s", company)
            self.main_window.set_focus()
            keyboard.send_keys("{F8}")  # abre Troca de empresas
            time.sleep(1)

            list_box = self.main_window.child_window(auto_id="1011")
            for item in list_box.children():
                if item.window_text().strip().upper() == company.upper():
                    item.click_input()
                    break
            else:
                self.main_window.set_focus()
                keyboard.send_keys("{ESC}")
                result["observacoes"] = "Empresa n\u00e3o encontrada"
                self.logger.warning("Empresa %s não encontrada", company)
                return result

            try:
                dados_btn = self.main_window.child_window(auto_id="1006")
                dados_btn.wait("ready", timeout=1)
                dados_btn.click_input()
            except Exception:
                keyboard.send_keys("%d")  # alternativa via atalho

            time.sleep(2)
            cnpj_edit = self.main_window.child_window(class_name="Edit")
            cnpj_raw = cnpj_edit.window_text()
            result["cnpj"] = re.sub(r"[^0-9]", "", cnpj_raw)
            self.logger.debug("CNPJ obtido: %s", result["cnpj"])
            self.verify_shareholders(result)

            self.main_window.set_focus()
            keyboard.send_keys("{ESC}")  # fecha Dados
            time.sleep(1)
            keyboard.send_keys("{ESC}")  # fecha Troca de empresas
            time.sleep(1)
        except Exception as exc:
            result["observacoes"] = str(exc)
            self.main_window.set_focus()
            keyboard.send_keys("{ESC}")
            keyboard.send_keys("{ESC}")
        return result

    def verify_shareholders(self, result: Dict) -> None:
        if not result.get("cnpj"):
            return
        try:
            time.sleep(30)
            url = f"https://receitaws.com.br/v1/cnpj/{result['cnpj']}"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                result["socios_receita"] = [s["nome"].upper() for s in data.get("qsa", [])]
        except Exception as exc:
            result["observacoes"] += f" Erro ReceitaWS: {exc}"

    # --------------------------------------------------------------
    # Registro
    # --------------------------------------------------------------
    def save_logs(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_name = f"log_consulta_socios_{timestamp}.csv"
        json_name = f"log_consulta_socios_{timestamp}.json"

        with open(csv_name, "w", newline="", encoding="utf-8") as csv_file:
            fieldnames = ["Empresa", "CNPJ", "Socios Receita", "Observacoes"]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for entry in self.log_json:
                writer.writerow(
                    {
                        "Empresa": entry.get("empresa", ""),
                        "CNPJ": entry.get("cnpj", ""),
                        "Socios Receita": " | ".join(entry.get("socios_receita", [])),
                        "Observacoes": entry.get("observacoes", ""),
                    }
                )

        with open(json_name, "w", encoding="utf-8") as json_file:
            json.dump(self.log_json, json_file, indent=2, ensure_ascii=False)

        self.logger.info("Logs salvos em %s e %s", csv_name, json_name)

    # --------------------------------------------------------------
    # Execu\u00e7\u00e3o principal
    # --------------------------------------------------------------
    def run(self) -> None:
        self.logger.info(Fore.GREEN + "Iniciando script" + Style.RESET_ALL)
        self.logger.debug("test_mode=%s manual_login=%s", self.test_mode, self.manual_login)
        self.init_app()
        success, message = self.login()
        if not success:
            print(message)
            return
        companies, msg = self.get_companies_list()
        if msg:
            print(msg)
        if self.test_mode:
            companies = companies[:3]
            print("Modo teste ativo: processando apenas as 3 primeiras empresas")
        print(f"Processando {len(companies)} empresas")
        for company in companies:
            selected, sel_msg = self.select_company(company)
            if not selected:
                print(sel_msg)
                continue
            result = self.check_company_shareholders(company)
            self.log_json.append(result)
        self.save_logs()
        if self.app:
            self.app.kill()


def main() -> None:
    consulta = DominioConsultaSocietaria()
    consulta.run()


if __name__ == "__main__":
    main()
