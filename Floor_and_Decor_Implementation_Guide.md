# Floor and Decor Automation Implementation Guide

## Overview

This guide provides specific implementation details and code examples for building the Floor and Decor automation script based on the design document. It includes concrete code snippets, selector strategies, and integration patterns with the existing infrastructure.

## 1. Project Structure

```
src/
├── floor_decor_automator.py          # Main orchestrator
├── floor_decor/
│   ├── __init__.py
│   ├── config.py                     # Configuration management
│   ├── models.py                     # Data models
│   ├── navigator.py                  # Product navigation
│   ├── cart_manager.py               # Cart operations
│   ├── session_manager.py            # Session handling
│   ├── error_handler.py              # Error handling
│   └── selectors.py                  # Element selectors
├── vision/
│   ├── floor_decor_vision.py         # Custom vision prompts
│   └── element_detectors.py          # Specialized detection
└── config/
    ├── floor_decor_config.yaml       # Default configuration
    └── tile_products.yaml            # Product definitions
```

## 2. Core Implementation

### 2.1 Main Orchestrator

```python
# src/floor_decor_automator.py

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from src.drivers.browser_selenium import SeleniumCanvasDriver
from src.agent.web_agent import VisionWebAgent, AgentConfig
from src.floor_decor.config import AutomationConfig
from src.floor_decor.models import ProductList, TileProduct, AutomationResult
from src.floor_decor.navigator import ProductNavigator
from src.floor_decor.cart_manager import CartManager
from src.floor_decor.session_manager import SessionManager
from src.floor_decor.error_handler import ErrorHandler

class FloorAndDecorAutomator:
    """Main automation orchestrator for Floor and Decor"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = AutomationConfig(config_path or "src/config/floor_decor_config.yaml")
        self.logger = self._setup_logging()
        
        # Initialize browser driver with profile
        self.driver = SeleniumCanvasDriver(
            profile_dir=self.config.browser.profile_dir
        )
        
        # Initialize vision agent
        self.vision_config = AgentConfig(
            provider=self.config.vision.provider,
            model=self.config.vision.model,
            max_steps=1,  # Single step per action
            step_delay_s=self.config.automation.default_delays.between_actions,
            log_dir=f"logs/floor_decor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.vision_agent = VisionWebAgent(drv=self.driver)
        
        # Initialize specialized managers
        self.navigator = ProductNavigator(self.driver, self.vision_agent, self.config)
        self.cart_manager = CartManager(self.driver, self.vision_agent, self.config)
        self.session_manager = SessionManager(self.driver, self.config)
        self.error_handler = ErrorHandler(self.config.retry)
    
    def run(self, product_list_name: str = "Default Tile Order") -> AutomationResult:
        """Execute the full automation workflow"""
        self.logger.info(f"Starting Floor and Decor automation for: {product_list_name}")
        
        try:
            # Initialize session
            self.session_manager.initialize()
            
            # Load product list
            products = self.config.get_product_list(product_list_name)
            self.logger.info(f"Loaded {len(products.products)} products to process")
            
            # Process each product
            results = []
            for i, product in enumerate(products.products, 1):
                self.logger.info(f"Processing product {i}/{len(products.products)}: {product.name}")
                
                result = self.error_handler.with_retry(
                    lambda: self.navigator.process_product(product)
                )
                results.append(result)
                
                if not result.success:
                    self.logger.warning(f"Failed to process product {product.sku}: {result.error}")
            
            # Review cart contents
            cart_contents = self.cart_manager.get_cart_contents()
            self.logger.info(f"Cart contains {len(cart_contents)} items")
            
            # Prepare for human takeover
            self.session_manager.prepare_for_handover()
            
            return AutomationResult(
                success=True,
                products_processed=results,
                cart_contents=cart_contents,
                total_products=len(products.products),
                successful_products=sum(1 for r in results if r.success)
            )
            
        except Exception as e:
            self.logger.error(f"Fatal error in automation: {str(e)}")
            return AutomationResult(
                success=False,
                error=str(e),
                products_processed=[],
                cart_contents=[]
            )
    
    def _setup_logging(self) -> logging.Logger:
        """Setup structured logging"""
        logger = logging.getLogger("FloorAndDecorAutomator")
        logger.setLevel(logging.INFO)
        
        # Create file handler
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler(
            log_dir / f"floor_decor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
```

### 2.2 Data Models

