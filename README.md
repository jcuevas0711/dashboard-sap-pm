# 📋 Dashboard KPI — SAP Plant Maintenance

Dashboard interactivo para visualizar KPIs de mantenimiento exportados desde SAP PM.

## Archivos requeridos (exportar desde SAP)

| Archivo | Transacción SAP | Descripción |
|---------|----------------|-------------|
| Órdenes.xlsx | IW38 | Órdenes de mantenimiento |
| Avisos.xlsx  | IW29 | Avisos de mantenimiento |
| IP16.xlsx    | IP16 | Planes de mantenimiento |
| IP24.xlsx    | IP24 | Posiciones de mantenimiento |

## Cómo usar

1. Abre la aplicación en tu URL de Streamlit
2. Sube los 4 archivos Excel en el panel lateral izquierdo
3. El dashboard se genera automáticamente
4. Usa los filtros de Empresa y Locación para analizar por área

## KPIs disponibles

- **Avisos**: Total, Abiertos, En Tratamiento, Concluidos, % Conclusión
- **Órdenes**: Total, Abiertas, Liberadas, Concluidas, Cerradas
- **Preventivo vs Correctivo**: Nivel de ejecución por tipo y empresa
- **Antigüedad**: Órdenes pendientes por rango de días
- **Planes PM**: Cobertura de órdenes, posiciones vencidas

## Instalación local (opcional)

```bash
pip install -r requirements.txt
streamlit run app.py
```
