# 📦 Crear Repositorio en GitHub

## Opción 1: Crear desde el navegador (RECOMENDADO)

1. **Ve a GitHub**: https://github.com/new
2. **Configura el repositorio**:
   - **Repository name**: `oye-api` (o el nombre que prefieras)
   - **Description**: "Dashboard de análisis de ventas Fudo"
   - **Visibilidad**: Elige Privado o Público
   - ⚠️ **NO marques** las opciones:
     - ❌ "Add a README file"
     - ❌ "Add .gitignore"
     - ❌ "Choose a license"
3. **Haz clic en "Create repository"**
4. **Luego vuelve aquí y ejecuta el push**

## Opción 2: Crear desde la terminal (requiere GitHub CLI)

Si tienes GitHub CLI instalado:

```bash
gh repo create oye-api --private --source=. --remote=origin --push
```

Si no tienes GitHub CLI, usa la Opción 1.