```python
# src/floor_decor/models.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class UnitType(Enum):
    PIECES = "pieces"
    BOXES = "boxes"
    SQFT = "sqft"

class ProcessingStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"

@dataclass
class TileProduct:
    sku: str
    name: str
    quantity: int
    unit_type: UnitType
    category: str
    url_pattern: str
    coverage_area: Optional[float] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.unit_type, str):
            self.unit_type = UnitType(self.unit_type)

@dataclass
class ProductList:
    name: str
    products: List[TileProduct]
    store_location: Optional[str] = None
    contingency_percentage: float = 0.1
    
    def get_product_by_sku(self, sku: str) -> Optional[TileProduct]:
        """Find product by SKU"""
        for product in self.products:
            if product.sku == sku:
                return product
        return None

@dataclass
class ProcessingResult:
    product: TileProduct
    status: ProcessingStatus
    success: bool
    error: Optional[str] = None
    attempts: int = 1
    cart_verified: bool = False

@dataclass
class CartItem:
    sku: str
    name: str
    quantity: int
    unit_type: UnitType
    price: float
    total_price: float

@dataclass
class AutomationResult:
    success: bool
    products_processed: List[ProcessingResult]
    cart_contents: List[CartItem]
    total_products: int = 0
    successful_products: int = 0
    error: Optional[str] = None
    execution_time: Optional[float] = None
```

### 2.3 Product Navigator Implementation

