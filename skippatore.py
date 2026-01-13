# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import json
import os
import threading
import time
from PIL import ImageTk
import pyautogui
import pytesseract
from PIL import Image, ImageEnhance, ImageOps
import ctypes
import win32api
import win32con
import mss
from screeninfo import get_monitors
import sys

# Config
pytesseract.pytesseract.tesseract_cmd = r'#' #inserisci posizione del tesseract
CONFIG_FILE = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "aree_config.json")



# Global state
monitoraggio_attivo = False
pausa_event = threading.Event()
log_entries = []
thread_monitoraggi = []
checkbox_vars = {}
utente_corrente = None
label_counter = None
click_counter = 0


def mostra_scelta_utente():
    scelta = tk.Tk()
    scelta.protocol("WM_DELETE_WINDOW", lambda: sys.exit())
    scelta.title("Selezione Profilo")
    scelta.geometry("400x280")
    scelta.configure(bg="#36454F") # Dark charcoal background

    # --- Frame centrale orizzontale per logo e scelta ---
    frame_centrale = tk.Frame(scelta, bg="#36454F") # Dark charcoal background
    frame_centrale.pack(expand=True)

    # Logo a sinistra all'interno del frame centrale
    try:
        # Assicurati che il percorso e il nome del file corrispondano al tuo logo caricato
        logo_path = r"#" #inserisci posizione del tuo logo 
        # Aggiungo un controllo per l'esistenza del file per evitare errori
        if not os.path.exists(logo_path):
            # Prova con l'estensione .jpg se .png non viene trovato
            logo_path = r"#"  #inserisci posizione del tuo logo
            if not os.path.exists(logo_path):
                raise FileNotFoundError(f"Logo non trovato in {os.path.dirname(logo_path)}")

        logo_img = Image.open(logo_path).resize((200, 200), Image.Resampling.LANCZOS)
        logo_tk = ImageTk.PhotoImage(logo_img)
        label_logo = tk.Label(frame_centrale, image=logo_tk, bg="#36454F") # Dark charcoal background
        label_logo.image = logo_tk
        label_logo.pack(side="left", padx=(0, 15))
    except Exception as e:
        print(f"Errore caricamento logo: {e}")
        # Placeholder se il logo non si carica
        label_logo = tk.Label(frame_centrale, text="[LOGO]", font=("Helvetica", 20), bg="#36454F", fg="#D3D3D3") # Light grey text
        label_logo.pack(side="left", padx=(0, 15))


    # Frame a destra per i bottoni (in colonna)
    frame_bottoni = tk.Frame(frame_centrale, bg="#36454F") # Dark charcoal background
    frame_bottoni.pack(side="left")

    tk.Label(frame_bottoni, text="Scegli il profilo:", bg="#36454F", fg="#D3D3D3", font=("Helvetica", 12)).pack(pady=(0,10)) # Light grey text

    def mostra_campo_password():
        btn_admin.pack_forget()
        btn_user.pack_forget()
        label_pwd.pack(pady=(5, 2))
        entry_pwd.pack()
        btn_conferma.pack(pady=10)

    def accedi_user():
        global utente_corrente
        utente_corrente = "user"
        scelta.destroy()

    def conferma_admin():
        if entry_pwd.get() == "pro":
            global utente_corrente
            utente_corrente = "admin"
            scelta.destroy()
        else:
            messagebox.showerror("Errore", "Password errata.")

    btn_admin = tk.Button(frame_bottoni, text="👑 Admin", command=mostra_campo_password, bg="#4A8C8E", fg="white", width=20) # Muted Teal
    btn_admin.pack(pady=5)

    btn_user = tk.Button(frame_bottoni, text="👤 User", command=accedi_user, bg="#D2691E", fg="white", width=20) # Orange-brown
    btn_user.pack(pady=5)

    # Elementi password, visibili solo dopo Admin
    label_pwd = tk.Label(frame_bottoni, text="Password admin:", bg="#36454F", fg="#D3D3D3", font=("Helvetica", 11)) # Light grey text
    entry_pwd = tk.Entry(frame_bottoni, show="*", width=25, bg="#4F6272", fg="#F5F5DC", font=("Helvetica", 11)) # Darker muted blue-grey for input, off-white text
    btn_conferma = tk.Button(frame_bottoni, text="✅ Conferma", command=conferma_admin, bg="#4A8C8E", fg="white", width=20) # Muted Teal

    scelta.mainloop()

