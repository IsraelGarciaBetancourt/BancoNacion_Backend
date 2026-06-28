# Core Financiero & API REST — Simulación Banco de la Nación (Perú)

Este es el backend del sistema de simulación financiera del **Banco de la Nación (Perú)**. Implementa las reglas de negocio, los algoritmos de amortización de créditos (Préstamo Multired), el scoring de elegibilidad, la gestión de cobranza y recuperaciones, y los endpoints de reportería para Power BI.

---

## 🛠️ Stack Tecnológico del Backend

*   **Framework principal:** FastAPI (Python 3.11+) - Asíncrono y de alto rendimiento.
*   **Motor de Base de Datos:** PostgreSQL 15+.
*   **Mapeador Relacional (ORM):** SQLAlchemy 2.0+ (Consultas estructuradas y transaccionales).
*   **Seguridad:** 
    *   `python-jose` (para firma y decodificación de tokens JWT).
    *   `bcrypt` (para hashing criptográfico y salting de contraseñas de clientes).
*   **Servidor ASGI:** Uvicorn.
*   **Gestión de variables:** Pydantic Settings.

---

## 📐 Motor de Cálculo de Crédito (Matemática Financiera)

El core calcula el cronograma de pagos bajo el **Método Francés (cuotas constantes)** utilizando las fórmulas y tasas del tarifario del **Banco de la Nación**:

### 1. Tarifario Vigente para Préstamo Multired
*   **Crédito Multired Clásico (Con seguro de desgravamen):**
    *   **TEA (Tasa Efectiva Anual):** `12.99%`
    *   **Seguro de Desgravamen Mensual:** `0.12%` (`0.0012`) cargado al saldo deudor (clientes hasta 84 años).
*   **Préstamo Básico (Sin seguro de desgravamen):**
    *   **TEA (Tasa Efectiva Anual):** `17.99%`
    *   **Seguro de Desgravamen Mensual:** `0.00%`

### 2. Equivalencia de Tasas (TEA a TEM)
Al tratarse de tasas de interés compuesto efectivas, la conversión exponencial mensual se realiza mediante:

$$\text{TEM}_{\text{interés}} = (1 + \text{TEA})^{1/12} - 1$$

*   Para TEA = 12.99% $\rightarrow$ $\text{TEM}_{\text{interés}} \approx 1.0229\%$
*   Para TEA = 17.99% $\rightarrow$ $\text{TEM}_{\text{interés}} \approx 1.3881\%$

### 3. Amortización Francesa con Seguro
El seguro de desgravamen sobre el saldo deudor se incorpora como un costo mensual acumulado a la tasa de interés. La cuota total fija se calcula en base a la tasa mensual combinada:

$$\text{TEM}_{\text{total}} = \text{TEM}_{\text{interés}} + \text{tasa}_{\text{desg}}$$

$$\text{Cuota Fija} = \text{Principal} \times \frac{\text{TEM}_{\text{total}} \times (1 + \text{TEM}_{\text{total}})^n}{(1 + \text{TEM}_{\text{total}})^n - 1}$$

En cada mes del cronograma:
*   $\text{Interés} = \text{Saldo Deudor} \times \text{TEM}_{\text{interés}}$
*   $\text{Seguro de Desgravamen} = \text{Saldo Deudor} \times 0.0012$ (si aplica)
*   $\text{Amortización} = \text{Cuota Fija} - (\text{Interés} + \text{Desgravamen})$
*   $\text{Saldo Nuevo} = \text{Saldo Anterior} - \text{Amortización}$
*   **Ajuste de Cierre (Mes final):** Se fuerza a que la amortización sea exactamente el saldo deudor restante para corregir cualquier diferencia por redondeo de céntimos, extinguiendo la deuda exactamente a **0.00**.

---

## 🔒 Pruebas de Ciberseguridad & Mitigaciones (Semana 14)

El backend incorpora contramedidas para los principales vectores de ataque del OWASP Top 10:

*   **Inyección SQL:** Evitada mediante el uso estricto de **consultas preparadas y parametrizadas** en SQLAlchemy (utilizando bindings como `SELECT * FROM solicitud WHERE id = :id`). No se utiliza concatenación directa de strings en consultas de base de datos.
*   **XSS (Cross-Site Scripting):** Sanitización e inspección estricta de todos los payloads entrantes a la API mediante la validación de tipos e inputs de los esquemas de **Pydantic**.
*   **IDOR (Insecure Direct Object Reference):** Las consultas y transacciones críticas no dependen de parámetros de identificación de usuario en la URL. El backend obtiene el identificador de cliente (`pkcliente`) directamente de la firma criptográfica del token JWT autenticado en el encabezado `Authorization`.
*   **Fuerza Bruta:** Hashing irreversible de contraseñas de homebanking mediante **Bcrypt** con salt aleatorio automático. Bloqueo inmediato de la cuenta de homebanking (`bloqueado = 'S'`) tras **5 intentos fallidos** consecutivos de login.
*   **Configuración Insegura:** Las credenciales y variables se extraen del archivo local `.env` (excluido de Git vía `.gitignore`). La API restringe el intercambio de recursos (CORS) a una whitelist configurada en `CORS_ORIGINS`, bloqueando el acceso permisivo de dominios comodines `*`.

---

## 📊 Endpoints de Exportación para Power BI

El backend expone endpoints REST en formato plano JSON para integrar la información con reportes analíticos de Power BI Desktop:
*   `GET /admin/powerbi/clientes` - Clientes activos y demografía.
*   `GET /admin/powerbi/ahorros` - Saldos contables y disponibles de ahorro.
*   `GET /admin/powerbi/creditos` - Saldos de capital, cuotas y calificación de mora SBS.
*   `GET /admin/powerbi/operaciones` - Historial transaccional.

---

## 🚀 Despliegue en Producción (Coolify)

1. En tu instancia de Coolify, levanta una base de datos **PostgreSQL** y copia la URI de conexión.
2. Crea una **Application** apuntando al repositorio de Git y define el **Base Directory** como `/BancoNacion_Backend`.
3. Selecciona el builder pack **Nixpacks** (compilará automáticamente al leer `requirements.txt`).
4. Configura las siguientes Variables de Entorno en el panel:
   *   `DATABASE_URL` = (URI de conexión a la base de datos PostgreSQL)
   *   `SECRET_KEY` = (Clave para la firma y cifrado de los tokens JWT)
   *   `ALGORITHM` = `HS256`
   *   `PORT` = `8002`
   *   `CORS_ORIGINS` = `https://tu-frontend.vercel.app` *(La URL que te proporcione Vercel para tu frontend)*.
5. Define el comando de inicio en Coolify:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8002
   ```
6. Expón el puerto **8002**.

---

## 💻 Desarrollo Local

1. Crea el entorno virtual e instala dependencias:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Crea un archivo `.env` en la raíz del backend con tus credenciales.
3. Levanta el servidor de desarrollo:
   ```bash
   uvicorn main:app --reload --port 8002
   ```
   Accede a la documentación interactiva de la API en `http://localhost:8002/docs`.
