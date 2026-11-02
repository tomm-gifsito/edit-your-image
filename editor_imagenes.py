import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageOps, ImageFilter, ImageEnhance
import pygame  # para reproducir el sonido de transición (pip install pygame)

app = tk.Tk()

# ancho y alto
app.geometry("1024x650")
app.configure(background="#252850")
tk.Wm.wm_title(app, "editor de imagenes")

COLOR_MARCO = "#1A1C38"

fotoO = None  # acá se guarda la imagen PIL "vigente" (con rotaciones/recortes aplicados)
foto_respaldo = None  # guarda la versión anterior para la vista previa "Antes / Después"
filtro_actual = "Original"  # nombre del filtro seleccionado en el combobox
ruta_guardado = None  # dónde se guardó/cargó por última vez (para "Guardar" sin preguntar)
guardada = False  # True si lo que se ve en pantalla ya está reflejado en el disco

# --- Historial para Deshacer / Rehacer ---
historial = []
historial_futuro = []

# --- Estado del modo "recortar" ---
modo_recorte = False
arrastrando = None  # qué borde se está moviendo ahora: "izq", "der", "sup", "inf" o None
recorte_izq = recorte_der = recorte_sup = recorte_inf = 0  # coordenadas del recuadro (en pantalla)
recorte_escala = 1.0  # cuánto más grande es la imagen real respecto a la que se ve en pantalla
img_recorte_tk = None  # referencia a la imagen mostrada durante el recorte
linea_izq = linea_der = linea_sup = linea_inf = None  # los 4 bordes dibujados en el canvas
handle_ni = handle_nd = handle_si = handle_sd = None  # las 4 manijas de las esquinas
img_clara_recorte = None  # imagen tal cual se ve (sin oscurecer)
img_oscura_recorte = None  # misma imagen, oscurecida (para lo que queda AFUERA del recuadro)
id_imagen_canvas = None  # id del item de imagen dentro del canvas, para poder reemplazarlo
offset_mover_x = 0
offset_mover_y = 0  # distancia entre el click y la esquina sup-izq, para mover sin "saltos"

# --- Sliders de ajuste: van de 0 a 100, con 50 = valor normal (sin cambios) ---
valor_brillo = 50
valor_contraste = 50
valor_saturacion = 50


# ---------------------------------------------------------------
# Cargar los íconos
# ---------------------------------------------------------------
RUTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
errores_recursos = []  # acá anotamos qué archivos (íconos o audio) no se pudieron cargar

ruta_flecha = os.path.join(RUTA_SCRIPT, "flecha.png")
icono_derecha = None
icono_izquierda = None

try:
    img_flecha = Image.open(ruta_flecha).convert("RGBA")
    img_flecha.thumbnail((22, 22))
    icono_derecha = ImageTk.PhotoImage(img_flecha)
    img_flecha_izq = ImageOps.mirror(img_flecha)
    icono_izquierda = ImageTk.PhotoImage(img_flecha_izq)
except Exception as e:
    errores_recursos.append(f"flecha.png: {e}")


def colorear_icono(imagen_rgba, color_hex):
    alpha = imagen_rgba.split()[-1]
    gris = ImageOps.grayscale(imagen_rgba.convert("RGB"))
    coloreado = ImageOps.colorize(gris, black="#000000", white=color_hex)
    coloreado.putalpha(alpha)
    return coloreado


ruta_guardar_icono = os.path.join(RUTA_SCRIPT, "guardar.png")
ruta_guardarcomo_icono = os.path.join(RUTA_SCRIPT, "guardarcomo.png")
icono_guardar = None
icono_guardar_verde = None
icono_guardarcomo = None

