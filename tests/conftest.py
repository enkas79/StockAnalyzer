import os

# GUI tests run headless (no real display in CI/sandboxes); only default this
# if the environment hasn't already picked a Qt platform plugin.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
