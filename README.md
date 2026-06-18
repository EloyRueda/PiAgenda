# PiAgenda
Una solución ligera, autohospedada y eficiente de **agenda personal y gestión de tareas**, diseñada específicamente para correr de forma nativa en servidores domésticos como **Raspberry Pi**. 

Este proyecto está dividido en dos componentes clave para maximizar el rendimiento y la estabilidad:
1. **`agenda-web`**: Interfaz de usuario accesible desde cualquier dispositivo de la red local.
2. **`agenda-cron`**: Motor en segundo plano que procesa recordatorios, alertas y mantenimiento de tareas de forma automática.

---

## 🚀 Características Clave

* 📱 **Interfaz Web Responsiva:** Gestiona tus eventos y tareas de forma fluida desde el móvil, tablet u ordenador.
* ⚙️ **Arquitectura Desacoplada:** El frontend web y el procesador de tareas corren de forma independiente bajo `systemd`.
* 💾 **Almacenamiento Local Seguro:** Base de datos ligera optimizada para el almacenamiento de la Raspberry Pi.
* 🔒 **Privacidad Total:** Tus datos no salen de tu red local; sin telemetría ni dependencias de nubes externas.

---

## 🛠️ Estructura del Proyecto

```text
├── src/
│   ├── web/               # Código de la aplicación web (Flask/Node/etc.)
│   └── cron/              # Scripts de automatización y tareas programadas
├── config/
│   └── agenda.env.example # Plantilla para variables de entorno
└── systemd/
    ├── agenda-web.service # Archivo de servicio systemd para la Web
    └── agenda-cron.service# Archivo de servicio systemd para el Cron
