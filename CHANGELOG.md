# 🚀 Novedades y Ajustes VIP v2.0 - LottoAnalytics Colombia

Este documento detalla los 3 ajustes y mejoras solicitados para la Suite VIP:

---

### 🎯 1. Optimizar Mis Números Favoritos (Hasta 3 números y Multi-Sorteo)
* **Antes:** Solo permitía 2 casillas y estaba prefijado para Baloto.
* **Ahora:**
  * **Selector de Sorteo Independiente:** Permite elegir entre **Baloto Tradicional**, **Baloto Revancha** y **MiLoto**. Al cambiar a MiLoto, los límites numéricos se ajustan automáticamente del 1 al 39 y se omite la Superbalota.
  * **Hasta 3 balotas fijas:** Se agregaron 3 casillas independientes (`vip-f1`, `vip-f2`, `vip-f3`). El usuario puede ingresar 1, 2 o hasta 3 de sus números favoritos.
  * **Cálculo de afinidad:** El algoritmo toma las balotas elegidas y completa las restantes utilizando la matriz de parejas más frecuentes (co-ocurrencia) y asegurando que la suma total caiga en el rango central del 50% de la campana de Gauss del sorteo seleccionado.

---

### 📡 2. Radar de Atrasos Críticos (>1.5x) con Identificación Clara
* **Antes:** No especificaba a qué sorteo pertenecían las balotas mostradas.
* **Ahora:**
  * **Selector de Sorteo:** Se agregó un menú desplegable para consultar por separado el Radar de **Baloto Tradicional**, **Baloto Revancha** o **MiLoto**.
  * **Detalles Explícitos:** Muestra el nombre del juego, la fecha del último sorteo analizado, los sorteos exactos que lleva cada balota sin salir, su intervalo promedio histórico y su índice de desviación crítica.
  * **Fundamento Explicado:** Aclara que las balotas que superan 1.5x su promedio entran en una ventana estadística típica de retorno en los siguientes 3 a 5 sorteos.

---

### 🔒 3. Generador de Jugada Única Privada (Multi-Sorteo y Fundamento Matemático)
* **Antes:** Solo generaba para Baloto y no explicaba en qué se basaba el número.
* **Ahora:**
  * **Compatible con Baloto, Revancha y MiLoto:** Permite elegir el juego deseado. En MiLoto genera 5 balotas del 1 al 39 con suma óptima [81 - 114]. En Baloto/Revancha genera 5 balotas del 1 al 43 + Superbalota con suma [89 - 130].
  * **¿En qué se basa el número que entrega?**
    1. **Asignación Única Criptográfica:** Cada boleto se sella con un código hash único de control (ej. `#VIP-BAL-8D2A` o `#VIP-MIL-3F1C`) generado exclusivamente para la sesión actual del usuario, asegurando que no se repita con otros suscriptores.
    2. **Filtro Anti-Aglomeración (Teoría de Juegos):** La gran mayoría de personas juega fechas de cumpleaños (del 1 al 31). Este algoritmo fuerza la dispersión incluyendo números superiores a 31 para garantizar que, en caso de acertar el premio mayor, no se tenga que compartir el dinero con decenas de ganadores.
    3. **Calibración Gaussiana y Paridad:** La combinación respeta estrictamente la campana de Gauss histórica y el balance de 3 Pares / 2 Impares o 2 Pares / 3 Impares (más del 61% de los sorteos reales).
