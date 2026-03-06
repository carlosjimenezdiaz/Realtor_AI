from __future__ import annotations
import os


class StateConfig:
    """
    State configuration driven entirely by environment variables.
    No state-specific Python files needed — just set the vars in .env.

    Required in .env:
        STATE_NAME          e.g. Florida
        STATE_ABBREVIATION  e.g. FL
        CITIES              e.g. Miami,Orlando,Tampa
        TIMEZONE            e.g. America/New_York

    Optional in .env:
        NEWSLETTER_NAME     defaults to "{STATE_NAME} Realty Intel"
        STATE_REALTORS_URL  state association site to scrape (leave blank to skip)
    """

    @property
    def state_name(self) -> str:
        return os.getenv("STATE_NAME", "Florida")

    @property
    def state_abbreviation(self) -> str:
        return os.getenv("STATE_ABBREVIATION", "FL")

    @property
    def major_cities(self) -> list[str]:
        cities_env = os.getenv("CITIES", "Miami,Orlando,Tampa,Jacksonville,Fort Lauderdale")
        return [c.strip() for c in cities_env.split(",") if c.strip()]

    @property
    def newsletter_name(self) -> str:
        return os.getenv("NEWSLETTER_NAME", f"{self.state_name} Realty Intel")

    @property
    def newsletter_tagline(self) -> str:
        return "Tu ventaja competitiva diaria"

    @property
    def timezone(self) -> str:
        return os.getenv("TIMEZONE", "America/New_York")

    @property
    def firecrawl_urls(self) -> list[dict]:
        # National sources — valid for any US state
        urls = [
            {"url": "https://www.freddiemac.com/pmms", "name": "Freddie Mac PMMS"},
            {"url": "https://www.redfin.com/news/data-center/", "name": "Redfin Data Center"},
            {"url": "https://www.zillow.com/research/", "name": "Zillow Research"},
            {"url": "https://www.nar.realtor/research-and-statistics", "name": "NAR Research"},
            {"url": "https://finance.yahoo.com/quote/BTC-USD/", "name": "Yahoo Finance BTC"},
        ]
        # State-specific realtor association (optional)
        state_url = os.getenv("STATE_REALTORS_URL", "")
        if state_url:
            urls.insert(0, {"url": state_url, "name": f"{self.state_name} Realtors"})
        return urls

    @property
    def research_categories(self) -> list[str]:
        state = self.state_name
        city_categories = [
            f"Mercado inmobiliario de {city} ({state}): precios, inventario, tendencias 2026"
            for city in self.major_cities
        ]
        return [
            f"Tasas hipotecarias y decisiones de la Reserva Federal (impacto en {state})",
            f"Legislación y nuevas leyes inmobiliarias en {state} 2026 (HOA, seguros, property tax)",
            *city_categories,
            f"Inversión latinoamericana en {state}: compradores de México, Colombia, Venezuela, Brasil, Argentina",
            f"Mercado de lujo en {state} ($3M+): ventas, desarrollos, récords",
            f"Nueva construcción y desarrollos en pre-venta en {state} 2026",
            f"Inventario de viviendas y métricas de mercado en {state}",
            f"Noticias económicas con impacto directo en bienes raíces de {state}",
            f"Bitcoin y criptomonedas como inversión en bienes raíces de {state}: pagos crypto, inversores BTC comprando propiedades, tokenización",
        ]
