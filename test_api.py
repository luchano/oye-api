"""
Script de prueba para verificar la conexión y funcionamiento de la API de Fudo
"""
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fudo_client import FudoAPIClient
from analytics import SalesAnalytics

load_dotenv()

def test_api_connection():
    """Prueba la conexión básica a la API"""
    print("=" * 70)
    print("🔍 PRUEBA 1: Conexión a la API")
    print("=" * 70)
    
    # Verificar variables de entorno
    api_key = os.getenv("FUDO_API_KEY")
    api_secret = os.getenv("FUDO_API_SECRET")
    
    print(f"\n✅ API Key configurada: {'Sí' if api_key and api_key != 'tu_api_key_aqui' else 'No'}")
    print(f"✅ API Secret configurada: {'Sí' if api_secret and api_secret != 'tu_api_secret_aqui' else 'No'}")
    
    if not api_key or api_key == 'tu_api_key_aqui' or not api_secret or api_secret == 'tu_api_secret_aqui':
        print("\n⚠️  ADVERTENCIA: Las credenciales no están configuradas correctamente.")
        print("   Por favor, configura FUDO_API_KEY y FUDO_API_SECRET en tu archivo .env")
        return False
    
    # Intentar crear cliente
    try:
        client = FudoAPIClient()
        print(f"\n✅ Cliente creado exitosamente")
        print(f"   URL API: {client.api_url}")
        print(f"   URL Auth: {client.auth_url}")
        
        # Verificar token
        if client.token:
            print(f"✅ Token obtenido: {client.token[:20]}...")
            print(f"   Expira en: {datetime.fromtimestamp(client.token_expires_at)}")
        else:
            print("⚠️  No se pudo obtener token")
            return False
            
        return True
    except Exception as e:
        print(f"\n❌ Error al crear cliente: {str(e)}")
        return False