try:
    img_guardar = Image.open(ruta_guardar_icono).convert("RGBA")
    img_guardar.thumbnail((20, 20))
    icono_guardar = ImageTk.PhotoImage(img_guardar)
    icono_guardar_verde = ImageTk.PhotoImage(colorear_icono(img_guardar, "#2ecc71"))

    img_guardarcomo = Image.open(ruta_guardarcomo_icono).convert("RGBA")
    img_guardarcomo.thumbnail((20, 20))
    icono_guardarcomo = ImageTk.PhotoImage(img_guardarcomo)
except Exception as e:
    errores_recursos.append(f"guardar.png / guardarcomo.png: {e}")


ruta_tijeras = os.path.join(RUTA_SCRIPT, "tijeras.jpg")
ruta_listo = os.path.join(RUTA_SCRIPT, "tilde_verde.png")
ruta_cancelar_recorte = os.path.join(RUTA_SCRIPT, "cruz.png")
ruta_deshacer = os.path.join(RUTA_SCRIPT, "desahcer.png")
ruta_rehacer = os.path.join(RUTA_SCRIPT, "rehacer.png")

icono_tijeras = None
icono_listo = None
icono_cancelar_recorte = None
icono_deshacer = None
icono_rehacer = None

try:
    img_tijeras = Image.open(ruta_tijeras).convert("RGBA")
    img_tijeras.thumbnail((20, 20))
    icono_tijeras = ImageTk.PhotoImage(img_tijeras)
except Exception as e:
    errores_recursos.append(f"tijeras.jpg: {e}")

try:
    img_listo = Image.open(ruta_listo).convert("RGBA")
    img_listo.thumbnail((20, 20))
    icono_listo = ImageTk.PhotoImage(img_listo)
except Exception as e:
    errores_recursos.append(f"tilde_verde.png: {e}")

try:
    img_cancelar_recorte = Image.open(ruta_cancelar_recorte).convert("RGBA")
    img_cancelar_recorte.thumbnail((20, 20))
    icono_cancelar_recorte = ImageTk.PhotoImage(img_cancelar_recorte)
except Exception as e:
    errores_recursos.append(f"cruz.png: {e}")

# Tamaño grande (32x32) para que se vean bien claros
try:
    img_desh = Image.open(ruta_deshacer).convert("RGBA")
    img_desh.thumbnail((32, 32))
    icono_deshacer = ImageTk.PhotoImage(img_desh)
except Exception as e:
    errores_recursos.append(f"desahcer.png: {e}")

try:
    img_reh = Image.open(ruta_rehacer).convert("RGBA")
    img_reh.thumbnail((32, 32))
    icono_rehacer = ImageTk.PhotoImage(img_reh)
except Exception as e:
    errores_recursos.append(f"rehacer.png: {e}")


# ---------------------------------------------------------------
# Sonido de transición
# ---------------------------------------------------------------
ruta_sonido = os.path.join(RUTA_SCRIPT, "tom.mp3")
sonido_transicion = None

try:
    pygame.mixer.init()
    sonido_transicion = pygame.mixer.Sound(ruta_sonido)
except Exception as e:
    errores_recursos.append(f"tom.mp3: {e}")


def reproducir_sonido():
    if sonido_transicion is not None:
        sonido_transicion.play()


def aplicar_filtro(imagen, nombre):
    if nombre == "Original":
        return imagen
    if nombre == "Desenfoque":
        return imagen.filter(ImageFilter.GaussianBlur(radius=4))
    if nombre == "Nitidez":
        return imagen.filter(ImageFilter.SHARPEN)
    if nombre == "Detección de bordes":
        gris = ImageOps.grayscale(imagen)
        return gris.filter(ImageFilter.FIND_EDGES).convert("RGB")
    if nombre == "Negativo":
        return ImageOps.invert(imagen)
    if nombre == "Sepia":
        gris = ImageOps.grayscale(imagen)
        return ImageOps.colorize(gris, black="#3a2410", white="#d9c7a3")
    return imagen


