"""
Script de prueba para verificar que el include funciona correctamente
y que se obtienen las categorías de productos con sus nombres
"""
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fudo_client import FudoAPIClient
from analytics import SalesAnalytics

load_dotenv()

def test_include_parameter():
    """Prueba que el parámetro include funciona correctamente"""
    print("=" * 70)
    print("🧪 PRUEBA: Parámetro include=items.product.productCategory")
    print("=" * 70)
    
    try:
        client = FudoAPIClient()
        
        # Obtener ventas de los últimos 7 días con include
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"\n📅 Consultando ventas desde {start_date.strftime('%Y-%m-%d')} hasta {end_date.strftime('%Y-%m-%d')}")
        print("   Endpoint: GET /sales?include=items.product.productCategory")
        
        sales_data = client.get_sales(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d"),
            include_related=True
        )
        
        print(f"\n✅ Respuesta recibida")
        print(f"   Cantidad de ventas: {len(sales_data)}")
        
        # Verificar que tenemos datos incluidos
        if hasattr(client, '_included_data'):
            included_data = client._included_data
            print(f"\n✅ Datos incluidos encontrados: {len(included_data)} entidades")
            
            # Agrupar por tipo
            types_count = {}
            for key in included_data.keys():
                entity_type = key.split(':')[0] if ':' in key else 'unknown'
                types_count[entity_type] = types_count.get(entity_type, 0) + 1
            
            print(f"\n📊 Distribución por tipo:")
            for entity_type, count in types_count.items():
                print(f"   - {entity_type}: {count}")
            
            # Mostrar algunos ejemplos
            print(f"\n📋 Ejemplos de entidades incluidas:")
            sample_count = 0
            for key, entity in included_data.items():
                if sample_count >= 5:
                    break
                entity_type, entity_id = key.split(':', 1) if ':' in key else (key, 'unknown')
                print(f"\n   {entity_type} (ID: {entity_id}):")
                if isinstance(entity, dict):
                    print(f"      Keys: {list(entity.keys())[:10]}")
                    if 'attributes' in entity:
                        attrs = entity['attributes']
                        if isinstance(attrs, dict):
                            print(f"      Attributes keys: {list(attrs.keys())[:10]}")
                    if 'relationships' in entity:
                        rels = entity['relationships']
                        if isinstance(rels, dict):
                            print(f"      Relationships keys: {list(rels.keys())[:10]}")
                sample_count += 1
        else:
            print(f"\n⚠️  No se encontraron datos incluidos (_included_data)")
            print("   Verifica que la API esté retornando el campo 'included' en la respuesta")
        
        # Verificar estructura de las ventas
        if len(sales_data) > 0:
            print(f"\n📊 Estructura de la primera venta:")
            first_sale = sales_data[0]
            print(f"   Keys principales: {list(first_sale.keys())[:15]}")
            
            if 'relationships' in first_sale:
                rels = first_sale['relationships']
                if isinstance(rels, dict):
                    print(f"   Relationships keys: {list(rels.keys())}")
                    if 'items' in rels:
                        items_rel = rels['items']
                        print(f"   Items relationship: {type(items_rel)}")
                        if isinstance(items_rel, dict) and 'data' in items_rel:
                            items_data = items_rel['data']
                            print(f"   Items data: {type(items_data)}")
                            if isinstance(items_data, list) and len(items_data) > 0:
                                print(f"   Primer item: {items_data[0]}")
        
        return sales_data, client
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None

