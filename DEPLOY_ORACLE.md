# Despliegue del Cripto Radar IA en Oracle VPS (guía paso a paso)

Meta: que el radar corra 24/7 en un servidor gratuito de Oracle Cloud.

---

## FASE 1 — Crear la máquina virtual gratis (10 min)

1. Entrá a **https://cloud.oracle.com** e iniciá sesión con tu cuenta de Oracle.
2. En el menú hamburguesa (☰, arriba a la izquierda) → **Compute** → **Instances**.
3. Botón **"Create instance"**.
4. **Name**: poné `cripto-radar`.
5. **Placement**: dejá lo que venga por defecto (si te avisa "Always Free eligible", perfecto).
6. **Image and shape** → botón **"Change image"**: elegí **Canonical Ubuntu 24.04** (o 22.04).
   - **Change shape**: elegí **Ampere** → `VM.Standard.A1.Flex` (es la gratis). Dejá **4 OCPU / 24 GB RAM** (o los límites que te muestre).
7. **Networking**: dejá todo por defecto (VCN y subred pública ya creadas automáticamente).
8. **Add SSH keys**: elegí **"Generate a key pair for me"**. 
   - Se te **descarga un archivo** (ej. `ssh-key-2026-09-23.key`). **GUARDALO BIEN** (es tu llave para entrar al servidor — no lo pierdas). Quedará en tu carpeta *Descargas*.
9. Botón **"Create"** (abajo).
10. Esperá 1-2 minutos hasta que la instancia muestre **estado "Running"** (verde).
11. Copiate la **IP pública** (aparece en la instancia, ej. `129.146.xx.xx`). La vas a necesitar.

✅ Cuando esté **Running** y tengas la **IP pública** y el **archivo .key** descargado, avisame.

---

## FASE 2 — Conectar al servidor (SSH) — te guío cuando lleguemos

- En Windows, se usa **Windows Terminal** o **PuTTY** con el archivo `.key`.
- También se puede entrar desde el navegador con la **"Console connection"** de Oracle (sin instalar nada).

---

## FASE 3 — Instalar y programar el radar

- Instalar Python + `uv` en el servidor.
- Subir los scripts (`opportunity_scanner.py`, `watchlist_analyst.py`, `notify.py`, `config.json`).
- Configurar `cron` para que corran solos cada X minutos.

---

## Datos importantes que NO debés perder
- **IP pública** del servidor.
- **Archivo `.key`** (la llave SSH).
- El **token de Telegram** ya está en `config.json` (local).
