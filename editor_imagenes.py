import os
import io
import smtplib
from email.message import EmailMessage
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageOps, ImageFilter, ImageEnhance
import pygame

ui = tk.Tk()
ui.geometry("1024x650")
ui.configure(background="#252850")
tk.Wm.wm_title(ui, "Editor de imágenes")

CLR_MARCO = "#1A1C38"

# ---------------------------------------------------------------
# ESTADO GLOBAL
# ---------------------------------------------------------------
img = None
img_ant = None
flt = "Original"
ruta_gd = None
gd_ok = False

hist, hist_r = [], []

rc_act = False
rc_sel = None
rc_i = rc_d = rc_s = rc_f = 0
rc_escala = 1.0
rc_img = rc_dark = None
rc_id = None
rc_ln_i = rc_ln_d = rc_ln_s = rc_ln_f = None
rc_h_ni = rc_h_nd = rc_h_si = rc_h_sd = None
rc_dx = rc_dy = 0

br = ct = sat = 50

# ---------------------------------------------------------------
# RECURSOS: ÍCONOS
# ---------------------------------------------------------------
DIR_APP = os.path.dirname(os.path.abspath(__file__))
errs = []

def colorear_icono(im, color):
    alpha = im.split()[-1]
    g = ImageOps.grayscale(im.convert("RGB"))
    c = ImageOps.colorize(g, black="#000000", white=color)
    c.putalpha(alpha)
    return c

def cargar_ico(nombre, tam=20):
    try:
        im = Image.open(os.path.join(DIR_APP, nombre)).convert("RGBA")
        im.thumbnail((tam, tam))
        return im
    except Exception as e:
        errs.append(f"{nombre}: {e}")
        return None

def a_tk(im):
    return ImageTk.PhotoImage(im) if im else None

_flecha = cargar_ico("flecha.png", 22)
ico_der = a_tk(_flecha)
ico_izq = a_tk(ImageOps.mirror(_flecha)) if _flecha else None

_guardar = cargar_ico("guardar.png")
ico_guardar = a_tk(_guardar)
ico_guardar_ok = a_tk(colorear_icono(_guardar, "#2ecc71")) if _guardar else None
ico_guardarcomo = a_tk(cargar_ico("guardarcomo.png"))

ico_tijeras = a_tk(cargar_ico("tijeras.jpg"))
ico_listo = a_tk(cargar_ico("tilde_verde.png"))
ico_cancelar_rec = a_tk(cargar_ico("cruz.png"))
ico_deshacer = a_tk(cargar_ico("desahcer.png", 32))
ico_rehacer = a_tk(cargar_ico("rehacer.png", 32))
ico_enviar = a_tk(cargar_ico("enviargmail.png", 30))

# ---------------------------------------------------------------
# RECURSOS: SONIDO DE TRANSICIÓN
# ---------------------------------------------------------------
snd = None
try:
    pygame.mixer.init()
    snd = pygame.mixer.Sound(os.path.join(DIR_APP, "tom.mp3"))
except Exception as e:
    errs.append(f"tom.mp3: {e}")

def reproducir_sonido():
    if snd is not None:
        snd.play()

# ---------------------------------------------------------------
# FILTROS Y AJUSTES
# ---------------------------------------------------------------
def aplicar_filtro(im, nom):
    if nom == "Original":
        return im
    if nom == "Desenfoque":
        return im.filter(ImageFilter.GaussianBlur(radius=4))
    if nom == "Nitidez":
        return im.filter(ImageFilter.SHARPEN)
    if nom == "Detección de bordes":
        g = ImageOps.grayscale(im)
        return g.filter(ImageFilter.FIND_EDGES).convert("RGB")
    if nom == "Negativo":
        return ImageOps.invert(im)
    if nom == "Sepia":
        g = ImageOps.grayscale(im)
        return ImageOps.colorize(g, black="#3a2410", white="#d9c7a3")
    return im

def aplicar_ajustes(im):

    im = ImageEnhance.Brightness(im).enhance(br / 50)
    im = ImageEnhance.Contrast(im).enhance(ct / 50)
    im = ImageEnhance.Color(im).enhance(sat / 50)
    return im