```python
# src/floor_decor/navigator.py

from __future__ import annotations
import time
from typing import Optional, Tuple

from src.drivers.browser_selenium import SeleniumCanvasDriver
from src.agent.web_agent import VisionWebAgent
from src.floor_decor.models import TileProduct, ProcessingResult, ProcessingStatus, UnitType
from src.floor_decor.config import AutomationConfig
from src.floor_decor.selectors import FloorDecorSelectors
from src.vision.floor_decor_vision import FloorDecorVisionPrompts

class ProductNavigator:
    """Handles product page navigation and interaction"""
    
    def __init__(self, driver: SeleniumCanvasDriver, vision_agent: VisionWebAgent, config: AutomationConfig):
        self.driver = driver
        self.vision_agent = vision_agent
        self.config = config
        self.selectors = FloorDecorSelectors()
        self.vision_prompts = FloorDecorVisionPrompts()
    
    def process_product(self, product: TileProduct) -> ProcessingResult:
        """Process a single product from navigation to cart addition"""
        try:
            # Navigate to product page
            if not self._navigate_to_product(product):
                return ProcessingResult(
                    product=product,
                    status=ProcessingStatus.FAILED,
                    success=False,
                    error="Failed to navigate to product page"
                )
            
            # Wait for page to load
            time.sleep(self.config.automation.default_delays.page_load)
            
            # Handle quantity selection
            if not self._select_quantity(product):
                return ProcessingResult(
                    product=product,
                    status=ProcessingStatus.FAILED,
                    success=False,
                    error="Failed to select quantity"
                )
            
            # Add to cart
            if not self._add_to_cart():
                return ProcessingResult(
                    product=product,
                    status=ProcessingStatus.FAILED,
                    success=False,
                    error="Failed to add item to cart"
                )
            
            # Verify cart addition
            cart_verified = self._verify_cart_addition(product)
            
            return ProcessingResult(
                product=product,
                status=ProcessingStatus.SUCCESS,
                success=True,
                cart_verified=cart_verified
            )
            
        except Exception as e:
            return ProcessingResult(
                product=product,
                status=ProcessingStatus.FAILED,
                success=False,
                error=str(e)
            )
    
    def _navigate_to_product(self, product: TileProduct) -> bool:
        """Navigate to product page"""
        try:
            self.driver.goto(product.url_pattern)
            
            # Verify we're on the correct product page
            page_sku = self._get_page_sku()
            if page_sku and page_sku != product.sku:
                # Try alternative URL construction
                alternative_url = f"https://www.flooranddecor.com/{product.category}/{product.sku}"
                self.driver.goto(alternative_url)
                page_sku = self._get_page_sku()
                
            return page_sku == product.sku if page_sku else True
            
        except Exception:
            return False
    
    def _get_page_sku(self) -> Optional[str]:
        """Extract SKU from current page"""
        try:
            # Look for SKU in various page elements
            sku_selectors = [
                "[data-sku]",
                ".product-sku",
                ".sku",
                "[itemprop='productID']"
            ]
            
            for selector in sku_selectors:
                try:
                    element = self.driver._find(selector)
                    sku_text = element.get_attribute("data-sku") or element.text or element.get_attribute("content")
                    if sku_text and sku_text.isdigit():
                        return sku_text
                except Exception:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def _select_quantity(self, product: TileProduct) -> bool:
        """Select appropriate quantity and unit"""
        try:
            # Switch to correct unit type if needed
            if product.unit_type == UnitType.BOXES:
                self._switch_to_box_quantity()
            else:
                self._switch_to_piece_quantity()
            
            # Enter quantity
            return self._enter_quantity(product.quantity)
            
        except Exception:
            return False
    
    def _switch_to_box_quantity(self) -> bool:
        """Switch quantity selector to boxes"""
        try:
            # Look for unit selector
            unit_selector = self._find_unit_selector()
            if unit_selector:
                # Use vision to find and click "Boxes" option
                goal = "Find and click the 'Boxes' option to switch quantity unit to boxes"
                result = self.vision_agent.run(
                    start_url=self.driver.driver.current_url,
                    goal=goal,
                    cfg=AgentConfig(
                        provider=self.config.vision.provider,
                        model=self.config.vision.model,
                        selector="body",
                        max_steps=1
                    )
                )
                return result.get("status") == "ok"
            
            return True  # Assume already in correct mode if no selector found
            
        except Exception:
            return False
    
    def _switch_to_piece_quantity(self) -> bool:
        """Switch quantity selector to pieces"""
        try:
            # Look for unit selector
            unit_selector = self._find_unit_selector()
            if unit_selector:
                # Use vision to find and click "Pieces" option
                goal = "Find and click the 'Pieces' option to switch quantity unit to individual pieces"
                result = self.vision_agent.run(
                    start_url=self.driver.driver.current_url,
                    goal=goal,
                    cfg=AgentConfig(
                        provider=self.config.vision.provider,
                        model=self.config.vision.model,
                        selector="body",
                        max_steps=1
                    )
                )
                return result.get("status") == "ok"
            
            return True  # Assume already in correct mode if no selector found
            
        except Exception:
            return False
    
    def _find_unit_selector(self) -> Optional[Any]:
        """Find unit selector element"""
        try:
            selectors = [
                ".quantity-unit-selector",
                ".unit-selector",
                "[data-unit-selector]",
                ".quantity-type"
            ]
            
            for selector in selectors:
                try:
                    return self.driver._find(selector)
                except Exception:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def _enter_quantity(self, quantity: int) -> bool:
        """Enter quantity in the quantity input field"""
        try:
            # Use vision to find quantity input
            goal = f"Find the quantity input field and enter the value {quantity}"
            result = self.vision_agent.run(
                start_url=self.driver.driver.current_url,
                goal=goal,
                cfg=AgentConfig(
                    provider=self.config.vision.provider,
                    model=self.config.vision.model,
                    selector="body",
                    max_steps=2  # One to find, one to enter
                )
            )
            
            return result.get("status") == "ok"
            
        except Exception:
            return False
    
    def _add_to_cart(self) -> bool:
        """Click add to cart button"""
        try:
            # Use vision to find and click add to cart button
            goal = "Find and click the 'Add to Cart' button to add the product to cart"
            result = self.vision_agent.run(
                start_url=self.driver.driver.current_url,
                goal=goal,
                cfg=AgentConfig(
                    provider=self.config.vision.provider,
                    model=self.config.vision.model,
                    selector="body",
                    max_steps=1
                )
            )
            
            return result.get("status") == "ok"
            
        except Exception:
            return False
    
    def _verify_cart_addition(self, product: TileProduct) -> bool:
        """Verify that the product was added to cart"""
        try:
            # Look for cart confirmation message
            time.sleep(2)  # Wait for confirmation
            
            # Check for success message
            goal = "Look for confirmation message that item was added to cart"
            result = self.vision_agent.run(
                start_url=self.driver.driver.current_url,
                goal=goal,
                cfg=AgentConfig(
                    provider=self.config.vision.provider,
                    model=self.config.vision.model,
                    selector="body",
                    max_steps=1
                )
            )
            
            # Alternatively, check cart icon for updated count
            return result.get("status") == "ok"
            
        except Exception:
            return False
```

### 2.4 Cart Manager Implementation

