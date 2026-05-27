# Database Architecture & Best Practices

## Version: 1.0.0
**Last Updated:** December 27, 2025  
**Author:** Development Team  
**Status:** Active Refactoring Plan

---

## 1. Current State Analysis

### 1.1 Current Pattern: Full Object Returns

The current `database_handler.py` returns full ORM-like objects from queries:

```python
# Current Pattern
def get_animals_by_trainer(self, trainer_id):
    """Returns List[Animal] - full objects"""
    animals = []
    for row in rows:
        animal = Animal(
            animal_id=row[0],
            lab_animal_id=row[1],
            name=row[2],
            initial_weight=row[3],
            last_weight=row[4],
            last_weighted=row[5],
            last_watering=row[6],
            sex=row[7]
        )
        animals.append(animal)
    return animals
```

### 1.2 Current Issues

| Issue ID | Severity | Description | Impact |
|----------|----------|-------------|--------|
| DB-001 | Medium | Over-fetching: All columns returned even when only ID/name needed | Memory, performance on Pi |
| DB-002 | Low | Inconsistent return types: Some methods return tuples, others objects | Developer confusion |
| DB-003 | Medium | No separation between read/write models | Accidental mutations |
| DB-004 | Low | Missing type hints | IDE support, maintainability |
| DB-005 | Medium | Direct SQL in handler | SQL injection risk if not careful |

### 1.3 Methods Inventory

| Method | Returns | Used By | Notes |
|--------|---------|---------|-------|
| `get_all_animals()` | `List[Animal]` | AnimalsTab, Wizard | Full objects |
| `get_animals_by_trainer()` | `List[Animal]` | AnimalsTab, Wizard | Full objects |
| `get_all_schedules()` | `List[tuple]` | SchedulesHub | Raw tuples! |
| `get_schedule_details()` | `List[dict]` | RunStopSection | Dict format |
| `add_schedule()` | `int` (schedule_id) | Wizard, SchedulesHub | Insert returns ID |
| `add_schedule_animal()` | `bool` | Wizard | Insert returns success |

---

## 2. Best Practices (Industry Standard)

### 2.1 Repository Pattern + DTOs

**Reference:** Martin Fowler's Patterns of Enterprise Application Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        UI LAYER (PyQt5)                          │
├─────────────────────────────────────────────────────────────────┤
│  Views call Services with DTOs                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SERVICE LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  • Business logic                                                │
│  • Validation                                                    │
│  • Orchestration of repository calls                             │
│  • Returns DTOs (Data Transfer Objects)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     REPOSITORY LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  • CRUD operations only                                          │
│  • Returns domain entities or DTOs                               │
│  • Hides SQL implementation                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE (SQLite)                           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 DTO Pattern (Data Transfer Objects)

**Purpose:** Return only the data needed for a specific use case.

```python
# RECOMMENDED: Specific DTOs for different use cases
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)  # Immutable
class AnimalSummary:
    """Lightweight DTO for list views."""
    animal_id: int
    lab_animal_id: str
    name: str

@dataclass(frozen=True)
class AnimalDetail:
    """Full DTO for detail views."""
    animal_id: int
    lab_animal_id: str
    name: str
    initial_weight: Optional[float]
    last_weight: Optional[float]
    last_weighted: Optional[str]
    last_watering: Optional[str]
    sex: Optional[str]

@dataclass
class AnimalCreate:
    """DTO for creating new animals (no ID)."""
    lab_animal_id: str
    name: str
    initial_weight: float
    sex: str
    trainer_id: int
```

### 2.3 Selective Fetching

```python
# RECOMMENDED: Method that fetches only needed columns
def get_animal_summaries(self, trainer_id: int) -> List[AnimalSummary]:
    """Fetch lightweight animal list for dropdowns/wizards."""
    with self.connect() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT animal_id, lab_animal_id, name 
            FROM animals 
            WHERE trainer_id = ?
        ''', (trainer_id,))
        return [
            AnimalSummary(
                animal_id=row[0],
                lab_animal_id=row[1],
                name=row[2]
            )
            for row in cursor.fetchall()
        ]
```

---

## 3. Migration Strategy

### 3.1 Approach: Additive First, Deprecate Later

**Principle:** Add new methods without breaking existing code, then gradually migrate.

```
Phase 1: ADD new DTO methods alongside existing ones
Phase 2: MIGRATE UI code to use new methods
Phase 3: DEPRECATE old methods with warnings
Phase 4: REMOVE deprecated methods (next major version)
```

### 3.2 Phase 1: Add New Methods (No Breaking Changes)

| New Method | Returns | Purpose | Existing Method |
|------------|---------|---------|-----------------|
| `get_animal_summaries()` | `List[AnimalSummary]` | List views, dropdowns | `get_all_animals()` stays |
| `get_animal_detail()` | `Optional[AnimalDetail]` | Detail/edit views | `get_animals_by_trainer()` stays |
| `get_schedule_summaries()` | `List[ScheduleSummary]` | Schedule list | `get_all_schedules()` stays |

### 3.3 Phase 2: Gradual Migration

```python
# Step 1: Add deprecation warning to old method
import warnings

def get_all_animals(self):
    """
    Retrieve all animals.
    
    .. deprecated:: 2.2.0
        Use :func:`get_animal_summaries` for list views or 
        :func:`get_animal_detail` for full details.
    """
    warnings.warn(
        "get_all_animals() is deprecated, use get_animal_summaries()",
        DeprecationWarning,
        stacklevel=2
    )
    # ... existing implementation
```

### 3.4 Files to Update (Migration Map)

