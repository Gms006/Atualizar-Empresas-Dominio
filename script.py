import csv
import json
import os
import re
import time
from datetime import datetime
from typing import Dict, List
import base64
import pyautogui
import pyperclip
import requests
from dotenv import load_dotenv
from pywinauto import Application, keyboard


# caminho padrão do atalho do Domínio Registro
APP_SHORTCUT = r"C:\Contabil\contabil.exe /registro"

class DominioAutomation:
    """Automação simplificada do Domínio utilizando pywinauto."""

    def __init__(self) -> None:
        load_dotenv()
        self.password = os.getenv("DOMINIO_PASSWORD", "")
        self.captcha_key = os.getenv("CAPTCHA_2CAPTCHA_KEY", "")

        self.test_mode = os.getenv("TEST_MODE", "false").lower() in ("1", "true", "yes")
        self.app: Application | None = None
        self.main_window = None
        self.log_json: List[Dict] = []

    # ------------------------------------------------------------------
    # Inicialização e login
    # ------------------------------------------------------------------
    def init_app(self) -> None:
        """Abre o aplicativo Domínio a partir do atalho."""
        self.app = Application(backend="uia").start(APP_SHORTCUT)
        self.main_window = self.app.window(title_re=".*Domínio.*")
        self.main_window.wait("visible", timeout=60)

    def login(self) -> bool:
        """Realiza login básico enviando a senha e pressionando Alt+O."""
        try:
            if not self.main_window:
                return False

            self.main_window.set_focus()
            # garante que o campo de senha esteja visível antes de digitar
            try:
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
        except Exception as exc:  # pragma: no cover - interação de UI
            print(f"Erro no login: {exc}")
            return False

    # ------------------------------------------------------------------
    # Processamento das empresas
    # ------------------------------------------------------------------
    def get_companies_list(self) -> List[str]:
        """Obtém a lista de empresas através da janela de troca de empresas."""
        try:
            keyboard.send_keys("{F8}")
            time.sleep(2)

            list_box = self.main_window.child_window(auto_id="Empresas")
            companies = [item.window_text() for item in list_box.children()]
            keyboard.send_keys("{ESC}")
            return companies
        except Exception as exc:  # pragma: no cover - interação de UI
            print(f"Erro ao obter empresas: {exc}")
            return []

    def select_company(self, name: str) -> bool:
        """Seleciona uma empresa na lista."""
        try:
            keyboard.send_keys("{F8}")
            time.sleep(1)

            list_box = self.main_window.child_window(auto_id="Empresas")
            list_box.select(name)
            keyboard.send_keys("%o")  # confirmar
            time.sleep(1)
            return True
        except Exception as exc:  # pragma: no cover - interação de UI
            print(f"Erro ao selecionar empresa {name}: {exc}")
            keyboard.send_keys("{ESC}")
            return False

    # ------------------------------------------------------------------
    # Atualização dos dados de cada empresa
    # ------------------------------------------------------------------
    def update_company_data(self, company: str) -> Dict:
        """Fluxo de atualização simplificado para uma única empresa."""
        result: Dict[str, object] = {
            "empresa": company,
            "cnpj": "",
            "status": "Erro",
            "alteracoes": {},
            "socios_dominio": [],
            "socios_receita": [],
            "divergencia_societaria": False,
            "observacoes": "",
        }

        try:
            keyboard.send_keys("%d")  # abre aba Dados (Alt+D)
            time.sleep(2)

            cnpj_edit = self.main_window.child_window(auto_id="CNPJ")
            cnpj_raw = cnpj_edit.get_value()  # type: ignore[attr-defined]
            result["cnpj"] = re.sub(r"[^0-9]", "", cnpj_raw)

            # chamar atualização pelo menu
            keyboard.send_keys("%u")  # Alt+U - Atualizar Cadastro
            time.sleep(2)

            if not self.solve_captcha():
                result["status"] = "Erro - Captcha não resolvido"
                keyboard.send_keys("{ESC}")
                return result

            keyboard.send_keys("%i")  # Alt+I - Importar
            time.sleep(3)

            self.verify_shareholders(result)
            self.save_changes()

            result["status"] = "Atualizada com sucesso"
            keyboard.send_keys("{ESC}")
            time.sleep(1)
            return result
        except Exception as exc:  # pragma: no cover - interação de UI
            result["status"] = f"Erro: {exc}"
            result["observacoes"] = str(exc)
            keyboard.send_keys("{ESC}")
            return result

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def solve_captcha(self) -> bool:
        """Exemplo de resolução de captcha utilizando 2Captcha."""
        try:
            # captura de tela do captcha
            screenshot = pyautogui.screenshot(region=(100, 100, 300, 300))
            screenshot.save("captcha.png")

            with open("captcha.png", "rb") as img_file:
                b64_img = base64.b64encode(img_file.read())

            data = {
                "key": self.captcha_key,
                "method": "base64",
                "body": b64_img,
                "json": 1,
            }
            response = requests.post("http://2captcha.com/in.php", data=data)
            result = response.json()
            if result.get("status") != 1:
                return False
            captcha_id = result["request"]

            for _ in range(30):
                time.sleep(5)
                check = requests.get(
                    f"http://2captcha.com/res.php?key={self.captcha_key}&action=get&id={captcha_id}&json=1"
                ).json()
                if check.get("status") == 1:
                    pyperclip.copy(check["request"])
                    keyboard.send_keys("^v")
                    return True
                if check.get("request") != "CAPCHA_NOT_READY":
                    break
            return False
        except Exception:
            return False

    def verify_shareholders(self, result: Dict) -> None:
        """Exemplo mínimo de consulta aos sócios na ReceitaWS."""
        if not result.get("cnpj"):
            return
        try:
            time.sleep(30)
            url = f"https://receitaws.com.br/v1/cnpj/{result['cnpj']}"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                result["socios_receita"] = [s["nome"].upper() for s in data.get("qsa", [])]
        except Exception as exc:  # pragma: no cover
            result["observacoes"] += f" Erro ReceitaWS: {exc}"

    def save_changes(self) -> None:
        """Dispara o atalho para gravar as alterações."""
        keyboard.send_keys("%g")
        time.sleep(1)

    # ------------------------------------------------------------------
    # Registro de logs
    # ------------------------------------------------------------------
    def save_logs(self) -> None:
        """Salva os resultados em arquivos CSV e JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_name = f"log_atualizacao_dominio_{timestamp}.csv"
        json_name = f"log_detalhado_{timestamp}.json"

        with open(csv_name, "w", newline="", encoding="utf-8") as csv_file:
            fieldnames = ["Empresa", "CNPJ", "Status", "Alterações", "Observações"]
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for entry in self.log_json:
                writer.writerow(
                    {
                        "Empresa": entry["empresa"],
                        "CNPJ": entry["cnpj"],
                        "Status": entry["status"],
                        "Alterações": len(entry["alteracoes"]),
                        "Observações": entry["observacoes"],
                    }
                )

        with open(json_name, "w", encoding="utf-8") as json_file:
            json.dump(self.log_json, json_file, indent=2, ensure_ascii=False)

        print(f"Logs salvos em {csv_name} e {json_name}")

    # ------------------------------------------------------------------
    # Execução principal
    # ------------------------------------------------------------------
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
            result = self.update_company_data(company)
            self.log_json.append(result)

        self.save_logs()

        if self.app:
            self.app.kill()


def main() -> None:
    automation = DominioAutomation()
    automation.run()


if __name__ == "__main__":
    main()
