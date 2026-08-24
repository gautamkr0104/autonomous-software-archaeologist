"""Create synthetic repositories for testing difficult cases.

These test specific edge cases:
  - Circular dependencies
  - Dynamic imports
  - Generated code
  - Monorepos
  - Multiple services
  - Event-driven architecture
  - Hidden coupling
  - Duplicated implementations
"""

from __future__ import annotations

import os
from pathlib import Path


def create_circular_dependency_repo(path: Path) -> None:
    """Repo with circular dependencies between modules."""
    repo = path / "circular-deps"
    repo.mkdir(parents=True, exist_ok=True)

    (repo / "module_a.py").write_text('''\
from module_b import ClassB

class ClassA:
    def __init__(self):
        self.b = ClassB()
    
    def do_a(self):
        self.b.do_b()
''')

    (repo / "module_b.py").write_text('''\
from module_a import ClassA

class ClassB:
    def __init__(self):
        self.a = ClassA()
    
    def do_b(self):
        self.a.do_a()
''')


def create_event_driven_repo(path: Path) -> None:
    """Repo with event-driven architecture."""
    repo = path / "event-driven"
    repo.mkdir(parents=True, exist_ok=True)

    (repo / "event_bus.py").write_text('''\
from typing import Callable, Dict, List
from dataclasses import dataclass

@dataclass
class Event:
    type: str
    payload: dict

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_type: str, handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)
    
    def publish(self, event: Event):
        for handler in self._handlers.get(event.type, []):
            handler(event)
''')

    (repo / "order_service.py").write_text('''\
from event_bus import EventBus, Event

class OrderService:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.event_bus.subscribe("order_created", self._on_order_created)
    
    def create_order(self, item: str, quantity: int):
        event = Event("order_created", {"item": item, "quantity": quantity})
        self.event_bus.publish(event)
    
    def _on_order_created(self, event: Event):
        print(f"Order created: {event.payload}")
''')

    (repo / "notification_service.py").write_text('''\
from event_bus import EventBus, Event

class NotificationService:
    def __init__(self, event_bus: EventBus):
        event_bus.subscribe("order_created", self._notify)
        event_bus.subscribe("payment_received", self._confirm)
    
    def _notify(self, event: Event):
        print(f"Notification: new order {event.payload}")
    
    def _confirm(self, event: Event):
        print(f"Payment confirmed: {event.payload}")
''')


def create_monorepo(path: Path) -> None:
    """Multi-package monorepo."""
    repo = path / "monorepo"
    (repo / "packages").mkdir(parents=True, exist_ok=True)

    # Package A
    pkg_a = repo / "packages" / "core"
    pkg_a.mkdir(parents=True)
    (pkg_a / "__init__.py").write_text('from .models import User, Order\n')
    (pkg_a / "models.py").write_text('''\
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
    email: str

@dataclass
class Order:
    id: int
    user_id: int
    items: list
''')

    # Package B
    pkg_b = repo / "packages" / "api"
    pkg_b.mkdir(parents=True)
    (pkg_b / "__init__.py").write_text("")
    (pkg_b / "routes.py").write_text('''\
from core.models import User, Order

class UserRoutes:
    def get_user(self, user_id: int) -> User:
        return User(id=user_id, name="test", email="test@test.com")

class OrderRoutes:
    def get_order(self, order_id: int) -> Order:
        return Order(id=order_id, user_id=1, items=[])
''')

    # Package C
    pkg_c = repo / "packages" / "worker"
    pkg_c.mkdir(parents=True)
    (pkg_c / "__init__.py").write_text("")
    (pkg_c / "tasks.py").write_text('''\
from core.models import Order
from api.routes import OrderRoutes

class OrderProcessor:
    def __init__(self):
        self.routes = OrderRoutes()
    
    def process(self, order_id: int) -> Order:
        order = self.routes.get_order(order_id)
        return order
''')


def create_hidden_coupling_repo(path: Path) -> None:
    """Repo with hidden coupling via global state."""
    repo = path / "hidden-coupling"
    repo.mkdir(parents=True, exist_ok=True)

    (repo / "globals.py").write_text('''\
# Shared mutable state — hidden coupling
CONFIG = {}
DATABASE = None
EVENT_LISTENERS = []
''')

    (repo / "service_a.py").write_text('''\
import globals

class ServiceA:
    def configure(self):
        globals.CONFIG["timeout"] = 30
        globals.EVENT_LISTENERS.append(self.on_event)
    
    def on_event(self, event):
        print(f"A received: {event}")
''')

    (repo / "service_b.py").write_text('''\
import globals

class ServiceB:
    def do_work(self):
        timeout = globals.CONFIG.get("timeout", 10)
        for listener in globals.EVENT_LISTENERS:
            listener("work_done")
        return timeout
''')


def create_duplicated_code_repo(path: Path) -> None:
    """Repo with duplicated implementations."""
    repo = path / "duplicated"
    repo.mkdir(parents=True, exist_ok=True)

    (repo / "utils_v1.py").write_text('''\
def validate_email(email: str) -> bool:
    """Validate email format."""
    return "@" in email and "." in email.split("@")[-1]

def format_name(first: str, last: str) -> str:
    """Format full name."""
    return f"{first.strip()} {last.strip()}"
''')

    (repo / "utils_v2.py").write_text('''\
def validate_email(address: str) -> bool:
    """Check if email is valid."""
    return "@" in address and "." in address.split("@")[-1]

def format_full_name(given: str, family: str) -> str:
    """Combine into full name."""
    return f"{given.strip()} {family.strip()}"
''')


def create_all_synthetic_repos(base_path: str) -> list[str]:
    """Create all synthetic test repos and return their paths."""
    base = Path(base_path)
    paths = [
        base / "circular-deps",
        base / "event-driven",
        base / "monorepo",
        base / "hidden-coupling",
        base / "duplicated",
    ]

    create_circular_dependency_repo(base)
    create_event_driven_repo(base)
    create_monorepo(base)
    create_hidden_coupling_repo(base)
    create_duplicated_code_repo(base)

    return [str(p) for p in paths]


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "D:/asa/data/synthetic"
    paths = create_all_synthetic_repos(target)
    print(f"Created {len(paths)} synthetic repos in {target}")
    for p in paths:
        print(f"  - {p}")
