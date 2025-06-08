<div align="center">
  
# 🕷️ Scraping Engine

</div>

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/yourusername/scraping-engine/issues)

**Scraping Engine** is a powerful and extensible web scraping framework that allows you to easily create and manage multiple scraping modules for different websites. Built with Python, it provides a robust architecture for handling various scraping scenarios with built-in logging and error handling.

</div>

## ✨ Features

- 🔌 **Modular Architecture**: Easily add new scraping modules without modifying the core engine
- 📊 **Automated Data Collection**: Streamlined process for gathering data from multiple sources
- 📝 **Built-in Logging**: Comprehensive logging system for tracking scraping operations
- ⚡ **Dynamic Module Loading**: Automatically discovers and loads all scraping modules
- 🛡️ **Error Handling**: Robust error handling to ensure continuous operation
- 🔄 **Independent Execution**: Each scraping module runs independently to prevent cascading failures

## 🚀 Getting Started

### Prerequisites

- Python 3.12 or higher
- uv (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/begonlabs/scraping-engine.git
cd scraping-engine
```



## 🛠️ Usage

### Running the Engine

To run all scraping modules and install dependecies:

```bash
uv run main.py
```

### Creating a New Scraper

1. Create a new Python file in the `sites` directory
2. Define your scraper class with a `main()` method
3. The engine will automatically discover and run your scraper

Example scraper:

```python
class MyScraper:
    def __init__(self):
        # Initialize your scraper
        pass
        
    def main(self):
        # Implement your scraping logic
        pass
```

## 📂 Project Structure

```
scraping-engine/
├── main.py              # Main engine script
├── config.py           # Configuration settings
├── sites/              # Scraping modules
│   ├── __init__.py
│   ├── axesor.py
│   ├── pa_abogados.py
│   └── ... (other scrapers)
└── data/               # Data output directory
```

## 📊 Available Scrapers

Currently includes scrapers for various business categories:
- 🏢 Business Information (Axesor)
- ⚖️ Lawyers
- 🍽️ Restaurants
- 🏥 Healthcare Services
- 🚗 Auto Services
- And many more...

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. 🍴 Fork the repository
2. 🌿 Create your feature branch (`git checkout -b feature/AmazingScraper`)
3. 💾 Commit your changes (`git commit -m 'Add some AmazingScraper'`)
4. 🚀 Push to the branch (`git push origin feature/AmazingScraper`)
5. 🔁 Open a Pull Request

## 📝 Logging

The engine automatically logs all operations to `scraping_engine.log`, including:
- Information about scraping processes
- Errors and exceptions
- Module loading status

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  
Made with ❤️ by Walkercito

</div>