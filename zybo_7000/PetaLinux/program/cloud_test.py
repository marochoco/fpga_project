import mmap
import struct
import urllib.request
import json
import time
import threading
import os
import sys
from datetime import datetime

# --- 設定 ---
# Google Apps Scriptのデプロイ済みURLをここに貼り付けてください
URL = "https://script.google.com/macros/s/AKfycbwpL9LeuG-7NkbjEorEInnKMY8nXrP9Ca2xG-EwEmlY7y-TCkaWt1Ape9ccBIujw0gzAA/exec"
BASE_ADDR = 0x43C00000
MAP_SIZE = 4096

def convert_fixed_to_float(raw_32bit):
    """32bit固定小数点を浮動小数点に変換"""
    is_negative = (raw_32bit >> 31) & 0x1
    value_part = raw_32bit & 0x7FFFFFFF
    float_val = value_part / 65536.0
    return -float_val if is_negative else float_val

def post_worker(data_dict):
    """クラウドへの送信用スレッド。失敗してもメイン処理を止めない。"""
    try:
        json_data = json.dumps(data_dict).encode("utf-8")
        req = urllib.request.Request(URL, data=json_data, method="POST")
        req.add_header("Content-Type", "application/json")
        # タイムアウトを短めに設定して詰まりを防止
        with urllib.request.urlopen(req, timeout=3) as res:
            pass
    except Exception:
        # ネットワークエラー等は無視して次に進む
        pass

def main():
    try:
        # FPGAレジスタへのアクセス準備
        fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        mm = mmap.mmap(fd, MAP_SIZE, mmap.MAP_SHARED, mmap.PROT_READ, offset=BASE_ADDR)
        
        print("Cloud Logging Started...")
        print("Target URL: {0}".format(URL))
        print("Press Ctrl+C to stop.")

        os.system('clear')

        while True:
            # 1. データ取得
            vals = []
            offsets = [0x20, 0x24, 0x28, 0x2C, 0x30, 0x34, 0x38]
            for offset in offsets:
                raw = struct.unpack('<I', mm[offset:offset+4])[0]
                vals.append(convert_fixed_to_float(raw))

            ax, ay, az, gx, gy, gz, temp = vals
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            # 2. 送信用データの作成（辞書形式）
            payload = {
                "timestamp": now_str,
                "accel": [ax, ay, az],
                "gyro": [gx, gy, gz],
                "temp": temp
            }

            # 3. 非同期でクラウド送信
            t = threading.Thread(target=post_worker, args=(payload,))
            t.daemon = True
            t.start()

            # 4. コンソール表示
            sys.stdout.write("\033[H")
            print("--- Pmod NAV Cloud Uploader ---")
            print("Status: Sending data every 0.5s")
            print("Time: {0}".format(now_str))
            print("ACCEL: X:{0:>7.3f} Y:{1:>7.3f} Z:{2:>7.3f}".format(ax, ay, az))
            print("GYRO : X:{0:>7.2f} Y:{1:>7.2f} Z:{2:>7.2f}".format(gx, gy, gz))
            print("TEMP : {0:>6.2f} C".format(temp))
            print("-" * 35)
            
            # 送信間隔（秒）
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nStopped by user.")
    except Exception as e:
        print("\nFatal Error: {0}".format(e))
    finally:
        if 'mm' in locals(): mm.close()
        if 'fd' in locals(): os.close(fd)

if __name__ == "__main__":
    main()