def aplicar_ajustes(imagen):
    factor_brillo = valor_brillo / 50
    factor_contraste = valor_contraste / 50
    factor_saturacion = valor_saturacion / 50

    imagen = ImageEnhance.Brightness(imagen).enhance(factor_brillo)
    imagen = ImageEnhance.Contrast(imagen).enhance(factor_contraste)
    imagen = ImageEnhance.Color(imagen).enhance(factor_saturacion)
    return imagen


def mostrar_imagen(usar_respaldo=False):
    if fotoO is None:
        return
    frame_imagen.update_idletasks()
    ancho = max(frame_imagen.winfo_width() - 10, 100)
    alto = max(frame_imagen.winfo_height() - 10, 100)
    
    if usar_respaldo and foto_respaldo is not None:
        copia = foto_respaldo.copy()
    else:
        copia = aplicar_filtro(fotoO.copy(), filtro_actual)
        copia = aplicar_ajustes(copia)
        
    copia.thumbnail((ancho, alto))
    imagen_tk = ImageTk.PhotoImage(copia)
    labelImag.config(image=imagen_tk)
    labelImag.image = imagen_tk


def mostrar_antes(event):
    mostrar_imagen(usar_respaldo=True)


def mostrar_despues(event):
    mostrar_imagen(usar_respaldo=False)


# --- Lógica de Historial (Deshacer / Rehacer) ---
def guardar_estado():
    global fotoO, historial, historial_futuro
    if fotoO is not None:
        historial.append(fotoO.copy())
        historial_futuro.clear()


def deshacer(event=None):
    global fotoO, foto_respaldo, historial, historial_futuro
    if not historial:
        return
    if fotoO is not None:
        historial_futuro.append(fotoO.copy())
    
    fotoO = historial.pop()
    foto_respaldo = fotoO.copy()
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()


def rehacer(event=None):
    global fotoO, foto_respaldo, historial, historial_futuro
    if not historial_futuro:
        return
    if fotoO is not None:
        historial.append(fotoO.copy())
        
    fotoO = historial_futuro.pop()
    foto_respaldo = fotoO.copy()
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()


def cambiar_brillo(valor):
    global valor_brillo
    valor_brillo = int(valor)
    mostrar_imagen()
    marcar_cambio()


def cambiar_contraste(valor):
    global valor_contraste
    valor_contraste = int(valor)
    mostrar_imagen()
    marcar_cambio()


def cambiar_saturacion(valor):
    global valor_saturacion
    valor_saturacion = int(valor)
    mostrar_imagen()
    marcar_cambio()


def cambiar_filtro(event):
    global filtro_actual
    filtro_actual = combo_filtros.get()
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()


def actualizar_icono_guardado():
    if icono_guardar is None:
        menu_guardar.config(text="✓ " if guardada else "💾 ")
        return
    if guardada:
        menu_guardar.config(image=icono_guardar_verde)
        menu_guardar.image = icono_guardar_verde
    else:
        menu_guardar.config(image=icono_guardar)
        menu_guardar.image = icono_guardar


def marcar_cambio():
    global guardada
    guardada = False
    actualizar_icono_guardado()


def guardar_imagen():
    global guardada
    if fotoO is None:
        messagebox.showwarning("Atención", "Primero cargá una imagen.")
        return
    if not ruta_guardado:
        guardar_como()
        return
    try:
        imagen_final = aplicar_filtro(fotoO, filtro_actual)
        imagen_final = aplicar_ajustes(imagen_final)
        if ruta_guardado.lower().endswith((".jpg", ".jpeg")):
            imagen_final = imagen_final.convert("RGB")
        imagen_final.save(ruta_guardado)
    except Exception as e:
        messagebox.showerror("Error al guardar", f"No se pudo guardar el archivo.\nDetalle: {e}")
        return
    guardada = True
    actualizar_icono_guardado()


