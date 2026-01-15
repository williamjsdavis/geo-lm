"""Pytest configuration and fixtures."""

import os
import sys
import asyncio
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_dsl_valid():
    """Valid DSL text for testing."""
    return '''
ROCK R1 [ name: "Sandstone"; type: sedimentary; age: 100Ma ]
ROCK R2 [ name: "Limestone"; type: sedimentary; age: 90Ma ]
ROCK R3 [ name: "Granite"; type: intrusive; age: 50Ma ]

DEPOSITION D1 [ rock: R1; time: 100Ma ]
DEPOSITION D2 [ rock: R2; time: 90Ma; after: D1 ]

EROSION E1 [ time: 80Ma; after: D2 ]

INTRUSION I1 [ rock: R3; style: stock; time: 50Ma; after: E1 ]
'''


@pytest.fixture
def sample_dsl_invalid_reference():
    """DSL with invalid rock reference."""
    return '''
ROCK R1 [ name: "Sandstone"; type: sedimentary; age: 100Ma ]

DEPOSITION D1 [ rock: R99; time: 100Ma ]
'''


@pytest.fixture
def sample_dsl_circular():
    """DSL with circular dependency."""
    return '''
ROCK R1 [ name: "Sandstone"; type: sedimentary ]

DEPOSITION D1 [ rock: R1; after: D2 ]
DEPOSITION D2 [ rock: R1; after: D1 ]
'''


@pytest.fixture
def sample_dsl_syntax_error():
    """DSL with syntax error."""
    return '''
ROCK R1 [ name: "Sandstone" type: sedimentary ]
'''


@pytest.fixture
def sample_geological_text():
    """Sample geological description text."""
    return """
    The Bingham Canyon deposit is hosted in Eocene volcanic and intrusive rocks.
    The oldest unit is the andesitic host rock, deposited around 40 million years ago.
    This was followed by sedimentary cover around 38 Ma.
    An erosional unconformity developed at approximately 37 Ma.
    The main quartz diorite porphyry intruded as a stock at 35 Ma,
    bringing copper-gold mineralization which occurred at 34 Ma as dikes.
    """
