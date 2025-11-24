import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d

# --- 1. Generación de Datos Simulados ---
# Nota: Como no tenemos los datos reales de la batería, simulamos la forma
# de las curvas usando puntos clave y suavizándolos con interpolación.

# Puntos de control estimados para la curva de DESCAGA (naranja)
# (Tiempo en horas, Voltaje en V)
t_dis_points = np.array([0, 0.5, 1.5, 2.8, 3.5, 4.0])
v_dis_points = np.array([4.2, 4.05, 3.85, 3.65, 3.35, 3.0])

# Puntos de control estimados para la curva de CARGA (azul punteada)
t_chg_points = np.array([0, 0.5, 1.2, 2.0, 2.8, 4.0])
v_chg_points = np.array([3.0, 3.35, 3.65, 3.95, 4.16, 4.2])

# Creamos funciones de interpolación cúbica para suavizar las líneas
f_dis = interp1d(t_dis_points, v_dis_points, kind='cubic')
# Para la carga, usamos 'linear' al final para simular la fase CV (voltaje constante)
# y evitar que la interpolación cúbica sobrepase los 4.2V
f_chg = interp1d(t_chg_points, v_chg_points, kind='cubic', bounds_error=False, fill_value=(3.0, 4.2))

# Generamos muchos puntos de tiempo para que la línea se vea suave
t_smooth = np.linspace(0, 4, 300)

# Calculamos los voltajes suavizados
v_dis_smooth = f_dis(t_smooth)
v_chg_smooth = f_chg(t_smooth)

# Pequeño ajuste para asegurar que la carga no pase de 4.2V por la interpolación
v_chg_smooth = np.clip(v_chg_smooth, 3.0, 4.2)


# --- 2. Creación de la Gráfica ---

# Configurar el tamaño de la figura (ancho, alto en pulgadas)
plt.figure(figsize=(8, 5))

# Graficar línea de Descarga (sólida, color naranja/dorado)
# Usamos un color hexadecimal para acertar más al tono de la imagen
plt.plot(t_smooth, v_dis_smooth,
         label='Descarga (0.3 A)',
         color='#E69F00',  # Color naranja personalizado
         linewidth=1.5)

# Graficar línea de Carga (punteada, color azul cielo)
plt.plot(t_smooth, v_chg_smooth,
         label='Carga (CC-CV)',
         color='#56B4E9',  # Color azul claro personalizado
         linestyle='--',   # Línea punteada
         linewidth=1.5)


# --- 3. Estilo y Etiquetas (Para igualar la imagen) ---

# Título con salto de línea (\n) para el subtítulo
plt.title("Curvas idealizadas de carga y descarga\nBatería Li-ion 18650, 3.7 V, 1200 mAh, I = 0.3 A",
          fontsize=14, pad=15, color='#333333')

# Etiquetas de los ejes
plt.xlabel("Tiempo (horas)", fontsize=12, color='#333333')
plt.ylabel("Voltaje (V)", fontsize=12, color='#333333')

# Configurar los límites y los "ticks" (marcas) de los ejes
plt.xlim(-0.1, 4.2) # Un poco de margen a los lados
plt.ylim(2.95, 4.25) # Un poco de margen arriba y abajo

plt.xticks(np.arange(0, 4.5, 0.5), fontsize=11)
plt.yticks(np.arange(3.0, 4.4, 0.2), fontsize=11)

# Agregar la cuadrícula (grid)
plt.grid(True, linestyle='--', alpha=0.7, color='gray')

# Agregar la leyenda
# 'loc' define la posición, 'frameon=True' pone el recuadro blanco
plt.legend(loc='lower center', frameon=True, fontsize=10)

# Remover los bordes superior y derecho de la gráfica (estilo limpio)
ax = plt.gca() # Obtener el eje actual
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#333333')
ax.spines['bottom'].set_color('#333333')
ax.tick_params(colors='#333333') # Color de las marcas

# Ajustar el diseño para que no se corten las etiquetas
plt.tight_layout()

# Mostrar la gráfica
plt.show()