def guardar_como():
    global ruta_guardado, guardada
    if fotoO is None:
        messagebox.showwarning("Atención", "Primero cargá una imagen.")
        return
    ruta = filedialog.asksaveasfilename(
        title="Guardar como",
        defaultextension=".png",
        filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")]
    )
    if not ruta:
        return
    try:
        imagen_final = aplicar_filtro(fotoO, filtro_actual)
        imagen_final = aplicar_ajustes(imagen_final)
        if ruta.lower().endswith((".jpg", ".jpeg")):
            imagen_final = imagen_final.convert("RGB")
        imagen_final.save(ruta)
    except Exception as e:
        messagebox.showerror("Error al guardar", f"No se pudo guardar el archivo.\nDetalle: {e}")
        return
    ruta_guardado = ruta
    guardada = True
    actualizar_icono_guardado()
    messagebox.showinfo("Guardado", "La imagen se guardó correctamente.")


def cargarf():
    global fotoO, foto_respaldo, ruta_guardado, guardada, historial, historial_futuro

    ruta = filedialog.askopenfilename(
        title="Seleccionar imagen",
        filetypes=[
            ("Imágenes", "*.jpg *.jpeg *.png *.bmp"),
            ("Todos los archivos", "*.*")
        ]
    )

    if not ruta:
        return

    extensiones_validas = (".jpg", ".jpeg", ".png", ".bmp")
    if not ruta.lower().endswith(extensiones_validas):
        messagebox.showerror("Formato no soportado", "El archivo debe ser JPG, PNG o BMP.")
        return
    try:
        imagen = Image.open(ruta)
        imagen.verify()
        imagen = Image.open(ruta).convert("RGB")
    except Exception as e:
        messagebox.showerror("Error", "No se puede abrir la imagen")
        return

    fotoO = imagen
    foto_respaldo = imagen.copy()
    historial.clear()
    historial_futuro.clear()
    
    label_nombre.config(text=ruta.split("/")[-1])

    ruta_guardado = ruta
    guardada = True
    actualizar_icono_guardado()

    mostrar_imagen()
    reproducir_sonido()


def rotateizquierda():
    global fotoO, foto_respaldo
    if fotoO is None:
        return
    guardar_estado()
    foto_respaldo = fotoO.copy()
    fotoO = fotoO.rotate(90, expand=True)
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()


def rotatederecha():
    global fotoO, foto_respaldo
    if fotoO is None:
        return
    guardar_estado()
    foto_respaldo = fotoO.copy()
    fotoO = fotoO.rotate(-90, expand=True)
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()


def rotate180():
    global fotoO, foto_respaldo
    if fotoO is None:
        return
    guardar_estado()
    foto_respaldo = fotoO.copy()
    fotoO = fotoO.rotate(180, expand=True)
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()


# ---------------- RECORTE (crop) ----------------

