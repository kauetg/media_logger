# file operations go here
import psutil
import platform

def get_external_disks():
    external_disks = []
    system_platform = platform.system()

    for part in psutil.disk_partitions(all=False):
        if system_platform == 'Windows':
            # 'removable' só funciona com win32com, então vamos usar heurística:
            if 'cdrom' in part.opts or part.fstype == '':
                continue
            if part.device.startswith('A:') or part.device.startswith('B:'):
                continue
            if 'fixed' not in part.opts:  # não é disco fixo
                external_disks.append(part.device)
        else:
            # Em Linux/macOS: evita root, boot, etc.
            if part.mountpoint.startswith("/media") or part.mountpoint.startswith("/run/media"):
                external_disks.append(part.mountpoint)

    return external_disks
