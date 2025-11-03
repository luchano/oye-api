"""
Funciones de análisis estratégico de ventas
"""
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
import pytz


class SalesAnalytics:
    """Clase para análisis de ventas"""
    
    def __init__(self, sales_data: List[Dict], timezone: str = "America/Argentina/Buenos_Aires"):
        """
        Inicializa el analizador con datos de ventas
        
        Args:
            sales_data: Lista de diccionarios con datos de ventas
            timezone: Zona horaria para convertir las fechas (default: America/Argentina/Buenos_Aires - GMT-3)
        """
        self.df = pd.DataFrame(sales_data)
        self.timezone = pytz.timezone(timezone)
        
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
            'id': 'count'
        }).reset_index()
        
        daily_sales.columns = ['date', 'total_sales', 'avg_sale', 'num_transactions', 'count']
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
            
            daily_sales = daily_sales.sort_values('date')
        
        return daily_sales[['date', 'total_sales', 'avg_sale', 'num_transactions']]
    
    def get_sales_by_hour(self) -> pd.DataFrame:
        """
        Obtiene ventas agrupadas por hora del día.
        Las horas se reorganizan comenzando desde las 12:00 (mediodía) 
        y continuando por las siguientes 24 horas.
        """
        if self.df.empty:
            return pd.DataFrame()
        
        hourly_sales = self.df.groupby('hour').agg({
            'amount': ['sum', 'mean', 'count']
        }).reset_index()
        
        hourly_sales.columns = ['hour', 'total_sales', 'avg_sale', 'num_transactions']
        
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
        
        return hourly_sales[['hour', 'hour_order', 'display_hour', 'hour_label', 'total_sales', 'avg_sale', 'num_transactions']]
    
    def get_sales_by_month(self) -> pd.DataFrame:
        """Obtiene ventas agrupadas por mes"""
        if self.df.empty:
            return pd.DataFrame()
        
        monthly_sales = self.df.groupby('month').agg({
            'amount': ['sum', 'mean', 'count']
        }).reset_index()
        
        monthly_sales.columns = ['month', 'total_sales', 'avg_sale', 'num_transactions']
        monthly_sales['month_str'] = monthly_sales['month'].astype(str)
        monthly_sales = monthly_sales.sort_values('month')
        
        return monthly_sales[['month', 'month_str', 'total_sales', 'avg_sale', 'num_transactions']]
    
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
        
        return {
            'total_sales': float(total_sales),
            'total_transactions': int(total_transactions),
            'avg_transaction': float(avg_transaction),
            'median_transaction': float(median_transaction),
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