def iniciar_recorte():
    global modo_recorte, recorte_escala
    global recorte_izq, recorte_der, recorte_sup, recorte_inf
    global linea_izq, linea_der, linea_sup, linea_inf
    global handle_ni, handle_nd, handle_si, handle_sd
    global img_clara_recorte, img_oscura_recorte, id_imagen_canvas

    if fotoO is None:
        messagebox.showwarning("Atención", "Primero cargá una imagen.")
        return

    modo_recorte = True

    frame_imagen.update_idletasks()
    ancho_disp = max(frame_imagen.winfo_width() - 10, 100)
    alto_disp = max(frame_imagen.winfo_height() - 10, 100)
    imagen_filtrada = aplicar_filtro(fotoO.copy(), filtro_actual)
    imagen_filtrada = aplicar_ajustes(imagen_filtrada)
    imagen_filtrada.thumbnail((ancho_disp, alto_disp))

    recorte_escala = fotoO.width / imagen_filtrada.width

    img_clara_recorte = imagen_filtrada
    img_oscura_recorte = ImageEnhance.Brightness(imagen_filtrada).enhance(0.35)

    labelImag.pack_forget()
    canvas_imagen.config(width=imagen_filtrada.width, height=imagen_filtrada.height)
    canvas_imagen.pack(expand=True)
    canvas_imagen.delete("all")

    id_imagen_canvas = canvas_imagen.create_image(0, 0, anchor="nw", tags="fondo")

    margen_x = imagen_filtrada.width * 0.1
    margen_y = imagen_filtrada.height * 0.1
    recorte_izq = margen_x
    recorte_der = imagen_filtrada.width - margen_x
    recorte_sup = margen_y
    recorte_inf = imagen_filtrada.height - margen_y

    linea_izq = canvas_imagen.create_line(0, 0, 0, 0, fill="#ffffff", width=2, tags="izq")
    linea_der = canvas_imagen.create_line(0, 0, 0, 0, fill="#ffffff", width=2, tags="der")
    linea_sup = canvas_imagen.create_line(0, 0, 0, 0, fill="#ffffff", width=2, tags="sup")
    linea_inf = canvas_imagen.create_line(0, 0, 0, 0, fill="#ffffff", width=2, tags="inf")

    handle_ni = canvas_imagen.create_rectangle(0, 0, 0, 0, fill="#ffffff", outline="", tags="ni")
    handle_nd = canvas_imagen.create_rectangle(0, 0, 0, 0, fill="#ffffff", outline="", tags="nd")
    handle_si = canvas_imagen.create_rectangle(0, 0, 0, 0, fill="#ffffff", outline="", tags="si")
    handle_sd = canvas_imagen.create_rectangle(0, 0, 0, 0, fill="#ffffff", outline="", tags="sd")

    redibujar_recorte()

    for parte in ("izq", "der", "sup", "inf", "ni", "nd", "si", "sd"):
        canvas_imagen.tag_bind(parte, "<ButtonPress-1>", lambda e, p=parte: iniciar_arrastre(p))

    canvas_imagen.tag_bind("fondo", "<ButtonPress-1>", iniciar_mover)
    canvas_imagen.bind("<B1-Motion>", arrastrar)
    canvas_imagen.bind("<ButtonRelease-1>", lambda e: detener_arrastre())

    boton_recortar.config(state="disabled")
    boton_listo.pack(fill="x", padx=15, pady=4)
    boton_cancelar_recorte.pack(fill="x", padx=15, pady=(0, 4))
    reproducir_sonido()


def redibujar_recorte():
    caja = (int(recorte_izq), int(recorte_sup), int(recorte_der), int(recorte_inf))
    compuesta = img_oscura_recorte.copy()
    compuesta.paste(img_clara_recorte.crop(caja), (caja[0], caja[1]))

    imagen_tk = ImageTk.PhotoImage(compuesta)
    canvas_imagen.itemconfig(id_imagen_canvas, image=imagen_tk)
    canvas_imagen.image = imagen_tk

    canvas_imagen.coords(linea_izq, recorte_izq, recorte_sup, recorte_izq, recorte_inf)
    canvas_imagen.coords(linea_der, recorte_der, recorte_sup, recorte_der, recorte_inf)
    canvas_imagen.coords(linea_sup, recorte_izq, recorte_sup, recorte_der, recorte_sup)
    canvas_imagen.coords(linea_inf, recorte_izq, recorte_inf, recorte_der, recorte_inf)

    m = 5
    canvas_imagen.coords(handle_ni, recorte_izq - m, recorte_sup - m, recorte_izq + m, recorte_sup + m)
    canvas_imagen.coords(handle_nd, recorte_der - m, recorte_sup - m, recorte_der + m, recorte_sup + m)
    canvas_imagen.coords(handle_si, recorte_izq - m, recorte_inf - m, recorte_izq + m, recorte_inf + m)
    canvas_imagen.coords(handle_sd, recorte_der - m, recorte_inf - m, recorte_der + m, recorte_inf + m)

    for item in (linea_izq, linea_der, linea_sup, linea_inf,
                 handle_ni, handle_nd, handle_si, handle_sd):
        canvas_imagen.tag_raise(item)


