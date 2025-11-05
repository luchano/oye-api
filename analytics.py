"""
Funciones de análisis estratégico de ventas
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz


class SalesAnalytics:
    """Clase para análisis de ventas"""
    
    def __init__(self, sales_data: List[Dict], timezone: str = "America/Argentina/Buenos_Aires", 
                 api_client: Optional[object] = None):
        """
        Inicializa el analizador con datos de ventas
        
        Args:
            sales_data: Lista de diccionarios con datos de ventas
            timezone: Zona horaria para convertir las fechas (default: America/Argentina/Buenos_Aires - GMT-3)
            api_client: Cliente de API de Fudo (opcional, necesario para obtener categorías)
        """
        self.df = pd.DataFrame(sales_data)
        self.timezone = pytz.timezone(timezone)
        self.api_client = api_client
        
        # Cache para datos relacionados
        self._items_cache = {}
        self._products_cache = {}
        self._categories_cache = {}
        
        # Normalizar y procesar datos
        if not self.df.empty:
            self._process_data()
    
    def _process_data(self):
        """Procesa y normaliza los datos de ventas"""
        # La API de Fudo usa formato JSON:API con datos en 'attributes'
        
        # Extraer datos del objeto 'attributes' si existe
        if 'attributes' in self.df.columns:
            # Extraer campos de attributes
            attributes_df = pd.json_normalize(self.df['attributes'])
            
            # Agregar columnas extraídas al DataFrame principal
            for col in attributes_df.columns:
                # Renombrar para evitar conflictos
                new_col = col.replace('.', '_') if '.' in col else col
                self.df[new_col] = attributes_df[col]
        
        # Mapear campo de fecha
        # La API de Fudo usa: attributes.createdAt
        date_column = None
        for col in ['createdAt', 'attributes_createdAt', 'datetime', 'date', 'created_at', 'created']:
            if col in self.df.columns:
                date_column = col
                break
        
        if date_column:
            # Convertir a datetime, asumiendo UTC si viene de la API
            self.df['datetime'] = pd.to_datetime(self.df[date_column], errors='coerce', utc=True)
            
            # Convertir de UTC a la zona horaria especificada (GMT-3 Buenos Aires)
            if self.df['datetime'].notna().any():
                # Convertir a la zona horaria local
                self.df['datetime'] = self.df['datetime'].dt.tz_convert(self.timezone)
        else:
            # Si no hay columna de fecha, crear una con la fecha actual en la zona horaria local
            self.df['datetime'] = pd.Timestamp.now(tz=self.timezone)
        
        # Extraer componentes de fecha (ya en la zona horaria correcta)
        self.df['date'] = self.df['datetime'].dt.date
        self.df['hour'] = self.df['datetime'].dt.hour
        self.df['month'] = self.df['datetime'].dt.to_period('M')
        self.df['weekday'] = self.df['datetime'].dt.day_name()
        
        # Calcular "día de servicio" para restaurante nocturno
        # El día de servicio va desde las 12:00 del día hasta las 05:00 del día siguiente
        # Todo se atribuye al día en que empezó (día de apertura)
        self.df['service_date'] = self.df['datetime'].apply(self._get_service_date)
        
        # Mapear campo de monto
        # La API de Fudo usa: attributes.total (en centavos/pesos chilenos)
        amount_column = None
        for col in ['total', 'attributes_total', 'totalAmount', 'amount', 'total_amount', 'price', 'value']:
            if col in self.df.columns:
                amount_column = col
                break
        
        if amount_column:
            # Convertir a numérico (el monto viene en centavos/pesos, mantener formato)
            self.df['amount'] = pd.to_numeric(self.df[amount_column], errors='coerce')
        else:
            # Si no hay columna de monto, usar 0
            self.df['amount'] = 0
        
        # Si el monto está en un formato de objeto (ej: {"currency": "USD", "value": 100})
        if self.df['amount'].isna().all() and 'total' in self.df.columns:
            # Intentar extraer el valor si es un diccionario
            if isinstance(self.df['total'].iloc[0], dict):
                self.df['amount'] = self.df['total'].apply(
                    lambda x: float(x.get('value', 0)) if isinstance(x, dict) else 0
                )
        
        # Asegurar que amount sea numérico y rellenar valores nulos con 0
        self.df['amount'] = pd.to_numeric(self.df['amount'], errors='coerce').fillna(0)
        
        # Asegurar que tengamos una columna id para contar transacciones
        if 'id' in self.df.columns:
            # El id ya existe
            pass
        elif 'saleId' in self.df.columns:
            self.df['id'] = self.df['saleId']
        elif 'orderId' in self.df.columns:
            self.df['id'] = self.df['orderId']
        else:
            self.df['id'] = range(1, len(self.df) + 1)
        
        # Mapear campo de número de personas (people/pax)
        people_column = None
        for col in ['people', 'attributes_people', 'pax', 'guests', 'customers', 'numberOfPeople', 'num_people']:
            if col in self.df.columns:
                people_column = col
                break
        
        if people_column:
            # Convertir a numérico
            self.df['people'] = pd.to_numeric(self.df[people_column], errors='coerce').fillna(0)
        else:
            # Si no hay columna de personas, usar 0
            self.df['people'] = 0
    
    def _get_service_date(self, dt):
        """
        Calcula el día de servicio para un restaurante nocturno.
        El día de servicio va desde las 12:00 del día hasta las 05:00 del día siguiente.
        Todo se atribuye al día en que empezó (día de apertura).
        
        Ejemplo:
        - 25/10 12:00 a 26/10 04:59 -> Día de servicio: 25/10
        - 26/10 05:00 a 27/10 04:59 -> Día de servicio: 26/10
        
        Args:
            dt: Timestamp con zona horaria
        
        Returns:
            date: Fecha del día de servicio (día en que empezó)
        """
        if pd.isna(dt):
            return None
        
        # Si la hora es antes de las 5:00 AM, pertenece al día de servicio anterior
        # (que empezó a las 12:00 del día anterior)
        if dt.hour < 5:
            # Es del día anterior (día de servicio que empezó ayer a las 12:00)
            return (dt.date() - pd.Timedelta(days=1))
        # Si la hora es >= 12:00 (mediodía), pertenece al día de servicio que empieza hoy
        elif dt.hour >= 12:
            return dt.date()
        # Si la hora está entre 5:00 AM y 11:59 AM, también pertenece al día de servicio anterior
        # (porque el día de servicio anterior terminó hoy a las 5am)
        else:
            # Entre 5am y 11:59am, pertenece al día de servicio que empezó ayer
            return (dt.date() - pd.Timedelta(days=1))
    
    def get_sales_by_day(self, fill_missing_days: bool = True) -> pd.DataFrame:
        """
        Obtiene ventas agrupadas por día de servicio.
        El día de servicio va desde las 12:00 del día hasta las 05:00 del día siguiente.
        
        Args:
            fill_missing_days: Si es True, completa los días faltantes con cero ventas
        """
        if self.df.empty:
            return pd.DataFrame()
        
        # Agrupar por día de servicio en lugar de día calendario
        daily_sales = self.df.groupby('service_date').agg({
            'amount': ['sum', 'mean', 'count'],
            'people': 'sum',
            'id': 'count'
        }).reset_index()
        
        daily_sales.columns = ['date', 'total_sales', 'avg_sale', 'num_transactions', 'total_people', 'count']
        # Convertir date a datetime manteniendo la zona horaria
        if not daily_sales.empty:
            # Si date viene como date object, convertir a datetime en la zona horaria correcta
            daily_sales['date'] = pd.to_datetime(daily_sales['date'])
        daily_sales = daily_sales.sort_values('date')
        
        # Completar días faltantes con cero ventas si se solicita
        if fill_missing_days and not daily_sales.empty:
            # Crear rango completo de fechas desde el primer día hasta el último
            start_date = daily_sales['date'].min()
            end_date = daily_sales['date'].max()
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            
            # Crear DataFrame con todas las fechas
            all_dates = pd.DataFrame({'date': date_range})
            
            # Hacer merge con los datos existentes
            daily_sales = all_dates.merge(daily_sales, on='date', how='left')
            
            # Rellenar valores faltantes con 0
            daily_sales['total_sales'] = daily_sales['total_sales'].fillna(0)
            daily_sales['avg_sale'] = daily_sales['avg_sale'].fillna(0)
            daily_sales['num_transactions'] = daily_sales['num_transactions'].fillna(0)
            daily_sales['total_people'] = daily_sales['total_people'].fillna(0)
            
            daily_sales = daily_sales.sort_values('date')
        
        return daily_sales[['date', 'total_sales', 'avg_sale', 'num_transactions', 'total_people']]
    
    def get_sales_by_hour(self) -> pd.DataFrame:
        """
        Obtiene ventas agrupadas por hora del día.
        Las horas se reorganizan comenzando desde las 12:00 (mediodía) 
        y continuando por las siguientes 24 horas.
        """
        if self.df.empty:
            return pd.DataFrame()
        
        hourly_sales = self.df.groupby('hour').agg({
            'amount': ['sum', 'mean', 'count'],
            'people': 'sum'
        }).reset_index()
        
        hourly_sales.columns = ['hour', 'total_sales', 'avg_sale', 'num_transactions', 'total_people']
        
        # Reorganizar horas: comenzar desde las 12:00 (mediodía) hasta las 23:00,
        # y luego desde las 0:00 hasta las 11:00
        # Crear una columna de orden: horas 12-23 primero, luego 0-11
        hourly_sales['hour_order'] = hourly_sales['hour'].apply(
            lambda x: x if x >= 12 else x + 24
        )
        
        # Ordenar por el orden de horas (12, 13, ..., 23, 24, 25, ..., 35)
        hourly_sales = hourly_sales.sort_values('hour_order')
        
        # Crear columna de hora para mostrar (12, 13, ..., 23, 0, 1, ..., 11)
        hourly_sales['display_hour'] = hourly_sales['hour']
        
        # Crear etiqueta de hora para el gráfico (12:00, 13:00, ..., 23:00, 0:00, 1:00, ..., 11:00)
        hourly_sales['hour_label'] = hourly_sales['hour'].apply(lambda x: f"{x:02d}:00")
        
        return hourly_sales[['hour', 'hour_order', 'display_hour', 'hour_label', 'total_sales', 'avg_sale', 'num_transactions', 'total_people']]
    
    def get_sales_by_hour_and_category(self, top_n: int = 10) -> pd.DataFrame:
        """
        Obtiene ventas agrupadas por hora del día y categoría de productos.
        Muestra las top N categorías más vendidas y agrupa el resto como "Otros".
        
        Args:
            top_n: Número de categorías principales a mostrar (default: 7)
        
        Returns:
            DataFrame con columns: hour, hour_order, hour_label, category, total_sales
        """
        if self.df.empty:
            return pd.DataFrame()
        
        # Obtener ventas por categoría para determinar las top N
        category_data = self.get_sales_by_category(debug=False)
        
        if category_data.empty:
            return pd.DataFrame()
        
        # Obtener las top N categorías por total de ventas
        top_categories = category_data.head(top_n)['category'].tolist()
        
        # Obtener datos incluidos del cliente de API
        included_data = {}
        if self.api_client and hasattr(self.api_client, '_included_data'):
            included_data = self.api_client._included_data
        
        # Construir mapeos (igual que en get_sales_by_category)
        item_product_map = {}
        product_category_map = {}
        category_name_map = {}
        
        for key, entity in included_data.items():
            entity_type = None
            entity_id = None
            
            if ':' in key:
                entity_type, entity_id = key.split(':', 1)
            else:
                if isinstance(entity, dict):
                    entity_type = entity.get('type', '')
                    entity_id = entity.get('id', '')
            
            if not entity_type or not entity_id:
                continue
            
            entity_type = entity_type.lower()
            
            if entity_type in ['items', 'item']:
                if 'relationships' in entity and isinstance(entity['relationships'], dict):
                    if 'product' in entity['relationships']:
                        product_rel = entity['relationships']['product']
                        if isinstance(product_rel, dict):
                            if 'data' in product_rel:
                                product_data = product_rel['data']
                                if isinstance(product_data, dict):
                                    product_id = product_data.get('id')
                                    if product_id:
                                        item_product_map[entity_id] = str(product_id)
            
            elif entity_type in ['products', 'product']:
                if 'relationships' in entity and isinstance(entity['relationships'], dict):
                    rels = entity['relationships']
                    cat_rel = None
                    for key_name in ['productCategory', 'ProductCategory', 'product-category', 'category']:
                        if key_name in rels:
                            cat_rel = rels[key_name]
                            break
                    
                    if cat_rel and isinstance(cat_rel, dict):
                        if 'data' in cat_rel:
                            cat_data = cat_rel['data']
                            if isinstance(cat_data, dict):
                                category_id = cat_data.get('id')
                                if category_id:
                                    product_category_map[entity_id] = str(category_id)
                        elif 'id' in cat_rel:
                            product_category_map[entity_id] = str(cat_rel['id'])
            
            elif entity_type in ['product-categories', 'productcategories', 'productcategory']:
                category_name = None
                if 'attributes' in entity and isinstance(entity['attributes'], dict):
                    attrs = entity['attributes']
                    if 'name' in attrs:
                        category_name = str(attrs['name']).strip()
                
                if category_name:
                    category_name_map[entity_id] = category_name
        
        # Construir mapeo item_id -> category_name
        item_category_map = {}
        for item_id, product_id in item_product_map.items():
            if product_id in product_category_map:
                category_id = product_category_map[product_id]
                if category_id in category_name_map:
                    item_category_map[item_id] = category_name_map[category_id]
        
        # Crear lista para almacenar ventas por hora y categoría
        hourly_category_sales = []
        
        # Iterar sobre cada venta
        for idx, row in self.df.iterrows():
            sale_id = row.get('id', idx)
            sale_amount = row.get('amount', 0)
            sale_hour = row.get('hour')
            
            if sale_amount == 0 or pd.isna(sale_hour):
                continue
            
            # Obtener items de la venta
            items_refs = None
            if 'relationships' in row and pd.notna(row['relationships']):
                rels = row['relationships']
                if isinstance(rels, dict) and 'items' in rels:
                    items_data = rels['items']
                    if isinstance(items_data, dict) and 'data' in items_data:
                        items_refs = items_data['data']
                    elif isinstance(items_data, list):
                        items_refs = items_data
            
            if not items_refs:
                continue
            
            if not isinstance(items_refs, list):
                items_refs = [items_refs]
            
            # Obtener categorías de los items
            categories_in_sale = []
            for item_ref in items_refs:
                item_id = None
                if isinstance(item_ref, dict):
                    item_id = item_ref.get('id')
                elif isinstance(item_ref, str):
                    item_id = item_ref
                
                if item_id and str(item_id) in item_category_map:
                    category_name = item_category_map[str(item_id)]
                    if category_name:
                        categories_in_sale.append(category_name)
            
            if not categories_in_sale:
                categories_in_sale = ['Sin categoría']
            
            # Dividir el monto entre las categorías
            amount_per_category = sale_amount / len(categories_in_sale)
            
            # Agregar venta para cada categoría
            for category in categories_in_sale:
                # Clasificar categoría: top N o "Otros"
                display_category = category if category in top_categories else 'Otros'
                
                hourly_category_sales.append({
                    'hour': int(sale_hour),
                    'category': display_category,
                    'amount': amount_per_category
                })
        
        if not hourly_category_sales:
            return pd.DataFrame()
        
        # Crear DataFrame y agrupar
        df_hourly_cat = pd.DataFrame(hourly_category_sales)
        
        hourly_category_agg = df_hourly_cat.groupby(['hour', 'category']).agg({
            'amount': 'sum'
        }).reset_index()
        
        hourly_category_agg.columns = ['hour', 'category', 'total_sales']
        
        # Agregar columnas de ordenamiento de horas
        hourly_category_agg['hour_order'] = hourly_category_agg['hour'].apply(
            lambda x: x if x >= 12 else x + 24
        )
        hourly_category_agg['hour_label'] = hourly_category_agg['hour'].apply(lambda x: f"{x:02d}:00")
        
        # Ordenar por hora y categoría
        hourly_category_agg = hourly_category_agg.sort_values(['hour_order', 'total_sales'], ascending=[True, False])
        
        return hourly_category_agg[['hour', 'hour_order', 'hour_label', 'category', 'total_sales']]
    
    def get_sales_by_month(self) -> pd.DataFrame:
        """Obtiene ventas agrupadas por mes"""
        if self.df.empty:
            return pd.DataFrame()
        
        monthly_sales = self.df.groupby('month').agg({
            'amount': ['sum', 'mean', 'count'],
            'people': 'sum'
        }).reset_index()
        
        monthly_sales.columns = ['month', 'total_sales', 'avg_sale', 'num_transactions', 'total_people']
        monthly_sales['month_str'] = monthly_sales['month'].astype(str)
        monthly_sales = monthly_sales.sort_values('month')
        
        return monthly_sales[['month', 'month_str', 'total_sales', 'avg_sale', 'num_transactions', 'total_people']]
    
    def get_sales_by_day_and_category(self, top_n: int = 10) -> pd.DataFrame:
        """
        Obtiene ventas agrupadas por día de servicio y categoría de productos.
        Muestra las top N categorías más vendidas y agrupa el resto como "Otros".
        
        Args:
            top_n: Número de categorías principales a mostrar (default: 7)
        
        Returns:
            DataFrame con columns: date, category, total_sales
        """
        if self.df.empty:
            return pd.DataFrame()
        
        # Obtener ventas por categoría para determinar las top N
        category_data = self.get_sales_by_category(debug=False)
        
        if category_data.empty:
            return pd.DataFrame()
        
        # Obtener las top N categorías por total de ventas
        top_categories = category_data.head(top_n)['category'].tolist()
        
        # Obtener datos incluidos del cliente de API
        included_data = {}
        if self.api_client and hasattr(self.api_client, '_included_data'):
            included_data = self.api_client._included_data
        
        # Construir mapeos (igual que en get_sales_by_category)
        item_product_map = {}
        product_category_map = {}
        category_name_map = {}
        
        for key, entity in included_data.items():
            entity_type = None
            entity_id = None
            
            if ':' in key:
                entity_type, entity_id = key.split(':', 1)
            else:
                if isinstance(entity, dict):
                    entity_type = entity.get('type', '')
                    entity_id = entity.get('id', '')
            
            if not entity_type or not entity_id:
                continue
            
            entity_type = entity_type.lower()
            
            if entity_type in ['items', 'item']:
                if 'relationships' in entity and isinstance(entity['relationships'], dict):
                    if 'product' in entity['relationships']:
                        product_rel = entity['relationships']['product']
                        if isinstance(product_rel, dict):
                            if 'data' in product_rel:
                                product_data = product_rel['data']
                                if isinstance(product_data, dict):
                                    product_id = product_data.get('id')
                                    if product_id:
                                        item_product_map[entity_id] = str(product_id)
            
            elif entity_type in ['products', 'product']:
                if 'relationships' in entity and isinstance(entity['relationships'], dict):
                    rels = entity['relationships']
                    cat_rel = None
                    for key_name in ['productCategory', 'ProductCategory', 'product-category', 'category']:
                        if key_name in rels:
                            cat_rel = rels[key_name]
                            break
                    
                    if cat_rel and isinstance(cat_rel, dict):
                        if 'data' in cat_rel:
                            cat_data = cat_rel['data']
                            if isinstance(cat_data, dict):
                                category_id = cat_data.get('id')
                                if category_id:
                                    product_category_map[entity_id] = str(category_id)
                        elif 'id' in cat_rel:
                            product_category_map[entity_id] = str(cat_rel['id'])
            
            elif entity_type in ['product-categories', 'productcategories', 'productcategory']:
                category_name = None
                if 'attributes' in entity and isinstance(entity['attributes'], dict):
                    attrs = entity['attributes']
                    if 'name' in attrs:
                        category_name = str(attrs['name']).strip()
                
                if category_name:
                    category_name_map[entity_id] = category_name
        
        # Construir mapeo item_id -> category_name
        item_category_map = {}
        for item_id, product_id in item_product_map.items():
            if product_id in product_category_map:
                category_id = product_category_map[product_id]
                if category_id in category_name_map:
                    item_category_map[item_id] = category_name_map[category_id]
        
        # Crear lista para almacenar ventas por día y categoría
        daily_category_sales = []
        
        # Iterar sobre cada venta
        for idx, row in self.df.iterrows():
            sale_id = row.get('id', idx)
            sale_amount = row.get('amount', 0)
            service_date = row.get('service_date')
            
            if sale_amount == 0 or pd.isna(service_date):
                continue
            
            # Obtener items de la venta
            items_refs = None
            if 'relationships' in row and pd.notna(row['relationships']):
                rels = row['relationships']
                if isinstance(rels, dict) and 'items' in rels:
                    items_data = rels['items']
                    if isinstance(items_data, dict) and 'data' in items_data:
                        items_refs = items_data['data']
                    elif isinstance(items_data, list):
                        items_refs = items_data
            
            if not items_refs:
                continue
            
            if not isinstance(items_refs, list):
                items_refs = [items_refs]
            
            # Obtener categorías de los items
            categories_in_sale = []
            for item_ref in items_refs:
                item_id = None
                if isinstance(item_ref, dict):
                    item_id = item_ref.get('id')
                elif isinstance(item_ref, str):
                    item_id = item_ref
                
                if item_id and str(item_id) in item_category_map:
                    category_name = item_category_map[str(item_id)]
                    if category_name:
                        categories_in_sale.append(category_name)
            
            if not categories_in_sale:
                categories_in_sale = ['Sin categoría']
            
            # Dividir el monto entre las categorías
            amount_per_category = sale_amount / len(categories_in_sale)
            
            # Agregar venta para cada categoría
            for category in categories_in_sale:
                # Clasificar categoría: top N o "Otros"
                display_category = category if category in top_categories else 'Otros'
                
                # Convertir service_date a datetime si es necesario
                if isinstance(service_date, pd.Timestamp):
                    date_value = service_date
                elif isinstance(service_date, str):
                    date_value = pd.to_datetime(service_date)
                else:
                    date_value = pd.to_datetime(service_date)
                
                daily_category_sales.append({
                    'date': date_value,
                    'category': display_category,
                    'amount': amount_per_category
                })
        
        if not daily_category_sales:
            return pd.DataFrame()
        
        # Crear DataFrame y agrupar
        df_daily_cat = pd.DataFrame(daily_category_sales)
        
        daily_category_agg = df_daily_cat.groupby(['date', 'category']).agg({
            'amount': 'sum'
        }).reset_index()
        
        daily_category_agg.columns = ['date', 'category', 'total_sales']
        
        # Asegurar que date sea datetime
        daily_category_agg['date'] = pd.to_datetime(daily_category_agg['date'])
        
        # Ordenar por fecha y categoría
        daily_category_agg = daily_category_agg.sort_values(['date', 'total_sales'], ascending=[True, False])
        
        return daily_category_agg[['date', 'category', 'total_sales']]
    
    def get_sales_by_month_and_category(self, top_n: int = 10) -> pd.DataFrame:
        """
        Obtiene ventas agrupadas por mes y categoría de productos.
        Muestra las top N categorías más vendidas y agrupa el resto como "Otros".
        
        Args:
            top_n: Número de categorías principales a mostrar (default: 7)
        
        Returns:
            DataFrame con columns: month, month_str, category, total_sales
        """
        if self.df.empty:
            return pd.DataFrame()
        
        # Obtener ventas por categoría para determinar las top N
        category_data = self.get_sales_by_category(debug=False)
        
        if category_data.empty:
            return pd.DataFrame()
        
        # Obtener las top N categorías por total de ventas
        top_categories = category_data.head(top_n)['category'].tolist()
        
        # Obtener datos incluidos del cliente de API
        included_data = {}
        if self.api_client and hasattr(self.api_client, '_included_data'):
            included_data = self.api_client._included_data
        
        # Construir mapeos (igual que en get_sales_by_category)
        item_product_map = {}
        product_category_map = {}
        category_name_map = {}
        
        for key, entity in included_data.items():
            entity_type = None
            entity_id = None
            
            if ':' in key:
                entity_type, entity_id = key.split(':', 1)
            else:
                if isinstance(entity, dict):
                    entity_type = entity.get('type', '')
                    entity_id = entity.get('id', '')
            
            if not entity_type or not entity_id:
                continue
            
            entity_type = entity_type.lower()
            
            if entity_type in ['items', 'item']:
                if 'relationships' in entity and isinstance(entity['relationships'], dict):
                    if 'product' in entity['relationships']:
                        product_rel = entity['relationships']['product']
                        if isinstance(product_rel, dict):
                            if 'data' in product_rel:
                                product_data = product_rel['data']
                                if isinstance(product_data, dict):
                                    product_id = product_data.get('id')
                                    if product_id:
                                        item_product_map[entity_id] = str(product_id)
            
            elif entity_type in ['products', 'product']:
                if 'relationships' in entity and isinstance(entity['relationships'], dict):
                    rels = entity['relationships']
                    cat_rel = None
                    for key_name in ['productCategory', 'ProductCategory', 'product-category', 'category']:
                        if key_name in rels:
                            cat_rel = rels[key_name]
                            break
                    
                    if cat_rel and isinstance(cat_rel, dict):
                        if 'data' in cat_rel:
                            cat_data = cat_rel['data']
                            if isinstance(cat_data, dict):
                                category_id = cat_data.get('id')
                                if category_id:
                                    product_category_map[entity_id] = str(category_id)
                        elif 'id' in cat_rel:
                            product_category_map[entity_id] = str(cat_rel['id'])
            
            elif entity_type in ['product-categories', 'productcategories', 'productcategory']:
                category_name = None
                if 'attributes' in entity and isinstance(entity['attributes'], dict):
                    attrs = entity['attributes']
                    if 'name' in attrs:
                        category_name = str(attrs['name']).strip()
                
                if category_name:
                    category_name_map[entity_id] = category_name
        
        # Construir mapeo item_id -> category_name
        item_category_map = {}
        for item_id, product_id in item_product_map.items():
            if product_id in product_category_map:
                category_id = product_category_map[product_id]
                if category_id in category_name_map:
                    item_category_map[item_id] = category_name_map[category_id]
        
        # Crear lista para almacenar ventas por mes y categoría
        monthly_category_sales = []
        
        # Iterar sobre cada venta
        for idx, row in self.df.iterrows():
            sale_id = row.get('id', idx)
            sale_amount = row.get('amount', 0)
            sale_month = row.get('month')
            
            if sale_amount == 0 or pd.isna(sale_month):
                continue
            
            # Obtener items de la venta
            items_refs = None
            if 'relationships' in row and pd.notna(row['relationships']):
                rels = row['relationships']
                if isinstance(rels, dict) and 'items' in rels:
                    items_data = rels['items']
                    if isinstance(items_data, dict) and 'data' in items_data:
                        items_refs = items_data['data']
                    elif isinstance(items_data, list):
                        items_refs = items_data
            
            if not items_refs:
                continue
            
            if not isinstance(items_refs, list):
                items_refs = [items_refs]
            
            # Obtener categorías de los items
            categories_in_sale = []
            for item_ref in items_refs:
                item_id = None
                if isinstance(item_ref, dict):
                    item_id = item_ref.get('id')
                elif isinstance(item_ref, str):
                    item_id = item_ref
                
                if item_id and str(item_id) in item_category_map:
                    category_name = item_category_map[str(item_id)]
                    if category_name:
                        categories_in_sale.append(category_name)
            
            if not categories_in_sale:
                categories_in_sale = ['Sin categoría']
            
            # Dividir el monto entre las categorías
            amount_per_category = sale_amount / len(categories_in_sale)
            
            # Agregar venta para cada categoría
            for category in categories_in_sale:
                # Clasificar categoría: top N o "Otros"
                display_category = category if category in top_categories else 'Otros'
                
                monthly_category_sales.append({
                    'month': sale_month,
                    'category': display_category,
                    'amount': amount_per_category
                })
        
        if not monthly_category_sales:
            return pd.DataFrame()
        
        # Crear DataFrame y agrupar
        df_monthly_cat = pd.DataFrame(monthly_category_sales)
        
        monthly_category_agg = df_monthly_cat.groupby(['month', 'category']).agg({
            'amount': 'sum'
        }).reset_index()
        
        monthly_category_agg.columns = ['month', 'category', 'total_sales']
        
        # Agregar columna month_str
        monthly_category_agg['month_str'] = monthly_category_agg['month'].astype(str)
        
        # Ordenar por mes y categoría
        monthly_category_agg = monthly_category_agg.sort_values(['month', 'total_sales'], ascending=[True, False])
        
        return monthly_category_agg[['month', 'month_str', 'category', 'total_sales']]
    
    def get_sales_by_weekday(self) -> pd.DataFrame:
        """
        Obtiene ventas agrupadas por día de la semana basado en día de servicio.
        """
        if self.df.empty:
            return pd.DataFrame()
        
        # Obtener el día de la semana del día de servicio
        self.df['service_weekday'] = pd.to_datetime(self.df['service_date']).dt.day_name()
        
        weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday_sales = self.df.groupby('service_weekday').agg({
            'amount': ['sum', 'mean', 'count']
        }).reset_index()
        
        weekday_sales.columns = ['weekday', 'total_sales', 'avg_sale', 'num_transactions']
        weekday_sales['weekday'] = pd.Categorical(weekday_sales['weekday'], categories=weekday_order, ordered=True)
        weekday_sales = weekday_sales.sort_values('weekday')
        
        return weekday_sales
    
    def get_key_metrics(self) -> Dict:
        """Obtiene métricas clave del negocio"""
        if self.df.empty:
            return {}
        
        total_sales = self.df['amount'].sum()
        total_transactions = len(self.df)
        avg_transaction = self.df['amount'].mean()
        median_transaction = self.df['amount'].median()
        
        # Mejor y peor día (solo días con ventas > 0)
        daily = self.get_sales_by_day(fill_missing_days=False)
        if not daily.empty:
            # Filtrar solo días con ventas > 0 para mejor/peor día
            daily_with_sales = daily[daily['total_sales'] > 0]
            if not daily_with_sales.empty:
                best_day = daily_with_sales.loc[daily_with_sales['total_sales'].idxmax()]
                worst_day = daily_with_sales.loc[daily_with_sales['total_sales'].idxmin()]
            else:
                best_day = None
                worst_day = None
        else:
            best_day = None
            worst_day = None
            
        if best_day is not None and worst_day is not None:
            best_day_info = {
                'date': best_day['date'].strftime('%Y-%m-%d'),
                'sales': best_day['total_sales']
            }
            worst_day_info = {
                'date': worst_day['date'].strftime('%Y-%m-%d'),
                'sales': worst_day['total_sales']
            }
        else:
            best_day_info = {}
            worst_day_info = {}
        
        # Mejor hora
        hourly = self.get_sales_by_hour()
        if not hourly.empty:
            best_hour = hourly.loc[hourly['total_sales'].idxmax()]
            best_hour_info = {
                'hour': int(best_hour['hour']),
                'sales': best_hour['total_sales']
            }
        else:
            best_hour_info = {}
        
        # Estadísticas de número de personas (Pax)
        total_people = self.df['people'].sum()
        avg_people_per_transaction = self.df['people'].mean() if total_transactions > 0 else 0
        
        return {
            'total_sales': float(total_sales),
            'total_transactions': int(total_transactions),
            'avg_transaction': float(avg_transaction),
            'median_transaction': float(median_transaction),
            'total_people': int(total_people),
            'avg_people_per_transaction': float(avg_people_per_transaction),
            'best_day': best_day_info,
            'worst_day': worst_day_info,
            'best_hour': best_hour_info
        }
    
    def get_trends(self, period: str = 'day') -> pd.DataFrame:
        """Obtiene tendencias de ventas"""
        if self.df.empty:
            return pd.DataFrame()
        
        if period == 'day':
            return self.get_sales_by_day(fill_missing_days=True)
        elif period == 'month':
            return self.get_sales_by_month()
        elif period == 'hour':
            return self.get_sales_by_hour()
        else:
            return pd.DataFrame()
    
    def get_sales_by_category(self, debug: bool = False) -> pd.DataFrame:
        """
        Obtiene ventas agrupadas por categoría de productos.
        
        Usa los datos incluidos (included) de la API cuando se usa include=items.product.productCategory
        Esto evita múltiples peticiones y saturación del servidor.
        
        Estructura esperada (JSON:API format):
        - Sale tiene relationships.items con referencias
        - Los items están en included[] con type="items"
        - Los products están en included[] con type="products"
        - Los productCategories están en included[] con type="product-categories"
        
        Args:
            debug: Si es True, imprime información de depuración
        
        Returns:
            DataFrame con columns: category, total_sales, num_transactions, avg_sale
        """
        if self.df.empty:
            return pd.DataFrame()
        
        # No necesitamos el api_client si los datos ya vienen incluidos
        # pero lo mantenemos para compatibilidad
        
        if debug:
            print(f"DEBUG: DataFrame tiene {len(self.df)} filas")
        
        # Verificar si tenemos datos incluidos del cliente de API
        included_data = {}
        if self.api_client and hasattr(self.api_client, '_included_data'):
            included_data = self.api_client._included_data
            if debug:
                print(f"DEBUG: Datos incluidos disponibles: {len(included_data)} entidades")
        
        # Construir mapeos desde los datos incluidos
        # included_data tiene formato: {"items:123": {...}, "products:456": {...}, "product-categories:789": {...}}
        
        # Mapeo de item_id -> product_id
        item_product_map = {}
        # Mapeo de product_id -> category_id
        product_category_map = {}
        # Mapeo de category_id -> category_name
        category_name_map = {}
        
        # Extraer información de los datos incluidos
        for key, entity in included_data.items():
            # El formato puede ser "type:id" o necesitamos extraer type e id del entity mismo
            entity_type = None
            entity_id = None
            
            if ':' in key:
                entity_type, entity_id = key.split(':', 1)
            else:
                # Si no está en el key, extraer del entity
                if isinstance(entity, dict):
                    entity_type = entity.get('type', '')
                    entity_id = entity.get('id', '')
            
            if not entity_type or not entity_id:
                continue
            
            # Normalizar entity_type (puede venir con mayúsculas)
            entity_type = entity_type.lower()
            
            if entity_type in ['items', 'item']:
                # Buscar product_id en el item
                if 'relationships' in entity and isinstance(entity['relationships'], dict):
                    if 'product' in entity['relationships']:
                        product_rel = entity['relationships']['product']
                        if isinstance(product_rel, dict):
                            if 'data' in product_rel:
                                product_data = product_rel['data']
                                if isinstance(product_data, dict):
                                    product_id = product_data.get('id')
                                    if product_id:
                                        item_product_map[entity_id] = str(product_id)
                                        if debug:
                                            print(f"   DEBUG: Item {entity_id} -> Product {product_id}")
                            elif 'id' in product_rel:
                                item_product_map[entity_id] = str(product_rel['id'])
                                if debug:
                                    print(f"   DEBUG: Item {entity_id} -> Product {product_rel['id']}")
            
            elif entity_type in ['products', 'product']:
                # Buscar productCategory_id en el product
                if 'relationships' in entity and isinstance(entity['relationships'], dict):
                    rels = entity['relationships']
                    cat_rel = None
                    
                    # Probar diferentes nombres posibles
                    for key in ['productCategory', 'ProductCategory', 'product-category', 'category']:
                        if key in rels:
                            cat_rel = rels[key]
                            break
                    
                    if cat_rel and isinstance(cat_rel, dict):
                        if 'data' in cat_rel:
                            cat_data = cat_rel['data']
                            if isinstance(cat_data, dict):
                                category_id = cat_data.get('id')
                                if category_id:
                                    product_category_map[entity_id] = str(category_id)
                                    if debug:
                                        print(f"   DEBUG: Product {entity_id} -> Category {category_id}")
                        elif 'id' in cat_rel:
                            product_category_map[entity_id] = str(cat_rel['id'])
                            if debug:
                                print(f"   DEBUG: Product {entity_id} -> Category {cat_rel['id']}")
            
            elif entity_type in ['product-categories', 'productcategories', 'productcategory']:
                # Extraer nombre de la categoría
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
                    if debug:
                        print(f"   DEBUG: Category {entity_id} -> Name: '{category_name}'")
        
        if debug:
            print(f"DEBUG: Mapeos construidos:")
            print(f"  items->products: {len(item_product_map)}")
            print(f"  products->categories: {len(product_category_map)}")
            print(f"  categories->names: {len(category_name_map)}")
        
        # Paso 2: Extraer items de cada venta y construir mapeo item->categoría
        sale_items_map = {}  # Mapea sale_id -> lista de item_ids
        item_category_map = {}  # Mapeo final item_id -> category_name
        
        for idx, row in self.df.iterrows():
            sale_id = row.get('id', idx)
            sale_items = []
            
            # Buscar items en relationships (JSON:API format)
            items_refs = None
            if 'relationships' in row and pd.notna(row['relationships']):
                rels = row['relationships']
                if isinstance(rels, dict) and 'items' in rels:
                    items_data = rels['items']
                    if isinstance(items_data, dict) and 'data' in items_data:
                        items_refs = items_data['data']
                    elif isinstance(items_data, list):
                        items_refs = items_data
            
            if items_refs:
                if not isinstance(items_refs, list):
                    items_refs = [items_refs]
                
                for item_ref in items_refs:
                    item_id = None
                    if isinstance(item_ref, dict):
                        item_id = item_ref.get('id')
                    elif isinstance(item_ref, str):
                        item_id = item_ref
                    
                    if item_id:
                        item_id = str(item_id)
                        sale_items.append(item_id)
                        
                        # Construir mapeo item->categoría usando los mapeos ya construidos
                        if item_id in item_product_map:
                            product_id = item_product_map[item_id]
                            if product_id in product_category_map:
                                category_id = product_category_map[product_id]
                                if category_id in category_name_map:
                                    item_category_map[item_id] = category_name_map[category_id]
            
            if sale_items:
                sale_items_map[sale_id] = sale_items
        
        if debug:
            print(f"DEBUG: Ventas con items: {len(sale_items_map)}")
            print(f"DEBUG: Mapeos item->category: {len(item_category_map)}")
        
        # Paso 3: Agrupar ventas por categoría
        category_sales = []
        
        for idx, row in self.df.iterrows():
            sale_id = row.get('id', idx)
            sale_amount = row.get('amount', 0)
            
            if sale_amount == 0:
                continue
            
            # Obtener los item_ids de esta venta
            sale_item_ids = sale_items_map.get(sale_id, [])
            
            if not sale_item_ids:
                # Si no tiene items, agregar como "Sin categoría"
                category_sales.append({
                    'category': 'Sin categoría',
                    'amount': sale_amount,
                    'transaction_id': sale_id
                })
                continue
            
            # Obtener las categorías de los items de esta venta
            categories_in_sale = []
            for item_id in sale_item_ids:
                if item_id in item_category_map:
                    category_name = item_category_map[item_id]
                    if category_name:
                        categories_in_sale.append(category_name)
            
            if not categories_in_sale:
                # Si no se encontraron categorías, usar "Sin categoría"
                category_sales.append({
                    'category': 'Sin categoría',
                    'amount': sale_amount,
                    'transaction_id': sale_id
                })
            else:
                # Dividir el monto de la venta entre las categorías encontradas
                # (si una venta tiene items de múltiples categorías)
                amount_per_category = sale_amount / len(categories_in_sale)
                
                for category in categories_in_sale:
                    category_sales.append({
                        'category': category,
                        'amount': amount_per_category,
                        'transaction_id': sale_id
                    })
        
        # Si no se encontraron categorías, retornar DataFrame vacío con estructura correcta
        if not category_sales:
            return pd.DataFrame(columns=['category', 'total_sales', 'num_transactions', 'avg_sale'])
        
        # Crear DataFrame y agrupar
        cat_df = pd.DataFrame(category_sales)
        
        category_agg = cat_df.groupby('category').agg({
            'amount': ['sum', 'mean', 'count'],
            'transaction_id': 'nunique'
        }).reset_index()
        
        category_agg.columns = ['category', 'total_sales', 'avg_sale', 'item_count', 'num_transactions']
        
        # Ordenar por total_sales descendente
        category_agg = category_agg.sort_values('total_sales', ascending=False)
        
        # Retornar solo las columnas necesarias
        return category_agg[['category', 'total_sales', 'num_transactions', 'avg_sale']]

