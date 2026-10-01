# LottoAnalytics Pro Colombia 🇨🇴
### Plataforma Web & PWA de Inteligencia de Datos y Pronósticos para Baloto, Revancha y MiLoto

Plataforma web profesional lista para desplegar en **Netlify** con diseño responsive de alta gama, generador algorítmico de combinaciones, mapas de calor, comprobador de boletos, **Suite VIP Exclusiva** (números personalizados, radar de atrasos, boletos únicos) y espacios integrados para monetización con **Google AdSense** y membresías VIP por Nequi/Daviplata.

---

## 👑 Suite VIP & Desbloqueo por PIN

La plataforma incluye un sistema de monetización dual (Gratis + VIP):

### Privilegios VIP incluidos:
1. **Generador Personalizado con Balotas Fijas:** El usuario digita 1 o 2 de sus números favoritos y el algoritmo completa las restantes asegurando el rango óptimo de Gauss y la mayor tasa de co-ocurrencia histórica.
2. **Radar de Atrasos Críticos (>1.5x):** Alertas sobre balotas que superan su récord de ausencia y entran en ventana de retorno estadístico.
3. **Boleto Único No Compartido:** Asignación de combinaciones con semilla privada para evitar compartir el premio mayor con otros jugadores.
4. **Alertas al Celular:** Botón de vinculación con canal o bot de Telegram.

### Cómo funciona el PIN VIP:
* Para probarlo de inmediato, ingresa el PIN: `VIP2026` o `BUCARAMANGA`.
* Cualquier PIN que inicie con `VIP` es aceptado automáticamente por la web y se guarda en el navegador del cliente (`localStorage`) durante 30 días.
* Para tus clientes, puedes asignarles códigos como `VIP-OCT-742` una vez te envíen el comprobante de pago por Nequi o Daviplata.

---

## ⏱️ Protocolo de Auto-Actualización y Doble Verificación (+1 Hora)

Dado que las loterías oficiales en Colombia a veces tardan en publicar sus números tras la transmisión en vivo:
* **MiLoto (Sorteo 10:15 PM):** Primer barrido a las **10:30 PM**, con re-verificación diferida a las **11:30 PM** (+1 hora).
* **Baloto / Revancha (Sorteo 11:15 PM):** Primer barrido a las **11:30 PM**, con re-verificación diferida a las **12:30 AM** (+1 hora).
* Este flujo está 100% automatizado en `.github/workflows/auto_update.yml`. Si la web oficial presenta demoras en el primer intento, el sistema no falla: espera la hora siguiente y actualiza Netlify automáticamente.

---

## 🚀 Despliegue en Netlify (2 Métodos)

### Método 1: Despliegue con Auto-Actualización Automática (Recomendado)
1. **Sube esta carpeta a GitHub:**
   * Crea un nuevo repositorio en [github.com](https://github.com) (ej. `lottoanalytics-colombia`).
   * Sube los archivos al repositorio.
2. **Conecta Netlify con GitHub:**
   * Inicia sesión en [netlify.com](https://www.netlify.com).
   * Haz clic en **"Add new site"** > **"Import an existing project"** > Selecciona **GitHub**.
   * Elige tu repositorio `lottoanalytics-colombia`.
   * En "Publish directory" déjalo vacío o pon `.` (ya está configurado en `netlify.toml`).
   * Haz clic en **"Deploy Site"**. ¡Tu web estará al aire en 30 segundos!
3. El GitHub Action ejecutará los barridos nocturnos automáticamente y Netlify redesplegará el sitio en vivo en menos de 30 segundos tras cada sorteo.

### Método 2: Despliegue Inmediato Drag & Drop (Sin GitHub)
1. Entra a [app.netlify.com/drop](https://app.netlify.com/drop).
2. Arrastra la carpeta `web_app` a la ventana del navegador.
3. Tendrás tu enlace público inmediato en segundos.

---

## 💰 Configuración de Monetización

### 1. Google AdSense (Publicidad Display)
El código incluye 3 espacios publicitarios optimizados:
* **Banner Superior (`#top-ad-slot`)**
* **Banner In-Feed (`#middle-ad-slot`)**
* **Banner Inferior (`#bottom-ad-slot`)**

Para activarlos, abre `index.html`, descomenta la línea 32 con tu código `ca-pub-XXXXXXXXXXXXXXXX` y pega tus bloques de anuncios dentro de los contenedores `.ad-slot`.

### 2. Pagos por Nequi / Daviplata / WhatsApp
En `index.html` (línea 66), cambia el número de teléfono del enlace de WhatsApp (`https://wa.me/573000000000`) por tu número de contacto real de Bucaramanga para recibir los comprobantes de pago de los clientes VIP.
