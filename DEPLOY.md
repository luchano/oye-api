# 🚀 Guía de Deploy - Streamlit Cloud

Esta guía te ayudará a desplegar tu dashboard de ventas en Streamlit Cloud usando GitHub.

## 📋 Requisitos Previos

1. **Cuenta de GitHub** (gratis)
2. **Cuenta de Streamlit Cloud** (gratis) - Regístrate en https://streamlit.io/cloud
3. **Repositorio en GitHub** con tu código

## 🔧 Paso 1: Preparar el Repositorio en GitHub

### 1.1. Inicializar Git (si aún no lo has hecho)

```bash
cd /Users/luchano/Documents/Oye/oye-api
git init
```

### 1.2. Verificar que .gitignore esté configurado correctamente

Asegúrate de que `.gitignore` incluya:
- `.env` (no subir credenciales)
- `venv/` (entorno virtual)
- `__pycache__/`

### 1.3. Crear un repositorio en GitHub

1. Ve a https://github.com/new
2. Crea un nuevo repositorio (ej: `oye-dashboard`)
3. **NO** inicialices con README, .gitignore o licencia (ya los tienes)

### 1.4. Subir tu código a GitHub

```bash
# Agregar todos los archivos
git add .

# Hacer commit
git commit -m "Initial commit: Dashboard de ventas Fudo"

# Agregar el repositorio remoto (reemplaza USERNAME y REPO_NAME)
git remote add origin https://github.com/USERNAME/REPO_NAME.git

# Cambiar a la rama main (si es necesario)
git branch -M main

# Subir el código
git push -u origin main
```

## 🌐 Paso 2: Configurar Streamlit Cloud

### 2.1. Conectar con GitHub

1. Ve a https://share.streamlit.io/
2. Inicia sesión con tu cuenta de GitHub
3. Haz clic en "New app"

### 2.2. Configurar la aplicación

- **Repository**: Selecciona tu repositorio (`USERNAME/REPO_NAME`)
- **Branch**: `main` (o la rama que uses)
- **Main file path**: `app.py`

### 2.3. Configurar Variables de Entorno

En la sección "Advanced settings", agrega las siguientes variables de entorno:

```
FUDO_ENVIRONMENT=production
FUDO_API_KEY=tu_api_key_aqui
FUDO_API_SECRET=tu_api_secret_aqui
DASHBOARD_PASSWORD=tu_contraseña_segura
```

⚠️ **IMPORTANTE**: 
- Reemplaza `tu_api_key_aqui` y `tu_api_secret_aqui` con tus credenciales reales de Fudo.
- Reemplaza `tu_contraseña_segura` con la contraseña que quieres usar para proteger el dashboard.
- Si no configuras `DASHBOARD_PASSWORD`, el dashboard será accesible sin contraseña (modo desarrollo).

### 2.4. Desplegar

Haz clic en "Deploy!" y espera a que Streamlit Cloud construya tu aplicación (generalmente toma 1-2 minutos).

## 🔗 Paso 3: Acceder a tu Dashboard

Una vez desplegado, Streamlit Cloud te dará una URL como:
```
https://USERNAME-REPO-NAME.streamlit.app
```

Esta URL será permanente y accesible desde cualquier lugar.

## 🔄 Actualizar la Aplicación

Para actualizar tu dashboard:

1. Haz cambios en tu código local
2. Haz commit y push a GitHub:
```bash
git add .
git commit -m "Descripción de los cambios"
git push
```

Streamlit Cloud detectará automáticamente los cambios y redeployará la aplicación (puede tomar 1-2 minutos).

## 🔒 Seguridad

- ✅ **NUNCA** subas el archivo `.env` a GitHub
- ✅ Usa variables de entorno en Streamlit Cloud para credenciales
- ✅ El archivo `.gitignore` ya está configurado para ignorar `.env`

## 🛠️ Solución de Problemas

### Error: "Module not found"
- Verifica que todas las dependencias estén en `requirements.txt`
- Asegúrate de incluir la versión específica (ej: `streamlit==1.28.1`)

### Error: "API authentication failed"
- Verifica que las variables de entorno estén configuradas correctamente en Streamlit Cloud
- Revisa que las credenciales sean válidas

### La app no se actualiza
- Espera 1-2 minutos después del push
- Verifica que el push se haya completado correctamente en GitHub
- Revisa los logs en Streamlit Cloud (sección "Manage app")

## 📚 Recursos Adicionales

- [Documentación de Streamlit Cloud](https://docs.streamlit.io/streamlit-community-cloud)
- [Soporte de Streamlit](https://discuss.streamlit.io/)

---

¡Tu dashboard estará disponible 24/7 en la nube! 🎉

