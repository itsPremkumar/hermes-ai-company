# MATLAB_Editor_State.xml — shape & extraction

Location (per release):
```
C:\Users\<user>\AppData\Roaming\MathWorks\MATLAB\R20xx\MATLAB_Editor_State.xml
```
Each opened file is one `<File>` element with `absPath` (folder) + `name` (filename).

## Example fragment
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Editor version="1.0">
   <File absPath="C:\Users\admin\Documents\MATLAB" lastWrittenTime="1716901545358" name="canny_edge_detection.m">
      <CodeFolds version="1.0"/>
   </File>
   <File absPath="C:\Users\PREM KUMAR\Downloads\dip proj\MATLAB" lastWrittenTime="1716902191557" name="classifyVehicles.m"/>
</Editor>
```

## Extraction snippets (bash / git-bash)
List every distinct project folder MATLAB ever opened:
```bash
F="$APPDATA/MathWorks/MATLAB/R2023b/MATLAB_Editor_State.xml"
grep -oE 'absPath="[^"]+"' "$F" | sed -E 's/absPath="//; s/"$//' | sort -u
```
List every distinct `.m` filename referenced:
```bash
grep -oE 'name="[^"]+\.m"' "$F" | sed -E 's/name="//; s/"$//' | sort -u
```

## Cross-reference with History.xml (same folder)
History holds executed commands (some marked `error="true"`), which hints at what the user
was debugging. Grep for `edit`/`run`/`open` of `.m`:
```bash
grep -oiE '(edit|run|open)\s+[A-Za-z0-9_\\:.-]+\.m' "$APPDATA/MathWorks/MATLAB/R2023b/History.xml"
```

## Gotcha
The `absPath` is the **folder**, `name` is the **file**. To test existence of a project,
check the folder:
```bash
for d in "C:/Users/admin/Documents/MATLAB" "C:/Users/PREM KUMAR/Downloads/dip proj/MATLAB"; do
  [ -d "$d" ] && echo "EXISTS: $d" || echo "MISSING: $d"
done
```
In the recovered case, `admin\Documents\MATLAB` EXISTED (had 30 .m files) while the
`Downloads\dip proj` folders were MISSING (deleted) — but the editor-state XML is what
pointed at both, so recovery knew exactly what was lost vs. surviving.
