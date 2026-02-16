[Setup]
AppName=SFW NSFW Sorter
AppVersion=1.0
DefaultDirName={pf}\SFWNSFWSorter
DefaultGroupName=SFW NSFW Sorter
OutputDir=.
OutputBaseFilename=Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\dist\app\*"; DestDir: "{app}"; Flags: recursesubdirs
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: Installing Microsoft Visual C++ Runtime...; Flags: waituntilterminated
Filename: "{app}\app.exe"; Description: "Launch Application"; Flags: nowait postinstall skipifsilent
