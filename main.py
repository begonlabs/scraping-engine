import importlib
import inspect
import logging
from pathlib import Path


logging.basicConfig(
    filename='scraping_engine.log',
    filemode='a',
    format='%(asctime)s %(levelname)s: %(message)s',
    level=logging.INFO
)


def load_all_sites():
    
    sites_dir = Path(__file__).parent / 'sites'
    sites = []

    for file in sites_dir.glob('*.py'):
        if file.name == '__init__.py':
            continue

        module_path = f"sites.{file.stem}"
        
        try:
            module = importlib.import_module(module_path)
            
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == module_path:
                    sites.append(obj)
        
        except Exception as e:
            logging.error(f"Error cargando: {module_path}: {e}")
    
    return sites


def main():
    
    sites = load_all_sites()
    for site_class in sites:
        try:
            logging.info(f"Procesando: {site_class.__name__}...")
            site = site_class()
            site.main()
        
        except Exception as e:
            logging.error(f"Error procesando: {site_class.__name__}: {e}")

if __name__ == "__main__":
    main()