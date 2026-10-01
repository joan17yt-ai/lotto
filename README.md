# LottoAnalytics Pro Colombia 🇨🇴
### Plataforma Web & PWA de Inteligencia de Datos y Pronósticos para Baloto, Revancha y MiLoto

Plataforma web profesional lista para desplegar en **Netlify** con diseño responsive de alta gama, generador algorítmico de combinaciones, mapas de calor, comprobador de boletos y espacios integrados para monetización con **Google AdSense** y membresías VIP.

---

## 🚀 Despliegue en Netlify (2 Métodos)

### Método 1: Despliegue con Auto-Actualización Automática (Recomendado)
Este método permite que la web se actualice sola todas las noches sin que tengas que intervenir.

1. **Sube esta carpeta a GitHub:**
   * Crea un nuevo repositorio en [github.com](https://github.com) (ej. `lottoanalytics-colombia`).
   * Sube los archivos de esta carpeta al repositorio.
2. **Conecta Netlify con GitHub:**
   * Inicia sesión en [netlify.com](https://www.netlify.com).
   * Haz clic en **"Add new site"** > **"Import an existing project"** > Selecciona **GitHub**.
   * Elige tu repositorio `lottoanalytics-colombia`.
   * En "Publish directory" déjalo vacío o pon `.` (ya está configurado en `netlify.toml`).
   * Haz clic en **"Deploy Site"**. ¡Tu web estará al aire en 30 segundos!
3. **¿Cómo funciona la auto-actualización automática?**
   * El archivo `.github/workflows/auto_update.yml` se ejecuta todas las noches a las **11:30 PM (hora Colombia)**.
   * Descarga los números oficiales de Baloto y MiLoto, actualiza las estadísticas y hace un commit automático.
   * Netlify detecta el cambio y actualiza tu sitio web en vivo de inmediato. **Cero servidores, 100% gratuito.**

---

### Método 2: Despliegue Inmediato Drag & Drop (Sin GitHub)
1. Entra a [app.netlify.com/drop](https://app.netlify.com/drop).
2. Arrastra la carpeta `web_app` a la ventana del navegador.
3. En 10 segundos tendrás un enlace activo (ej. `https://tu-nombre-aleatorio.netlify.app`).
4. Puedes vincular tu propio dominio personalizado en la pestaña **Domain management**.

---

## 💰 ¿Cómo Monetizar esta Web?

### 1. Google AdSense (Publicidad Display)
El código ya viene con 3 espacios publicitarios optimizados para altos ingresos:
* **Banner Superior (`#top-ad-slot`):** Ubicado antes del contenido para impresiones tempranas.
* **Banner In-Feed (`#middle-ad-slot`):** Entre el generador y las tablas de datos.
* **Banner Inferior (`#bottom-ad-slot`):** Al final de la página.

**Para activarlos:**
1. Abre `index.html`.
2. En la línea 27, descomenta la etiqueta del script de AdSense y coloca tu ID de cliente (`ca-pub-XXXXXXXXXXXXXXXX`).
3. Reemplaza el contenido de los contenedores `.ad-slot` con tus códigos de bloque de anuncios de AdSense.

### 2. Membresía VIP / Canal de Telegram
* En el archivo `index.html` encontrarás el contenedor `.vip-card`.
* Cambia el enlace `https://t.me/` por el enlace directo a tu canal de Telegram o grupo de WhatsApp.
* Puedes ofrecer alertas gratuitas y cobrar una suscripción mensual (por ejemplo $20.000 COP/mes) a usuarios que quieran recibir las jugadas filtradas antes de cada sorteo.

### 3. Afiliados / Patrocinios
* Puedes colocar enlaces de afiliado de plataformas de recarga o loterías oficiales autorizadas por Coljuegos.

---

## 📱 Instalación como App Móvil (PWA)
La web incluye `manifest.json` y `sw.js`. Cuando los usuarios ingresen desde el celular:
* **Android (Chrome):** Verán el mensaje "Añadir a la pantalla de inicio" o "Instalar aplicación".
* **iPhone (Safari):** Tocan el botón de compartir y seleccionan "Añadir a pantalla de inicio".
* La app se abrirá en pantalla completa con icono propio, sin barra de direcciones.

---

## ⚖️ Aviso Legal
Incluye pie de página con cumplimiento de la Ley 643 de 2001 (prohibición a menores de 18 años y advertencia de juego responsable).