def test_sales_endpoint():
    """Prueba el endpoint de ventas"""
    print("\n" + "=" * 70)
    print("🔍 PRUEBA 2: Endpoint de Ventas")
    print("=" * 70)
    
    try:
        client = FudoAPIClient()
        
        # Obtener ventas de los últimos 7 días
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"\n📅 Consultando ventas desde {start_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}")
        print("   Endpoint: GET /sales")
        print("   Filtro: filter[createdAt]=and(gte.FECHA,lte.FECHA)")
        
        sales_data = client.get_sales(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        print(f"\n✅ Respuesta recibida")
        print(f"   Tipo: {type(sales_data)}")
        print(f"   Cantidad de registros: {len(sales_data) if isinstance(sales_data, list) else 'N/A'}")
        
        if isinstance(sales_data, list) and len(sales_data) > 0:
            print(f"\n📊 Primer registro de ejemplo:")
            first_sale = sales_data[0]
            print(json.dumps(first_sale, indent=2, default=str))
            
            # Verificar campos importantes
            print(f"\n🔍 Verificación de campos:")
            required_fields = ['createdAt', 'totalAmount', 'id', 'saleId']
            found_fields = []
            missing_fields = []
            
            for field in required_fields:
                if field in first_sale:
                    found_fields.append(field)
                    print(f"   ✅ {field}: {first_sale[field]}")
                else:
                    missing_fields.append(field)
            
            # Buscar campos alternativos
            if 'createdAt' not in first_sale:
                for alt_field in ['created_at', 'date', 'datetime', 'timestamp']:
                    if alt_field in first_sale:
                        print(f"   ⚠️  Campo alternativo encontrado: {alt_field}")
                        found_fields.append(alt_field)
                        break
            
            if 'totalAmount' not in first_sale:
                for alt_field in ['total_amount', 'amount', 'total', 'price', 'value']:
                    if alt_field in first_sale:
                        print(f"   ⚠️  Campo alternativo encontrado: {alt_field}")
                        found_fields.append(alt_field)
                        break
            
            return sales_data
        else:
            print("\n⚠️  No se recibieron datos de ventas")
            print("   Esto puede significar:")
            print("   - No hay ventas en el período seleccionado")
            print("   - El formato de respuesta es diferente al esperado")
            return None
            
    except Exception as e:
        print(f"\n❌ Error al obtener ventas: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_data_processing(sales_data):
    """Prueba el procesamiento de datos"""
    print("\n" + "=" * 70)
    print("🔍 PRUEBA 3: Procesamiento de Datos")
    print("=" * 70)
    
    if not sales_data or len(sales_data) == 0:
        print("\n⚠️  No hay datos para procesar")
        return None
    
    try:
        # Usar zona horaria de Buenos Aires (GMT-3)
        analytics = SalesAnalytics(sales_data, timezone="America/Argentina/Buenos_Aires")
        
        print(f"\n✅ Datos procesados exitosamente")
        print(f"   Total de registros: {len(analytics.df)}")
        
        if analytics.df.empty:
            print("\n⚠️  El DataFrame está vacío después del procesamiento")
            return None
        
        # Mostrar información del DataFrame
        print(f"\n📊 Información del DataFrame:")
        print(f"   Columnas: {list(analytics.df.columns)}")
        print(f"\n   Primeras filas:")
        print(analytics.df.head().to_string())
        
        # Verificar campos procesados
        print(f"\n🔍 Campos procesados:")
        if 'datetime' in analytics.df.columns:
            print(f"   ✅ datetime: {analytics.df['datetime'].notna().sum()} valores válidos")
        else:
            print(f"   ❌ datetime: No encontrado")
        
        if 'amount' in analytics.df.columns:
            print(f"   ✅ amount: {analytics.df['amount'].notna().sum()} valores válidos")
            print(f"      Suma total: ${analytics.df['amount'].sum():,.2f}")
            print(f"      Promedio: ${analytics.df['amount'].mean():,.2f}")
        else:
            print(f"   ❌ amount: No encontrado")
        
        if 'date' in analytics.df.columns:
            print(f"   ✅ date: {analytics.df['date'].notna().sum()} valores válidos")
        
        if 'hour' in analytics.df.columns:
            print(f"   ✅ hour: {analytics.df['hour'].notna().sum()} valores válidos")
            # Mostrar algunos ejemplos de horas convertidas
            if analytics.df['datetime'].notna().any():
                print(f"      Ejemplos de fechas/horas convertidas:")
                sample_datetimes = analytics.df[analytics.df['datetime'].notna()][['datetime', 'hour']].head(5)
                for idx, row in sample_datetimes.iterrows():
                    print(f"         {row['datetime']} -> Hora: {int(row['hour'])}")
        
        return analytics
        
    except Exception as e:
        print(f"\n❌ Error al procesar datos: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_analytics_functions(analytics):
    """Prueba las funciones de análisis"""
    print("\n" + "=" * 70)
    print("🔍 PRUEBA 4: Funciones de Análisis")
    print("=" * 70)
    
    if analytics is None or analytics.df.empty:
        print("\n⚠️  No hay datos para analizar")
        return
    
    try:
        # Probar ventas por día
        print("\n📅 Probando get_sales_by_day()...")
        daily = analytics.get_sales_by_day()
        if not daily.empty:
            print(f"   ✅ Datos diarios: {len(daily)} días")
            print(f"   Primeros días:")
            print(daily.head().to_string())
        else:
            print("   ❌ No se generaron datos diarios")
        
        # Probar ventas por hora
        print("\n🕐 Probando get_sales_by_hour()...")
        hourly = analytics.get_sales_by_hour()
        if not hourly.empty:
            print(f"   ✅ Datos horarios: {len(hourly)} horas")
            print(f"   Primeras horas:")
            print(hourly.head().to_string())
        else:
            print("   ❌ No se generaron datos horarios")
        
        # Probar ventas por mes
        print("\n📆 Probando get_sales_by_month()...")
        monthly = analytics.get_sales_by_month()
        if not monthly.empty:
            print(f"   ✅ Datos mensuales: {len(monthly)} meses")
            print(monthly.to_string())
        else:
            print("   ❌ No se generaron datos mensuales")
        
        # Probar métricas clave
        print("\n📈 Probando get_key_metrics()...")
        metrics = analytics.get_key_metrics()
        if metrics:
            print(f"   ✅ Métricas obtenidas:")
            print(json.dumps(metrics, indent=2, default=str))
        else:
            print("   ❌ No se generaron métricas")
            
    except Exception as e:
        print(f"\n❌ Error en funciones de análisis: {str(e)}")
        import traceback
        traceback.print_exc()

def test_raw_api_response():
    """Hace una petición directa a la API para ver la respuesta cruda"""
    print("\n" + "=" * 70)
    print("🔍 PRUEBA 5: Respuesta Cruda de la API")
    print("=" * 70)
    
    try:
        client = FudoAPIClient()
        
        # Hacer petición directa
        params = {
            "page[size]": "10",  # Solo pedir 10 registros para prueba
            "page[number]": "1"
        }
        
        print("\n📡 Haciendo petición directa a /sales...")
        response = client._make_request("sales", params=params)
        
        print(f"\n✅ Respuesta recibida:")
        print(f"   Tipo: {type(response)}")
        print(f"\n📄 Respuesta completa (primeros 2000 caracteres):")
        response_str = json.dumps(response, indent=2, default=str)
        print(response_str[:2000])
        if len(response_str) > 2000:
            print("\n... (respuesta truncada)")
            
        # Guardar respuesta completa en archivo para análisis
        with open("api_response_sample.json", "w") as f:
            json.dump(response, f, indent=2, default=str)
        print(f"\n💾 Respuesta completa guardada en: api_response_sample.json")
        
    except Exception as e:
        print(f"\n❌ Error al obtener respuesta cruda: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Ejecuta todas las pruebas"""
    print("\n" + "=" * 70)
    print("🧪 PRUEBAS DE LA API DE FUDO")
    print("=" * 70)
    
    # Prueba 1: Conexión
    if not test_api_connection():
        print("\n" + "=" * 70)
        print("❌ PRUEBAS DETENIDAS: No se pudo conectar a la API")
        print("=" * 70)
        return
    
    # Prueba 2: Endpoint de ventas
    sales_data = test_sales_endpoint()
    
    # Prueba 3: Procesamiento de datos
    analytics = test_data_processing(sales_data)
    
    # Prueba 4: Funciones de análisis
    test_analytics_functions(analytics)
    
    # Prueba 5: Respuesta cruda (opcional, comentado para no sobrecargar)
    # test_raw_api_response()
    
    print("\n" + "=" * 70)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 70)
    print("\n💡 Si hay errores, revisa:")
    print("   1. Las credenciales en el archivo .env")
    print("   2. El formato de respuesta de la API")
    print("   3. Los campos mapeados en analytics.py")
    print("\n")

if __name__ == "__main__":
    main()

