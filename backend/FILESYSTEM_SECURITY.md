# In-Game File System Security Architecture

## Overview

The RecursiveNeon in-game file system is designed with complete isolation from the player's real computer. No matter what actions a player takes within the game, they **cannot** affect files on their real computer (except within a single, controlled directory).

## Security Design

### 1. Virtual File System (In-Memory)

All file operations work with **virtual `FileNode` objects** stored in memory:

```python
class FileNode(BaseModel):
    id: str                    # UUID (not a real file path)
    name: str                  # Just a name (not a path)
    type: str                  # "file" or "directory"
    parent_id: Optional[str]   # Reference to parent (UUID)
    content: Optional[str]     # File content (in memory)
    mime_type: Optional[str]   # MIME type
```

**Key Security Features:**
- All nodes identified by **UUID**, not file paths
- No path traversal possible (names are just strings)
- All content stored **in memory** as Python objects
- Parent-child relationships maintained via UUID references

### 2. Controlled File System Access

The system **only** accesses the real file system in three specific, controlled ways:

#### a) Initial State Loading (Read-Only)
- **Source:** `backend/initial_fs/` directory
- **Purpose:** Populate initial game state on first run
- **Access:** Read-only, one-time copy into virtual filesystem
- **Safety:** Only reads from controlled source directory

```python
app_service.load_initial_filesystem("backend/initial_fs")
```

#### b) Persistence (Save)
- **Destination:** `backend/game_data/filesystem.json`
- **Purpose:** Save game state on shutdown
- **Access:** Writes to single JSON file in controlled directory
- **Safety:** No file paths from players, only serialized FileNode objects

```python
app_service.save_filesystem_to_disk("backend/game_data")
```

#### c) Persistence (Load)
- **Source:** `backend/game_data/filesystem.json`
- **Purpose:** Restore game state on startup
- **Access:** Reads from single JSON file
- **Safety:** Validates and deserializes into FileNode objects

```python
app_service.load_filesystem_from_disk("backend/game_data")
```

### 3. File Operations

All file operations work **purely with virtual nodes**:

| Operation | What It Does | Real FS Access? |
|-----------|-------------|-----------------|
| `create_file()` | Creates virtual FileNode in memory | ❌ No |
| `create_directory()` | Creates virtual directory node | ❌ No |
| `update_file()` | Updates FileNode in memory | ❌ No |
| `delete_file()` | Removes FileNode from memory (cascade) | ❌ No |
| `copy_file()` | Duplicates FileNode with new UUID | ❌ No |
| `move_file()` | Changes parent_id reference | ❌ No |
| `list_directory()` | Filters nodes by parent_id | ❌ No |

**None of these operations touch the real file system.**

### 4. Example: Why Path Traversal is Impossible

```python
# Player tries to create a file with a suspicious name
api.createFile("../../../etc/passwd", parent_id, "malicious", "text/plain")

# What happens:
# 1. Creates FileNode with name="../../../etc/passwd" (just a string)
# 2. Stores in memory with UUID: "550e8400-e29b-41d4-a716-446655440000"
# 3. parent_id references another UUID, not a real path
# 4. Content stored in memory
# 5. NO interaction with real file system

# The "path" is just a display name, not a real file system path
```

### 5. Isolation Guarantees

| Scenario | Result |
|----------|--------|
| Player creates file named `../../etc/passwd` | Just a node name, doesn't access real `/etc/passwd` |
| Player tries to read system files | No access - can only read from virtual filesystem |
| Player fills virtual FS with huge files | Memory limit only, no disk space affected |
| Player deletes everything in-game | Only clears virtual nodes, real files untouched |
| Game crashes before save | Virtual FS lost, real files untouched |

### 6. Persistence Safety

The `game_data/filesystem.json` file contains:

```json
{
  "nodes": [
    {
      "id": "uuid-1",
      "name": "Documents",
      "type": "directory",
      "parent_id": "uuid-root"
    },
    {
      "id": "uuid-2",
      "name": "test.txt",
      "type": "file",
      "parent_id": "uuid-1",
      "content": "Hello world",
      "mime_type": "text/plain"
    }
  ],
  "root_id": "uuid-root"
}
```

**Safety Features:**
- No file paths, only UUIDs and names
- All content embedded in JSON
- Single file location (`backend/game_data/`)
- Added to `.gitignore` to prevent accidental commits

### 7. Frontend Safety

The frontend API uses WebSocket messages:

```typescript
// Frontend sends
{
  type: "app",
  data: {
    operation: "fs.create.file",
    payload: {
      name: "test.txt",
      parent_id: "uuid-123",
      content: "content",
      mime_type: "text/plain"
    }
  }
}
```

**No file paths are ever sent or used.**

## Security Summary

✅ **What Players CAN do:**
- Create/edit/delete virtual files and folders
- Organize virtual filesystem
- Save/load game state

❌ **What Players CANNOT do:**
- Access files outside the game
- Execute arbitrary code
- Traverse to parent directories on real system
- Affect system files
- Write to arbitrary locations
- Read sensitive data from host computer

## Implementation Files

- **Backend Service:** `backend/services/app_service.py`
- **Models:** `backend/models/app_models.py`
- **Message Handler:** `backend/services/message_handler.py`
- **Frontend API:** `frontend/src/utils/appApi.ts`
- **File Browser UI:** `frontend/src/components/apps/FileBrowserApp.tsx`
- **Initial State:** `backend/initial_fs/` (source)
- **Game Data:** `backend/game_data/` (runtime storage)

## Testing

Security can be verified by:

1. Running the test suite: `pytest backend/tests/unit/test_filesystem_security.py`
2. Inspecting the code - all operations use UUIDs, no path operations
3. Manual verification script: `python test_filesystem_manual.py`

## Conclusion

The in-game file system provides a rich, functional file management experience while maintaining **complete isolation** from the player's real computer. This is achieved through:

1. Virtual FileNode objects with UUID-based identification
2. In-memory storage during gameplay
3. Controlled persistence to a single directory
4. No path-based operations
5. Read-only initial state loading

**The player's real files are completely safe.**
