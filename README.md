# Reflective Pause Core Library

A shared Python library providing toxicity checking and prompt generation for the Reflective Pause Bot system.

## Features

- **Toxicity Detection**: Multiple engine support (ONNX on-device, Google Perspective API)
- **CBT Prompt Generation**: Cognitive Behavioral Therapy question rotation with i18n support
- **Decision Logging**: Anonymized analytics for user decisions
- **Strategy Pattern**: Pluggable toxicity detection engines
- **Performance Optimized**: <50ms latency for modal rendering

## Installation

```bash
pip install reflectpause-core
```

Or from source:

```bash
git clone <repository-url>
cd reflectpause-core
pip install -e .
```

## Quick Start

```python
from reflectpause_core import check, generate_prompt, log_decision
from reflectpause_core.logging import DecisionType

# Check text toxicity
is_toxic = check("This is a test message")

# Generate localized CBT prompt
prompt_data = generate_prompt("en")
print(prompt_data.question)

# Log user decision
log_decision(DecisionType.CONTINUED_SENDING)
```

## Configuration

### ONNX Engine (Default)

```python
from reflectpause_core.toxicity import ONNXEngine

engine = ONNXEngine({
    'model_path': 'path/to/model.onnx',
    'max_sequence_length': 512
})
```

### Perspective API Engine

```python
from reflectpause_core.toxicity import PerspectiveAPIEngine

engine = PerspectiveAPIEngine({
    'api_key': 'your-api-key',
    'timeout': 10
})
```

## Supported Locales

- English (`en`)
- Vietnamese (`vi`)

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black reflectpause_core/

# Type checking
mypy reflectpause_core/
```

## Performance Requirements

- Modal rendering: ≤50ms latency
- Bot DM round-trip: ≤250ms
- Cost-zero operation: <$10/month with on-device inference

## License

MIT License - see LICENSE file for details.