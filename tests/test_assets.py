from django.contrib.staticfiles import finders

from integrations.onjourney.adapters.demo import DemoClient


def test_all_demo_product_illustrations_are_bundled_locally():
    for product in DemoClient().list_products():
        assert finders.find(product["image"]) is not None


def test_storefront_css_and_progressive_enhancement_are_bundled():
    assert finders.find("css/app.css") is not None
    assert finders.find("js/app.js") is not None
