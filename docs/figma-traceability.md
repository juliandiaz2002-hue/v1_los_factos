# Trazabilidad Figma -> Codigo

## Fuente de diseno
- Archivo: https://www.figma.com/make/aW8HtWE1AzwIPWr7VJDq41/Los-Factos?t=d54L4j6x0wPkBhRo-1
- Nota tecnica: en archivos Figma Make el tool `get_screenshot` no aplica. Se toma como referencia `get_design_context` + recursos fuente (`App.tsx`, `KPICard.tsx`, `InsightCard.tsx`, `DESIGN_SYSTEM.md`).

## Paginas requeridas
- Foundations
- Components
- Screens
- Flows
- Handoff

## Regla de PR
Cada PR debe incluir:
1. Link al frame/componente Figma.
2. Archivos implementados en codigo.
3. Desviaciones y razon tecnica.
4. Screenshot de staging.

## Mapeo inicial v2
- `src/app/components/KPICard.tsx` -> `/Users/juliandiazphillips/Desktop/Los nuevos Facto$/los-factos-v2/ui/components/cards.py`
- `src/app/components/InsightCard.tsx` -> `/Users/juliandiazphillips/Desktop/Los nuevos Facto$/los-factos-v2/ui/components/cards.py`
- `src/app/components/FilterChip.tsx` -> `/Users/juliandiazphillips/Desktop/Los nuevos Facto$/los-factos-v2/ui/components/filters.py`
- `DESIGN_SYSTEM.md` tokens -> `/Users/juliandiazphillips/Desktop/Los nuevos Facto$/los-factos-v2/ui/components/theme.py`