# ---------------------------------------------------------------
# MOSTRAR IMAGEN / VISTA PREVIA
# ---------------------------------------------------------------
def mostrar_imagen(bak=False):
    if img is None:
        return
    frm_img.update_idletasks()
    aw = max(frm_img.winfo_width() - 10, 100)
    ah = max(frm_img.winfo_height() - 10, 100)

    copia = img_ant.copy() if (bak and img_ant is not None) else aplicar_ajustes(aplicar_filtro(img.copy(), flt))
    copia.thumbnail((aw, ah))
    tkimg = ImageTk.PhotoImage(copia)
    lbl_img.config(image=tkimg)
    lbl_img.image = tkimg

def ver_antes(e):
    mostrar_imagen(bak=True)

def ver_despues(e):
    mostrar_imagen(bak=False)

# ---------------------------------------------------------------
# HISTORIAL (DESHACER / REHACER)
# ---------------------------------------------------------------
def guardar_estado():
    global hist
    if img is not None:
        hist.append(img.copy())
        hist_r.clear()

def deshacer(e=None):
    global img, img_ant
    if not hist:
        return
    if img is not None:
        hist_r.append(img.copy())
    img = hist.pop()
    img_ant = img.copy()
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()

def rehacer(e=None):
    global img, img_ant
    if not hist_r:
        return
    if img is not None:
        hist.append(img.copy())
    img = hist_r.pop()
    img_ant = img.copy()
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()

# ---------------------------------------------------------------
# CALLBACKS: SLIDERS Y COMBOBOX DE FILTRO
# ---------------------------------------------------------------
def cambiar_ajuste(tipo):
    def cb(valor):
        global br, ct, sat
        n = int(valor)
        if tipo == "br":
            br = n
        elif tipo == "ct":
            ct = n
        else:
            sat = n
        mostrar_imagen()
        marcar_cambio()
    return cb

def cambiar_filtro(e):
    global flt
    flt = cmb_filtro.get()
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()

# ---------------------------------------------------------------
# GUARDADO
# ---------------------------------------------------------------
def act_icono():
    if ico_guardar is None:
        menu_g.config(text="✓ " if gd_ok else "💾 ")
        return
    icono = ico_guardar_ok if gd_ok else ico_guardar
    menu_g.config(image=icono)
    menu_g.image = icono

def marcar_cambio():
    global gd_ok
    gd_ok = False
    act_icono()

def guardar_img():
    global gd_ok
    if img is None:
        messagebox.showwarning("Atención", "Primero cargá una imagen.")
        return
    if not ruta_gd:
        guardar_como()
        return
    try:
        final = aplicar_ajustes(aplicar_filtro(img, flt))
        if ruta_gd.lower().endswith((".jpg", ".jpeg")):
            final = final.convert("RGB")
        final.save(ruta_gd)
    except Exception as e:
        messagebox.showerror("Error al guardar", f"No se pudo guardar el archivo.\nDetalle: {e}")
        return
    gd_ok = True
    act_icono()

def guardar_como():
    global ruta_gd, gd_ok
    if img is None:
        messagebox.showwarning("Atención", "Primero cargá una imagen.")
        return
    ruta = filedialog.asksaveasfilename(
        title="Guardar como", defaultextension=".png",
        filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")]
    )
    if not ruta:
        return
    try:
        final = aplicar_ajustes(aplicar_filtro(img, flt))
        if ruta.lower().endswith((".jpg", ".jpeg")):
            final = final.convert("RGB")
        final.save(ruta)
    except Exception as e:
        messagebox.showerror("Error al guardar", f"No se pudo guardar el archivo.\nDetalle: {e}")
        return
    ruta_gd = ruta
    gd_ok = True
    act_icono()
    messagebox.showinfo("Guardado", "La imagen se guardó correctamente.")

# ---------------------------------------------------------------
# CARGAR IMAGEN
# ---------------------------------------------------------------
def cargar_img():
    global img, img_ant, ruta_gd, gd_ok

    ruta = filedialog.askopenfilename(
        title="Seleccionar imagen",
        filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp"), ("Todos los archivos", "*.*")]
    )
    if not ruta:
        return

    if not ruta.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
        messagebox.showerror("Formato no soportado", "El archivo debe ser JPG, PNG o BMP.")
        return
    try:
        nueva = Image.open(ruta)
        nueva.verify()
        nueva = Image.open(ruta).convert("RGB")
    except Exception as e:
        messagebox.showerror("Error", "No se puede abrir la imagen")
        return

    img = nueva
    img_ant = nueva.copy()
    hist.clear()
    hist_r.clear()

    lbl_nombre.config(text=ruta.split("/")[-1])
    ruta_gd = ruta
    gd_ok = True
    act_icono()

    mostrar_imagen()
    reproducir_sonido()

