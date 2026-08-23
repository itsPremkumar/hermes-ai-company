# NetBeans Forensics — worked example & exact path map

## Exact path map (Windows, NetBeans 22, user "PREM KUMAR")
```
IDE install : C:\Program Files\NetBeans-22
User config : C:\Users\PREM KUMAR\AppData\Roaming\NetBeans\22\
  ├─ config\Preferences\org\netbeans\modules\utilities\RecentFilesHistory.properties   ← GOLD MINE
  ├─ config\Windows2Local\Groups\OpenedProjects\projectTabLogical_tc.wstcgrp
  └─ var\filehistory\storage                                                          ← Local History (often empty)
Cache      : C:\Users\PREM KUMAR\AppData\Local\NetBeans\Cache
Bundled JDK: C:\Users\PREM KUMAR\.jdks\corretto-1.8.0_432   (demo/sample .java here confuse searches)
```

## Parsed RecentFilesHistory.properties (real sample)
The file mixes `RecentFilesIcon.N` (base64 PNG, ignore) with `RecentFilesURL.N`
(the payload). Stripped to URLs only:

```
RecentFilesURL.0  = ...\NetBeansProjects\BaseStationServer6\src\basestationserver6\MobileDeviceClient.java
RecentFilesURL.1  = ...\NetBeansProjects\BaseStationServer6\src\basestationserver6\BaseStationServer6.java
RecentFilesURL.2  = ...\NetBeansProjects\BaseStationServer3\src\basestationserver3\MobileDeviceClient.java
RecentFilesURL.3  = ...\NetBeansProjects\BaseStationServer3\src\basestationserver3\BaseStationServer3.java
RecentFilesURL.4  = ...\NetBeansProjects\MobileDeviceClient7\src\mobiledeviceclient7\MobileDeviceClient7.java
RecentFilesURL.5  = ...\NetBeansProjects\MobileDeviceClient7\src\mobiledeviceclient7\MobileDeviceClient8.java
RecentFilesURL.6  = ...\NetBeansProjects\BaseStationServer\src\NewClass.java
RecentFilesURL.7  = ...\NetBeansProjects\BaseStationServer4\src\basestationserver4\BaseStationServer4.java
RecentFilesURL.8  = ...\NetBeansProjects\BaseStationServer4\src\basestationserver4\MobileDeviceClient.java
RecentFilesURL.9  = ...\NetBeansProjects\BaseStationServer 3\src\basestationserver\pkg3\BaseStationServer3.java
RecentFilesURL.10 = ...\NetBeansProjects\BaseStationServer 3\src\basestationserver\pkg3\MobileDeviceClient.java
```

Common prefix = `C:\Users\PREM KUMAR\Documents\NetBeansProjects\`.
Reconstructed projects: `BaseStationServer6`, `BaseStationServer3`,
`MobileDeviceClient7`, `BaseStationServer`, `BaseStationServer4`,
`BaseStationServer 3`. All socket-based "Base Station Server" <-> "Mobile Device
Client" networking labs.

## Outcome of this recovery attempt
- RecentFiles PROVED the projects existed (paths + filenames).
- `Documents\NetBeansProjects\` -> GONE.
- Recycle Bin (`S-1-5-21-*-1001`) -> not present.
- D: drive -> empty/unavailable.
- OneDrive -> empty.
- Local History `storage` -> 10-byte stub (no snapshots).
- No `project.xml` / `build.xml` / `*.java` anywhere in profile except JDK demos.
Conclusion: **code unrecoverable on this machine**; recovery requires an
external backup/old laptop/USB.
