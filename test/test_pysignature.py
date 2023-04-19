import pytest
from grode.signature import PySignature, ImportSignature


def test_analyze_file():
    test_code = """
import os
import sys

def example_function(a, b):
    return a + b

class ExampleClass:
    def __init__(self, x):
        self.x = x
    def get_x(self):
        return self.x
"""
    pysignature = PySignature(file_path=None, code=test_code)
    module_signature = pysignature.signature
    assert len(module_signature.imports) == 2
    assert len(module_signature.functions) == 1
    assert len(module_signature.classes) == 1
    assert module_signature.imports[0] == ImportSignature(name="os", alias=None, specified=[])
    assert module_signature.imports[1] == ImportSignature(name="sys", alias=None, specified=[])
    assert module_signature.functions[0].name == "example_function"
    assert module_signature.functions[0].args == ["a", "b"]
    assert module_signature.functions[0].return_type is None
    assert "a + b" in module_signature.functions[0].source_code
    assert module_signature.classes[0].name == "ExampleClass"
    assert module_signature.classes[0].args == ["x"]
