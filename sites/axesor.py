import re
import json
import random
import time
import os
from typing import List, Dict, Optional, TypedDict
import config
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext
from rich import print as rprint
from contextlib import contextmanager


class CompanyMetadata(TypedDict):
    nombre: str
    direccion: str
    cif: str
    forma_juridica: str
    fecha_constitucion: str
    objeto_social: str
    cnae: str
    sic: str
    url: str



class Axesor:
    
    def __init__(self) -> None:
        self.USER_AGENTS: List[str] = config.USER_AGENTS
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.request_delay = (2, 4)
        self.max_retries = 3
        self.json_filename = f"axesor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


    @contextmanager
    def _get_page(self, user_agent: str = None):
        
        context = None
        page = None
        try:
            user_agent = user_agent or random.choice(self.USER_AGENTS)
            context = self.browser.new_context(
                user_agent=user_agent,
                ignore_https_errors=True
            )
            page = context.new_page()
            yield page
        
        finally:
            if page is not None:
                page.close()
            if context is not None:
                context.close()


    def _random_delay(self):
        
        delay = random.uniform(*self.request_delay)
        rprint(f"[yellow]Esperando {delay:.2f} segundos...[/yellow]")
        time.sleep(delay)


    def _append_to_json(self, data: CompanyMetadata):
        
        if os.path.exists(f"data/{self.json_filename}"):
            with open(f"data/{self.json_filename}", 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        
        existing_data.append(data)
        
        with open(f"data/{self.json_filename}", 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)


    def scrap_places(self, URL: str) -> List[str]:
        
        rprint("[yellow]Intentando obtener municipios de Comunidad Madrid[/yellow]")
        self._random_delay()
        
        for attempt in range(self.max_retries):
            try:
                with self._get_page() as page:
                    page.goto(URL, wait_until="networkidle", timeout=60000)
                    page.wait_for_selector("tr a", timeout=30000)

                    places: List[str] = page.eval_on_selector_all(
                        "tr a",
                        "elements => elements.map(el => el.href)"
                    )

                    pattern = re.compile(r"^https://www\.axesor\.es/directorio-informacion-empresas/empresas-de-Madrid/.*")
                    filtered_places: List[str] = []
                    
                    for place in places:
                        if pattern.match(place):
                            filtered_places.append(place.rstrip('/'))

                    for place in filtered_places:
                        rprint("[green]Municipio encontrado:[/green]", place)

                    return filtered_places

            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f"Error después de {self.max_retries} intentos: {str(e)[:100]}")
                    return []
                rprint(f"[red]Intento {attempt + 1} fallido, reintentando...[/red]")
                self._random_delay()


    def scrap_company_links(self, place_url: str) -> List[str]:
        
        rprint(f"[yellow]Extrayendo enlaces de empresas de: {place_url}[/yellow]")
        self._random_delay()
        
        company_links = []
        current_url = place_url
        page_num = 1
        
        while True:
            rprint(f"[cyan]Procesando página {page_num}: {current_url}[/cyan]")
            
            for attempt in range(self.max_retries):
                try:
                    with self._get_page() as page:
                        response = page.goto(current_url, wait_until="networkidle", timeout=60000)
                        
                        if response.status == 404:
                            rprint(f"[yellow]Página {page_num} no encontrada (404)[/yellow]")
                            rprint(f"[green]Total empresas en municipio: {len(company_links)}[/green]")
                            return company_links
                        
                        error_element = page.query_selector('div.error_cabecera.reloaded h2.resaltado')
                        if error_element and "Estimado usuario" in (error_element.inner_text() or ""):
                            rprint(f"[green]Total empresas en municipio: {len(company_links)}[/green]")
                            return company_links
                        
                        page.wait_for_selector("a[href^='//www.axesor.es/Informes-Empresas/']", timeout=30000)

                        raw_links = page.eval_on_selector_all(
                            "a[href^='//www.axesor.es/Informes-Empresas/']",
                            "elements => elements.map(el => el.getAttribute('href'))"
                        )

                        pattern = re.compile(r"^//www\.axesor\.es/Informes-Empresas/.*")
                        current_page_links = [f"https:{href}" for href in raw_links if pattern.match(href)]
                        current_count = len(current_page_links)
                        
                        if current_count == 0:
                            rprint(f"[yellow]No se encontraron empresas en página {page_num}[/yellow]")
                            rprint(f"[green]Total empresas en municipio: {len(company_links)}[/green]")
                            return company_links
                        
                        company_links.extend(current_page_links)
                        rprint(f"[green]Encontradas {current_count} empresas en página {page_num} (Total: {len(company_links)})[/green]")
                        
                        pagination_info = self._detect_pagination(page)
                        
                        rprint(f"[cyan]Info paginación: {pagination_info}[/cyan]")
                        
                        if not pagination_info['has_more_pages']:
                            rprint(f"[green]No hay más páginas disponibles[/green]")
                            rprint(f"[green]Total empresas en municipio: {len(company_links)}[/green]")
                            return company_links

                        next_page_num = page_num + 1
                        base_url = place_url.rstrip('/')
                        
                        if re.search(r'/\d+$', base_url):
                            current_url = re.sub(r'/\d+$', f'/{next_page_num}', base_url)
                        else:
                            current_url = f"{base_url}/{next_page_num}"
                        
                        rprint(f"[green]Siguiente página: {current_url}[/green]")
                        page_num += 1
                        break

                except Exception as e:
                    if attempt == self.max_retries - 1:
                        rprint(f"[red]Error después de {self.max_retries} intentos: {str(e)[:100]}[/red]")
                        rprint(f"[green]Total empresas en municipio: {len(company_links)}[/green]")
                        return company_links
                    
                    rprint(f"[red]Intento {attempt + 1} fallido, reintentando...[/red]")
                    self._random_delay()
            
            self._random_delay()


    def _detect_pagination(self, page: Page) -> Dict[str, any]:
        
        try:
            pagination_div = page.query_selector('#paginacion')
            
            if not pagination_div:
                rprint(f"[yellow]No se encontró div #paginacion[/yellow]")
                return {'has_more_pages': False, 'reason': 'no_pagination_div'}
            
            current_page_element = pagination_div.query_selector('.paginacion-numeracion .seleccion')
            current_page = 1
            if current_page_element:
                current_page_text = current_page_element.inner_text().strip()
                current_page = int(current_page_text) if current_page_text.isdigit() else 1
            
            page_links = pagination_div.query_selector_all('.paginacion-numeracion a')
            page_numbers = []
            
            for link in page_links:
                page_text = link.inner_text().strip()
                if page_text.isdigit():
                    page_numbers.append(int(page_text))
            
            next_button = pagination_div.query_selector('a.next[rel="next"]')
            has_next_button = next_button is not None
            
            max_visible_page = max(page_numbers) if page_numbers else current_page

            has_more_pages = False
            reason = ""
            
            if has_next_button:
                has_more_pages = True
                reason = "next_button_exists"
            elif current_page < max_visible_page:
                has_more_pages = True
                reason = f"current_page_{current_page}_less_than_max_{max_visible_page}"
            else:
                disabled_buttons = pagination_div.query_selector_all('.paginacion-botones span.icomoon')
                if len(disabled_buttons) >= 2:
                    has_more_pages = False
                    reason = "disabled_navigation_buttons"
                else:
                    has_more_pages = False
                    reason = "no_more_pages_detected"
            
            result = {
                'has_more_pages': has_more_pages,
                'current_page': current_page,
                'visible_pages': page_numbers,
                'max_visible_page': max_visible_page,
                'has_next_button': has_next_button,
                'reason': reason
            }
            
            return result
            
        except Exception as e:
            rprint(f"[red]Error detectando paginación: {str(e)}[/red]")
            return {'has_more_pages': False, 'reason': f'error: {str(e)}'}


    def scrap_company_metadata(self, company_url: str) -> Optional[CompanyMetadata]:
        
        rprint("[blue]*[/blue]" * 15)
        self._random_delay()
        
        for attempt in range(self.max_retries):
            try:
                with self._get_page() as page:
                    page.goto(company_url, wait_until="networkidle", timeout=60000)
                    page.wait_for_selector("tbody tr", timeout=30000)
                    
                    new_format = page.query_selector(".c-empresa__detail-label") is not None
                    
                    if new_format:
                        rprint("[cyan]Formato nuevo detectado (c-empresa)[/cyan]")
                        metadata: CompanyMetadata = {
                            "nombre": self._get_text_safe(page, "th:has-text('Nombre') + td.c-empresa__detail-value") or 
                                     self._get_text_safe(page, "h1, h2, h3") or "N/A",
                            "direccion": self._clean_address(
                                self._get_text_safe(page, "th:has-text('Dirección') + td.c-empresa__detail-value")
                            ),
                            "cif": self._get_text_safe(page, "th:has-text('CIF') + td.c-empresa__detail-value"),
                            "forma_juridica": self._get_text_safe(page, "th:has-text('Forma jurídica') + td.c-empresa__detail-value"),
                            "fecha_constitucion": self._get_text_safe(page, "th:has-text('Fecha de constitución') + td.c-empresa__detail-value"),
                            "objeto_social": self._get_text_safe(page, "th:has-text('Objeto social') + td.c-empresa__detail-value span.category") or
                                           self._get_text_safe(page, "th:has-text('Objeto social') + td.c-empresa__detail-value"),
                            "cnae": self._get_text_safe(page, "th:has-text('CNAE') + td.c-empresa__detail-value"),
                            "sic": self._get_text_safe(page, "th:has-text('SIC') + td.c-empresa__detail-value"),
                            "url": company_url
                        }
                    else:
                        rprint("[cyan]Formato antiguo detectado[/cyan]")
                        metadata: CompanyMetadata = {
                            "nombre": self._get_text_safe(page, "h3.name") or "N/A",
                            "direccion": self._clean_address(
                                self._get_text_safe(page, "#Direccion + td")
                            ),
                            "cif": self._get_text_safe(page, "td:has-text('CIF:') + td"),
                            "forma_juridica": self._get_text_safe(page, "td:has-text('Forma jurídica:') + td"),
                            "fecha_constitucion": self._get_text_safe(page, "td:has-text('Fecha de constitución:') + td"),
                            "objeto_social": self._get_text_safe(page, "td:has-text('Objeto social:') + td span.category") or
                                           self._get_text_safe(page, "td:has-text('Objeto social:') + td"),
                            "cnae": self._get_text_safe(page, "td:has-text('CNAE:') + td"),
                            "sic": self._get_text_safe(page, "td:has-text('SIC:') + td"),
                            "url": company_url
                        }
                    
                    rprint(f"[green]Datos obtenidos para {metadata['nombre']}:[/green]")
                    for key, value in metadata.items():
                        if key != "url":
                            rprint(f"[cyan]{key.capitalize()}:[/cyan] {value}")
                    
                    return metadata
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(f"Error al extraer metadatos después de {self.max_retries} intentos: {str(e)[:100]}")
                    return None
                rprint(f"[red]Intento {attempt + 1} fallido, reintentando...[/red]")
                self._random_delay()


    def _get_text_safe(self, page: Page, selector: str) -> str:
        
        try:
            element = page.query_selector(selector)
            return element.inner_text().strip() if element else "N/A"
        except:
            return "N/A"
    

    def _clean_address(self, address: str) -> str:
        
        if not address or address == "N/A":
            return "N/A"
        
        cleaned_parts = []
        for part in address.split():
            part = part.strip()
            if part and not part.startswith("Consultar") and not part.startswith("Ver mapa"):
                cleaned_parts.append(part)
        
        return " ".join(cleaned_parts)


    def main(self) -> None:
        
        try:
            self.playwright = sync_playwright().start()
            rprint("[green]Conectando...[/green]")

            self.browser = self.playwright.chromium.launch(
                headless=True,
                timeout=60000
            )

            places: List[str] = self.scrap_places(
                "https://www.axesor.es/directorio-informacion-empresas/empresas-de-Madrid"
            )
            
            total_companies_processed = 0
            
            rprint(f"[blue]Procesando {len(places)} municipios...[/blue]")
            rprint(f"[blue]Archivo de salida: ./data/{self.json_filename}[/blue]")
            
            for place_index, place in enumerate(places, 1):
                rprint(f"[magenta]{'='*50}[/magenta]")
                rprint(f"[magenta]Procesando municipio {place_index}/{len(places)}: {place}[/magenta]")
                rprint(f"[magenta]{'='*50}[/magenta]")
                
                company_links: List[str] = self.scrap_company_links(place)
                
                if not company_links:
                    rprint(f"[yellow]No se encontraron empresas en {place}[/yellow]")
                    continue
                
                rprint(f"[blue]Extrayendo metadatos de {len(company_links)} empresas del municipio...[/blue]")
                
                for company_index, company_url in enumerate(company_links, 1):
                    rprint(f"[cyan]Empresa {company_index}/{len(company_links)} del municipio {place_index}/{len(places)}[/cyan]")
                    
                    company_data = self.scrap_company_metadata(company_url)
                    if company_data:
                        self._append_to_json(company_data)
                        total_companies_processed += 1
                        rprint(f"[green]Empresa guardada en JSON. Total: {total_companies_processed}[/green]")
                    
                    rprint(f"[yellow]Progreso total: {total_companies_processed} empresas procesadas[/yellow]")
                
                rprint(f"[green]Municipio {place} completado ({len([l for l in company_links])} empresas)[/green]")
                self._random_delay()

            rprint(f"[green]Proceso completado! Total de empresas procesadas: {total_companies_processed}[/green]")
            rprint(f"[green]Total de municipios procesados: {len(places)}[/green]")
            rprint(f"[green]Archivo final: ./data/{self.json_filename}[/green]")

        finally:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()



#if __name__ == "__main__":
#    Axesor().main()