# ---------------------------------------------------------------
# ROTAR
# ---------------------------------------------------------------
def rot_izq():
    global img, img_ant
    if img is None:
        return
    guardar_estado()
    img_ant = img.copy()
    img = img.rotate(90, expand=True)
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()

def rot_der():
    global img, img_ant
    if img is None:
        return
    guardar_estado()
    img_ant = img.copy()
    img = img.rotate(-90, expand=True)
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()

def rot_180():
    global img, img_ant
    if img is None:
        return
    guardar_estado()
    img_ant = img.copy()
    img = img.rotate(180, expand=True)
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()

# ---------------------------------------------------------------
# RECORTAR (estilo Editor de fotos de Windows)
# ---------------------------------------------------------------
def rec_iniciar():
    global rc_act, rc_escala, rc_i, rc_d, rc_s, rc_f
    global rc_ln_i, rc_ln_d, rc_ln_s, rc_ln_f
    global rc_h_ni, rc_h_nd, rc_h_si, rc_h_sd
    global rc_img, rc_dark, rc_id

    if img is None:
        messagebox.showwarning("Atención", "Primero cargá una imagen.")
        return

    rc_act = True
    frm_img.update_idletasks()
    aw = max(frm_img.winfo_width() - 10, 100)
    ah = max(frm_img.winfo_height() - 10, 100)
    im = aplicar_ajustes(aplicar_filtro(img.copy(), flt))
    im.thumbnail((aw, ah))

    rc_escala = img.width / im.width
    rc_img = im
    rc_dark = ImageEnhance.Brightness(im).enhance(0.35)

    lbl_img.pack_forget()
    cv_img.config(width=im.width, height=im.height)
    cv_img.pack(expand=True)
    cv_img.delete("all")
    rc_id = cv_img.create_image(0, 0, anchor="nw", tags="fondo")

    mx, my = im.width * 0.1, im.height * 0.1
    rc_i, rc_d = mx, im.width - mx
    rc_s, rc_f = my, im.height - my

    rc_ln_i = cv_img.create_line(0, 0, 0, 0, fill="#ffffff", width=2, tags="izq")
    rc_ln_d = cv_img.create_line(0, 0, 0, 0, fill="#ffffff", width=2, tags="der")
    rc_ln_s = cv_img.create_line(0, 0, 0, 0, fill="#ffffff", width=2, tags="sup")
    rc_ln_f = cv_img.create_line(0, 0, 0, 0, fill="#ffffff", width=2, tags="inf")
    rc_h_ni = cv_img.create_rectangle(0, 0, 0, 0, fill="#ffffff", outline="", tags="ni")
    rc_h_nd = cv_img.create_rectangle(0, 0, 0, 0, fill="#ffffff", outline="", tags="nd")
    rc_h_si = cv_img.create_rectangle(0, 0, 0, 0, fill="#ffffff", outline="", tags="si")
    rc_h_sd = cv_img.create_rectangle(0, 0, 0, 0, fill="#ffffff", outline="", tags="sd")
    rec_redibujar()

    for p in ("izq", "der", "sup", "inf", "ni", "nd", "si", "sd"):
        cv_img.tag_bind(p, "<ButtonPress-1>", lambda e, p=p: rec_arrastre_ini(p))
    cv_img.tag_bind("fondo", "<ButtonPress-1>", rec_mover_ini)
    cv_img.bind("<B1-Motion>", rec_arrastrar)
    cv_img.bind("<ButtonRelease-1>", lambda e: rec_arrastre_fin())

    btn_recortar.config(state="disabled")
    btn_listo.pack(fill="x", padx=15, pady=4)
    btn_cancelar_rec.pack(fill="x", padx=15, pady=(0, 4))
    reproducir_sonido()

