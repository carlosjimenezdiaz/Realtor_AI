def build_analysis_system_prompt(state_name: str) -> str:
    return f"""
Eres un analista de mercado inmobiliario senior con 20 años de experiencia en {state_name}.
Tu trabajo es evaluar artículos periodísticos y datos de mercado para seleccionar
el contenido más valioso para agentes inmobiliarios latinos en {state_name}.

CRITERIOS DE EVALUACIÓN (0-10 cada uno, total máximo 50):
1. RELEVANCIA: ¿Impacta directamente al mercado inmobiliario de {state_name}?
2. ACCIONABILIDAD: ¿Puede un agente usar esta información para tomar decisiones hoy?
3. AUDIENCIA: ¿Es relevante para compradores/vendedores latinos en {state_name}?
4. DATOS: ¿Contiene números, estadísticas o datos concretos?
5. NOVEDAD: ¿Es información reciente y fresca?

RESPONDE SIEMPRE con JSON válido. Sin texto antes ni después del JSON.
""".strip()


def build_analysis_user_prompt(
    research_text: str,
    scraped_context: str,
    state_name: str,
    cities: list[str],
) -> str:
    cities_text = ", ".join(cities)
    max_per_city = max(2, 12 // len(cities) + 1)
    city_medians_template = "\n".join(
        f'    "{city}": "$XXX,XXX"' for city in cities
    )
    return f"""
DATOS SCRAPEADOS DE SITIOS OFICIALES (fuentes de datos estructurados):
{scraped_context}

---

ARTÍCULOS ENCONTRADOS POR INVESTIGACIÓN (noticias y contexto):
{research_text}

---

Evalúa todos los artículos y datos anteriores. Selecciona los 12 más importantes
para agentes inmobiliarios latinos en {state_name}.

DISTRIBUCIÓN GEOGRÁFICA OBLIGATORIA: Los 12 artículos seleccionados deben cubrir
al menos {len(cities) - 1} ciudades distintas de: {cities_text}.
Máximo {max_per_city} artículos por ciudad.

Extrae también todos los datos numéricos de mercado que encuentres (tasas hipotecarias,
precios medianos, inventario, días en mercado) de AMBAS fuentes.

Responde ÚNICAMENTE con este JSON:
{{
  "selected_articles": [
    {{
      "title": "Título del artículo",
      "url": "https://...",
      "category": "Categoría temática",
      "scores": {{
        "relevancia": 8,
        "accionabilidad": 9,
        "audiencia": 7,
        "datos": 8,
        "novedad": 9
      }},
      "score_total": 41,
      "content_summary": "Resumen de 2-3 oraciones en español con datos concretos",
      "why_important_for_agents": "Una oración explicando el impacto directo para el agente",
      "key_data_points": ["tasa 6.18%", "inventario +14.2%", "$405,000 mediana"]
    }}
  ],
  "market_data": {{
    "mortgage_rate_30yr": "6.XX%",
    "mortgage_rate_15yr": "5.XX%",
    "mortgage_rate_fha": "6.XX%",
    "mortgage_rate_jumbo": "6.XX%",
    "inventory_sfh": "XX,XXX",
    "inventory_condos": "XX,XXX",
    "median_price_sfh": "$XXX,XXX",
    "median_days_on_market": "XX",
    "inventory_yoy_change": "+X.X%",
    "city_medians": {{
{city_medians_template}
    }}
  }},
  "coverage_gaps": ["Lista de temas sin cobertura hoy, si aplica"]
}}

Si no tienes datos para un campo numérico, usa "N/D" (no disponible).
""".strip()