```python
# src/floor_decor/cart_manager.py

from __future__ import annotations
import time
from typing import List, Optional

from src.drivers.browser_selenium import SeleniumCanvasDriver
from src.agent.web_agent import VisionWebAgent
from src.floor_decor.models import CartItem, TileProduct
from src.floor_decor.config import AutomationConfig

class CartManager:
    """Handles all cart-related operations"""
    
    def __init__(self, driver: SeleniumCanvasDriver, vision_agent: VisionWebAgent, config: AutomationConfig):
        self.driver = driver
        self.vision_agent = vision_agent
        self.config = config
    
    def get_cart_contents(self) -> List[CartItem]:
        """Retrieve current cart contents"""
        try:
            # Navigate to cart page
            self.driver.goto("https://www.flooranddecor.com/cart")
            time.sleep(self.config.automation.default_delays.page_load)
            
            # Extract cart items using vision
            goal = "Extract all items from the shopping cart including SKU, name, quantity, and price"
            result = self.vision_agent.run(
                start_url=self.driver.driver.current_url,
                goal=goal,
                cfg=AgentConfig(
                    provider=self.config.vision.provider,
                    model=self.config.vision.model,
                    selector="body",
                    max_steps=1
                )
            )
            
            # Parse vision response to extract cart items
            return self._parse_cart_items(result)
            
        except Exception as e:
            print(f"Error getting cart contents: {str(e)}")
            return []
    
    def _parse_cart_items(self, vision_result: dict) -> List[CartItem]:
        """Parse vision response to extract cart items"""
        # This would need custom parsing logic based on the vision response format
        # For now, return empty list as placeholder
        return []
    
    def verify_item_in_cart(self, product: TileProduct) -> bool:
        """Verify specific item was added to cart"""
        cart_contents = self.get_cart_contents()
        for item in cart_contents:
            if item.sku == product.sku:
                return True
        return False
    
    def get_cart_total(self) -> Optional[float]:
        """Get total cart value"""
        try:
            goal = "Find and extract the total cart price or order total"
            result = self.vision_agent.run(
                start_url=self.driver.driver.current_url,
                goal=goal,
                cfg=AgentConfig(
                    provider=self.config.vision.provider,
                    model=self.config.vision.model,
                    selector="body",
                    max_steps=1
                )
            )
            
            # Parse total from vision response
            return self._parse_cart_total(result)
            
        except Exception:
            return None
    
    def _parse_cart_total(self, vision_result: dict) -> Optional[float]:
        """Parse total from vision response"""
        # Implementation would depend on vision response format
        return None
```

### 2.5 Session Manager Implementation

```python
# src/floor_decor/session_manager.py

from __future__ import annotations
import time
from datetime import datetime

from src.drivers.browser_selenium import SeleniumCanvasDriver
from src.floor_decor.config import AutomationConfig

class SessionManager:
    """Handles browser session lifecycle and handover"""
    
    def __init__(self, driver: SeleniumCanvasDriver, config: AutomationConfig):
        self.driver = driver
        self.config = config
        self.session_start_time = None
    
    def initialize(self) -> None:
        """Initialize browser session"""
        self.session_start_time = datetime.now()
        
        # Open browser with start page
        self.driver.open("https://www.flooranddecor.com")
        time.sleep(self.config.automation.default_delays.page_load)
        
        print(f"\n{'='*80}")
        print(f"🚀 FLOOR AND DECOR AUTOMATION STARTED")
        print(f"📅 Started at: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔐 Using Chrome profile: {self.config.browser.profile_dir}")
        print(f"{'='*80}\n")
    
    def prepare_for_handover(self) -> None:
        """Prepare browser session for human takeover"""
        try:
            # Navigate to cart for review
            self.driver.goto("https://www.flooranddecor.com/cart")
            time.sleep(2)
            
            # Display completion message
            self._show_completion_message()
            
            # Keep browser open
            if self.config.session.keep_open:
                self._keep_session_open()
                
        except Exception as e:
            print(f"Error preparing for handover: {str(e)}")
    
    def _show_completion_message(self) -> None:
        """Display completion message in browser"""
        try:
            # Execute JavaScript to show message
            message = self.config.session.handover_message
            script = f"""
            alert('{message}');
            """
            self.driver.driver.execute_script(script)
            
        except Exception:
            # Fallback to console message
            print(f"\n{self.config.session.handover_message}\n")
    
    def _keep_session_open(self) -> None:
        """Keep browser session open for specified duration"""
        timeout_seconds = self.config.session.timeout_minutes * 60
        
        print(f"\n{'='*80}")
        print(f"🎉 AUTOMATION COMPLETE")
        print(f"🛒 Cart is ready for review")
        print(f"⏰ Session will remain open for {self.config.session.timeout_minutes} minutes")
        print(f"👤 Ready for human takeover")
        print(f"📊 Session duration: {datetime.now() - self.session_start_time}")
        print(f"{'='*80}\n")
        
        # Keep session alive
        time.sleep(timeout_seconds)
    
    def close(self) -> None:
        """Close browser session"""
        if self.driver:
            self.driver.close()
```

