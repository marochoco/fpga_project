import mmap
import os
import time
import struct
import sys

BASE_ADDR = 0x43C00000
MAP_SIZE = 0x1000 

def convert_fixed_to_float(raw_32bit):
    is_negative = (raw_32bit >> 31) & 0x1
    value_part = raw_32bit & 0x7FFFFFFF
    float_val = value_part / 65536.0
    return -float_val if is_negative else float_val

def main():
    try:
        fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        mem = mmap.mmap(fd, MAP_SIZE, mmap.MAP_SHARED, mmap.PROT_READ, offset=BASE_ADDR)
    except OSError:
        print("Error: root権限が必要です")
        return

    # 画面を一度クリアして開始
    os.system('clear')
    print("--- Pmod NAV 9-Axis Real-time Monitor ---")
    print("Base Address: {} | Press Ctrl+C to stop".format(hex(BASE_ADDR)))
    print("-" * 50)

    try:
        while True:
            # データ取得
            vals = []
            for offset in [0x20, 0x24, 0x28, 0x2C, 0x30, 0x34, 0x38]:
                raw = struct.unpack('<I', mem[offset:offset+4])[0]
                vals.append(convert_fixed_to_float(raw))

            ax, ay, az, gx, gy, gz, temp = vals

            # \033[s : 現在のカーソル位置を保存
            # \033[u : 保存した位置に復帰
            # これを組み合わせて、常に同じ場所から書き直します
            sys.stdout.write("\033[s") 
            
            sys.stdout.write("\n[ACCEL] X: {:>7.3f}, Y: {:>7.3f}, Z: {:>7.3f} (G)  ".format(ax, ay, az))
            sys.stdout.write("\n[GYRO ] X: {:>7.2f}, Y: {:>7.2f}, Z: {:>7.2f} (dps)".format(gx, gy, gz))
            sys.stdout.write("\n[TEMP ] {:>6.2f} C".format(temp))
            
            sys.stdout.write("\033[u") # カーソルを最初のアサイン位置に戻す
            sys.stdout.flush()

            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    finally:
        mem.close()
        os.close(fd)

if __name__ == "__main__":
    main()
