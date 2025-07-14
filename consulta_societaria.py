import csv
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List

import requests
from dotenv import load_dotenv
from pywinauto import Application, keyboard
import pyautogui
import pyperclip

APP_SHORTCUT = r"C:\\Contabil\\contabil.exe /registro"

class DominioConsultaSocietaria:
    """Consulta simplificada do quadro societ\u00e1rio no Dom\u00ednio."""

    def __init__(self) -> None:
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
        # inicia o Dom\u00ednio sem aguardar ocioso para evitar travamentos
        self.app = Application(backend="uia").start(APP_SHORTCUT, wait_for_idle=False)
        time.sleep(2)  # pequena pausa para a janela ser criada

        # conecta na janela principal, que pode demorar alguns segundos para surgir
        self.app.connect(title_re=".*Dom\u00ednio.*", timeout=60)
        self.main_window = self.app.window(title_re=".*Dom\u00ednio.*")
        self.main_window.wait("visible", timeout=60)

    def login(self) -> bool:
        """Realiza login automatico ou aguarda login manual."""
        try:
            if not self.main_window:
                return False
            self.main_window.wait("ready", timeout=30)
            self.main_window.set_focus()

            if self.manual_login:
                print("Aguardando login manual. Realize o login e pressione Enter...")
                input()
                return True

                password_edit = self.main_window.child_window(control_type="Edit")
                password_edit.wait("ready", timeout=5)
                password_edit.click_input()
                pyperclip.copy(self.password)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.5)

            except Exception:  # pragma: no cover - depende da UI
                keyboard.send_keys(self.password)

            keyboard.send_keys("%o")  # Alt+O
            time.sleep(2)
            return True
        except Exception:
            return False

    # --------------------------------------------------------------
    # Processamento das empresas
    # --------------------------------------------------------------
    def get_companies_list(self) -> List[str]:
        try:
            keyboard.send_keys("{F8}")
            time.sleep(2)
            list_box = self.main_window.child_window(auto_id="Empresas")
            companies = [item.window_text() for item in list_box.children()]
            keyboard.send_keys("{ESC}")
            return companies
        except Exception:
            return []

    def select_company(self, name: str) -> bool:
        try:
            keyboard.send_keys("{F8}")
            time.sleep(1)
            list_box = self.main_window.child_window(auto_id="Empresas")
            list_box.select(name)
            keyboard.send_keys("%o")
            time.sleep(1)
            return True
        except Exception:
            keyboard.send_keys("{ESC}")
            return False

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
            keyboard.send_keys("%d")  # abre aba Dados
            time.sleep(2)
            cnpj_edit = self.main_window.child_window(auto_id="CNPJ")
            cnpj_raw = cnpj_edit.get_value()  # type: ignore[attr-defined]
            result["cnpj"] = re.sub(r"[^0-9]", "", cnpj_raw)
            self.verify_shareholders(result)
            keyboard.send_keys("{ESC}")
            time.sleep(1)
        except Exception as exc:
            result["observacoes"] = str(exc)
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

        print(f"Logs salvos em {csv_name} e {json_name}")

    # --------------------------------------------------------------
    # Execu\u00e7\u00e3o principal
    # --------------------------------------------------------------
    def run(self) -> None:
        self.init_app()
        if not self.login():
            print("Falha no login")
            return
        companies = self.get_companies_list()
        if self.test_mode:
            companies = companies[:3]
            print("Modo teste ativo: processando apenas as 3 primeiras empresas")
        print(f"Processando {len(companies)} empresas")
        for company in companies:
            if not self.select_company(company):
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