def rec_redibujar():
    caja = (int(rc_i), int(rc_s), int(rc_d), int(rc_f))
    compuesta = rc_dark.copy()
    compuesta.paste(rc_img.crop(caja), (caja[0], caja[1]))

    tkimg = ImageTk.PhotoImage(compuesta)
    cv_img.itemconfig(rc_id, image=tkimg)
    cv_img.image = tkimg

    cv_img.coords(rc_ln_i, rc_i, rc_s, rc_i, rc_f)
    cv_img.coords(rc_ln_d, rc_d, rc_s, rc_d, rc_f)
    cv_img.coords(rc_ln_s, rc_i, rc_s, rc_d, rc_s)
    cv_img.coords(rc_ln_f, rc_i, rc_f, rc_d, rc_f)

    m = 5
    cv_img.coords(rc_h_ni, rc_i - m, rc_s - m, rc_i + m, rc_s + m)
    cv_img.coords(rc_h_nd, rc_d - m, rc_s - m, rc_d + m, rc_s + m)
    cv_img.coords(rc_h_si, rc_i - m, rc_f - m, rc_i + m, rc_f + m)
    cv_img.coords(rc_h_sd, rc_d - m, rc_f - m, rc_d + m, rc_f + m)

    for it in (rc_ln_i, rc_ln_d, rc_ln_s, rc_ln_f, rc_h_ni, rc_h_nd, rc_h_si, rc_h_sd):
        cv_img.tag_raise(it)

def rec_arrastre_ini(p):
    global rc_sel
    rc_sel = p

def rec_mover_ini(e):
    global rc_sel, rc_dx, rc_dy
    if rc_i < e.x < rc_d and rc_s < e.y < rc_f:
        rc_sel = "mover"
        rc_dx = e.x - rc_i
        rc_dy = e.y - rc_s

def rec_arrastre_fin():
    global rc_sel
    rc_sel = None

def rec_arrastrar(e):
    global rc_i, rc_d, rc_s, rc_f
    if rc_sel is None:
        return

    an, al = rc_img.width, rc_img.height
    mm = 20

    if rc_sel == "izq":
        rc_i = min(max(e.x, 0), rc_d - mm)
    elif rc_sel == "der":
        rc_d = max(min(e.x, an), rc_i + mm)
    elif rc_sel == "sup":
        rc_s = min(max(e.y, 0), rc_f - mm)
    elif rc_sel == "inf":
        rc_f = max(min(e.y, al), rc_s + mm)
    elif rc_sel == "ni":
        rc_i = min(max(e.x, 0), rc_d - mm)
        rc_s = min(max(e.y, 0), rc_f - mm)
    elif rc_sel == "nd":
        rc_d = max(min(e.x, an), rc_i + mm)
        rc_s = min(max(e.y, 0), rc_f - mm)
    elif rc_sel == "si":
        rc_i = min(max(e.x, 0), rc_d - mm)
        rc_f = max(min(e.y, al), rc_s + mm)
    elif rc_sel == "sd":
        rc_d = max(min(e.x, an), rc_i + mm)
        rc_f = max(min(e.y, al), rc_s + mm)
    elif rc_sel == "mover":
        caja_w, caja_h = rc_d - rc_i, rc_f - rc_s
        ni = min(max(e.x - rc_dx, 0), an - caja_w)
        ns = min(max(e.y - rc_dy, 0), al - caja_h)
        rc_i, rc_d = ni, ni + caja_w
        rc_s, rc_f = ns, ns + caja_h

    rec_redibujar()

def rec_finalizar():
    global rc_act, rc_sel
    rc_act = False
    rc_sel = None
    cv_img.pack_forget()
    lbl_img.pack(fill="both", expand=True, padx=2, pady=2)
    btn_listo.pack_forget()
    btn_cancelar_rec.pack_forget()
    btn_recortar.config(state="normal")

def rec_confirmar():
    global img, img_ant
    if img is None:
        return
    guardar_estado()
    img_ant = img.copy()
    img = img.crop((int(rc_i * rc_escala), int(rc_s * rc_escala), int(rc_d * rc_escala), int(rc_f * rc_escala)))
    rec_finalizar()
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()

def rec_cancelar():
    rec_finalizar()
    mostrar_imagen()
    reproducir_sonido()

# ---------------------------------------------------------------
# ENVIAR POR GMAIL
# ---------------------------------------------------------------
def enviar_gmail(remit, clave, dest, asunto, im):
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = asunto, remit, dest
    msg.set_content("Te comparto esta imagen editada.")

    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="JPEG")
    msg.add_attachment(buf.getvalue(), maintype="image", subtype="jpeg", filename="imagen.jpg")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(remit, clave)
        srv.send_message(msg)

