"""
Cliente para interactuar con la API de Fudo
"""
import requests
import os
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class FudoAPIClient:
    """Cliente para la API de Fudo"""
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None, 
                 api_secret: Optional[str] = None, environment: str = "production"):
        """
        Inicializa el cliente de la API de Fudo
        
        Args:
            api_url: URL base de la API (opcional, se determina por environment)
            api_key: API Key para autenticación
            api_secret: API Secret para autenticación
            environment: "production" o "staging"
        """
        # Determinar URLs según el entorno
        if environment == "staging":
            self.api_url = api_url or "https://api.staging.fu.do/v1alpha1"
            self.auth_url = "https://auth.staging.fu.do/api"
        else:
            self.api_url = api_url or os.getenv("FUDO_API_URL", "https://api.fu.do/v1alpha1")
            self.auth_url = os.getenv("FUDO_AUTH_URL", "https://auth.fu.do/api")
        
        self.api_key = api_key or os.getenv("FUDO_API_KEY")
        self.api_secret = api_secret or os.getenv("FUDO_API_SECRET")
        self.environment = environment
        
        # Token y expiración
        self.token = None
        self.token_expires_at = 0
        
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        
        # Obtener token si tenemos credenciales
        if self.api_key and self.api_secret:
            self._authenticate()
    
    def _authenticate(self) -> bool:
        """
        Obtiene el token de autenticación de la API
        
        Returns:
            True si la autenticación fue exitosa
        """
        if not self.api_key or not self.api_secret:
            print("⚠️ API Key o API Secret no configurados")
            return False
        
        try:
            auth_data = {
                "apiKey": self.api_key,
                "apiSecret": self.api_secret
            }
            
            response = requests.post(
                self.auth_url,
                json=auth_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            response.raise_for_status()
            
            auth_response = response.json()
            self.token = auth_response.get("token")
            self.token_expires_at = int(auth_response.get("exp", 0))
            
            # Actualizar header de autorización
            if self.token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                return True
            return False
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Error al autenticar con la API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"   Detalles: {error_detail}")
                except:
                    print(f"   Respuesta: {e.response.text}")
            return False
    
    def _ensure_authenticated(self):
        """Asegura que tenemos un token válido"""
        current_time = int(time.time())
        # Renovar si el token expira en menos de 5 minutos o ya expiró
        if not self.token or self.token_expires_at < current_time + 300:
            if self.api_key and self.api_secret:
                self._authenticate()
    
    def _make_request(self, endpoint: str, method: str = "GET", params: Optional[Dict] = None, 
                     data: Optional[Dict] = None) -> Dict:
        """Realiza una petición a la API"""
        self._ensure_authenticated()
        
        url = f"{self.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, json=data, params=params)
            else:
                response = self.session.request(method, url, json=data, params=params)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                # Token expirado, intentar renovar
                if self._authenticate():
                    # Reintentar la petición
                    if method == "GET":
                        response = self.session.get(url, params=params)
                    elif method == "POST":
                        response = self.session.post(url, json=data, params=params)
                    else:
                        response = self.session.request(method, url, json=data, params=params)
                    response.raise_for_status()
                    return response.json()
            raise
        except requests.exceptions.RequestException as e:
            print(f"Error en la petición a {url}: {str(e)}")
            raise
    
    def get_sales(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        Obtiene datos de ventas
        
        Args:
            start_date: Fecha de inicio en formato YYYY-MM-DD
            end_date: Fecha de fin en formato YYYY-MM-DD
        
        Returns:
            Lista de ventas
        """
        params = {}
        
        # Construir filtro de fecha en formato ISO8601
        if start_date and end_date:
            # Convertir fechas a formato ISO8601 con tiempo
            start_datetime = f"{start_date}T00:00:00Z"
            end_datetime = f"{end_date}T23:59:59Z"
            params["filter[createdAt]"] = f"and(gte.{start_datetime},lte.{end_datetime})"
        elif start_date:
            start_datetime = f"{start_date}T00:00:00Z"
            params["filter[createdAt]"] = f"gte.{start_datetime}"
        elif end_date:
            end_datetime = f"{end_date}T23:59:59Z"
            params["filter[createdAt]"] = f"lte.{end_datetime}"
        
        # Configurar paginación (máximo 500 por página)
        params["page[size]"] = "500"
        params["page[number]"] = "1"
        
        all_sales = []
        
        try:
            while True:
                response = self._make_request("sales", params=params)
                
                # La respuesta puede estar en diferentes formatos
                if isinstance(response, dict):
                    # Si es un objeto con 'data'
                    if "data" in response:
                        sales = response["data"]
                    # Si es un objeto con 'sales'
                    elif "sales" in response:
                        sales = response["sales"]
                    # Si es directamente una lista (menos común)
                    elif isinstance(response.get("items"), list):
                        sales = response["items"]
                    else:
                        # Intentar obtener cualquier lista en el response
                        sales = [v for v in response.values() if isinstance(v, list)]
                        sales = sales[0] if sales else []
                elif isinstance(response, list):
                    sales = response
                else:
                    sales = []
                
                if not sales:
                    break
                
                all_sales.extend(sales)
                
                # Si recibimos menos de 500 items, hemos llegado al final
                if len(sales) < 500:
                    break
                
                # Página siguiente
                params["page[number]"] = str(int(params["page[number]"]) + 1)
            
            return all_sales
            
        except requests.exceptions.RequestException as e:
            # Solo mostrar el error una vez, no en cada intento
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                print("⚠️ Error de autenticación. Verifica tus credenciales (FUDO_API_KEY y FUDO_API_SECRET) en el archivo .env")
                print("   Para obtener credenciales, contacta a soporte@fu.do")
            elif "404" in error_msg:
                print("⚠️ Endpoint no encontrado. Verifica que la URL de la API sea correcta.")
            else:
                print(f"⚠️ No se pudo conectar a la API de Fudo: {error_msg}")
            print("   Usando datos de ejemplo para desarrollo...")
            return self._get_sample_data(start_date, end_date)
    
    def get_sales_by_date_range(self, days: int = 30) -> List[Dict]:
        """Obtiene ventas de los últimos N días"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return self.get_sales(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
    
    def _get_sample_data(self, start_date: Optional[str], end_date: Optional[str]) -> List[Dict]:
        """Genera datos de ejemplo para desarrollo/testing"""
        import random
        from datetime import datetime, timedelta
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        sample_data = []
        current = start
        
        while current <= end:
            # Generar varias ventas por día
            for _ in range(random.randint(5, 20)):
                hour = random.randint(8, 22)
                minute = random.randint(0, 59)
                sale_time = current.replace(hour=hour, minute=minute)
                
                sample_data.append({
                    "id": len(sample_data) + 1,
                    "date": sale_time.strftime("%Y-%m-%d"),
                    "datetime": sale_time.isoformat(),
                    "amount": round(random.uniform(15.0, 150.0), 2),
                    "items": random.randint(1, 5),
                    "status": "completed"
                })
            
            current += timedelta(days=1)
        
        return sample_data