def test_category_extraction(sales_data, client):
    """Prueba la extracción de categorías desde los datos incluidos"""
    print("\n" + "=" * 70)
    print("🧪 PRUEBA: Extracción de Categorías")
    print("=" * 70)
    
    if not sales_data or not client:
        print("\n⚠️  No hay datos para procesar")
        return None
    
    try:
        # Crear analytics con los datos
        analytics = SalesAnalytics(sales_data, timezone="America/Argentina/Buenos_Aires", api_client=client)
        
        # Verificar datos incluidos
        if hasattr(client, '_included_data'):
            included_data = client._included_data
            print(f"\n✅ Datos incluidos disponibles: {len(included_data)} entidades")
            
            # Construir mapeos manualmente para verificar
            item_product_map = {}
            product_category_map = {}
            category_name_map = {}
            
            for key, entity in included_data.items():
                entity_type, entity_id = key.split(':', 1) if ':' in key else (None, None)
                if not entity_type or not entity_id:
                    continue
                
                if entity_type == 'items':
                    if 'relationships' in entity and 'product' in entity['relationships']:
                        product_rel = entity['relationships']['product']
                        if isinstance(product_rel, dict):
                            if 'data' in product_rel:
                                product_data = product_rel['data']
                                if isinstance(product_data, dict):
                                    product_id = product_data.get('id')
                                    if product_id:
                                        item_product_map[entity_id] = product_id
                                        print(f"   ✅ Item {entity_id} -> Product {product_id}")
                            elif 'id' in product_rel:
                                item_product_map[entity_id] = product_rel['id']
                                print(f"   ✅ Item {entity_id} -> Product {product_rel['id']}")
                
                elif entity_type == 'products':
                    if 'relationships' in entity:
                        rels = entity['relationships']
                        if 'productCategory' in rels:
                            cat_rel = rels['productCategory']
                        elif 'ProductCategory' in rels:
                            cat_rel = rels['ProductCategory']
                        else:
                            cat_rel = None
                        
                        if cat_rel and isinstance(cat_rel, dict):
                            if 'data' in cat_rel:
                                cat_data = cat_rel['data']
                                if isinstance(cat_data, dict):
                                    category_id = cat_data.get('id')
                                    if category_id:
                                        product_category_map[entity_id] = category_id
                                        print(f"   ✅ Product {entity_id} -> Category {category_id}")
                            elif 'id' in cat_rel:
                                product_category_map[entity_id] = cat_rel['id']
                                print(f"   ✅ Product {entity_id} -> Category {cat_rel['id']}")
                
                elif entity_type == 'product-categories' or entity_type == 'productCategories':
                    category_name = None
                    if 'attributes' in entity and isinstance(entity['attributes'], dict):
                        attrs = entity['attributes']
                        if 'name' in attrs:
                            category_name = str(attrs['name']).strip()
                        elif 'title' in attrs:
                            category_name = str(attrs['title']).strip()
                        elif 'label' in attrs:
                            category_name = str(attrs['label']).strip()
                    elif 'name' in entity:
                        category_name = str(entity['name']).strip()
                    
                    if category_name:
                        category_name_map[entity_id] = category_name
                        print(f"   ✅ Category {entity_id} -> Name: '{category_name}'")
            
            print(f"\n📊 Resumen de mapeos:")
            print(f"   Items -> Products: {len(item_product_map)}")
            print(f"   Products -> Categories: {len(product_category_map)}")
            print(f"   Categories -> Names: {len(category_name_map)}")
            
            # Mostrar nombres de categorías únicos
            unique_categories = set(category_name_map.values())
            print(f"\n🏷️  Categorías encontradas ({len(unique_categories)}):")
            for cat_name in sorted(unique_categories):
                print(f"   - {cat_name}")
            
            # Probar la función get_sales_by_category
            print(f"\n🧪 Probando get_sales_by_category()...")
            category_data = analytics.get_sales_by_category(debug=True)
            
            if not category_data.empty:
                print(f"\n✅ Categorías obtenidas: {len(category_data)}")
                print(f"\n📊 Datos por categoría:")
                for idx, row in category_data.iterrows():
                    print(f"   {row['category']}: ${row['total_sales']:,.2f} ({row['num_transactions']} transacciones)")
            else:
                print(f"\n⚠️  No se obtuvieron datos de categorías")
        
        return analytics
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Ejecuta todas las pruebas"""
    print("\n" + "=" * 70)
    print("🧪 PRUEBAS DE INCLUDE Y CATEGORÍAS")
    print("=" * 70)
    
    # Prueba 1: Verificar que include funciona
    sales_data, client = test_include_parameter()
    
    # Prueba 2: Verificar extracción de categorías
    analytics = test_category_extraction(sales_data, client)
    
    print("\n" + "=" * 70)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 70)

if __name__ == "__main__":
    main()

