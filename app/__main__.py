"""``python -m app`` → samma som ``python -m app.main``."""
from .main import main

raise SystemExit(main())
