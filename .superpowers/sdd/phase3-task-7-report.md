# Phase 3 Task 7: Community Adapter SDK — Report

## Status: DONE

## Commit
`feat(sdk): add community adapter creator SDK` (143beb0)

## Files Created/Modified
- `sdk/src/flight_recorder/adapters/creator.py` — `create_adapter` factory + `build_step` helper
- `sdk/src/flight_recorder/adapters/__init__.py` — updated exports
- `sdk/tests/test_adapter_creator.py` — 12 tests (3 build_step, 9 create_adapter)

## API Surface

### `build_step(step_type, name, input_data, output_data, **kwargs) -> Step`
Convenience wrapper around `Step(...)`. Accepts `StepType` enum or string (`"llm_call"`). All optional fields (`index`, `tokens_in`, `tokens_out`, `cost`, `duration_ms`, `error`) default to sensible zero/None values.

### `create_adapter(name, event_handlers) -> BaseAdapter`
Factory returning a `_DynamicAdapter` (BaseAdapter subclass). The adapter exposes `handle_event(event_name, **kwargs)` which:
1. Looks up the handler by name
2. Calls it with the provided kwargs
3. Auto-assigns sequential `index` to each returned Step
4. Skips if handler returns `None`
5. Raises `ValueError` for unknown events

`build_trace()` returns a fresh `Trace` copy each call.

## Test Coverage (12 tests)
| Test | What it verifies |
|------|-----------------|
| `test_build_step_minimal` | Defaults for optional fields |
| `test_build_step_with_optional_fields` | All kwargs pass through |
| `test_build_step_accepts_string_step_type` | String → enum coercion |
| `test_returns_base_adapter_instance` | isinstance check |
| `test_adapter_name_in_trace` | Name propagates to Trace |
| `test_event_handler_produces_steps` | Single handler → single step |
| `test_multiple_event_handlers` | Two handlers → two step types |
| `test_unknown_event_raises` | ValueError on bad event name |
| `test_handler_returning_none_skips_step` | None handler → no step |
| `test_step_indices_are_sequential` | Auto-indexing across calls |
| `test_multiple_adapters_are_independent` | No shared state between instances |
| `test_build_trace_returns_fresh_copy` | Each call returns new Trace |

## Full Suite: 70/70 passing