def iniciar_arrastre(parte):
    global arrastrando
    arrastrando = parte


def iniciar_mover(event):
    global arrastrando, offset_mover_x, offset_mover_y
    if recorte_izq < event.x < recorte_der and recorte_sup < event.y < recorte_inf:
        arrastrando = "mover"
        offset_mover_x = event.x - recorte_izq
        offset_mover_y = event.y - recorte_sup


def detener_arrastre():
    global arrastrando
    arrastrando = None


def arrastrar(event):
    global recorte_izq, recorte_der, recorte_sup, recorte_inf

    if arrastrando is None:
        return

    ancho_img = img_clara_recorte.width
    alto_img = img_clara_recorte.height
    margen_minimo = 20

    if arrastrando == "izq":
        recorte_izq = min(max(event.x, 0), recorte_der - margen_minimo)
    elif arrastrando == "der":
        recorte_der = max(min(event.x, ancho_img), recorte_izq + margen_minimo)
    elif arrastrando == "sup":
        recorte_sup = min(max(event.y, 0), recorte_inf - margen_minimo)
    elif arrastrando == "inf":
        recorte_inf = max(min(event.y, alto_img), recorte_sup + margen_minimo)
    elif arrastrando == "ni":
        recorte_izq = min(max(event.x, 0), recorte_der - margen_minimo)
        recorte_sup = min(max(event.y, 0), recorte_inf - margen_minimo)
    elif arrastrando == "nd":
        recorte_der = max(min(event.x, ancho_img), recorte_izq + margen_minimo)
        recorte_sup = min(max(event.y, 0), recorte_inf - margen_minimo)
    elif arrastrando == "si":
        recorte_izq = min(max(event.x, 0), recorte_der - margen_minimo)
        recorte_inf = max(min(event.y, alto_img), recorte_sup + margen_minimo)
    elif arrastrando == "sd":
        recorte_der = max(min(event.x, ancho_img), recorte_izq + margen_minimo)
        recorte_inf = max(min(event.y, alto_img), recorte_sup + margen_minimo)
    elif arrastrando == "mover":
        ancho_caja = recorte_der - recorte_izq
        alto_caja = recorte_inf - recorte_sup
        nuevo_izq = min(max(event.x - offset_mover_x, 0), ancho_img - ancho_caja)
        nuevo_sup = min(max(event.y - offset_mover_y, 0), alto_img - alto_caja)
        recorte_izq = nuevo_izq
        recorte_der = nuevo_izq + ancho_caja
        recorte_sup = nuevo_sup
        recorte_inf = nuevo_sup + alto_caja

    redibujar_recorte()


def finalizar_recorte():
    global modo_recorte, arrastrando
    modo_recorte = False
    arrastrando = None
    canvas_imagen.pack_forget()
    labelImag.pack(fill="both", expand=True, padx=2, pady=2)
    boton_listo.pack_forget()
    boton_cancelar_recorte.pack_forget()
    boton_recortar.config(state="normal")


def confirmar_recorte():
    global fotoO, foto_respaldo
    if fotoO is None:
        return
    guardar_estado()
    foto_respaldo = fotoO.copy()
    
    izq_real = int(recorte_izq * recorte_escala)
    der_real = int(recorte_der * recorte_escala)
    sup_real = int(recorte_sup * recorte_escala)
    inf_real = int(recorte_inf * recorte_escala)

    fotoO = fotoO.crop((izq_real, sup_real, der_real, inf_real))
    finalizar_recorte()
    mostrar_imagen()
    marcar_cambio()
    reproducir_sonido()


def cancelar_recorte():
    finalizar_recorte()
    mostrar_imagen()
    reproducir_sonido()


# ---------------- LAYOUT ----------------

