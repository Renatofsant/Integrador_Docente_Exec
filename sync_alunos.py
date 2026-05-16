import psycopg2
import psycopg2.extras
import customtkinter as ctk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image
import time
import sys
import os
import webbrowser

# --- CONFIGURAÇÕES NUVEM ---
DB_URI = "postgresql://postgres.upjxocjacpsdtdcigqfe:Schrodinger48Rfs2321@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

# --- FUNÇÃO DE CAMINHO PARA RECURSOS (VITAL PARA O .EXE) ---
def recurso_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, para rodar no PyCharm ou no .EXE """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# =================================================================
# COMPONENTES DE INTERFACE (U.I. PREMIUM)
# =================================================================

class JanelaDialogo(ctk.CTkToplevel):
    def __init__(self, titulo, prompt, placeholder=""):
        super().__init__()
        self.title(titulo);
        self.geometry("380x220");
        self.attributes("-topmost", True)
        self.resultado = None
        ctk.CTkLabel(self, text=prompt, font=("Roboto", 14), wraplength=300).pack(pady=20)
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder, width=280)
        self.entry.pack(pady=5);
        self.entry.focus()
        ctk.CTkButton(self, text="Confirmar", command=self.confirmar, fg_color="#3b82f6").pack(pady=20)
        self.wait_window()

    def confirmar(self): self.resultado = self.entry.get(); self.destroy()


class CardInstrucao(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Ação Requerida");
        self.geometry("400x380");
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a");
        self.grab_set()
        ctk.CTkLabel(self, text="⚡ PRÓXIMO PASSO", font=("Urbanist", 20, "bold"), text_color="#3b82f6").pack(
            pady=(30, 20))
        instrucoes = "1. Faça Login Manual no Portal\n2. Resolva o Captcha\n3. Entre na tela da Turma\n\n👉 Clique abaixo quando a lista\nde alunos estiver visível."
        ctk.CTkLabel(self, text=instrucoes, font=("Roboto", 14), justify="left", text_color="#e0e0e0").pack(pady=10,
                                                                                                            padx=40)
        ctk.CTkButton(self, text="ESTOU NA TELA!", command=self.destroy, fg_color="#3b82f6", height=50).pack(pady=30,
                                                                                                             padx=40,
                                                                                                             fill="x")
        self.wait_window()


class CardFinalizacao(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Sucesso");
        self.geometry("400x320");
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a");
        self.grab_set();
        self.resultado = False
        ctk.CTkLabel(self, text="🎉", font=("Roboto", 50)).pack(pady=(20, 5))
        ctk.CTkLabel(self, text="MISSÃO CUMPRIDA!", font=("Urbanist", 18, "bold"), text_color="#10b981").pack()
        ctk.CTkLabel(self, text="Deseja lançar outra turma?", font=("Roboto", 13), text_color="gray").pack(pady=10)
        btn_f = ctk.CTkFrame(self, fg_color="transparent");
        btn_f.pack(pady=20)
        ctk.CTkButton(btn_f, text="SIM, OUTRA", command=self.sim, width=120, fg_color="#3b82f6").pack(side="left",
                                                                                                      padx=5)
        ctk.CTkButton(btn_f, text="SAIR", command=self.nao, width=120, fg_color="#4b5563").pack(side="left", padx=5)
        self.wait_window()

    def sim(self): self.resultado = True; self.destroy()

    def nao(self): self.resultado = False; self.destroy()


# =================================================================
# MOTOR PRINCIPAL (PAINEL SGI COM LOGIN)
# =================================================================

class PainelSGI(ctk.CTk):
    def __init__(self, usuario):
        super().__init__()
        self.usuario = usuario
        self.title(f"Integrador Docente - {self.usuario}")
        self.geometry("500x520");
        ctk.set_appearance_mode("dark");
        self.attributes("-topmost", True)

        ctk.CTkLabel(self, text="INTEGRADOR DOCENTE", font=("Urbanist", 24, "bold"), text_color="#3b82f6").pack(
            pady=(30, 20))

        self.btn_iniciar = ctk.CTkButton(self, text="🚀 INICIAR LANÇAMENTO TOTAL", command=self.executar_fluxo,
                                         height=60, width=380, font=("Roboto", 16, "bold"))
        self.btn_iniciar.pack(pady=10)

        # Frame de Ferramentas (Sincronia + Relatório)
        self.f_tools = ctk.CTkFrame(self, fg_color="transparent");
        self.f_tools.pack(pady=20)

        self.btn_sinc = ctk.CTkButton(self.f_tools, text="🔄 Sincronizar Alunos", command=self.sincronizar_apenas_alunos,
                                      fg_color="#10b981", width=185, height=45)
        self.btn_sinc.pack(side="left", padx=5)

        self.btn_rel = ctk.CTkButton(self.f_tools, text="📊 Gerar Relatório", command=self.gerar_relatorio_final,
                                     fg_color="#8b5cf6", width=185, height=45)
        self.btn_rel.pack(side="left", padx=5)

        self.status = ctk.CTkLabel(self, text=f"Professor logado: {self.usuario}", font=("Roboto", 11),
                                   text_color="gray")
        self.status.pack(side="bottom", pady=20)

    def sincronizar_apenas_alunos(self):
        driver = None;
        conn = None
        try:
            self.withdraw()
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
            driver.get("https://docenteonline.educacao.rj.gov.br/NovoDocente/")
            CardInstrucao(self)
            t = JanelaDialogo("Sincronia", "Qual turma deseja atualizar?", "Ex: 2005").resultado
            if not t: return

            script_extracao = "let r=[]; document.querySelectorAll('tr').forEach(tr=>{let d=tr.querySelectorAll('td'); if(d.length>=2){let n=d[0].innerText.trim(); let s=d[1]?d[1].innerText.trim():''; if(n.length>5 && !n.includes('Aulas')) r.push({nome:n, status:(s==='Matriculado'||s==='')?'Ativo':'Inativo'});}}); return r;"
            alunos_portal = driver.execute_script(script_extracao)
            conn = psycopg2.connect(DB_URI);
            cur = conn.cursor()
            for a in alunos_portal:
                cur.execute(
                    "INSERT INTO alunos (escola_id, nome_completo, turma, status) VALUES (2, %s, %s, %s) ON CONFLICT (escola_id, nome_completo, turma) DO UPDATE SET status = EXCLUDED.status",
                    (a['nome'], t, a['status']))
            conn.commit();
            messagebox.showinfo("Sucesso", f"Relação da turma {t} atualizada!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))
        finally:
            if driver: driver.quit()
            if conn: conn.close()
            self.deiconify()

    def gerar_relatorio_final(self):
        t = JanelaDialogo("Relatório", "Turma para o relatório:", "Ex: 2005").resultado
        if not t: return
        try:
            conn = psycopg2.connect(DB_URI);
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("""SELECT a.nome_completo, n.av1, n.av2, n.av3, n.recuperacao, n.faltas FROM alunos a 
                           JOIN notas_bimestre n ON a.id = n.aluno_id WHERE a.turma = %s AND n.professor_username = %s""",
                        (t, self.usuario))
            dados = cur.fetchall();
            conn.close()
            if not dados: messagebox.showwarning("Aviso", "Nenhuma nota encontrada."); return

            html = f"<html><head><style>body{{font-family:sans-serif; padding:20px; background:#f4f7f6;}} .card{{background:white; border-radius:8px; padding:20px; box-shadow:0 2px 5px rgba(0,0,0,0.1);}} table{{width:100%; border-collapse:collapse; margin-top:20px;}} th{{background:#3b82f6; color:white; padding:12px; text-align:left;}} td{{padding:10px; border-bottom:1px solid #eee;}}</style></head><body>"
            html += f"<div class='card'><h2>📊 Relatório de Lançamento - Turma {t}</h2><p>Professor: <b>{self.usuario}</b></p><table><tr><th>Aluno</th><th>AV1</th><th>AV2</th><th>AV3</th><th>Rec</th><th>Faltas</th></tr>"
            for r in dados: html += f"<tr><td>{r['nome_completo']}</td><td>{r['av1'] or '-'}</td><td>{r['av2'] or '-'}</td><td>{r['av3'] or '-'}</td><td>{r['recuperacao'] or '-'}</td><td>{r['faltas'] or '0'}</td></tr>"
            html += "</table><p style='font-size:12px; color:gray; margin-top:20px;'>Gerado por Integrador Docente</p></div></body></html>"

            path = os.path.abspath(f"Relatorio_{t}.html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            webbrowser.open(path);
            messagebox.showinfo("Sucesso", "Relatório aberto!")
        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def executar_fluxo(self):
        conn = None
        driver = None
        try:
            self.withdraw()
            opt = Options()
            opt.add_experimental_option("detach", True)
            opt.add_argument("--start-maximized")
            
            # 1. INICIALIZA O NAVEGADOR UMA ÚNICA VEZ
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opt)
            driver.get("https://docenteonline.educacao.rj.gov.br/NovoDocente/")
            
            # 2. PEDE O LOGIN MANUAL APENAS UMA VEZ ANTES DE ENTRAR NO LOOP DE TURMAS
            CardInstrucao(self)
            
            conn = psycopg2.connect(DB_URI)
            cursor = conn.cursor()

            # 3. ENTRA NO LOOP APENAS PARA ALTERNAR AS TURMAS
            while True:
                turma_alvo = JanelaDialogo("Identificação", "Entre na nova turma no portal e digite o número dela aqui:", "Ex: 2005").resultado
                if not turma_alvo: 
                    break  # Se fechar ou clicar em cancelar, sai do robô
                    
                trimestre_alvo = JanelaDialogo("Trimestre", "Trimestre (1, 2 ou 3):", "1").resultado or "1"

                # Script JavaScript de extração na pauta ativa
                script_extracao = "let r=[]; document.querySelectorAll('tr').forEach(tr=>{let d=tr.querySelectorAll('td'); if(d.length>=2){let n=d[0].innerText.trim(); let s=d[1]?d[1].innerText.trim():''; if(n.length>5 && !n.includes('Aulas')) r.push({n:n, s:(s==='Matriculado'||s==='')?'Ativo':'Inativo'});}}); return r;"
                alunos_portal = driver.execute_script(script_extracao)

                for aluno in alunos_portal:
                    nome, status = aluno['n'], aluno['s']
                    try:
                        cursor.execute(
                            "INSERT INTO alunos (escola_id, nome_completo, turma, status) VALUES (2, %s, %s, %s) ON CONFLICT (escola_id, nome_completo, turma) DO UPDATE SET status = EXCLUDED.status RETURNING id",
                            (nome, turma_alvo, status))
                        res = cursor.fetchone()
                        conn.commit()
                        
                        if res and status == "Ativo":
                            aluno_id = res[0]
                            cursor.execute(
                                "SELECT av1, av2, av3, recuperacao, faltas FROM notas_bimestre WHERE aluno_id = %s AND trimestre = %s AND professor_username = %s",
                                (aluno_id, int(trimestre_alvo), self.usuario))
                            nota_data = cursor.fetchone()

                            if nota_data:
                                v1, v2, v3, vr, vf = nota_data
                                soma = float(v1 or 0) + float(v2 or 0) + float(v3 or 0)
                                linha = driver.find_element(By.XPATH, f"//tr[td[contains(text(), '{nome}')]]")
                                c_n = linha.find_element(By.CSS_SELECTOR, "input[name*='.NotaProva']")
                                c_f = linha.find_element(By.CSS_SELECTOR, "input[name*='.Faltas']")

                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", c_n)
                                time.sleep(0.1)
                                c_n.click()
                                c_n.clear()
                                c_n.send_keys(str(round(soma, 1)).replace('.', ','))

                                if soma < 5.0:
                                    try:
                                        try:
                                            WebDriverWait(driver, 2).until(EC.alert_is_present())
                                            driver.switch_to.alert.accept()
                                        except:
                                            pass
                                        driver.execute_script(
                                            "let tr=arguments[0]; let cb=tr.querySelector(\"input[type='checkbox'][name*='.PossuiRecuperacao']\"); if(cb && !cb.checked) cb.click();",
                                            linha)
                                        time.sleep(1.2)
                                        c_r = linha.find_element(By.CSS_SELECTOR, "input.inputnotarecuperacao")
                                        driver.execute_script("arguments[0].value = arguments[1];", c_r,
                                                              str(round(float(vr or 0), 1)).replace('.', ','))
                                        driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", c_r)
                                    except:
                                        pass
                                c_f.click()
                                c_f.clear()
                                c_f.send_keys(str(int(vf or 0)))
                    except Exception as e:
                        conn.rollback()

                # Pergunta se quer ir para outra turma mantendo o mesmo navegador aberto
                if not CardFinalizacao(self).resultado: 
                    break
                    
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro no Fluxo", str(e))
            self.deiconify()
        finally:
            if conn: 
                conn.close()
            if driver:
                driver.quit() # Só fecha o navegador quando você decidir sair de vez do robô


# =================================================================
# TELA DE LOGIN
# =================================================================

class TelaLogin(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🛡️ Acesso Integrador Docente")
        self.geometry("420x560")
        self.eval('tk::PlaceWindow . center')
        self.attributes("-topmost", True)
        self.configure(fg_color="#1a1a1a")
        self.usuario_logado = None

        self.grid_columnconfigure(0, weight=1)

        try:
            # --- USANDO RECURSO_PATH PARA LOCALIZAR A LOGO ---
            img_path = recurso_path("logo_robot.png")
            img_original = Image.open(img_path)
            self.logo_image = ctk.CTkImage(light_image=img_original,
                                           dark_image=img_original,
                                           size=(90, 90))

            self.logo_label = ctk.CTkLabel(self, text="", image=self.logo_image)
            self.logo_label.grid(row=0, column=0, pady=(40, 10), sticky="ew")

        except Exception as e:
            print(f"Erro ao carregar imagem: {e}")
            self.logo_label = ctk.CTkLabel(self, text="[LOGO]", font=("Roboto", 14), text_color="gray")
            self.logo_label.grid(row=0, column=0, pady=(40, 10))

        ctk.CTkLabel(self, text="LOGIN DO DOCENTE", font=("Urbanist", 22, "bold"), text_color="#3b82f6").grid(row=1,
                                                                                                              column=0,
                                                                                                              pady=5,
                                                                                                              sticky="ew")

        self.u = ctk.CTkEntry(self, placeholder_text="Usuário", width=300, height=45)
        self.u.grid(row=2, column=0, pady=10)

        self.p = ctk.CTkEntry(self, placeholder_text="Senha", show="*", width=300, height=45)
        self.p.grid(row=3, column=0, pady=10)

        ctk.CTkButton(self, text="ACESSAR SISTEMA", command=self.logar, fg_color="#3b82f6",
                      height=50, width=300, font=("Roboto", 14, "bold")).grid(row=4, column=0, pady=20)

        t = "Ao acessar, você concorda com os Termos de Uso\ne com a Política de Privacidade do sistema."
        ctk.CTkLabel(self, text=t, font=("Roboto", 11, "bold"), text_color="#cbd5e1", justify="center").grid(row=5,
                                                                                                             column=0,
                                                                                                             pady=10,
                                                                                                             sticky="ew")

        self.msg = ctk.CTkLabel(self, text="", text_color="#ef4444")
        self.msg.grid(row=6, column=0)

    def logar(self):
        user = self.u.get().lower().strip();
        senha = self.p.get()
        try:
            conn = psycopg2.connect(DB_URI);
            cur = conn.cursor()
            cur.execute("SELECT username FROM usuarios_integrador WHERE username=%s AND senha=%s AND ativo=TRUE",
                        (user, senha))
            res = cur.fetchone();
            conn.close()
            if res:
                self.usuario_logado = res[0]; self.destroy()
            else:
                self.msg.configure(text="Acesso negado ou conta suspensa.")
        except:
            self.msg.configure(text="Erro de conexão.")


if __name__ == "__main__":
    login = TelaLogin();
    login.mainloop()
    if login.usuario_logado:
        PainelSGI(usuario=login.usuario_logado).mainloop()
