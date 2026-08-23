---
name: recover-ide-projects
description: Locate or recover lost/moved/deleted IDE projects (NetBeans primary, Eclipse/IntelliJ extensible) by mining the IDE's own metadata — recent-files history, local history, and opened-project state — instead of only searching for project folders. Use when a user says "find my old projects", "analyze the NetBeans/Eclipse folders", "do I still have my college project source", or a project folder appears missing.
---

# Recover IDE Projects (from IDE metadata, not just folders)

When a user wants to know what projects they had in an IDE, or where their old
source code went, the naive approach (search for `nbproject` / `project.xml` /
`build.xml` / `*.java`) FAILS the moment the project folder was deleted or
moved — those markers vanish with the folder. The IDE's own usage metadata
survives deletion and reveals the exact original paths and file names. Mine the
metadata FIRST.

## Trigger
- "Analyze the NetBeans/IDE folders — any project source available?"
- "Do I have any useful projects in Apache NetBeans / Eclipse / IntelliJ?"
- A project folder the user remembers is now missing from Documents.
- Any request to recover/relocate old IDE work without a known backup path.

## Workflow (NetBeans — the worked case)
NetBeans 22 stores everything under the user dir, split across Roaming and Local:

- IDE install: `C:\Program Files\NetBeans-<ver>` (or `Program Files (x86)`).
- Config + Local History: `AppData\Roaming\NetBeans\<ver>\`
  - `config\` — preferences, modules, window layout
  - `var\` — `filehistory\` (Local History), `log\`
- Cache: `AppData\Local\NetBeans\Cache`

### 1. GOLD MINE — Recent Files History (survives folder deletion)
File:
`AppData\Roaming\NetBeans\<ver>\config\Preferences\org\netbeans\modules\utilities\RecentFilesHistory.properties`

Format (one line per recently opened file):
```
8|RecentFilesURL.0=C:\\Users\\PREM KUMAR\\Documents\\NetBeansProjects\\BaseStationServer6\\src\\basestationserver6\\MobileDeviceClient.java
```
- `RecentFilesURL.N` → exact absolute path of each of the last ~12 opened files.
- `RecentFilesIcon.N` → base64 PNG icon (ignore; pure noise).
- This file persists even after the project folder is deleted, so it is the
  single best evidence of WHAT the user built and WHERE. Parse the
  `RecentFilesURL.*` lines and reconstruct the project-folder tree from the
  common path prefixes.

### 2. Opened-projects tab state (corroborates project names)
`config\Windows2Local\Groups\OpenedProjects\*.wstcgrp` — lists projects the
Projects tab had open. Lower signal than RecentFiles but useful.

### 3. Local History (shadow copies of edited files)
`AppData\Roaming\NetBeans\<ver>\var\filehistory\storage`
- This is NetBeans' per-file version history. It CAN contain full old source
  even after deletion — BUT it is frequently empty (Local History disabled or
  auto-cleared). Always check; never assume it has content.

## When the project folders are missing — recovery search order
After reading metadata, locate the actual files (or confirm they're gone):
1. **Default location**: `Documents\NetBeansProjects\` (NetBeans default).
2. **Recycle Bin**: `C:\$Recycle.Bin\S-1-5-21-*-1001\` (match the SID to the
   active user; it may be `-1001` not `-1000`). Search for the project folder
   names or `*.java`.
3. **Other drives** (D:, E:, USB) — `ls /d`, `ls /e`.
4. **Cloud/backup**: OneDrive folder, any backup the user used in college.
5. **IDE Local History** (step 3 above).

## Pitfalls (learned the hard way)
- **Never start with `find` for `nbproject`/`project.xml`/`*.java` across the
  whole profile.** If the folder was deleted these return nothing and you've
  wasted the user's trust. Read `RecentFilesHistory.properties` FIRST.
- **Whole-drive / whole-profile `find /c/Users` TIMES OUT on Windows** because
  the bundled JDK (`.jdks\...`) contains thousands of `.java` demo files. Bound
  every search with `-maxdepth` and a specific parent, or target known
  filenames with `-iname "ExactName.java"`. Keep `timeout 45` on risky finds.
- **D: drive empty is normal** if there's no optical/USB volume — don't treat
  `ls /d` returning nothing as an error.
- **Recycle Bin is per-SID.** The live user is often `-1001`; check both
  `-1000` and `-1001` (and any others present).
- **Local History is often a 10-byte stub.** Empty `storage` = no snapshots;
  say so honestly rather than implying recovery is possible.
- **Decode path separators**: the `.properties` file stores `\\` for `\`. When
  reconstructing project trees, collapse `\\` → `\`.

## Reporting format
Give the user: (a) what IDE is installed, (b) the project names + source files
proven by RecentFilesHistory (as a table), (c) where the code actually is now
(found / gone / in Recycle Bin), (d) recovery options. Be honest when code is
unrecoverable on this machine.

### Confirmed real outcome (NetBeans 22, this host)
Searched after the user asked "do I have my college NetBeans project source?".
Findings: `Documents\NetBeansProjects\` GONE; Recycle Bin (`-1000` AND `-1001`
SIDs) had NO `*.java`/project folders; `D:` empty; OneDrive empty; Local History
`storage` = 10-byte stub (no snapshots). Code was **unrecoverable on this machine**.
BUT `RecentFilesHistory.properties` fully reconstructed the project set — six
BaseStation/MobileDevice socket projects under `Documents\NetBeansProjects\`:
`BaseStationServer6`, `BaseStationServer3`, `MobileDeviceClient7`, `BaseStationServer`,
`BaseStationServer4`, `BaseStationServer 3` (note the space in the last name).
Takeaway: even with zero recoverable source, the metadata is enough to
**faithfully reconstruct/rebuild** the project (one was rebuilt, structured,
documented, and pushed to GitHub) — so "unrecoverable" is not "lost forever";
offer a clean rebuild from the recovered names as a recovery path.

## Extensibility (not yet documented — add when encountered)
- Eclipse: recent workspaces in
  `workspace\.metadata\.plugins\org.eclipse.ui.workbench\...` and
  `org.eclipse.core.resources\.projects\`; `.project`/`.classpath` markers.
- IntelliJ: `RecentProjects.xml` under
  `AppData\Roaming\JetBrains\IntelliJIdea<ver>\options\`, and
  `LocalHistory` under `system\LocalHistory`.
