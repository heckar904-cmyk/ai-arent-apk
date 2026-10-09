#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitch AI Linux — GUI приложение с кнопками, автообновлением
Запуск: python3 gui.py или двойной клик
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
import urllib.request

CONFIG_PATH = Path(__file__).parent / "config.json"
GITHUB_API = "https://api.github.com/repos/heckar904-cmyk/ai-arent-apk/commits?path=twitch-ai-linux&per_page=1"

class App:
    def __init__(self, root):
        self.root = root
        root.title("Twitch AI Linux — Установка в 1 клик")
        root.geometry("620x720")
        root.configure(bg="#0a0a0a")
        
        # Стили
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background="#0a0a0a", foreground="#ececec", font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=8)
        style.configure('Header.TLabel', font=('Segoe UI', 14, 'bold'))
        
        # Заголовок
        ttk.Label(root, text="🎙️ Twitch AI Linux v3", style='Header.TLabel').pack(pady=10)
        ttk.Label(root, text="Только голос + текст на стриме, не пишет в чат, реальный контроль Linux, 24/7", font=('Segoe UI', 9), foreground="#888").pack()
        
        # Статус
        self.status_var = tk.StringVar(value="🔍 Проверяю...")
        ttk.Label(root, textvariable=self.status_var, font=('Segoe UI', 10, 'bold'), foreground="#4ade80").pack(pady=5)
        
        # Поля
        frame = tk.Frame(root, bg="#0a0a0a")
        frame.pack(fill='x', padx=16, pady=10)
        
        tk.Label(frame, text="Twitch канал (без #):", bg="#0a0a0a", fg="#aaa", font=('Segoe UI', 9)).pack(anchor='w')
        self.channel_entry = tk.Entry(frame, font=('Segoe UI', 11), bg="#1a1a1a", fg="#fff", insertbackground="#fff", relief='flat', bd=0)
        self.channel_entry.pack(fill='x', pady=(2,8), ipady=6)
        
        tk.Label(frame, text="Twitch Token (oauth:... с twitchtokengenerator.com):", bg="#0a0a0a", fg="#aaa", font=('Segoe UI', 9)).pack(anchor='w')
        self.token_entry = tk.Entry(frame, font=('Segoe UI', 10), bg="#1a1a1a", fg="#fff", insertbackground="#fff", relief='flat', bd=0, show="*")
        self.token_entry.pack(fill='x', pady=(2,8), ipady=6)
        tk.Button(frame, text="Показать/Скрыть", command=self.toggle_token, bg="#1e1e1e", fg="#888", relief='flat', font=('Segoe UI', 8)).pack(anchor='e')
        
        tk.Label(frame, text="Groq API ключ (gsk_... с console.groq.com/keys):", bg="#0a0a0a", fg="#aaa", font=('Segoe UI', 9)).pack(anchor='w', pady=(8,0))
        self.groq_entry = tk.Entry(frame, font=('Segoe UI', 10), bg="#1a1a1a", fg="#fff", insertbackground="#fff", relief='flat', bd=0, show="*")
        self.groq_entry.pack(fill='x', pady=(2,8), ipady=6)
        tk.Button(frame, text="Показать/Скрыть", command=self.toggle_groq, bg="#1e1e1e", fg="#888", relief='flat', font=('Segoe UI', 8)).pack(anchor='e')
        
        # Кнопки
        btn_frame = tk.Frame(root, bg="#0a0a0a")
        btn_frame.pack(fill='x', padx=16, pady=10)
        
        tk.Button(btn_frame, text="💾 Сохранить ключи", command=self.save_config, bg="#fff", fg="#000", font=('Segoe UI', 10, 'bold'), relief='flat', padx=10, pady=8).pack(side='left', fill='x', expand=True, padx=(0,4))
        tk.Button(btn_frame, text="🔍 Проверить", command=self.check_install, bg="#1e1e1e", fg="#fff", relief='flat', padx=10, pady=8).pack(side='left', fill='x', expand=True, padx=(4,0))
        
        btn_frame2 = tk.Frame(root, bg="#0a0a0a")
        btn_frame2.pack(fill='x', padx=16, pady=(0,10))
        
        self.start_btn = tk.Button(btn_frame2, text="▶️ ЗАПУСТИТЬ ИИ", command=self.start_bot, bg="#4ade80", fg="#000", font=('Segoe UI', 12, 'bold'), relief='flat', padx=10, pady=10)
        self.start_btn.pack(side='left', fill='x', expand=True, padx=(0,4))
        
        tk.Button(btn_frame2, text="⏹️ Стоп", command=self.stop_bot, bg="#ff4d6d", fg="#fff", font=('Segoe UI', 10, 'bold'), relief='flat', padx=10, pady=10).pack(side='left', padx=(4,0))
        
        btn_frame3 = tk.Frame(root, bg="#0a0a0a")
        btn_frame3.pack(fill='x', padx=16, pady=(0,10))
        
        tk.Button(btn_frame3, text="🔄 Проверить обновление", command=self.check_update, bg="#1e1e1e", fg="#fff", relief='flat', padx=8, pady=6).pack(side='left', fill='x', expand=True, padx=(0,2))
        tk.Button(btn_frame3, text="⬇️ Автообновление", command=self.auto_update, bg="#00f0ff", fg="#000", font=('Segoe UI', 9, 'bold'), relief='flat', padx=8, pady=6).pack(side='left', fill='x', expand=True, padx=(2,2))
        tk.Button(btn_frame3, text="🖥️ Оверлей OBS", command=self.open_overlay, bg="#1e1e1e", fg="#fff", relief='flat', padx=8, pady=6).pack(side='left', fill='x', expand=True, padx=(2,0))
        
        btn_frame4 = tk.Frame(root, bg="#0a0a0a")
        btn_frame4.pack(fill='x', padx=16, pady=(0,10))
        tk.Button(btn_frame4, text="⚙️ Установить 24/7 (не отваливается)", command=self.install_service, bg="#a855f7", fg="#fff", relief='flat', padx=8, pady=6).pack(fill='x')
        
        # Лог
        tk.Label(root, text="Лог:", bg="#0a0a0a", fg="#888", font=('Segoe UI', 9)).pack(anchor='w', padx=16)
        self.log_text = scrolledtext.ScrolledText(root, height=12, bg="#111", fg="#8a92b8", font=('Consolas', 9), relief='flat', bd=0)
        self.log_text.pack(fill='both', expand=True, padx=16, pady=(2,10))
        
        # Загрузка конфига
        self.load_config()
        self.check_install()
        
        # Процесс бота
        self.bot_process = None
    
    def toggle_token(self):
        self.token_entry.config(show="" if self.token_entry.cget('show')=="*" else "*")
    def toggle_groq(self):
        self.groq_entry.config(show="" if self.groq_entry.cget('show')=="*" else "*")
    
    def log(self, msg):
        self.log_text.insert('end', f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.log_text.see('end')
        print(msg)
    
    def load_config(self):
        try:
            if CONFIG_PATH.exists():
                data = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
                self.channel_entry.insert(0, data.get('twitch_channel',''))
                self.token_entry.insert(0, data.get('twitch_token',''))
                self.groq_entry.insert(0, data.get('groq_api_key',''))
                self.log("✅ Config загружен")
        except Exception as e:
            self.log(f"Config load fail: {e}")
    
    def save_config(self):
        try:
            # Читаем существующий чтобы не потерять другие поля
            existing = {}
            if CONFIG_PATH.exists():
                try:
                    existing = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
                except:
                    pass
            
            existing['twitch_channel'] = self.channel_entry.get().strip().replace('#','')
            existing['twitch_token'] = self.token_entry.get().strip()
            existing['groq_api_key'] = self.groq_entry.get().strip()
            # Дефолты для v3 как ты хотел — только голос + оверлей
            existing.setdefault('groq_model','llama-3.3-70b-versatile')
            existing.setdefault('write_to_chat', False)
            existing.setdefault('show_overlay', True)
            existing.setdefault('overlay_port', 8080)
            existing.setdefault('allow_exec', True)
            existing.setdefault('allow_screen', True)
            existing.setdefault('reply_all', True)
            
            CONFIG_PATH.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
            self.log("✅ Ключи сохранены в config.json")
            messagebox.showinfo("Сохранено", "Ключи сохранены! Теперь жми ЗАПУСТИТЬ ИИ")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def check_install(self):
        def run():
            self.status_var.set("🔍 Проверяю...")
            checks = []
            # Папка
            if Path.home().joinpath("twitch-ai-linux-v3").exists() or Path.home().joinpath("twitch-ai-linux").exists():
                checks.append("✅ Папка найдена")
            else:
                checks.append("❌ Папка не найдена")
            
            # venv
            if (Path(__file__).parent / "venv").exists():
                checks.append("✅ venv есть")
            else:
                checks.append("❌ venv нет — нажми УСТАНОВИТЬ")
            
            # config
            if CONFIG_PATH.exists():
                try:
                    d=json.loads(CONFIG_PATH.read_text())
                    if d.get('twitch_channel') and d.get('groq_api_key'):
                        checks.append(f"✅ Config: канал {d.get('twitch_channel')}")
                    else:
                        checks.append("⚠️ Config пустой — вставь ключи")
                except:
                    checks.append("❌ Config битый")
            else:
                checks.append("❌ config.json нет")
            
            # espeak
            try:
                subprocess.run(["which","espeak"], capture_output=True, check=True)
                checks.append("✅ espeak установлен (голос)")
            except:
                checks.append("❌ espeak нет")
            
            # systemd
            try:
                result = subprocess.run(["systemctl","is-active","twitch-ai"], capture_output=True, text=True)
                if result.returncode==0:
                    checks.append("🟢 24/7 сервис работает")
                else:
                    checks.append("🔴 24/7 сервис остановлен")
            except:
                checks.append("❓ systemd не проверен")
            
            self.status_var.set(" | ".join(checks[:2]))
            for c in checks:
                self.log(c)
        
        threading.Thread(target=run, daemon=True).start()
    
    def start_bot(self):
        if self.bot_process and self.bot_process.poll() is None:
            messagebox.showinfo("Уже запущен", "Бот уже работает!")
            return
        self.save_config()
        def run():
            try:
                self.log("🚀 Запускаю бота...")
                self.start_btn.config(text="⏳ Запускается...", state='disabled')
                venv_python = Path(__file__).parent / "venv" / "bin" / "python"
                if not venv_python.exists():
                    venv_python = Path(sys.executable)
                self.bot_process = subprocess.Popen(
                    [str(venv_python), "main.py"],
                    cwd=str(Path(__file__).parent),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                self.log("✅ Процесс запущен, читаю лог...")
                for line in self.bot_process.stdout:
                    self.log(line.strip())
            except Exception as e:
                self.log(f"❌ Ошибка запуска: {e}")
                messagebox.showerror("Ошибка", str(e))
            finally:
                self.start_btn.config(text="▶️ ЗАПУСТИТЬ ИИ", state='normal')
        
        threading.Thread(target=run, daemon=True).start()
    
    def stop_bot(self):
        try:
            if self.bot_process:
                self.bot_process.terminate()
                self.log("⏹️ Бот остановлен")
            subprocess.run(["pkill","-f","twitch-ai-linux.*main.py"], capture_output=True)
            subprocess.run(["systemctl","stop","twitch-ai"], capture_output=True)
            self.log("⏹️ Все процессы остановлены")
        except Exception as e:
            self.log(f"Stop fail: {e}")
    
    def check_update(self):
        def run():
            try:
                self.log("🔍 Проверяю обновления с GitHub...")
                req = urllib.request.Request(GITHUB_API, headers={'User-Agent':'TwitchAI'})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = json.loads(r.read().decode())
                    last = data[0]['commit']['message'][:80]
                    date = data[0]['commit']['author']['date'][:10]
                    self.log(f"Последнее обновление GitHub: {date} — {last}")
                    messagebox.showinfo("Обновление", f"Последнее: {date}\n{last}\n\nНажми Автообновление чтобы обновить")
            except Exception as e:
                self.log(f"Check update fail: {e}")
                messagebox.showerror("Ошибка", f"Не смог проверить: {e}")
        threading.Thread(target=run, daemon=True).start()
    
    def auto_update(self):
        def run():
            try:
                self.log("⬇️ Автообновление — качаю с GitHub...")
                # Сохраняем config
                backup = None
                if CONFIG_PATH.exists():
                    backup = CONFIG_PATH.read_text(encoding='utf-8')
                    Path("/tmp/config.json.bak").write_text(backup, encoding='utf-8')
                    self.log("  ✅ Бэкап config.json")
                
                # Качаем новые файлы
                base = "https://raw.githubusercontent.com/heckar904-cmyk/ai-arent-apk/main/twitch-ai-linux/"
                files = ["main.py","config.json.example","requirements.txt","overlay.html","gui.py","install.sh"]
                for fname in files:
                    try:
                        url = base + fname
                        self.log(f"  Качаю {fname}...")
                        urllib.request.urlretrieve(url, str(Path(__file__).parent / fname))
                    except Exception as e:
                        self.log(f"  ⚠️ {fname} fail: {e}")
                
                # Восстанавливаем config
                if backup:
                    # Не перезаписываем, а мерджим — оставляем ключи
                    try:
                        old = json.loads(backup)
                        new_path = Path(__file__).parent / "config.json"
                        if new_path.exists():
                            new_data = json.loads(new_path.read_text(encoding='utf-8'))
                            # Сохраняем ключи из старого
                            for k in ['twitch_channel','twitch_token','groq_api_key','owner_username']:
                                if k in old:
                                    new_data[k] = old[k]
                            new_path.write_text(json.dumps(new_data, ensure_ascii=False, indent=2), encoding='utf-8')
                        else:
                            CONFIG_PATH.write_text(backup, encoding='utf-8')
                        self.log("  ✅ Ключи восстановлены")
                    except:
                        Path("/tmp/config.json.bak").write_text(backup, encoding='utf-8')
                        self.log("  ✅ Бэкап в /tmp/config.json.bak")
                
                self.log("✅ Обновлено! Перезапусти приложение")
                messagebox.showinfo("Готово", "Обновлено! Ключи сохранены. Перезапусти GUI и нажми ЗАПУСТИТЬ ИИ")
                self.load_config()
            except Exception as e:
                self.log(f"Auto update fail: {e}")
                messagebox.showerror("Ошибка", str(e))
        
        threading.Thread(target=run, daemon=True).start()
    
    def open_overlay(self):
        url = "http://localhost:8080/overlay.html"
        self.log(f"🖥️ Открываю оверлей: {url}")
        try:
            webbrowser.open(url)
        except:
            self.log(f"Открой вручную в браузере: {url} или в OBS как Browser Source")
    
    def install_service(self):
        def run():
            try:
                self.log("⚙️ Устанавливаю 24/7 сервис...")
                service_src = Path(__file__).parent / "twitch-ai.service"
                if not service_src.exists():
                    self.log("❌ twitch-ai.service не найден")
                    return
                # Копируем
                subprocess.run(["sudo","cp",str(service_src),"/etc/systemd/system/twitch-ai.service"], check=True)
                subprocess.run(["sudo","systemctl","daemon-reload"], check=True)
                subprocess.run(["sudo","systemctl","enable","--now","twitch-ai"], check=True)
                self.log("✅ 24/7 сервис установлен и запущен!")
                self.log("   journalctl -u twitch-ai -f — логи")
            except subprocess.CalledProcessError as e:
                self.log(f"❌ Нужен sudo пароль: {e}")
                messagebox.showinfo("Нужен пароль", "В терминале введи:\nsudo cp twitch-ai.service /etc/systemd/system/\nsudo systemctl enable --now twitch-ai")
            except Exception as e:
                self.log(f"Service install fail: {e}")
        
        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