def abrir_envio():
    if img is None:
        messagebox.showwarning("Atención", "Primero cargá una imagen.")
        return

    im_envio = aplicar_ajustes(aplicar_filtro(img.copy(), flt))

    vent = tk.Toplevel(ui)
    vent.title("Enviar por Gmail")
    vent.configure(background="#252850")
    vent.geometry("340x520")
    vent.resizable(False, False)
    vent.grab_set()

    e_remit = campo(vent, "Tu Gmail")
    e_clave = campo(vent, "Contraseña de aplicación", oculto=True)
    e_dest = campo(vent, "Gmail destinatario")
    e_asunto = campo(vent, "Asunto")
    e_asunto.insert(0, "Imagen editada")

    tk.Label(vent, text="Se enviará:", background="#252850", foreground="#aaaaaa",
             font=("Segoe UI", 8)).pack(anchor="w", padx=20, pady=(10, 2))

    prev = im_envio.copy()
    prev.thumbnail((180, 140))
    prev_tk = ImageTk.PhotoImage(prev)
    lbl_prev = tk.Label(vent, image=prev_tk, background="#1A1C38",
                         highlightbackground=CLR_MARCO, highlightthickness=2)
    lbl_prev.image = prev_tk
    lbl_prev.pack(pady=(0, 15))

    def enviar():
        r, c, d = e_remit.get().strip(), e_clave.get().strip(), e_dest.get().strip()
        a = e_asunto.get().strip() or "Imagen editada"
        if not r or not c or not d:
            messagebox.showerror("Faltan datos", "Completá tu Gmail, la clave y el destinatario.")
            return
        btn_env.config(state="disabled", text="Enviando...")
        vent.update_idletasks()
        try:
            enviar_gmail(r, c, d, a, im_envio)
        except Exception as e:
            messagebox.showerror("Error al enviar", f"No se pudo enviar.\nDetalle: {e}")
            btn_env.config(state="normal", text="Enviar")
            return
        messagebox.showinfo("Enviado", "¡La imagen se envió correctamente!")
        vent.destroy()

    btn_env = tk.Button(vent, text="Enviar", relief="flat", background="#2ecc71",
                         foreground="white", command=enviar, padx=15, pady=6)
    btn_env.pack(pady=(0, 6))
    tk.Button(vent, text="Cancelar", relief="flat", background="#ffffff",
              command=vent.destroy, padx=15, pady=6).pack()

# ---------------------------------------------------------------
# AYUDANTES DE INTERFAZ (para no repetir estilo botón a botón)
# ---------------------------------------------------------------
def crear_boton(parent, texto, cmd, icono=None, bg="#ffffff"):
    kw = dict(text=texto, relief="flat", command=cmd, background=bg,
              anchor="w", padx=10, pady=4, font=("Segoe UI", 9))
    if icono:
        kw["image"], kw["compound"] = icono, "left"
    return tk.Button(parent, **kw)

def crear_slider(parent, texto, cmd, pb=0):
    tk.Label(parent, text=texto, background="#1A1C38", foreground="white",
             font=("Segoe UI", 8)).pack(anchor="w", padx=10, pady=(2, 0))
    s = tk.Scale(parent, from_=0, to=100, orient="horizontal",
                 background="#1A1C38", foreground="white", highlightthickness=0,
                 troughcolor="#ffffff", command=cmd)
    s.set(50)
    s.pack(fill="x", padx=10, pady=(0, pb))
    return s

def boton_top(icono, cmd, x):
    b = tk.Button(ui, image=icono, relief="flat", background="#252850",
                  activebackground="#1A1C38", bd=0, command=cmd, cursor="hand2")
    b.place(x=x, y=8)
    return b

def campo(parent, texto, oculto=False):
    tk.Label(parent, text=texto, background="#252850", foreground="white",
             font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=(10, 0))
    e = tk.Entry(parent, show="•" if oculto else "")
    e.pack(fill="x", padx=20, pady=(2, 0))
    return e