mostra_scelta_utente()

def salva_area(area, nome):
    aree = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            aree = json.load(f)
    aree[nome] = area
    with open(CONFIG_FILE, 'w') as f:
        json.dump(aree, f, indent=2)

def carica_lista_aree():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def rimuovi_area():
    aree = carica_lista_aree()
    if not aree:
        messagebox.showinfo("Info", "Nessuna area da rimuovere.")
        return
    nomi = list(aree.keys())
    nome_da_rimuovere = simpledialog.askstring("Rimuovi area", f"Inserisci il nome da rimuovere:\n{', '.join(nomi)}")
    if nome_da_rimuovere and nome_da_rimuovere in aree:
        del aree[nome_da_rimuovere]
        with open(CONFIG_FILE, 'w') as f:
            json.dump(aree, f, indent=2)
        aggiorna_lista_checkbox()
        aggiungi_log(f"Area '{nome_da_rimuovere}' rimossa.")
    else:
        messagebox.showerror("Errore", "Nome area non valido o non esistente.")

def click_invisibile(x, y):
    current_pos = win32api.GetCursorPos()
    ctypes.windll.user32.SetCursorPos(x, y)
    ctypes.windll.user32.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    ctypes.windll.user32.SetCursorPos(current_pos[0], current_pos[1])

def trova_scritta(schermata, target_text):
    data = pytesseract.image_to_data(schermata, output_type=pytesseract.Output.DICT)
    for i, parola in enumerate(data['text']):
        if target_text.lower() in parola.lower():
            return data['left'][i], data['top'][i]
    return None

def cattura_schermata(area_x, area_y, width, height):
    with mss.mss() as sct:
        monitor = {"top": area_y, "left": area_x, "width": width, "height": height}
        try:
            img = sct.grab(monitor)
            return Image.frombytes("RGB", img.size, img.rgb)
        except:
            return None

def aggiungi_log(msg):
    global click_counter, label_counter
    if utente_corrente == "user":
        if "Clic su" in msg:
            click_counter += 1
            if label_counter:
                label_counter.config(text=f"🔢 ELEMENTI SKIPPATI: {click_counter}")
        return  # Nessun log per gli user

    # Se è admin:
    timestamp = time.strftime("[%H:%M:%S]")
    testo = f"{timestamp} {msg}\n"
    log_entries.append(testo)
    if len(log_entries) > 50:
        log_entries.pop(0)
    log_box.config(state="normal")
    log_box.delete(1.0, tk.END)
    log_box.insert(tk.END, "".join(log_entries))
    log_box.config(state="disabled")
    log_box.see(tk.END)

def mostra_cornice_monitor(mon):
    cornice = tk.Toplevel()
    cornice.overrideredirect(True)
    cornice.attributes("-topmost", True)
    cornice.attributes("-alpha", 0.7)
    cornice.configure(bg="red")
    cornice.geometry(f"{mon.width}x{mon.height}+{mon.x}+{mon.y}")
    cornice.after(2000, cornice.destroy)
    cornice.lift()

def monitoraggio(area_rel, parola, mon):
    if "x_pct" in area_rel:
        area_x = int(mon.x + area_rel["x_pct"] * mon.width)
        area_y = int(mon.y + area_rel["y_pct"] * mon.height)
        width = int(area_rel["width_pct"] * mon.width)
        height = int(area_rel["height_pct"] * mon.height)
    else:
        area_x = mon.x + area_rel.get("x", 0)
        area_y = mon.y + area_rel.get("y", 0)
        width = area_rel.get("width", 100)
        height = area_rel.get("height", 100)
    trovato_precedente = False
    while monitoraggio_attivo:
        pausa_event.wait()
        screenshot = cattura_schermata(area_x, area_y, width, height)
        if screenshot is None:
            time.sleep(1); continue
        screenshot = ImageOps.grayscale(screenshot)
        screenshot = ImageEnhance.Contrast(screenshot).enhance(2)
        pos = trova_scritta(screenshot, parola)
        if pos and not trovato_precedente:
            globale = (pos[0] + area_x, pos[1] + area_y)
            click_invisibile(globale[0], globale[1])
            aggiungi_log(f"Clic su '{parola}' a {globale}")
            trovato_precedente = True
        elif not pos:
            trovato_precedente = False
        time.sleep(1)