# --- Menú de guardado y botones grandes de Deshacer / Rehacer arriba a la izquierda ---
menu_guardar = tk.Menubutton(
    app, relief="flat", background="#252850",
    activebackground="#1A1C38", bd=0
)
menu_guardar.place(x=15, y=10)

menu_desplegable = tk.Menu(menu_guardar, tearoff=0)
menu_desplegable.add_command(label=" Guardar", image=icono_guardar,
                            compound="left", command=guardar_imagen)
menu_desplegable.add_command(label=" Guardar como...", image=icono_guardarcomo,
                            compound="left", command=guardar_como)
menu_desplegable.icono1 = icono_guardar
menu_desplegable.icono2 = icono_guardarcomo
menu_guardar.config(menu=menu_desplegable)
actualizar_icono_guardado()

# Botón Deshacer grande (más espaciado y tamaño 32x32)
btn_deshacer = tk.Button(
    app, image=icono_deshacer, relief="flat", background="#252850",
    activebackground="#1A1C38", bd=0, command=deshacer, cursor="hand2"
)
btn_deshacer.place(x=60, y=8)

# Botón Rehacer grande al lado
btn_rehacer = tk.Button(
    app, image=icono_rehacer, relief="flat", background="#252850",
    activebackground="#1A1C38", bd=0, command=rehacer, cursor="hand2"
)
btn_rehacer.place(x=105, y=8)

# Atajos de teclado (Ctrl + Z y Ctrl + Y)
app.bind("<Control-z>", deshacer)
app.bind("<Control-y>", rehacer)

if errores_recursos:
    mensaje = "No se pudieron cargar estos archivos de ícono:\n\n"
    mensaje += "\n".join(f"• {e}" for e in errores_recursos)
    mensaje += "\n\nRevisá que estén guardados en la MISMA carpeta que el script."
    messagebox.showwarning("Faltan íconos", mensaje)

cargf = tk.Button(app, text="Cargar imagen", command=cargarf)
cargf.pack(pady=5)

label_nombre = tk.Label(app, text="Sin imagen cargada",
                        background="#252850", foreground="white",
                        font=("Segoe UI", 9))
label_nombre.pack(pady=(2, 5))

frame_imagen = tk.Frame(
    app,
    background="#1A1C38",
    highlightbackground=COLOR_MARCO,
    highlightthickness=3
)
frame_imagen.pack(side="left", fill="both", expand=True, padx=15, pady=5)
frame_imagen.pack_propagate(False)

labelImag = tk.Label(frame_imagen, background="#1A1C38")
labelImag.pack(fill="both", expand=True, padx=2, pady=2)

canvas_imagen = tk.Canvas(frame_imagen, background="#1A1C38", highlightthickness=0)

# --- Menú en columna, a la derecha ---
frame_menu = tk.Frame(
    app,
    background="#1A1C38",
    highlightbackground=COLOR_MARCO,
    highlightthickness=3,
    width=200
)
frame_menu.pack(side="right", fill="y", padx=(0, 15), pady=5)
frame_menu.pack_propagate(False)

# Botón de Vista Previa (Antes / Después)
boton_preview = tk.Button(frame_menu, text="👁 Vista Previa (Mantener)", relief="flat",
                          background="#4e54c8", foreground="white", anchor="w", padx=10, pady=4, font=("Segoe UI", 9))
boton_preview.pack(fill="x", padx=10, pady=(10, 4))
boton_preview.bind("<ButtonPress-1>", mostrar_antes)
boton_preview.bind("<ButtonRelease-1>", mostrar_despues)

boton4 = tk.Button(frame_menu, text=" Voltear izquierda", image=icono_izquierda,
                   compound="left", relief="flat", command=rotateizquierda,
                   background="#ffffff", anchor="w", padx=10, pady=4, font=("Segoe UI", 9))
boton4.pack(fill="x", padx=10, pady=4)