| File | Current Method | New Method | Priority |
|------|----------------|------------|----------|
| `ui/schedule_wizard.py` | `get_animals_by_trainer()` | `get_animal_summaries()` | High |
| `ui/animals_tab.py` | `get_all_animals()` | `get_animal_summaries()` | Medium |
| `ui/schedules_hub.py` | `get_all_schedules()` | `get_schedule_summaries()` | Medium |
| `ui/run_stop_section.py` | `get_schedule_details()` | Keep (already returns dict) | Low |

---

## 4. Technical Debt Register

| ID | Category | Description | Effort | Risk | Status |
|----|----------|-------------|--------|------|--------|
| TD-DB-001 | Performance | Over-fetching in list views | Low | Low | Open |
| TD-DB-002 | Consistency | Mixed return types (tuple vs object) | Medium | Medium | Open |
| TD-DB-003 | Type Safety | Missing type hints | Low | Low | Open |
| TD-DB-004 | Security | Raw SQL strings (injection risk) | Medium | High | Open |
| TD-DB-005 | Architecture | No repository pattern | High | Low | Open |

---

## 5. Implementation Plan

### Sprint 2.2.0: Database Layer Improvements

#### Task 1: Create DTOs (2 story points)

```python
# New file: models/dto.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass(frozen=True)
class AnimalSummary:
    animal_id: int
    lab_animal_id: str
    name: str

@dataclass(frozen=True)
class ScheduleSummary:
    schedule_id: int
    name: str
    delivery_mode: str
    created_at: str
    animal_count: int
```

#### Task 2: Add Selective Fetch Methods (3 story points)

```python
# In database_handler.py - ADD these methods (don't modify existing)

def get_animal_summaries(self, trainer_id: Optional[int] = None) -> List[AnimalSummary]:
    """Lightweight animal fetch for list views."""
    ...

def get_schedule_summaries(self, created_by: Optional[int] = None) -> List[ScheduleSummary]:
    """Lightweight schedule fetch for list views."""
    ...
```

#### Task 3: Migrate Wizard to Use DTOs (2 story points)

```python
# In schedule_wizard.py
# Change: animals = self._database_handler.get_animals_by_trainer(trainer_id)
# To:     animals = self._database_handler.get_animal_summaries(trainer_id)
```

---

## 6. Best Practice: When to Return Full Objects vs DTOs

### Return Full Objects When:
- Editing/updating entity
- Need all fields for business logic
- Single entity detail view

### Return DTOs When:
- List/table views (only show subset)
- Dropdowns/selects (ID + display text)
- API responses (controlled data exposure)
- Cross-component data transfer

---

## 7. SQLite Best Practices (Raspberry Pi Specific)

### 7.1 Connection Pooling

```python
# Current: Creates new connection per query (slow)
def connect(self):
    return sqlite3.connect(self.db_path)

# RECOMMENDED: Singleton connection with context manager
class DatabaseHandler:
    _instance = None
    _connection = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False  # For PyQt threading
            )
            self._connection.row_factory = sqlite3.Row
        return self._connection
```

### 7.2 Parameterized Queries (Security)

```python
# NEVER do this (SQL injection risk)
cursor.execute(f"SELECT * FROM animals WHERE name = '{name}'")

# ALWAYS do this
cursor.execute("SELECT * FROM animals WHERE name = ?", (name,))
```

### 7.3 Transaction Management

```python
# RECOMMENDED: Explicit transactions for batch operations
def add_schedule_with_animals(self, schedule_data, animals):
    conn = self.connection
    try:
        conn.execute("BEGIN TRANSACTION")
        
        schedule_id = self._insert_schedule(schedule_data)
        for animal in animals:
            self._insert_schedule_animal(schedule_id, animal)
        
        conn.commit()
        return schedule_id
    except Exception as e:
        conn.rollback()
        raise
```

---

## 8. Monitoring & Metrics

### 8.1 Query Logging (Development)

```python
# Add to database_handler.py for debugging
import time
import logging

logger = logging.getLogger(__name__)

def _log_query(self, query: str, params: tuple, duration: float):
    if duration > 0.1:  # Log slow queries (>100ms)
        logger.warning(f"SLOW QUERY ({duration:.3f}s): {query[:100]}...")
    else:
        logger.debug(f"Query ({duration:.3f}s): {query[:50]}...")
```

---

## 9. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing UI during migration | Medium | High | Additive approach - keep old methods |
| Performance regression | Low | Medium | Benchmark before/after |
| Data inconsistency | Low | High | Transaction management |
| Developer confusion (two ways to do things) | Medium | Low | Clear deprecation warnings |

---

## 10. Decision Log

| Date | Decision | Rationale | Alternatives Considered |
|------|----------|-----------|-------------------------|
| 2025-12-27 | Use DTOs for new features | Prevents over-fetching, cleaner API | Full ORM (too heavy for SQLite) |
| 2025-12-27 | Additive migration | No breaking changes | Big-bang refactor (too risky) |
| 2025-12-27 | Keep Animal class | Still useful for mutations | Remove entirely (breaks too much) |

---

## Appendix A: File Change Matrix

| File | Change Type | Description |
|------|-------------|-------------|
| `models/dto.py` | NEW | DTO dataclasses |
| `models/database_handler.py` | MODIFY | Add new methods, deprecate old |
| `ui/schedule_wizard.py` | MODIFY | Use DTOs, per-animal params |
| `ui/animals_tab.py` | MODIFY (Phase 2) | Use `get_animal_summaries()` |
| `ui/schedules_hub.py` | MODIFY (Phase 2) | Use `get_schedule_summaries()` |

---

*Document maintained by: Development Team*  
*Review cycle: Per sprint*