### 2.6 Error Handler Implementation

```python
# src/floor_decor/error_handler.py

from __future__ import annotations
import time
import random
from typing import Callable, Any

from src.floor_decor.config import AutomationConfig

class ErrorHandler:
    """Handles errors and retry mechanisms"""
    
    def __init__(self, retry_config):
        self.retry_config = retry_config
    
    def with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry mechanism"""
        last_exception = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                return func(*args, **kwargs)
                
            except Exception as e:
                last_exception = e
                
                if attempt == self.retry_config.max_attempts - 1:
                    # Last attempt failed, raise exception
                    raise e
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt)
                print(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
        
        # This should not be reached, but just in case
        if last_exception:
            raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt with exponential backoff and jitter"""
        base_delay = self.retry_config.base_delay
        max_delay = self.retry_config.max_delay
        exponential_base = self.retry_config.exponential_base
        
        # Calculate exponential backoff
        delay = base_delay * (exponential_base ** attempt)
        
        # Apply jitter if enabled
        if self.retry_config.jitter:
            jitter = random.uniform(0.8, 1.2)
            delay *= jitter
        
        # Cap at maximum delay
        return min(delay, max_delay)
    
    def handle_fatal_error(self, error: Exception) -> None:
        """Handle fatal errors that cannot be retried"""
        print(f"\n{'='*80}")
        print(f"❌ FATAL ERROR: {str(error)}")
        print(f"🔍 Error type: {type(error).__name__}")
        print(f"{'='*80}\n")
        
        # Log error details
        # Could also send notifications here
        
        raise error
```

## 3. Vision Integration

### 3.1 Custom Vision Prompts

```python
# src/vision/floor_decor_vision.py

class FloorDecorVisionPrompts:
    """Custom vision prompts for Floor and Decor automation"""
    
    @staticmethod
    def find_quantity_input():
        return """
        Find the quantity input field on this product page. Look for:
        - A number input field where quantity can be entered
        - Usually labeled "Quantity" or has a quantity icon
        - May have increment/decrement buttons nearby
        Return the coordinates to click on this input field.
        """
    
    @staticmethod
    def find_add_to_cart_button():
        return """
        Find the "Add to Cart" button on this product page. Look for:
        - A prominent button with text "Add to Cart"
        - Usually brightly colored (orange, blue, or green)
        - May be near the quantity selector
        Return the coordinates to click on this button.
        """
    
    @staticmethod
    def find_unit_selector(unit_type: str):
        return f"""
        Find the quantity unit selector and click on the "{unit_type}" option. Look for:
        - A dropdown or toggle that switches between "Pieces", "Boxes", and "Sq Ft"
        - May be near the quantity input field
        - Click on the option that shows "{unit_type}"
        Return the coordinates to click on the {unit_type} option.
        """
    
    @staticmethod
    def extract_cart_items():
        return """
        Extract all items from the shopping cart. For each item, identify:
        - Product SKU or item number
        - Product name/description
        - Quantity ordered
        - Unit type (pieces or boxes)
        - Price per unit
        - Total price for that item
        Return a structured list of all cart items with their details.
        """
```

## 4. Configuration Implementation

### 4.1 Configuration Management