# ---------------------------------------------------------------
# LAYOUT
# ---------------------------------------------------------------
menu_g = tk.Menubutton(ui, relief="flat", background="#252850", activebackground="#1A1C38", bd=0)
menu_g.place(x=15, y=10)

menu_d = tk.Menu(menu_g, tearoff=0)
menu_d.add_command(label=" Guardar", image=ico_guardar, compound="left", command=guardar_img)
menu_d.add_command(label=" Guardar como...", image=ico_guardarcomo, compound="left", command=guardar_como)
menu_d.i1, menu_d.i2 = ico_guardar, ico_guardarcomo
menu_g.config(menu=menu_d)
act_icono()

btn_gmail = boton_top(ico_enviar, abrir_envio, 50)
btn_desh = boton_top(ico_deshacer, deshacer, 95)
btn_reh = boton_top(ico_rehacer, rehacer, 140)

ui.bind("<Control-z>", deshacer)
ui.bind("<Control-y>", rehacer)

if errs:
    msg = "No se pudieron cargar estos archivos:\n\n" + "\n".join(f"• {e}" for e in errs)
    msg += "\n\nRevisá que estén guardados en la MISMA carpeta que el script."
    messagebox.showwarning("Faltan archivos", msg)

btn_cargar = tk.Button(ui, text="Cargar imagen", command=cargar_img)
btn_cargar.pack(pady=5)

lbl_nombre = tk.Label(ui, text="Sin imagen cargada", background="#252850",
                       foreground="white", font=("Segoe UI", 9))
lbl_nombre.pack(pady=(2, 5))

frm_img = tk.Frame(ui, background="#1A1C38", highlightbackground=CLR_MARCO, highlightthickness=3)
frm_img.pack(side="left", fill="both", expand=True, padx=15, pady=5)
frm_img.pack_propagate(False)

lbl_img = tk.Label(frm_img, background="#1A1C38")
lbl_img.pack(fill="both", expand=True, padx=2, pady=2)

cv_img = tk.Canvas(frm_img, background="#1A1C38", highlightthickness=0)

frm_menu = tk.Frame(ui, background="#1A1C38", highlightbackground=CLR_MARCO,
                     highlightthickness=3, width=200)
frm_menu.pack(side="right", fill="y", padx=(0, 15), pady=5)
frm_menu.pack_propagate(False)

btn_preview = tk.Button(frm_menu, text="👁 Vista Previa (Mantener)", relief="flat",
                         background="#4e54c8", foreground="white", anchor="w",
                         padx=10, pady=4, font=("Segoe UI", 9))
btn_preview.pack(fill="x", padx=10, pady=(10, 4))
btn_preview.bind("<ButtonPress-1>", ver_antes)
btn_preview.bind("<ButtonRelease-1>", ver_despues)

crear_boton(frm_menu, " Voltear izquierda", rot_izq, ico_izq).pack(fill="x", padx=10, pady=4)
crear_boton(frm_menu, " Voltear derecha", rot_der, ico_der).pack(fill="x", padx=10, pady=4)
crear_boton(frm_menu, "Voltear 180°", rot_180).pack(fill="x", padx=10, pady=4)

btn_recortar = crear_boton(frm_menu, " Recortar", rec_iniciar, ico_tijeras)
btn_recortar.pack(fill="x", padx=10, pady=4)
btn_listo = crear_boton(frm_menu, " Listo", rec_confirmar, ico_listo)
btn_cancelar_rec = crear_boton(frm_menu, " Cancelar", rec_cancelar, ico_cancelar_rec)

tk.Label(frm_menu, text="Filtro", background="#1A1C38", foreground="white",
          font=("Segoe UI", 9)).pack(anchor="w", padx=10, pady=(6, 2))

cmb_filtro = ttk.Combobox(frm_menu, state="readonly",
                           values=["Original", "Desenfoque", "Nitidez",
                                   "Detección de bordes", "Negativo", "Sepia"])
cmb_filtro.set("Original")
cmb_filtro.pack(fill="x", padx=10, pady=(0, 4))
cmb_filtro.bind("<<ComboboxSelected>>", cambiar_filtro)

crear_slider(frm_menu, "Brillo", cambiar_ajuste("br"))
crear_slider(frm_menu, "Contraste", cambiar_ajuste("ct"))
crear_slider(frm_menu, "Saturación", cambiar_ajuste("sat"), pb=10)

ui.mainloop()
