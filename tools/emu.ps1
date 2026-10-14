# PCSX2 driver helpers: launch, screenshot the emulator window, send key presses.
# Usage: powershell -ExecutionPolicy Bypass -File emu.ps1 <start ISO | shot PNG | keys "K" | stop | wait N>
param([string]$cmd, [string]$arg)
$ErrorActionPreference = 'Stop'
$pcsx2 = 'D:\ps2\pcsx2-v2.2.0-windows-x64-Qt\pcsx2-qt.exe'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr after, int x, int y, int cx, int cy, uint f);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint mapType);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags, int dx, int dy, uint data, UIntPtr extra);
  [DllImport("user32.dll")] public static extern uint SendInput(uint n, INPUT[] inputs, int size);
  [StructLayout(LayoutKind.Sequential)] public struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
  [StructLayout(LayoutKind.Explicit)] public struct INPUTUNION { [FieldOffset(0)] public KEYBDINPUT ki; [FieldOffset(0)] public long pad1; [FieldOffset(8)] public long pad2; [FieldOffset(16)] public long pad3; }
  [StructLayout(LayoutKind.Sequential)] public struct INPUT { public uint type; public INPUTUNION u; }
  public static void Press(ushort vk, int ms) {
    ushort sc = (ushort)MapVirtualKey(vk, 0);
    bool ext = (vk >= 0x21 && vk <= 0x2E) || vk == 0x5B;   // arrows/home/end/ins/del + win are extended keys
    uint fl = (uint)(ext ? 0x0001 : 0);
    INPUT[] d = new INPUT[1]; d[0].type = 1; d[0].u.ki = new KEYBDINPUT { wVk = vk, wScan = sc, dwFlags = fl };
    INPUT[] u = new INPUT[1]; u[0].type = 1; u[0].u.ki = new KEYBDINPUT { wVk = vk, wScan = sc, dwFlags = fl | 0x0002 };
    SendInput(1, d, Marshal.SizeOf(typeof(INPUT))); System.Threading.Thread.Sleep(ms); SendInput(1, u, Marshal.SizeOf(typeof(INPUT)));
  }
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
"@
$pidfile = Join-Path $PSScriptRoot 'emu.pid'
function Get-Emu { if (-not (Test-Path $pidfile)) { return $null }; $id = [int](Get-Content $pidfile); $p = Get-Process -Id $id -ErrorAction SilentlyContinue; if ($p -and $p.MainWindowHandle -ne 0) { $p } else { $null } }
switch ($cmd) {
  'start' {
    # 백그라운드 실행: 사용자의 현재 창 포커스를 되돌리고 PCSX2 창은 맨 뒤(HWND_BOTTOM)로, 활성화하지 않음
    $fg = [W]::GetForegroundWindow()
    $p = Start-Process -FilePath $pcsx2 -ArgumentList @('-batch', '-nogui', "`"$arg`"") -PassThru
    Set-Content -Path $pidfile -Value $p.Id
    for ($i = 0; $i -lt 100 -and $p.MainWindowHandle -eq 0; $i++) { Start-Sleep -Milliseconds 100; $p.Refresh() }
    if ($p.MainWindowHandle -ne 0) { [W]::SetWindowPos($p.MainWindowHandle, [IntPtr]1, 0, 0, 0, 0, 0x13) | Out-Null }
    if ($fg -ne [IntPtr]::Zero) { [W]::SetForegroundWindow($fg) | Out-Null }
    Write-Output "started pid $($p.Id)"
  }
  'shot' {
    $p = Get-Emu; if (-not $p) { throw 'no pcsx2 window' }
    $h = $p.MainWindowHandle
    Start-Sleep -Milliseconds 100
    $r = New-Object W+RECT; [W]::GetWindowRect($h, [ref]$r) | Out-Null
    $w = $r.R - $r.L; $hh = $r.B - $r.T
    $bmp = New-Object System.Drawing.Bitmap $w, $hh
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc(); [W]::PrintWindow($h, $hdc, 2) | Out-Null; $g.ReleaseHdc($hdc)
    $bmp.Save($arg, [System.Drawing.Imaging.ImageFormat]::Png); $g.Dispose(); $bmp.Dispose()
    Write-Output "saved $arg ($w x $hh) title='$($p.MainWindowTitle)'"
  }
  'keys' {
    $p = Get-Emu; if (-not $p) { throw 'no pcsx2 window' }
    [W]::SetForegroundWindow($p.MainWindowHandle) | Out-Null; Start-Sleep -Milliseconds 200
    [System.Windows.Forms.SendKeys]::SendWait($arg); Write-Output "sent $arg"
  }
  'hold' {
    # arg: "VK[,ms]" e.g. "0D,150" (Return), "4B" (K=Cross), "26" (Up), "28" (Down)
    $parts = $arg.Split(','); $vk = [Convert]::ToByte($parts[0], 16); $ms = if ($parts.Length -gt 1) { [int]$parts[1] } else { 150 }
    $p = Get-Emu; if (-not $p) { throw 'no pcsx2 window' }
    [W]::SetForegroundWindow($p.MainWindowHandle) | Out-Null; Start-Sleep -Milliseconds 200
    $sc = [byte][W]::MapVirtualKey($vk, 0); $ex = if ($vk -ge 0x21 -and $vk -le 0x2E) { 1 } else { 0 }; [W]::keybd_event($vk, $sc, $ex, [UIntPtr]::Zero); Start-Sleep -Milliseconds $ms; [W]::keybd_event($vk, $sc, ($ex -bor 2), [UIntPtr]::Zero)
    Write-Output "held $($parts[0]) for $ms ms"
  }
  'press' {
    # SendInput with scan code. arg: "VK[,ms]" hex VK, e.g. "0D,200"
    $parts = $arg.Split(','); $vk = [Convert]::ToUInt16($parts[0], 16); $ms = if ($parts.Length -gt 1) { [int]$parts[1] } else { 200 }
    $p = Get-Emu; if (-not $p) { throw 'no pcsx2 window' }
    [W]::SetForegroundWindow($p.MainWindowHandle) | Out-Null; Start-Sleep -Milliseconds 250
    [W]::Press($vk, $ms); Write-Output "pressed $($parts[0]) for $ms ms"
  }
  'click' {
    $p = Get-Emu; if (-not $p) { throw 'no pcsx2 window' }
    $h = $p.MainWindowHandle; [W]::SetForegroundWindow($h) | Out-Null; Start-Sleep -Milliseconds 200
    $r = New-Object W+RECT; [W]::GetWindowRect($h, [ref]$r) | Out-Null
    $x = [int](($r.L + $r.R) / 2); $y = [int](($r.T + $r.B) / 2)
    [W]::SetCursorPos($x, $y) | Out-Null; Start-Sleep -Milliseconds 100
    [W]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 80; [W]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
    Write-Output "clicked $x,$y"
  }
  'post' {
    # Post WM_KEYDOWN/WM_KEYUP directly to the window. arg: "VK[,ms]"
    $parts = $arg.Split(','); $vk = [Convert]::ToUInt32($parts[0], 16); $ms = if ($parts.Length -gt 1) { [int]$parts[1] } else { 200 }
    $p = Get-Emu; if (-not $p) { throw 'no pcsx2 window' }
    $h = $p.MainWindowHandle   # 포커스를 바꾸지 않고 창에 직접 메시지 전송
    $sc = [W]::MapVirtualKey($vk, 0)
    $ext = if ($vk -ge 0x21 -and $vk -le 0x2E) { 0x01000000 } else { 0 }
    $ldown = [IntPtr]([int64](1 -bor ($sc -shl 16) -bor $ext)); $lup = [IntPtr]([int64](1 -bor ($sc -shl 16) -bor $ext) -bor 0xC0000000)
    [W]::PostMessage($h, 0x100, [IntPtr]$vk, $ldown) | Out-Null; Start-Sleep -Milliseconds $ms; [W]::PostMessage($h, 0x101, [IntPtr]$vk, $lup) | Out-Null
    Write-Output "posted $($parts[0]) for $ms ms"
  }
  'stop' { if (Test-Path $pidfile) { $id = [int](Get-Content $pidfile); Stop-Process -Id $id -Force -ErrorAction SilentlyContinue; Remove-Item $pidfile }; Write-Output 'stopped' }
  'wait' { Start-Sleep -Seconds ([int]$arg); Write-Output 'ok' }
  'title' { $p = Get-Emu; if ($p) { Write-Output $p.MainWindowTitle } else { Write-Output 'none' } }
}