def avvia_monitoraggio():
    global monitoraggio_attivo, thread_monitoraggi
    parola = entry_parola.get().strip()
    if not parola:
        return messagebox.showerror("Errore", "Inserisci una parola.")
    selezionate = [n for n,v in checkbox_vars.items() if v.get()]
    if not selezionate:
        return messagebox.showerror("Errore", "Seleziona almeno un'area.")
    idx = combo_monitor.current(); mons = get_monitors()
    if idx<0 or idx>=len(mons):
        return messagebox.showerror("Errore", "Seleziona un monitor valido.")
    mon = mons[idx]
    mostra_cornice_monitor(mon)
    monitoraggio_attivo = True
    pausa_event.set()
    thread_monitoraggi = []
    for nome in selezionate:
        area_rel = carica_lista_aree()[nome]
        t = threading.Thread(target=monitoraggio, args=(area_rel, parola, mon))
        t.daemon = True
        t.start()
        thread_monitoraggi.append(t)

def toggle_pausa():
    if not monitoraggio_attivo: return
    if pausa_event.is_set():
        pausa_event.clear()
        btn_pausa.config(text="⏯️ Riprendi")
    else:
        pausa_event.set()
        btn_pausa.config(text="⏸️ Pausa")

def aggiorna_lista_checkbox():
    for w in frame_checkbox.winfo_children():
        w.destroy()
    checkbox_vars.clear()
    for nome in carica_lista_aree():
        var = tk.BooleanVar()
        cb = tk.Checkbutton(frame_checkbox, text=nome, variable=var, bg="#36454F", fg="#D3D3D3", selectcolor="#4A8C8E") # Adjusted colors
        cb.pack(anchor="w")
        checkbox_vars[nome] = var

def popola_monitor():
    mons = get_monitors()
    combo_monitor['values'] = [f"Monitor {i+1} - {m.width}x{m.height} @ ({m.x},{m.y})" for i,m in enumerate(mons)]
    if mons: combo_monitor.set("Monitor 1")

def termina_programma():
    global monitoraggio_attivo
    monitoraggio_attivo = False
    pausa_event.set()
    for t in thread_monitoraggi:
        if t.is_alive():
            t.join(timeout=1)
    root.quit()

def lampeggia_luce():
    acceso = True
    while True:
        if monitoraggio_attivo and pausa_event.is_set():
            canvas_luce.itemconfig(luce, fill="#00ff99" if acceso else "#36454F") # Dark charcoal when off
            acceso = not acceso
        else:
            canvas_luce.itemconfig(luce, fill="#36454F") # Dark charcoal when off
        time.sleep(0.5)

# --- Variabili globali per selezione con tasto N ---
selezione_attiva = False
start_x = 0
start_y = 0
rect_id = None
overlay = None
canvas = None

