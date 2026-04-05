"""Unit test configuration.

Unit tests are pure logic — no external dependencies (no DISPLAY, no AT-SPI,
no D-Bus, no running apps). They run on both host and VM, with or without
pytest-xdist parallelism.
"""
