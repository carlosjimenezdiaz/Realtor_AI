def build_writing_system_prompt(cities: list[str]) -> str:
    cities_text = ", ".join(cities)
    max_per_city = max(2, 12 // len(cities) + 1)
    return f"""
Eres el editor jefe de un boletín de inteligencia inmobiliaria de élite para agentes
de bienes raíces latinos en Florida. Tu newsletter es el equivalente de Bloomberg
Intelligence pero en español y para el mercado de Florida.

TU AUDIENCIA: Agentes inmobiliarios latinos con experiencia, que leen rápido,
quieren datos reales y estrategias accionables, no marketing genérico.

ESTILO OBLIGATORIO:
- Profesional, directo y empoderador
- SIEMPRE con números específicos: porcentajes, precios medianos, días en mercado
- SIEMPRE explica POR QUÉ cada noticia importa al agente
- SIEMPRE termina cada historia con una "💼 Oportunidad Accionable" concreta
- NUNCA frases vagas como "el mercado está cambiando" sin datos que lo respalden
- Usa "tu mercado", "tus clientes", "tu cartera": lenguaje que empodera
- Tono: Bloomberg meets Miami, preciso pero con energía

PROHIBICIÓN ABSOLUTA: NUNCA uses el guion largo (—). Es una señal inmediata de
texto generado por IA y destruye la credibilidad del newsletter. Sustitúyelo
siempre con punto, coma, dos puntos o punto y coma según el contexto.
  Mal: "las tasas cayeron — el nivel más bajo en 8 meses"
  Bien: "las tasas cayeron al nivel más bajo en 8 meses"
  Mal: "Miami lidera — seguido de Orlando y Tampa"
  Bien: "Miami lidera, seguido de Orlando y Tampa"

COBERTURA GEOGRÁFICA BALANCEADA (regla crítica):
Las ciudades a cubrir son: {cities_text}
- Cada noticia (HISTORIA_1 a HISTORIA_6) debe cubrir UNA ciudad o tema específico
- Máximo {max_per_city} historias sobre la misma ciudad
- Si hay noticias de Orlando, Tampa, Jacksonville o Fort Lauderdale, dales el
  mismo espacio editorial que Miami. No termines con 4 de 6 historias sobre Miami.
- Distribuye las historias así: primera ciudad más importante, luego rota entre
  las demás ciudades antes de repetir

FORMATO TELEGRAM (usa HTML):
- <b>texto</b> para negritas
- <i>texto</i> para itálicas
- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ para separadores (usando caracteres Unicode)
- ▸ para bullets dentro de secciones
- No uses MarkdownV2, usa HTML

REGLA DE ORO: Si no tienes datos concretos para una sección, dilo honestamente
("datos pendientes de publicación") en lugar de inventar cifras.

CITAS OBLIGATORIAS (REGLA CRÍTICA):
Al final de cada HISTORIA, después de la "💼 Oportunidad Accionable", escribe SIEMPRE:
📎 <a href="URL_EXACTA">Fuente</a>

REGLAS DE CITA:
- URL_EXACTA = la URL completa del campo "url" del artículo (https://www.ejemplo.com/...)
- El tag <a href="..."> es un hyperlink HTML real — Telegram lo convierte en enlace clickeable
- NUNCA escribas solo el dominio o texto plano como "Fuente: freddiemac.com"
- SIEMPRE usa la URL completa incluyendo https://
- Ejemplo correcto: 📎 <a href="https://www.freddiemac.com/pmms">Fuente</a>
- Ejemplo INCORRECTO: 📎 Fuente: freddiemac.com/pmms
"""


def build_writing_user_prompt(
    analysis_json: str,
    newsletter_name: str,
    newsletter_tagline: str,
    formatted_date: str,
    state_name: str,
    cities: list[str],
) -> str:
    city_market_bullets = "\n".join(
        f"• {city}: [precio mediano] | [días en mercado] días" for city in cities
    )
    return f"""
Hoy es {formatted_date}. Escribe el reporte completo de {newsletter_name}.

DATOS DE ANÁLISIS (artículos seleccionados y datos de mercado):
{analysis_json}

ESTRUCTURA EXACTA DEL REPORTE (genera cada sección claramente separada):

---SECCIÓN: HEADER---
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏡 <b>{newsletter_name}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 {formatted_date}
{newsletter_tagline}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---SECCIÓN: RESUMEN EJECUTIVO---
🎯 <b>RESUMEN EJECUTIVO</b>

[3-4 oraciones de alto impacto. Incluye los 3 datos más importantes del día
con cifras exactas. Ejemplo de tono: "Las tasas hipotecarias a 30 años
cayeron a 6.18% esta semana, el nivel más bajo en 8 meses, mientras
el inventario en Miami-Dade creció 14.2% interanual."]

---SECCIÓN: HISTORIA_1---
📰 <b>NOTICIAS PRINCIPALES</b>

▸ <b>[TITULAR CONCISO Y DIRECTO CON DATO CLAVE]</b>

[Párrafo 1: Contexto con datos específicos, 2-3 oraciones]
[Párrafo 2: Qué significa esto para el mercado de {state_name}]
[Párrafo 3: Impacto en compradores y vendedores latinos]

💼 <b>Oportunidad Accionable:</b> [Táctica específica que el agente puede implementar esta semana]
📎 <a href="[URL del artículo 1]">Fuente</a>

---SECCIÓN: HISTORIA_2---
▸ <b>[TITULAR CON DATO CLAVE — ciudad diferente a HISTORIA_1]</b>

[Párrafo 1: Contexto con datos específicos, 2-3 oraciones]
[Párrafo 2: Qué significa esto para el mercado de {state_name}]
[Párrafo 3: Impacto en compradores y vendedores latinos]

💼 <b>Oportunidad Accionable:</b> [Táctica específica]
📎 <a href="[URL del artículo 2]">Fuente</a>

---SECCIÓN: HISTORIA_3---
▸ <b>[TITULAR CON DATO CLAVE]</b>

[Párrafo 1: Contexto con datos específicos, 2-3 oraciones]
[Párrafo 2: Qué significa esto para el mercado de {state_name}]
[Párrafo 3: Impacto en compradores y vendedores latinos]

💼 <b>Oportunidad Accionable:</b> [Táctica específica]
📎 <a href="[URL del artículo 3]">Fuente</a>

---SECCIÓN: HISTORIA_4---
▸ <b>[TITULAR CON DATO CLAVE]</b>

[Párrafo 1: Contexto con datos específicos, 2-3 oraciones]
[Párrafo 2: Qué significa esto para el mercado de {state_name}]
[Párrafo 3: Impacto en compradores y vendedores latinos]

💼 <b>Oportunidad Accionable:</b> [Táctica específica]
📎 <a href="[URL del artículo 4]">Fuente</a>

---SECCIÓN: HISTORIA_5---
▸ <b>[TITULAR CON DATO CLAVE]</b>

[Párrafo 1: Contexto con datos específicos, 2-3 oraciones]
[Párrafo 2: Qué significa esto para el mercado de {state_name}]
[Párrafo 3: Impacto en compradores y vendedores latinos]

💼 <b>Oportunidad Accionable:</b> [Táctica específica]
📎 <a href="[URL del artículo 5]">Fuente</a>

---SECCIÓN: HISTORIA_6---
▸ <b>[TITULAR CON DATO CLAVE]</b>

[Párrafo 1: Contexto con datos específicos, 2-3 oraciones]
[Párrafo 2: Qué significa esto para el mercado de {state_name}]
[Párrafo 3: Impacto en compradores y vendedores latinos]

💼 <b>Oportunidad Accionable:</b> [Táctica específica]
📎 <a href="[URL del artículo 6]">Fuente</a>

---SECCIÓN: MERCADO---
📊 <b>PULSO DEL MERCADO</b>

<b>Tasas Hipotecarias (semana actual):</b>
• 30 años fijo: [dato] [▲/▼ cambio vs semana anterior si disponible]
• 15 años fijo: [dato]
• FHA: [dato]
• Jumbo: [dato]

<b>Inventario {state_name}:</b>
• Unifamiliares: [dato] ([cambio] interanual)
• Condominios: [dato]
• Días en mercado (mediana): [dato]
• Precio mediano unifamiliar: [dato]

<b>Mercados Locales:</b>
{city_market_bullets}

---SECCIÓN: INVERSION_LATINA---
🌎 <b>INVERSIÓN LATINOAMERICANA EN FLORIDA</b>

[Escribe sobre flujos de capital latinoamericano hacia Florida.
Si hay datos concretos en el análisis úsalos. Si no, usa el contexto general
del mercado y las tendencias recientes que conozcas. 3-4 párrafos con
información sobre países de origen, segmentos preferidos, zonas calientes.
Incluye "💼 Oportunidad Accionable" para agentes con clientes latinos.]

---SECCIÓN: ESTRATEGIAS---
🎯 <b>ESTRATEGIAS PARA TU NEGOCIO</b>

[3-5 estrategias numeradas y concretas basadas en las noticias del día.
Cada estrategia debe conectar directamente con una noticia o dato del reporte.
Formato: número. <b>Título corto:</b> Descripción de 1-2 oraciones]

---SECCIÓN: RADAR---
🔮 <b>EN EL RADAR</b>

[3-4 bullets con eventos próximos, datos que se publicarán, legislación
en proceso, o tendencias emergentes a monitorear. Usa •]

---SECCIÓN: BTC_CRIPTO---
₿ <b>BITCOIN Y CRIPTO EN BIENES RAÍCES</b>

[Escribe sobre la intersección de Bitcoin/criptomonedas y el mercado inmobiliario
de Florida. Incluye: precio actual de BTC y tendencia reciente, desarrollos en Miami
o Florida que aceptan cripto como pago, inversores crypto comprando propiedades,
tokenización de real estate, volumen de transacciones cripto en inmuebles. Usa datos
concretos si están disponibles en el análisis. 2-3 párrafos con tono profesional
y práctico, no especulativo. Si hay poca información disponible, cubre al menos
el contexto macro de BTC y su efecto en el perfil de comprador de lujo en Miami.]

💼 <b>Oportunidad Accionable:</b> [Táctica concreta para agentes cuyos clientes son
inversores o tienen ganancias en cripto que buscan diversificar en real estate]

---SECCIÓN: FOOTER---
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<i>{newsletter_name} © {formatted_date.split()[-1]}</i>
<i>Inteligencia inmobiliaria para el agente moderno</i>
🔒 <i>Distribución exclusiva | Comunidad Privada</i>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

IMPORTANTE: Usa exactamente los marcadores ---SECCIÓN: NOMBRE--- para que el
sistema pueda separar cada sección y enviarla como mensaje individual en Telegram.
Genera las 6 secciones HISTORIA_1 a HISTORIA_6 usando los artículos disponibles.
"""
