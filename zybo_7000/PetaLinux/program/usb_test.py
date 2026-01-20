import mmap
import struct
import time
import os
import subprocess
import sys
from datetime import datetime

# --- 設定 ---
BASE_ADDR = 0x43C00000
MAP_SIZE = 4096
USB_DEVICE = "/dev/sda1"
USB_MOUNT_DIR = "/mnt/usb"
CSV_FILE = os.path.join(USB_MOUNT_DIR, "pmod_nav_log.csv")

def mount_usb():
    """USBメモリをマウントする"""
    if not os.path.ismount(USB_MOUNT_DIR):
        if not os.path.exists(USB_MOUNT_DIR):
            os.makedirs(USB_MOUNT_DIR)
        try:
            # .format() 形式に変更
            subprocess.run(["mount", USB_DEVICE, USB_MOUNT_DIR], check=True)
            print("Success: {0} mounted at {1}".format(USB_DEVICE, USB_MOUNT_DIR))
        except Exception as e:
            print("Error: Mount failed. {0}".format(e))
            return False
    else:
        print("Info: USB is already mounted.")
    return True

def convert_fixed_to_float(raw_32bit):
    """32bit固定小数点を浮動小数点に変換"""
    is_negative = (raw_32bit >> 31) & 0x1
    value_part = raw_32bit & 0x7FFFFFFF
    float_val = value_part / 65536.0
    return -float_val if is_negative else float_val

def main():
    if not mount_usb():
        print("USBメモリが利用できないため終了します。")
        return

    if not os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, 'w') as f:
                f.write("Timestamp,AccX,AccY,AccZ,GyroX,GyroY,GyroZ,Temp\n")
        except Exception as e:
            print("Error: Log file creation failed. {0}".format(e))
            return

    try:
        fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        mm = mmap.mmap(fd, MAP_SIZE, mmap.MAP_SHARED, mmap.PROT_READ, offset=BASE_ADDR)
        
        print("Logging started. Saving to: {0}".format(CSV_FILE))
        print("Press Ctrl+C to stop.")

        os.system('clear')

        while True:
            vals = []
            offsets = [0x20, 0x24, 0x28, 0x2C, 0x30, 0x34, 0x38]
            for offset in offsets:
                raw = struct.unpack('<I', mm[offset:offset+4])[0]
                vals.append(convert_fixed_to_float(raw))

            ax, ay, az, gx, gy, gz, temp = vals
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            csv_row = "{0},{1:.3f},{2:.3f},{3:.3f},{4:.2f},{5:.2f},{6:.2f},{7:.2f}\n".format(
                now_str, ax, ay, az, gx, gy, gz, temp
            )

            with open(CSV_FILE, mode='a', buffering=1) as f:
                f.write(csv_row)
                f.flush()
                os.fsync(f.fileno())

            # コンソール表示
            sys.stdout.write("\033[H")
            print("--- Pmod NAV USB Logger ---")
            print("Time: {0}".format(now_str))
            print("ACCEL [G]  : X:{0:>7.3f} Y:{1:>7.3f} Z:{2:>7.3f}".format(ax, ay, az))
            print("GYRO [dps] : X:{0:>7.2f} Y:{1:>7.2f} Z:{2:>7.2f}".format(gx, gy, gz))
            print("TEMP [C]   : {0:>6.2f}".format(temp))
            print("-" * 30)
            
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nLogging stopped by user.")
    except Exception as e:
        print("\nFatal Error: {0}".format(e))
    finally:
        if 'mm' in locals(): mm.close()
        if 'fd' in locals(): os.close(fd)

if __name__ == "__main__":
    main()
