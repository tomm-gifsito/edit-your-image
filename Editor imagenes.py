import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageOps, ImageFilter

app = tk.Tk()

# ancho y alto
app.geometry("1024x650")
app.configure(background="#252850")
tk.Wm.wm_title(app, "editor de imagenes")

COLOR_MARCO = "#1A1C38"

fotoO = None  # acá se guarda la imagen PIL "vigente" (con rotaciones aplicadas)
filtro_actual = "Original"  # nombre del filtro seleccionado en el combobox


# ---------------------------------------------------------------
# Cargar los íconos de flecha (uno para la derecha, otro espejado
# para la izquierda) ANTES de crear los botones, porque los botones
# los van a necesitar ya listos.
# ---------------------------------------------------------------
RUTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
ruta_flecha = os.path.join(RUTA_SCRIPT, "flecha.png")

icono_derecha = None
icono_izquierda = None

try:
    img_flecha = Image.open(ruta_flecha).convert("RGBA")
    img_flecha.thumbnail((22, 22))  # ícono chico, para que entre bien en el botón

    icono_derecha = ImageTk.PhotoImage(img_flecha)

    # ImageOps.mirror() voltea la imagen horizontalmente (como un espejo),
    # así reutilizamos la misma flecha para el giro hacia la izquierda
    img_flecha_izq = ImageOps.mirror(img_flecha)
    icono_izquierda = ImageTk.PhotoImage(img_flecha_izq)
except Exception as e:
    print(f"No se pudo cargar flecha.png: {e}")
    # Si no se encuentra el archivo, los botones van a mostrar
    # solo el texto, sin ícono (no se rompe el programa)


def aplicar_filtro(imagen, nombre):
    """Devuelve una COPIA de imagen con el filtro 'nombre' aplicado.
    No modifica la imagen original que recibe."""
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


def mostrar_imagen():
    """Redimensiona fotoO (con el filtro actual) al tamaño del marco y la muestra."""
    if fotoO is None:
        return
    frame_imagen.update_idletasks()
    ancho = max(frame_imagen.winfo_width() - 10, 100)
    alto = max(frame_imagen.winfo_height() - 10, 100)
    copia = aplicar_filtro(fotoO.copy(), filtro_actual)
    copia.thumbnail((ancho, alto))
    imagen_tk = ImageTk.PhotoImage(copia)
    labelImag.config(image=imagen_tk)
    labelImag.image = imagen_tk


def cambiar_filtro(event):
    global filtro_actual
    filtro_actual = combo_filtros.get()
    mostrar_imagen()


def cargarf():
    global fotoO

    ruta = filedialog.askopenfilename(
        title="Seleccionar imagen",
        filetypes=[
            ("Imágenes", "*.jpg *.jpeg *.png *.bmp"),
            ("Todos los archivos", "*.*")
        ]
    )

    if not ruta:
        #  "Cancelar", ruta vacía ("") no se hace nada
        return

    extensiones_validas = (".jpg", ".jpeg", ".png", ".bmp")
    if not ruta.lower().endswith(extensiones_validas):
        messagebox.showerror("Formato no soportado",
                              "El archivo debe ser JPG, PNG o BMP.")
        return
    try:
        imagen = Image.open(ruta)
        imagen.verify()
        imagen = Image.open(ruta).convert("RGB")
    except Exception as e:
        messagebox.showerror("Error", "No se puede abrir la imagen")
        return

    fotoO = imagen  # ACÁ faltaba guardar la imagen cargada en la variable global
    label_nombre.config(text=ruta.split("/")[-1])
    mostrar_imagen()


def rotateizquierda():
    global fotoO
    if fotoO is None:
        return
    fotoO = fotoO.rotate(90, expand=True)
    mostrar_imagen()


def rotatederecha():
    global fotoO
    if fotoO is None:
        return
    fotoO = fotoO.rotate(-90, expand=True)
    mostrar_imagen()


def rotate180():
    global fotoO
    if fotoO is None:
        return
    fotoO = fotoO.rotate(180, expand=True)
    mostrar_imagen()


# ---------------- LAYOUT ----------------

cargf = tk.Button(app, text="Cargar imagen", command=cargarf)
cargf.pack(pady=10)

label_nombre = tk.Label(app, text="Sin imagen cargada",
                         background="#252850", foreground="white",
                         font=("Segoe UI", 10))
label_nombre.pack(pady=(10, 5))

frame_imagen = tk.Frame(
    app,
    background="#1A1C38",
    highlightbackground=COLOR_MARCO,
    highlightthickness=3
)
frame_imagen.pack(side="left", fill="both", expand=True, padx=20, pady=10)

labelImag = tk.Label(frame_imagen, background="#1A1C38")
labelImag.pack(fill="both", expand=True, padx=2, pady=2)

# --- Menú en columna, a la derecha ---
frame_menu = tk.Frame(
    app,
    background="#1A1C38",
    highlightbackground=COLOR_MARCO,
    highlightthickness=3,
    width=200
)
frame_menu.pack(side="right", fill="y", padx=(0, 20), pady=10)
frame_menu.pack_propagate(False)  # mantiene el ancho fijo de 200, no se achica

boton4 = tk.Button(frame_menu, text=" Voltear izquierda", image=icono_izquierda,
                    compound="left", relief="flat", command=rotateizquierda,
                    background="#ffffff", anchor="w", padx=15, pady=8)
boton4.pack(fill="x", padx=15, pady=(20, 8))

boton3 = tk.Button(frame_menu, text=" Voltear derecha", image=icono_derecha,
                    compound="left", relief="flat", command=rotatederecha,
                    background="#ffffff", anchor="w", padx=15, pady=8)
boton3.pack(fill="x", padx=15, pady=8)

boton2 = tk.Button(frame_menu, text="Voltear 180°", relief="flat", command=rotate180,
                    background="#ffffff", padx=15, pady=8)
boton2.pack(fill="x", padx=15, pady=8)

# --- Combobox de filtros ---
label_filtro = tk.Label(frame_menu, text="Filtro",
                         background="#1A1C38", foreground="white",
                         font=("Segoe UI", 9))
label_filtro.pack(anchor="w", padx=15, pady=(20, 2))

combo_filtros = ttk.Combobox(
    frame_menu,
    state="readonly",  # el usuario solo puede elegir de la lista, no tipear texto libre
    values=["Original", "Desenfoque", "Nitidez",
            "Detección de bordes", "Negativo", "Sepia"]
)
combo_filtros.set("Original")
combo_filtros.pack(fill="x", padx=15, pady=(0, 8))
combo_filtros.bind("<<ComboboxSelected>>", cambiar_filtro)


app.mainloop()