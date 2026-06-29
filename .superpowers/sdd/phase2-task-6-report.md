# Phase 2 Task 6 Report: Desktop Branch UI

## Status: DONE

## Commit
- `a7c5c69` — feat(desktop): add branch UI with fork button and comparison

## Compilation
`cargo build` succeeded with only expected dead_code warnings.

## What was built

### Data Structures
- `BranchSummary` {id, name, fork_step_index, step_count, total_cost}
- `BranchDetail` {id, name, parent_trace_id, fork_step_index, modifications, steps}
- `Modification` {field, old_value, new_value}
- `ForkRequest` (serializable) {branch_name, model_name}

### Message Enum Additions
- `ForkRequested(usize)` — step index to fork at
- `ForkNameChanged(String)` — branch name input
- `ForkModelChanged(String)` — model name input
- `ForkConfirmed` — triggers POST to /api/traces/{id}/fork
- `ForkCancelled` — dismisses fork dialog
- `BranchCreated(String)` — branch ID from successful fork
- `BranchesLoaded(Vec<BranchSummary>)` — branches for current trace
- `BranchSelected(String)` — branch ID selected in sidebar
- `BranchLoaded(BranchDetail)` — full branch detail loaded

### Fork Button in Timeline
- Each step row now has a "Fork" button alongside [type], name, and cost
- Clicking "Fork" opens an inline dialog with:
  - Branch name text input
  - Model name text input
  - Confirm button (POSTs to /api/traces/{id}/fork)
  - Cancel button
- Active fork target shows "(forking)" indicator

### Branch List in Sidebar
- Below the "Traces" section, a "Branches" section appears when branches exist
- Each branch shows name, step count, cost, and fork step index
- Selected branch is indicated with ">>" prefix
- Clicking loads branch detail from /api/branches/{id}

### Branch Comparison in Inspector
- When a branch step is selected, inspector shows:
  - Branch name header, step details, modifications list
  - Comparison vs parent trace: step count, total cost, total duration
  - Delta indicators (+$X.XX / -X.XXms or "no change")

### Backend Endpoints Used
- GET /api/traces — list traces
- GET /api/traces/{id} — trace detail
- GET /api/traces/{id}/branches — branches for trace
- GET /api/branches/{id} — branch detail
- POST /api/traces/{id}/fork — create fork (JSON body: {branch_name, model_name})

## Concerns
- None. Clean build, all requested functionality implemented.
