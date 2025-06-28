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


class ProductMetadata(TypedDict):
    nombre: str
    precio: str
    categoria: str
    marca: str
    descripcion: str
    url: str


class Supermarket:

    def __init__(self) -> None:
        self.USER_AGENTS: List[str] = config.USER_AGENTS
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.request_delay = (2, 4)
        self.max_retries = 3
        self.json_filename = f"supermarket_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


    @contextmanager
    def _get_page(self, user_agent: str = None):
        """
        Context manager para crear y cerrar páginas de Playwright
        """
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
        """
        Pausa aleatoria entre solicitudes
        """
        delay = random.uniform(*self.request_delay)
        rprint(f"[yellow]Esperando {delay:.2f} segundos...[/yellow]")
        time.sleep(delay)


    def _append_to_json(self, data: ProductMetadata):
        """
        Añade datos al archivo JSON
        """
        data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(data_dir, exist_ok=True)

        json_path = os.path.join(data_dir, self.json_filename)
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []

        existing_data.append(data)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)


    def _handle_location_dialog(self, page: Page) -> bool:
        """
        Maneja el diálogo de selección de ubicación
        """
        try:
            # Verificar si el dialog está presente
            dialog_selector = 'app-target-delivery-dialog'
            
            dialog_element = page.query_selector(dialog_selector)
            if not dialog_element:
                rprint("[yellow]No se encontró el dialog de ubicación[/yellow]")
                return False
            
            rprint("[cyan]Dialog de ubicación detectado, configurando...[/cyan]")
            
            # Verificar si el diálogo es visible
            is_visible = page.is_visible(dialog_selector)
            rprint(f"[cyan]¿Dialog visible? {is_visible}[/cyan]")
            
            # Buscar todos los selectores posibles para provincia
            province_selectors = [
                'select[name="province"]',
                'select[id="province"]',
                '#province',
                'select:has-text("provincia")',
                'select:has-text("Provincia")',
                'select'  # Fallback genérico
            ]
            
            province_selector = None
            for selector in province_selectors:
                if page.query_selector(selector):
                    province_selector = selector
                    rprint(f"[green]Selector de provincia encontrado: {selector}[/green]")
                    break
            
            if not province_selector:
                rprint("[red]No se encontró selector de provincia[/red]")
                return False
            
            page.wait_for_selector(province_selector, timeout=10000)
            
            # Buscar la opción de La Habana por el texto visible
            province_options = page.query_selector_all(f'{province_selector} option')
            rprint(f"[cyan]Opciones de provincia encontradas: {len(province_options)}[/cyan]")
            
            habana_found = False
            for i, option in enumerate(province_options):
                option_text = option.inner_text().strip()
                rprint(f"[cyan]Opción {i}: '{option_text}'[/cyan]")
                if "La Habana" in option_text or "Habana" in option_text:
                    option_value = option.get_attribute('value')
                    rprint(f"[green]Intentando seleccionar La Habana con valor: {option_value}[/green]")
                    page.select_option(province_selector, option_value)
                    rprint("[green]Provincia 'La Habana' seleccionada[/green]")
                    habana_found = True
                    break
            
            if not habana_found:
                rprint("[red]No se encontró la opción 'La Habana'[/red]")
                return False
            
            # Esperar a que se carguen los municipios
            rprint("[cyan]Esperando a que se carguen los municipios...[/cyan]")
            time.sleep(5)
            
            # Buscar selectores de municipio
            municipality_selectors = [
                'select[name="municipality"]',
                'select[id="municipality"]',
                '#municipality',
                'select:has-text("municipio")',
                'select:has-text("Municipio")'
            ]
            
            municipality_selector = None
            for selector in municipality_selectors:
                if page.query_selector(selector):
                    municipality_selector = selector
                    rprint(f"[green]Selector de municipio encontrado: {selector}[/green]")
                    break
            
            if not municipality_selector:
                rprint("[red]No se encontró selector de municipio[/red]")
                return False
            
            # ✅ CORREGIDO: Esperar a que el select de municipios tenga opciones cargadas
            page.wait_for_function(
                f'''() => {{
                    const select = document.querySelector("{municipality_selector}");
                    return select && select.options.length > 1;
                }}''',
                timeout=15000
            )
            
            # Buscar la opción de Centro Habana por el texto visible
            municipality_options = page.query_selector_all(f'{municipality_selector} option')
            rprint(f"[cyan]Opciones de municipio encontradas: {len(municipality_options)}[/cyan]")
            
            centro_habana_found = False
            for i, option in enumerate(municipality_options):
                option_text = option.inner_text().strip().upper()
                rprint(f"[cyan]Opción municipio {i}: '{option_text}'[/cyan]")
                if "CENTRO HABANA" in option_text:
                    option_value = option.get_attribute('value')
                    rprint(f"[green]Intentando seleccionar Centro Habana con valor: {option_value}[/green]")
                    page.select_option(municipality_selector, option_value)
                    rprint("[green]Municipio 'CENTRO HABANA' seleccionado[/green]")
                    centro_habana_found = True
                    break
            
            if not centro_habana_found:
                rprint("[red]No se encontró el municipio 'CENTRO HABANA'[/red]")
                return False
            
            # Buscar botón Aceptar con múltiples selectores
            accept_selectors = [
                'button.btn-primary-yellow.yellow-rounded',
                'button:has-text("Aceptar")',
                'button:has-text("Continuar")',
                'button:has-text("Confirmar")',
                'button[type="submit"]',
                '.btn-primary',
                '.btn-yellow'
            ]
            
            accept_button = None
            for selector in accept_selectors:
                button = page.query_selector(selector)
                if button:
                    accept_button = button
                    rprint(f"[green]Botón aceptar encontrado con selector: {selector}[/green]")
                    break
            
            if accept_button:
                # ✅ CORREGIDO: Asegurarse de que el botón es clickeable
                page.wait_for_function(
                    '''(button) => {
                        return button.offsetParent !== null && !button.disabled;
                    }''',
                    arg=accept_button,
                    timeout=5000
                )
                
                accept_button.click()
                rprint("[green]Botón 'Aceptar' clickeado[/green]")
                
                # Esperar a que el dialog desaparezca
                page.wait_for_selector(dialog_selector, state='detached', timeout=15000)
                rprint("[green]Dialog de ubicación cerrado exitosamente[/green]")
                
                # Esperar a que la página se recargue/actualice después del diálogo
                rprint("[cyan]Esperando a que la página se actualice...[/cyan]")
                time.sleep(5)
                
                # Esperar a que la página esté completamente cargada
                page.wait_for_load_state("networkidle", timeout=30000)
                rprint("[cyan]Página actualizada correctamente[/cyan]")
                
                return True
            else:
                rprint("[red]No se encontró el botón Aceptar con ningún selector[/red]")
                return False
                
        except Exception as e:
            rprint(f"[red]Error manejando dialog de ubicación: {str(e)}[/red]")
            import traceback
            rprint(f"[red]Traceback: {traceback.format_exc()}[/red]")
            return False


    def _get_text_safe(self, page: Page, selector: str) -> str:
        """
        Extrae texto de forma segura
        """
        try:
            element = page.query_selector(selector)
            return element.inner_text().strip() if element else "N/A"
        except:
            return "N/A"


    def _get_price_safe(self, page: Page) -> str:
        """
        Extrae precio de forma segura
        """
        try:
            # Intentar obtener precio desde meta tag primero
            price_meta = page.query_selector('meta[itemprop="price"]')
            if price_meta:
                price_value = price_meta.get_attribute('content')
                if price_value:
                    return f"{price_value} USD"
            
            # Si no, desde el span visible
            price_span = page.query_selector('span.regular_price')
            if price_span:
                return price_span.inner_text().strip()
            
            return "N/A"
        except:
            return "N/A"


    def _get_category_safe(self, page: Page) -> str:
        """
        Extrae categoría de forma segura
        """
        try:
            category_link = page.query_selector('span[itemtype="https://schema.org/CategoryCode"] a.link')
            if category_link:
                return category_link.inner_text().strip()
            
            # Alternativa: desde meta tag
            category_meta = page.query_selector('meta[itemprop="name"][content]')
            if category_meta:
                return category_meta.get_attribute('content') or "N/A"
                
            return "N/A"
        except:
            return "N/A"


    def _get_brand_safe(self, page: Page) -> str:
        """
        Extrae marca de forma segura
        """
        try:
            brand_link = page.query_selector('span[itemprop="brand"] a.link')
            if brand_link:
                return brand_link.inner_text().strip()
            
            # Alternativa: desde meta tag
            brand_meta = page.query_selector('span[itemprop="brand"] meta[itemprop="name"]')
            if brand_meta:
                return brand_meta.get_attribute('content') or "N/A"
                
            return "N/A"
        except:
            return "N/A"


    def _get_description_safe(self, page: Page) -> str:
        """
        Extrae descripción de forma segura
        """
        try:
            desc_p = page.query_selector('p[itemprop="description"]')
            if desc_p:
                return desc_p.inner_text().strip()
            return "N/A"
        except:
            return "N/A"


    def _check_and_handle_dialog(self, page: Page):
        """
        Verifica y maneja diálogos en cada página
        """
        try:
            rprint("[cyan]Verificando si hay diálogos en la página...[/cyan]")
            
            # Verificar múltiples selectores de diálogo
            dialog_selectors = [
                'app-target-delivery-dialog',
                '.modal',
                '.dialog',
                '[role="dialog"]',
                '.popup'
            ]
            
            dialog_found = False
            dialog_selector_used = None
            
            for selector in dialog_selectors:
                dialog_present = page.query_selector(selector)
                if dialog_present:
                    is_visible = page.is_visible(selector)
                    rprint(f"[cyan]Diálogo encontrado con selector '{selector}', visible: {is_visible}[/cyan]")
                    if is_visible:
                        dialog_found = True
                        dialog_selector_used = selector
                        break
            
            if dialog_found:
                rprint(f"[cyan]Manejando diálogo con selector: {dialog_selector_used}[/cyan]")
                success = self._handle_location_dialog(page)
                if success:
                    rprint("[green]Diálogo manejado exitosamente[/green]")
                    # Pequeña pausa después de manejar el dialog
                    time.sleep(2)
                else:
                    rprint("[red]Error manejando el diálogo[/red]")
            else:
                rprint("[cyan]No se encontraron diálogos visibles[/cyan]")
                
        except Exception as e:
            rprint(f"[yellow]Error verificando dialog: {str(e)}[/yellow]")
            import traceback
            rprint(f"[yellow]Traceback: {traceback.format_exc()[:200]}[/yellow]")


    def _detect_pagination(self, page: Page) -> Dict[str, any]:
        """
        Detecta información de paginación
        """
        try:
            pagination_container = page.query_selector('pagination ul.pagination')
            
            if not pagination_container:
                rprint(f"[yellow]No se encontró contenedor de paginación[/yellow]")
                return {'has_more_pages': False, 'reason': 'no_pagination_container'}
            
            # Obtener página actual
            current_page_element = pagination_container.query_selector('li.pagination-page.active a')
            current_page = 1
            if current_page_element:
                current_page_text = current_page_element.inner_text().strip()
                current_page = int(current_page_text) if current_page_text.isdigit() else 1
            
            # Obtener todas las páginas visibles
            page_links = pagination_container.query_selector_all('li.pagination-page a')
            page_numbers = []
            
            for link in page_links:
                page_text = link.inner_text().strip()
                if page_text.isdigit():
                    page_numbers.append(int(page_text))

            # Verificar botón siguiente
            next_button = pagination_container.query_selector('li.pagination-next:not(.disabled) a')
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


    def _process_products_from_current_page(self, page: Page) -> int:
        """
        Procesa productos de la página actual
        """
        try:
            rprint("[cyan]Intentando extraer enlaces de productos...[/cyan]")
            
            # ✅ CORREGIDO: Selectores más específicos y en orden de prioridad
            selectors_to_try = [
                'a.primary_img',  # ✅ Con underscore, no asterisco
                'a[href*="/es/producto/"]',  # ✅ Más específico para español
                'a[href*="/producto/"]',
                '.product-item a',
                '.product-link',
                'a[href*="/es/productos/"]'
            ]
            
            product_links = []
            
            for selector in selectors_to_try:
                try:
                    rprint(f"[cyan]Probando selector: {selector}[/cyan]")
                    links = page.eval_on_selector_all(
                        selector,
                        '''nodes => nodes
                            .map(node => {
                                const href = node.getAttribute('href');
                                if (!href) return null;
                                
                                // ✅ MEJORA: Filtrar solo enlaces de productos
                                if (href.includes('/producto/') || href.includes('/es/producto/')) {
                                    return href.startsWith('/') ? 'https://www.supermarket23.com' + href : href;
                                }
                                return null;
                            })
                            .filter(Boolean)
                        '''
                    )
                    
                    if links and len(links) > 0:
                        # ✅ MEJORA: Eliminar duplicados
                        product_links = list(set(links))
                        rprint(f"[green]Encontrados {len(product_links)} enlaces únicos con selector: {selector}[/green]")
                        break
                    else:
                        rprint(f"[yellow]No se encontraron enlaces con selector: {selector}[/yellow]")
                        
                except Exception as e:
                    rprint(f"[red]Error con selector {selector}: {str(e)[:50]}[/red]")
                    continue
            
            products_processed = 0
            
            if not product_links:
                rprint(f"[red]No se encontraron productos en esta página con ningún selector[/red]")
                
                # ✅ MEJORA: Debug más específico
                try:
                    all_product_links = page.eval_on_selector_all(
                        'a[href*="/producto/"]',
                        'nodes => nodes.map(node => node.getAttribute("href")).filter(Boolean).slice(0, 5)'
                    )
                    rprint(f"[yellow]Enlaces de producto encontrados (primeros 5): {all_product_links}[/yellow]")
                    
                    # Verificar si hay elementos con clase primary_img
                    primary_img_count = page.locator('a.primary_img').count()
                    rprint(f"[yellow]Elementos con clase 'primary_img': {primary_img_count}[/yellow]")
                    
                except Exception as debug_error:
                    rprint(f"[yellow]Error en debug: {debug_error}[/yellow]")
                    
                return 0
            
            rprint(f"[cyan]Procesando {len(product_links)} productos de esta página...[/cyan]")
            
            for i, product_url in enumerate(product_links, 1):
                rprint(f"[cyan]  Producto {i}/{len(product_links)}: {product_url[:80]}...[/cyan]")
                
                if i > 1:
                    time.sleep(random.uniform(1, 2))
                
                product_data = self.scrape_product_metadata(product_url)
                
                if product_data:
                    self._append_to_json(product_data)
                    products_processed += 1
                    rprint(f"[green]  ✓ Guardado en JSON[/green]")
                else:
                    rprint(f"[red]  ✗ Error al procesar producto[/red]")
            
            return products_processed
            
        except Exception as e:
            rprint(f"[red]Error procesando productos de la página actual: {str(e)}[/red]")
            return 0


    def scrape_product_urls(self, base_url: str) -> List[str]:
        """
        Extrae URLs de productos y los procesa directamente
        """
        rprint(f"[yellow]Extrayendo enlaces de productos de: {base_url}[/yellow]")
        self._random_delay()
        
        current_url = base_url
        page_num = 1
        total_products_processed = 0
        
        while True:
            rprint(f"[cyan]Procesando página {page_num}: {current_url}[/cyan]")
            
            for attempt in range(self.max_retries):
                try:
                    with self._get_page() as page:
                        rprint(f"[cyan]Navegando a: {current_url}[/cyan]")
                        page.goto(current_url, wait_until="networkidle", timeout=60000)
                        
                        # Verificar y manejar dialog en cada página
                        self._check_and_handle_dialog(page)
                        
                        # ✅ CORREGIDO: Verificar múltiples selectores para productos
                        rprint("[cyan]Buscando productos en la página...[/cyan]")
                        product_selectors = [
                            'a.primary_img',  # ✅ Con underscore
                            'a[href*="/es/producto/"]',
                            'a[href*="/producto/"]',
                            '.product-item a',
                            '.product-link'
                        ]
                        
                        products_found = False
                        for selector in product_selectors:
                            try:
                                page.wait_for_selector(selector, timeout=10000)
                                rprint(f"[green]Productos encontrados con selector: {selector}[/green]")
                                products_found = True
                                break
                            except:
                                rprint(f"[yellow]No se encontraron productos con selector: {selector}[/yellow]")
                                continue
                        
                        if not products_found:
                            rprint("[red]No se encontraron productos con ningún selector[/red]")
                            # Intentar ver qué hay en la página
                            page_content = page.content()
                            if "producto" in page_content.lower():
                                rprint("[yellow]La palabra 'producto' está en la página, revisando estructura...[/yellow]")
                            raise Exception("No se encontraron productos en la página")
                        
                        # Procesar productos de esta página directamente
                        products_processed = self._process_products_from_current_page(page)
                        total_products_processed += products_processed
                        rprint(f"[green]Procesados {products_processed} productos en página {page_num} (Total: {total_products_processed})[/green]")
                        
                        pagination_info = self._detect_pagination(page)
                        rprint(f"[cyan]Info paginación: {pagination_info}[/cyan]")
                        
                        if not pagination_info['has_more_pages']:
                            rprint(f"[green]No hay más páginas disponibles - {pagination_info['reason']}[/green]")
                            rprint(f"[green]Total productos procesados: {total_products_processed}[/green]")
                            return []

                        # Construir URL de siguiente página
                        next_page_num = page_num + 1
                        current_url = f"https://www.supermarket23.com/es/productos?pagina={next_page_num}"
                        
                        rprint(f"[green]Siguiente página: {current_url}[/green]")
                        page_num += 1
                        break

                except Exception as e:
                    rprint(f"[red]Error en intento {attempt + 1}: {str(e)}[/red]")
                    if attempt == self.max_retries - 1:
                        rprint(f"[red]Error después de {self.max_retries} intentos: {str(e)[:200]}[/red]")
                        rprint(f"[green]Total productos procesados: {total_products_processed}[/green]")
                        return []
                    
                    rprint(f"[red]Intento {attempt + 1} fallido, reintentando...[/red]")
                    self._random_delay()
            
            self._random_delay()


    def scrape_product_metadata(self, product_url: str) -> Optional[ProductMetadata]:
        """
        Extrae metadatos de un producto específico
        """
        rprint("[blue]*[/blue]" * 15)
        self._random_delay()

        for attempt in range(self.max_retries):
            try:
                with self._get_page() as page:
                    page.goto(product_url, wait_until="networkidle", timeout=60000)
                    
                    # Verificar dialog en página de producto
                    self._check_and_handle_dialog(page)
                    
                    # Esperar elemento principal del producto
                    page.wait_for_selector('h1[itemprop="name"]', timeout=30000)

                    metadata: ProductMetadata = {
                        "nombre": self._get_text_safe(page, 'h1[itemprop="name"]'),
                        "precio": self._get_price_safe(page),
                        "categoria": self._get_category_safe(page),
                        "marca": self._get_brand_safe(page),
                        "descripcion": self._get_description_safe(page),
                        "url": product_url
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
        """
        Método principal para ejecutar el scraping
        """
        try:
            self.playwright = sync_playwright().start()
            rprint("[green]Conectando...[/green]")

            self.browser = self.playwright.chromium.launch(
                headless=False,
                timeout=60000
            )
            
            URL = "https://www.supermarket23.com/es/productos?pagina=1"
            
            rprint(f"[blue]Iniciando scraping de: {URL}[/blue]")
            rprint(f"[blue]Archivo de salida: ./data/{self.json_filename}[/blue]")
            
            products = self.scrape_product_urls(URL)
            rprint(f"[green]Proceso completado![/green]")
            
            return products
                
        except Exception as e:
            rprint(f"[red]Error general: {str(e)[:120]}[/red]")
            return []
            
        finally:
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
