import pytest
from src.vision.normalizer import extract_json_object

def test_extract_simple_json():
    text = '{"version":"1.0","coords":{"space":"normalized","x":0.2,"y":0.8}}'
    data = extract_json_object(text)
    assert data["version"] == "1.0"
    assert data["coords"]["x"] == pytest.approx(0.2)


def test_extract_from_wrapped_text():
    text = """
    Model output:
    Sure, here is the JSON:
    ```json
    {"version":"1.0","coords":{"space":"normalized","x":0.25,"y":0.75}}
    ```
    extra trailing text
    """
    data = extract_json_object(text)
    assert data["coords"]["y"] == pytest.approx(0.75)


def test_extract_nested_braces_in_string():
    text = 'prefix {"why":"uses braces } inside string { not real }","version":"1.0","coords":{"space":"normalized","x":0.1,"y":0.9}} suffix'
    data = extract_json_object(text)
    assert data["coords"]["x"] == pytest.approx(0.1)
