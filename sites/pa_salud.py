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
    descripcion: str
    direccion: str
    telefono: str
    website: str
    actividades: str
    url: str



class Salud:
    
    def __init__(self):
        self.USER_AGENTS: List[str] = config.USER_AGENTS
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.request_delay = (2, 4)
        self.max_retries = 3
        self.json_filename = f"pa_salud_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

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


    def _get_text_safe(self, page: Page, selector: str) -> str:
        
        try:
            element = page.query_selector(selector)
            return element.inner_text().strip() if element else "N/A"
        except:
            return "N/A"


    def _get_address_safe(self, page: Page) -> str:
        
        try:
            address_element = page.query_selector('.address[itemprop="address"]')
            if address_element:
                street = self._get_text_safe(page, '[itemprop="streetAddress"]')
                postal_code = self._get_text_safe(page, '[itemprop="postalCode"]')
                locality = self._get_text_safe(page, '[itemprop="addressLocality"]')
                
                address_parts = [part for part in [street, postal_code, locality] if part != "N/A"]
                return ", ".join(address_parts) if address_parts else "N/A"
            return "N/A"
        except:
            return "N/A"


    def _get_website_safe(self, page: Page) -> str:
        
        try:
            website_element = page.query_selector('.sitio-web[itemprop="url"]')
            return website_element.get_attribute('href') if website_element else "N/A"
        except:
            return "N/A"


    def _detect_pagination(self, page: Page) -> Dict[str, any]:
        
        try:
            pagination_container = page.query_selector('div.pag2 ul.pagination')
            
            if not pagination_container:
                rprint(f"[yellow]No se encontró contenedor de paginación[/yellow]")
                return {'has_more_pages': False, 'reason': 'no_pagination_container'}
            
            current_page_element = pagination_container.query_selector('li.active a')
            current_page = 1
            if current_page_element:
                current_page_text = current_page_element.inner_text().strip()
                current_page = int(current_page_text) if current_page_text.isdigit() else 1
            
            page_links = pagination_container.query_selector_all('li a[href]:not([href*="javascript:void"])')
            page_numbers = []
            
            for link in page_links:
                page_text = link.inner_text().strip()
                if page_text.isdigit():
                    page_numbers.append(int(page_text))

            next_button = pagination_container.query_selector('li a i.fa.icon-flecha-derecha')
            has_next_button = next_button is not None

            next_url = None
            if has_next_button:
                next_link = next_button.evaluate('el => el.closest("a")')
                if next_link:
                    next_url = page.evaluate('el => el.href', next_link)

            max_visible_page = max(page_numbers) if page_numbers else current_page
            has_more_pages = False
            reason = ""
            
            if has_next_button and next_url and "javascript:void" not in next_url:
                has_more_pages = True
                reason = "next_button_with_valid_url"
            elif current_page < max_visible_page:
                has_more_pages = True
                reason = f"current_page_{current_page}_less_than_max_{max_visible_page}"
            else:
                has_more_pages = False
                reason = "no_more_pages_detected"
            
            result = {
                'has_more_pages': has_more_pages,
                'current_page': current_page,
                'visible_pages': page_numbers,
                'max_visible_page': max_visible_page,
                'has_next_button': has_next_button,
                'next_url': next_url,
                'reason': reason
            }
            
            return result
            
        except Exception as e:
            rprint(f"[red]Error detectando paginación: {str(e)}[/red]")
            return {'has_more_pages': False, 'reason': f'error: {str(e)}'}


    def _process_companies_from_current_page(self, page: Page) -> int:
        
        try:
            company_links = page.eval_on_selector_all(
                '.listado-item',
                '''nodes => nodes
                    .map(node => node.querySelector('.row a')?.href)
                    .filter(Boolean)
                '''
            )
            
            companies_processed = 0
            
            if not company_links:
                rprint(f"[yellow]No se encontraron empresas en esta página[/yellow]")
                return 0
            
            rprint(f"[cyan]Procesando {len(company_links)} empresas de esta página...[/cyan]")
            
            for i, company_url in enumerate(company_links, 1):
                rprint(f"[cyan]  Empresa {i}/{len(company_links)}[/cyan]")
                
                if i > 1:
                    time.sleep(random.uniform(1, 2))
                
                company_data = self.scrape_company_metadata(company_url)
                
                if company_data:
                    self._append_to_json(company_data)
                    companies_processed += 1
                    rprint(f"[green]  ✓ Guardada en JSON[/green]")
                else:
                    rprint(f"[red]  ✗ Error al procesar empresa[/red]")
            
            return companies_processed
            
        except Exception as e:
            rprint(f"[red]Error procesando empresas de la página actual: {str(e)}[/red]")
            return 0


    def scrape_company_urls(self, base_url: str) -> List[str]:
        
        rprint(f"[yellow]Extrayendo enlaces de empresas de: {base_url}[/yellow]")
        self._random_delay()
        
        all_company_links = []
        current_url = base_url
        page_num = 1
        
        while True:
            rprint(f"[cyan]Procesando página {page_num}: {current_url}[/cyan]")
            
            for attempt in range(self.max_retries):
                try:
                    with self._get_page() as page:
                        response = page.goto(current_url, wait_until="networkidle", timeout=60000)
                        
                        if response.status == 404:
                            rprint(f"[yellow]Página {page_num} no encontrada (404)[/yellow]")
                            rprint(f"[green]Total empresas encontradas: {len(all_company_links)}[/green]")
                            return all_company_links
                        
                        page.wait_for_selector('.listado-item', timeout=30000)
                        
                        # Procesar empresas de esta página directamente
                        companies_processed = self._process_companies_from_current_page(page)
                        rprint(f"[green]Procesadas {companies_processed} empresas en página {page_num}[/green]")
                        
                        pagination_info = self._detect_pagination(page)
                        rprint(f"[cyan]Info paginación: {pagination_info}[/cyan]")
                        
                        if not pagination_info['has_more_pages']:
                            rprint(f"[green]No hay más páginas disponibles - {pagination_info['reason']}[/green]")
                            return []

                        if pagination_info.get('next_url'):
                            current_url = pagination_info['next_url']
                        else:
                            next_page_num = page_num + 1
                            base_url_clean = base_url.rstrip('/')
                            if re.search(r'/\d+$', base_url_clean):
                                current_url = re.sub(r'/\d+$', f'/{next_page_num}', base_url_clean)
                            else:
                                current_url = f"{base_url_clean}/{next_page_num}"
                        
                        rprint(f"[green]Siguiente página: {current_url}[/green]")
                        page_num += 1
                        break

                except Exception as e:
                    if attempt == self.max_retries - 1:
                        rprint(f"[red]Error después de {self.max_retries} intentos: {str(e)[:100]}[/red]")
                        return []
                    
                    rprint(f"[red]Intento {attempt + 1} fallido, reintentando...[/red]")
                    self._random_delay()
            
            self._random_delay()

    
    def scrape_company_metadata(self, company_url: str) -> Optional[CompanyMetadata]:

        rprint("[blue]*[/blue]" * 15)
        self._random_delay()

        for attempt in range(self.max_retries):
            try:
                with self._get_page() as page:
                    page.goto(company_url, wait_until="networkidle", timeout=60000)
                    page.wait_for_selector('h1[itemprop="name"]', timeout=30000)

                    metadata: CompanyMetadata = {
                        "nombre": self._get_text_safe(page, 'h1[itemprop="name"]'),
                        "descripcion": self._get_text_safe(page, '.claim p'),
                        "direccion": self._get_address_safe(page),
                        "telefono": self._get_text_safe(page, '.telephone[itemprop="telephone"]'),
                        "website": self._get_website_safe(page),
                        "actividades": self._get_text_safe(page, '.actividades p'),
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


    def main(self):
        
        try:
            self.playwright = sync_playwright().start()
            rprint("[green]Conectando...[/green]")
            
            URL = "https://www.paginasamarillas.es/a/centro-de-salud/madrid/"
            
            self.browser = self.playwright.chromium.launch(
                headless = True,
                timeout = 60000,
                args=["--ignore-certificate-errors", "--ignore-ssl-errors"]
            )
            
            rprint(f"[blue]Iniciando scraping de: {URL}[/blue]")
            rprint(f"[blue]Archivo de salida: ./data/{self.json_filename}[/blue]")
            
            companies = self.scrape_company_urls(URL)
            rprint(f"[green]Proceso completado![/green]")
            
            return companies
            
        except Exception as e:
            rprint(f"[red]Error general: {str(e)[:120]}[/red]")
            return []
            
        finally:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