def inizia_selezione_area_con_n():
    global selezione_attiva, start_x, start_y, rect_id, overlay, canvas

    mons = get_monitors()
    idx = combo_monitor.current()
    if idx < 0 or idx >= len(mons):
        messagebox.showerror("Errore", "Seleziona un monitor valido.")
        return
    mon = mons[idx]

    # Crea overlay trasparente sopra il monitor selezionato
    overlay = tk.Toplevel(root)
    overlay.geometry(f"{mon.width}x{mon.height}+{mon.x}+{mon.y}")
    overlay.attributes("-topmost", True)
    overlay.attributes("-alpha", 0.3)
    overlay.configure(bg='black')

    canvas = tk.Canvas(overlay, bg=None, highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    selezione_attiva = False
    rect_id = None

    def on_key_press(event):
        global selezione_attiva, start_x, start_y, rect_id
        if event.keysym.lower() == 'n' and not selezione_attiva:
            selezione_attiva = True
            # Punto iniziale = posizione mouse globale rispetto monitor (coordinate relative)
            x_root, y_root = overlay.winfo_pointerx(), overlay.winfo_pointery()
            start_x = x_root - mon.x
            start_y = y_root - mon.y
            if rect_id:
                canvas.delete(rect_id)
            rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='#00CC00', width=2) # Green outline

    def on_key_release(event):
        global selezione_attiva, rect_id
        if event.keysym.lower() == 'n' and selezione_attiva:
            selezione_attiva = False
            # Fine selezione: calcola area
            x1, y1, x2, y2 = canvas.coords(rect_id)
            x1, x2 = sorted([x1, x2])
            y1, y2 = sorted([y1, y2])
            larghezza = x2 - x1
            altezza = y2 - y1

            if larghezza < 5 or altezza < 5:
                messagebox.showwarning("Avviso", "Area troppo piccola, riprova.")
                overlay.destroy()
                return

            # Calcola percentuali rispetto monitor
            rel = {
                "x_pct": x1 / mon.width,
                "y_pct": y1 / mon.height,
                "width_pct": larghezza / mon.width,
                "height_pct": altezza / mon.height
            }

            nome = simpledialog.askstring("Nome area", "Dai un nome a questa area:")
            if nome:
                salva_area(rel, nome)
                aggiorna_lista_checkbox()
                aggiungi_log(f"Nuova area '{nome}' salvata.")
            overlay.destroy()

    def on_mouse_move(event):
        global selezione_attiva, rect_id
        if selezione_attiva and rect_id:
            # Aggiorna rettangolo mentre il tasto N è premuto e il mouse si muove
            x_root, y_root = overlay.winfo_pointerx(), overlay.winfo_pointery()
            x = x_root - mon.x
            y = y_root - mon.y
            canvas.coords(rect_id, start_x, start_y, x, y)

    overlay.bind("<KeyPress-n>", on_key_press)
    overlay.bind("<KeyRelease-n>", on_key_release)
    overlay.bind("<Motion>", on_mouse_move)

    # Per catturare i tasti, serve focus su overlay
    overlay.focus_set()

# === GUI Setup ===
root = tk.Tk()
root.title("OCR Monitor by Gregorio")
root.geometry("500x650")
root.configure(bg="#36454F") # Dark charcoal background

root.geometry("700x650")  # Allarga un po' per lasciare spazio al logo

# Frame principale a 2 colonne: logo a sinistra, contenuti a destra
main_frame = tk.Frame(root, bg="#36454F") # Dark charcoal background
main_frame.pack(fill="both", expand=True)

frame_sinistra = tk.Frame(main_frame, bg="#36454F", width=150) # Dark charcoal background
frame_sinistra.pack(side="left", fill="y")

frame_destra = tk.Frame(main_frame, bg="#36454F") # Dark charcoal background
frame_destra.pack(side="left", fill="both", expand=True)


# Carica e ridimensiona il logo
try:
    logo_path = r"#"  # inserisci la posizione della tua immagine 
    # Aggiungo un controllo per l'esistenza del file per evitare errori
    if not os.path.exists(logo_path):
        logo_path = r"#" #inserisci posizione sul tup pc del tuo logo 
        if not os.path.exists(logo_path):
            raise FileNotFoundError(f"Logo non trovato in {os.path.dirname(logo_path)}")
            
    logo_img = Image.open(logo_path).resize((250, 250), Image.Resampling.LANCZOS)
    logo_tk = ImageTk.PhotoImage(logo_img)

    # Crea un wrapper per centrare il logo verticalmente
    frame_logo_wrapper = tk.Frame(frame_sinistra, bg="#36454F") # Dark charcoal background
    frame_logo_wrapper.pack(expand=True)

    label_logo = tk.Label(frame_logo_wrapper, image=logo_tk, bg="#36454F") # Dark charcoal background
    label_logo.image = logo_tk
    label_logo.pack(padx=10, pady=10)

