# Temporary test: mock ollama.chat to return compressed JSON and call _ollama_request
import importlib, types, sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from reasoning.llm_client import _ollama_request

class MockMessage:
    def __init__(self, content):
        self.content = content

class MockResponse:
    def __init__(self, content):
        self.message = {'content': content}

class MockOllama:
    def __init__(self, content):
        self._content = content
    def chat(self, model, messages, options):
        return {'message': {'content': self._content}}

# Create compressed response string
compressed = '{"c":[{"a":"15","ac":"m","t":[8,3]},{"a":"16","ac":"rs","t":[2,12]},{"a":"17","ac":"dh","t":[17,2]},{"a":"18","ac":"cr","t":[7,7]}],"s":"mock_strategy"}'

# Monkeypatch ollama
import reasoning.llm_client as lc
lc.ollama = MockOllama(compressed)
lc.OLLAMA_AVAILABLE = True

res = _ollama_request('test prompt', temperature=0.1)
print('Result:', res)
