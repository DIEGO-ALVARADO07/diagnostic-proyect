from fastapi import FastAPI, UploadFile, File, HTTPException
import fastexcel
import polars as pl

# Inicializamos FastAPI (genera OpenAPI automáticamente)
app = FastAPI(
    title="API Lector Rápido de Excel",
    description="API construida con FastAPI y fastexcel para leer hojas de cálculo.",
    version="1.0.0"
)

@app.post("/leer-excel/", summary="Sube y lee un archivo Excel")
async def leer_excel(archivo: UploadFile = File(...)):
    # 1. Validar que sea un archivo de Excel
    if not archivo.filename.endswith((".xlsx", ".xlsm" ,".xls", ".ods")):
        raise HTTPException(
            status_code=400, 
            detail="Formato no válido. Por favor sube un archivo .xlsx, .xlsm, .xls o .ods"
        )
    
    try:
        # 2. Leer los bytes del archivo subido
        contenido = await archivo.read()
        
        # 3. Cargar el libro con fastexcel directamente desde los bytes
        lector = fastexcel.read_excel(contenido)
        
        # Obtener los nombres de todas las hojas
        nombres_hojas = lector.sheet_names
        
        # Cargar la primera hoja (índice 0)
        hoja = lector.load_sheet(1)
        
        # 4. Convertir a DataFrame de Polars (transferencia de memoria sin copias)
        df = hoja.to_polars()
        
        # Convertir los datos a una lista de diccionarios para devolver como JSON
        datos_json = df.to_dicts()
        
        return {
            "nombre_archivo": archivo.filename,
            "hojas_disponibles": nombres_hojas,
            "hoja_leida": nombres_hojas[0],
            "total_filas": len(datos_json),
            "datos": datos_json
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el Excel: {str(e)}")