```python
# src/floor_decor/config.py

from __future__ import annotations
import os
import yaml
import re
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from src.floor_decor.models import ProductList, TileProduct, UnitType

@dataclass
class BrowserConfig:
    profile_dir: Optional[str] = None
    window_size: tuple = (1280, 900)
    headless: bool = False

@dataclass
class VisionConfig:
    provider: str = "openai"
    model: str = "gpt-5-vision"
    confidence_threshold: float = 0.7

@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 2.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True

@dataclass
class SessionConfig:
    keep_open: bool = True
    timeout_minutes: int = 30
    handover_message: str = "Automation complete. Ready for human takeover."

@dataclass
class AutomationDelays:
    page_load: float = 3.0
    element_wait: float = 2.0
    between_actions: float = 1.0

@dataclass
class AutomationConfig:
    base_url: str = "https://www.flooranddecor.com"
    automation_delays: AutomationDelays = field(default_factory=AutomationDelays)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    products: list = field(default_factory=list)
    
    def __post_init__(self):
        # Set default profile directory from environment
        if not self.browser.profile_dir:
            self.browser.profile_dir = os.getenv("CHROME_PROFILE_DIR")
    
    @classmethod
    def from_file(cls, config_path: str) -> 'AutomationConfig':
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Substitute environment variables
        config_data = substitute_env_vars(config_data)
        
        # Convert to config objects
        return cls.from_dict(config_data)
    
    @classmethod
    def from_dict(cls, config_data: Dict[str, Any]) -> 'AutomationConfig':
        """Create config from dictionary"""
        # Extract nested configurations
        automation_delays = AutomationDelays(**config_data.get('automation', {}).get('default_delays', {}))
        browser = BrowserConfig(**config_data.get('browser', {}))
        vision = VisionConfig(**config_data.get('vision', {}))
        retry = RetryConfig(**config_data.get('retry', {}))
        session = SessionConfig(**config_data.get('session', {}))
        
        return cls(
            base_url=config_data.get('automation', {}).get('base_url', 'https://www.flooranddecor.com'),
            automation_delays=automation_delays,
            browser=browser,
            vision=vision,
            retry=retry,
            session=session,
            products=config_data.get('products', [])
        )
    
    def get_product_list(self, name: str) -> ProductList:
        """Load specific product list by name"""
        for product_config in self.products:
            if product_config['name'] == name:
                return load_product_list(product_config['file'])
        raise ValueError(f"Product list '{name}' not found")

def substitute_env_vars(config_data: Any) -> Any:
    """Recursively substitute environment variables in configuration"""
    if isinstance(config_data, dict):
        return {k: substitute_env_vars(v) for k, v in config_data.items()}
    elif isinstance(config_data, list):
        return [substitute_env_vars(item) for item in config_data]
    elif isinstance(config_data, str):
        # Replace ${VAR_NAME} or $VAR_NAME patterns
        pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'
        
        def replace_var(match):
            var_name = match.group(1) or match.group(2)
            return os.getenv(var_name, match.group(0))
        
        return re.sub(pattern, replace_var, config_data)
    else:
        return config_data

def load_product_list(file_path: str) -> ProductList:
    """Load product list from YAML file"""
    full_path = Path(file_path)
    if not full_path.is_absolute():
        # Relative to config directory
        full_path = Path("src/config") / full_path
    
    with open(full_path, 'r') as f:
        data = yaml.safe_load(f)
    
    products = []
    for product_data in data.get('products', []):
        # Convert unit_type string to enum
        if 'unit_type' in product_data:
            product_data['unit_type'] = UnitType(product_data['unit_type'])
        
        products.append(TileProduct(**product_data))
    
    return ProductList(
        name=data.get('name', 'Unnamed Product List'),
        products=products,
        store_location=data.get('store_location'),
        contingency_percentage=data.get('contingency_percentage', 0.1)
    )
```

## 5. Usage Examples

### 5.1 Command Line Usage

```python
# src/floor_decor_cli.py

import argparse
from src.floor_decor_automator import FloorAndDecorAutomator

def main():
    parser = argparse.ArgumentParser(description="Floor and Decor Automation Script")
    parser.add_argument(
        "--config",
        type=str,
        default="src/config/floor_decor_config.yaml",
        help="Configuration file path"
    )
    parser.add_argument(
        "--products",
        type=str,
        default="Default Tile Order",
        help="Product list name to process"
    )
    parser.add_argument(
        "--profile",
        type=str,
        help="Chrome profile directory path"
    )
    
    args = parser.parse_args()
    
    # Initialize automator
    automator = FloorAndDecorAutomator(args.config)
    
    # Override profile if specified
    if args.profile:
        automator.config.browser.profile_dir = args.profile
    
    # Run automation
    result = automator.run(args.products)
    
    # Report results
    if result.success:
        print(f"\n✅ Automation completed successfully!")
        print(f"📊 Processed {result.successful_products}/{result.total_products} products")
        print(f"🛒 Cart contains {len(result.cart_contents)} items")
    else:
        print(f"\n❌ Automation failed: {result.error}")

if __name__ == "__main__":
    main()
```

