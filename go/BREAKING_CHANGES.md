# Breaking Changes

This document describes breaking changes in the Go `orgdatacore` package and how to migrate your code.

## Version 2.0 (Current Branch)

### 1. `OrgInfo.Type` Changed from `string` to `OrgInfoType`

**What changed**: The `Type` field in `OrgInfo` struct is now a typed enum (`OrgInfoType`) instead of a raw `string`.

**Before**:
```go
type OrgInfo struct {
    Name string `json:"name"`
    Type string `json:"type"`  // Was a plain string
}

// Usage
for _, org := range orgs {
    if org.Type == "team" {
        // ...
    }
}
```

**After**:
```go
type OrgInfo struct {
    Name string      `json:"name"`
    Type OrgInfoType `json:"type"`  // Now a typed enum
}

// Usage - compare with constants
for _, org := range orgs {
    if org.Type == orgdatacore.OrgTypeTeam {
        // ...
    }
}

// If you need the string value
typeString := string(org.Type)
```

**Available `OrgInfoType` constants**:
- `OrgTypeTeam` - "team"
- `OrgTypeOrganization` - "organization"
- `OrgTypePillar` - "pillar"
- `OrgTypeTeamGroup` - "team_group"
- `OrgTypeParentTeam` - "parent_team"

**Migration**: Replace string comparisons with typed constants. If you need string concatenation, explicitly convert using `string(org.Type)`.

---

### 2. `StartDataSourceWatcher` Now Returns `ErrWatcherAlreadyRunning`

**What changed**: Calling `StartDataSourceWatcher` when a watcher is already running now returns `ErrWatcherAlreadyRunning` instead of silently succeeding.

**Before**:
```go
// First call starts the watcher
err := service.StartDataSourceWatcher(ctx, source)

// Second call would silently succeed (undefined behavior)
err = service.StartDataSourceWatcher(ctx, source)
```

**After**:
```go
import "errors"

// First call starts the watcher
err := service.StartDataSourceWatcher(ctx, source)

// Second call returns an error
err = service.StartDataSourceWatcher(ctx, source)
if errors.Is(err, orgdatacore.ErrWatcherAlreadyRunning) {
    // Handle: watcher already running
}
```

**New method `StopWatcher()`**: To stop a running watcher before starting a new one:
```go
service.StopWatcher()
err := service.StartDataSourceWatcher(ctx, newSource)
```

**Migration**: Check for `ErrWatcherAlreadyRunning` if your code may call `StartDataSourceWatcher` multiple times. Use `StopWatcher()` if you need to switch data sources.

---

### 3. Iterator Behavior Changed (Snapshot Approach)

**What changed**: The `All*()` iterator methods now use a snapshot approach instead of iterating while holding a lock.

**Before** (hypothetical original behavior):
- Iterators held a read lock for the entire duration of iteration
- Long-running iterations could block data reloads
- Modifications during iteration were undefined

**After**:
- Iterators snapshot data while briefly holding a lock
- Iteration proceeds without any lock held
- Safe for slow consumer operations
- Concurrent reloads don't affect in-progress iterations
- Iteration reflects data at snapshot time (not live updates)

**Affected methods**:
- `AllEmployeeUIDs()` - returns `iter.Seq[string]`
- `AllEmployees()` - returns `iter.Seq[*Employee]`
- `AllTeamNames()` - returns `iter.Seq[string]`
- `AllTeams()` - returns `iter.Seq2[string, *Team]`
- `AllOrgNames()` - returns `iter.Seq[string]`
- `AllOrgs()` - returns `iter.Seq2[string, *Org]`
- `AllPillarNames()` - returns `iter.Seq[string]`
- `AllPillars()` - returns `iter.Seq2[string, *Pillar]`
- `AllTeamGroupNames()` - returns `iter.Seq[string]`
- `AllTeamGroups()` - returns `iter.Seq2[string, *TeamGroup]`

**Migration**: No code changes required. This is a behavioral improvement that maintains API compatibility. Your iterations are now safer for concurrent use.

---

### 4. New `GetEmployeeByEmail` Method Added

**What changed**: A new method `GetEmployeeByEmail(email string) *Employee` was added to `ServiceInterface`.

**Impact**: If you implement `ServiceInterface` in your own code, you must add this method.

**Implementation**:
```go
func (s *MyService) GetEmployeeByEmail(email string) *Employee {
    // Case-insensitive email lookup
    emailLower := strings.ToLower(email)
    for _, emp := range s.employees {
        if strings.ToLower(emp.Email) == emailLower {
            return &emp
        }
    }
    return nil
}
```

**Migration**: Add the new method to any custom implementations of `ServiceInterface`.

---

## Module Path Change

**What changed**: The module path changed from `github.com/openshift-eng/cyborg-data` to `github.com/openshift-eng/cyborg-data/go`.

**Before**:
```go
import orgdatacore "github.com/openshift-eng/cyborg-data"
```

**After**:
```go
import orgdatacore "github.com/openshift-eng/cyborg-data/go"
```

**Migration**: Update all import statements throughout your codebase.

---

## Summary of Required Changes

1. Replace `org.Type == "team"` with `org.Type == orgdatacore.OrgTypeTeam` (or other constants)
2. Handle `ErrWatcherAlreadyRunning` when calling `StartDataSourceWatcher`
3. Update import path to `github.com/openshift-eng/cyborg-data/go`
4. Add `GetEmployeeByEmail` to custom `ServiceInterface` implementations

## New Features

In addition to breaking changes, this release adds:

- **Email lookup**: `GetEmployeeByEmail(email string) *Employee` for case-insensitive email search
- **Watcher control**: `StopWatcher()` method to stop a running data source watcher
- **Iterator safety**: Snapshot-based iterators safe for concurrent use with slow consumers
- **Type-safe enums**: `OrgInfoType`, `MembershipType`, `EntityType` for compile-time safety