except Exception as e:
    print(f"Errore caricamento logo: {e}")
    # Placeholder se il logo non si carica
    frame_logo_wrapper = tk.Frame(frame_sinistra, bg="#36454F")
    frame_logo_wrapper.pack(expand=True)
    label_logo = tk.Label(frame_logo_wrapper, text="[LOGO]", font=("Helvetica", 24, "bold"), bg="#36454F", fg="#D3D3D3") # Light grey text
    label_logo.pack(padx=10, pady=10)


style = ttk.Style()
style.theme_use("clam")
# Aggiorna lo stile della Combobox per adattarsi al nuovo tema
style.configure("TCombobox", fieldbackground="#4F6272", background="#36454F", foreground="#F5F5DC", selectbackground="#4A8C8E", selectforeground="white")
style.map("TCombobox", fieldbackground=[("readonly", "#4F6272")])


tk.Label(frame_destra, text="🔤 Parola da cercare:", bg="#36454F", fg="#D3D3D3").pack(pady=5) # Light grey text
entry_parola = tk.Entry(frame_destra, width=30, bg="#4F6272", fg="#F5F5DC") # Darker muted blue-grey for input, off-white text
entry_parola.pack()

tk.Label(frame_destra, text="📦 Seleziona aree:", bg="#36454F", fg="#D3D3D3").pack(pady=5) # Light grey text
frame_checkbox = tk.Frame(frame_destra, bg="#36454F") # Dark charcoal background
frame_checkbox.pack()

tk.Label(frame_destra, text="🖥️ Seleziona monitor:", bg="#36454F", fg="#D3D3D3").pack(pady=5) # Light grey text
combo_monitor = ttk.Combobox(frame_destra, state="readonly")
combo_monitor.pack()

frame_luce = tk.Frame(root, bg="#36454F") # Dark charcoal background
frame_luce.pack(pady=10)
tk.Label(frame_luce, text="🟢 Stato:", bg="#36454F", fg="#D3D3D3").pack(side="left") # Light grey text
canvas_luce = tk.Canvas(frame_luce, width=20, height=20, highlightthickness=0, bg="#36454F") # Dark charcoal background
canvas_luce.pack(side="left")
luce = canvas_luce.create_oval(2, 2, 18, 18, fill="#36454F") # Starts dark charcoal when off

btn_avvia = tk.Button(frame_destra, text="▶️ Avvia Monitoraggio", command=avvia_monitoraggio, bg="#4A8C8E", fg="white") # Muted Teal
btn_avvia.pack(pady=5)

btn_pausa = tk.Button(frame_destra, text="⏯️ Pausa", command=toggle_pausa, bg="#D2691E", fg="white") # Orange-brown
btn_pausa.pack(pady=5)

if utente_corrente == "admin":
    btn_area = tk.Button(frame_destra, text="➕ Nuova Area", command=inizia_selezione_area_con_n, bg="#4A8C8E", fg="white") # Muted Teal
    btn_area.pack(pady=5)
    btn_rimuovi = tk.Button(frame_destra, text="🗑️ Rimuovi Area", command=rimuovi_area, bg="#B22222", fg="white") # Brick Red
    btn_rimuovi.pack(pady=5)

# Se è user, i bottoni sopra non vengono nemmeno creati

btn_esci = tk.Button(frame_destra, text="❌ Esci", command=termina_programma, bg="#B22222", fg="white") # Brick Red
btn_esci.pack(pady=5)

if utente_corrente == "admin":
    log_box = tk.Text(frame_destra, height=10, bg="#4F6272", fg="#F5F5DC", state="disabled") # Darker muted blue-grey for log, off-white text
    log_box.pack(fill="both", padx=10, pady=10, expand=True)
else:
    label_counter = tk.Label(frame_destra, text="🔢 ELEMENTI SKIPPATI: 0", bg="#36454F", fg="#D3D3D3", font=("Helvetica", 12)) # Light grey text
    label_counter.pack(pady=10)

popola_monitor()
aggiorna_lista_checkbox()

threading.Thread(target=lampeggia_luce, daemon=True).start()
root.protocol("WM_DELETE_WINDOW", termina_programma)
root.mainloop()