### 5.2 Python API Usage

```python
# Example usage in Python script

from src.floor_decor_automator import FloorAndDecorAutomator

# Initialize with custom configuration
automator = FloorAndDecorAutomator("path/to/config.yaml")

# Run automation
result = automator.run("My Custom Product List")

# Check results
if result.success:
    print(f"Successfully added {result.successful_products} products to cart")
    
    # Print cart contents
    for item in result.cart_contents:
        print(f"- {item.name}: {item.quantity} {item.unit_type.value} (${item.total_price:.2f})")
else:
    print(f"Automation failed: {result.error}")
```

## 6. Testing Implementation

### 6.1 Unit Tests

```python
# tests/test_floor_decor_models.py

import pytest
from src.floor_decor.models import TileProduct, UnitType, ProductList

def test_tile_product_creation():
    product = TileProduct(
        sku="100507714",
        name="Test Tile",
        quantity=100,
        unit_type="pieces",
        category="test-category",
        url_pattern="https://example.com/test"
    )
    
    assert product.sku == "100507714"
    assert product.unit_type == UnitType.PIECES

def test_product_list():
    products = [
        TileProduct(
            sku="100507714",
            name="Test Tile 1",
            quantity=100,
            unit_type=UnitType.PIECES,
            category="test",
            url_pattern="https://example.com/test1"
        ),
        TileProduct(
            sku="101055184",
            name="Test Tile 2",
            quantity=5,
            unit_type=UnitType.BOXES,
            category="test",
            url_pattern="https://example.com/test2"
        )
    ]
    
    product_list = ProductList(
        name="Test List",
        products=products
    )
    
    assert len(product_list.products) == 2
    assert product_list.get_product_by_sku("100507714") is not None
    assert product_list.get_product_by_sku("999999999") is None
```

### 6.2 Integration Tests

```python
# tests/test_floor_decor_integration.py

import pytest
from unittest.mock import Mock, patch
from src.floor_decor_automator import FloorAndDecorAutomator
from src.floor_decor.models import TileProduct, UnitType

@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = Mock()
    config.browser.profile_dir = "/test/profile"
    config.vision.provider = "none"  # Use center-only for testing
    config.vision.model = "test"
    config.automation.default_delays.page_load = 0.1
    config.automation.default_delays.between_actions = 0.1
    return config

@pytest.fixture
def test_product():
    """Test product for integration testing"""
    return TileProduct(
        sku="100507714",
        name="Test Tile",
        quantity=10,
        unit_type=UnitType.PIECES,
        category="test",
        url_pattern="https://example.com/test"
    )

def test_product_navigation(mock_config, test_product):
    """Test product navigation with mocked browser"""
    with patch('src.floor_decor.navigator.SeleniumCanvasDriver') as mock_driver:
        # Setup mock driver
        mock_driver_instance = Mock()
        mock_driver.return_value = mock_driver_instance
        
        # Test navigation
        from src.floor_decor.navigator import ProductNavigator
        navigator = ProductNavigator(mock_driver_instance, Mock(), mock_config)
        
        # Mock successful navigation
        mock_driver_instance.goto.return_value = True
        mock_driver_instance._find.return_value.text = "100507714"
        
        result = navigator._navigate_to_product(test_product)
        
        assert result is True
        mock_driver_instance.goto.assert_called_once_with(test_product.url_pattern)
```

## 7. Deployment

### 7.1 Docker Configuration

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONPATH=/app
ENV DISPLAY=:99

# Start Xvfb and run application
CMD ["sh", "-c", "Xvfb :99 -screen 0 1280x900x24 & python -m src.floor_decor_cli"]
```

### 7.2 Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  floor-decor-automator:
    build: .
    volumes:
      - ./logs:/app/logs
      - ./config:/app/src/config
      - ./chrome_profiles:/app/chrome_profiles
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ZAI_API_KEY=${ZAI_API_KEY}
      - CHROME_PROFILE_DIR=/app/chrome_profiles/agent
    command: ["python", "-m", "src.floor_decor_cli", "--config", "src/config/floor_decor_config.yaml"]
```

---

This implementation guide provides the technical details needed to build the Floor and Decor automation script based on the design document. It includes concrete code examples, testing strategies, and deployment configurations that leverage the existing Selenium-based infrastructure with vision-guided automation capabilities.