boton3 = tk.Button(frame_menu, text=" Voltear derecha", image=icono_derecha,
                   compound="left", relief="flat", command=rotatederecha,
                   background="#ffffff", anchor="w", padx=10, pady=4, font=("Segoe UI", 9))
boton3.pack(fill="x", padx=10, pady=4)

boton2 = tk.Button(frame_menu, text="Voltear 180°", relief="flat", command=rotate180,
                   background="#ffffff", anchor="w", padx=10, pady=4, font=("Segoe UI", 9))
boton2.pack(fill="x", padx=10, pady=4)

# --- Botón de recorte y sus confirmaciones ---
boton_recortar = tk.Button(frame_menu, text=" Recortar", image=icono_tijeras,
                           compound="left", relief="flat", command=iniciar_recorte,
                           background="#ffffff", anchor="w", padx=10, pady=4, font=("Segoe UI", 9))
boton_recortar.pack(fill="x", padx=10, pady=4)

boton_listo = tk.Button(frame_menu, text=" Listo", image=icono_listo,
                       compound="left", relief="flat", command=confirmar_recorte,
                       background="#ffffff", anchor="w", padx=10, pady=4, font=("Segoe UI", 9))

boton_cancelar_recorte = tk.Button(frame_menu, text=" Cancelar", image=icono_cancelar_recorte,
                                   compound="left", relief="flat", command=cancelar_recorte,
                                   background="#ffffff", anchor="w", padx=10, pady=4, font=("Segoe UI", 9))

# --- Combobox de filtros ---
label_filtro = tk.Label(frame_menu, text="Filtro",
                        background="#1A1C38", foreground="white",
                        font=("Segoe UI", 9))
label_filtro.pack(anchor="w", padx=10, pady=(6, 2))

combo_filtros = ttk.Combobox(
    frame_menu,
    state="readonly",
    values=["Original", "Desenfoque", "Nitidez",
            "Detección de bordes", "Negativo", "Sepia"]
)
combo_filtros.set("Original")
combo_filtros.pack(fill="x", padx=10, pady=(0, 4))
combo_filtros.bind("<<ComboboxSelected>>", cambiar_filtro)

# --- Sliders de Brillo / Contraste / Saturación ---
label_brillo = tk.Label(frame_menu, text="Brillo",
                       background="#1A1C38", foreground="white", font=("Segoe UI", 8))
label_brillo.pack(anchor="w", padx=10, pady=(2, 0))

slider_brillo = tk.Scale(
    frame_menu, from_=0, to=100, orient="horizontal",
    background="#1A1C38", foreground="white", highlightthickness=0,
    troughcolor="#ffffff", command=cambiar_brillo
)
slider_brillo.set(50)
slider_brillo.pack(fill="x", padx=10)

label_contraste = tk.Label(frame_menu, text="Contraste",
                            background="#1A1C38", foreground="white", font=("Segoe UI", 8))
label_contraste.pack(anchor="w", padx=10, pady=(2, 0))

slider_contraste = tk.Scale(
    frame_menu, from_=0, to=100, orient="horizontal",
    background="#1A1C38", foreground="white", highlightthickness=0,
    troughcolor="#ffffff", command=cambiar_contraste
)
slider_contraste.set(50)
slider_contraste.pack(fill="x", padx=10)

label_saturacion = tk.Label(frame_menu, text="Saturación",
                             background="#1A1C38", foreground="white", font=("Segoe UI", 8))
label_saturacion.pack(anchor="w", padx=10, pady=(2, 0))

slider_saturacion = tk.Scale(
    frame_menu, from_=0, to=100, orient="horizontal",
    background="#1A1C38", foreground="white", highlightthickness=0,
    troughcolor="#ffffff", command=cambiar_saturacion
)
slider_saturacion.set(50)
slider_saturacion.pack(fill="x", padx=10, pady=(0, 10))


app.mainloop()