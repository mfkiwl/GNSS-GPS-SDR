import serial
import time
import curses
from datetime import datetime, timezone, timedelta

# Map NMEA system prefixes to labels
SYSTEM_LABELS = {
    '$GP': 'GPS',
    '$GA': 'Galileo',
    '$GL': 'GLONASS',
    '$GB': 'Beidou',
    '$BD': 'Beidou'  # $BD is sometimes used instead of $GB
}

# Store satellite data
satellite_data = {
    'GPS': [],
    'Galileo': [],
    'GLONASS': [],
    'Beidou': []
}

# Store fix and time info
fix_info = {
    'utc_time': '',
    'local_time': '',
    'hdop': '',
    'vdop': '',
    'pdop': ''
}

# Parse GSV (GNSS Satellites in View) message
def parse_gsv(fields, system):
    try:
        total_sentences = int(fields[1])
        sentence_num = int(fields[2])
        sats_in_view = int(fields[3])

        sats = []
        for i in range(4, len(fields) - 4, 4):
            prn = fields[i]
            elevation = fields[i+1]
            azimuth = fields[i+2]
            snr = fields[i+3] if fields[i+3] != '' else '0'
            sats.append((prn, snr))
        return sats
    except (ValueError, IndexError):
        return []

# Parse GGA (fix data)
def parse_gga(fields):
    try:
        utc_raw = fields[1]
        if utc_raw:
            hour = int(utc_raw[0:2])
            minute = int(utc_raw[2:4])
            second = int(utc_raw[4:6])
            utc_time = datetime.utcnow().replace(hour=hour, minute=minute, second=second)
            fix_info['utc_time'] = utc_time.strftime('%H:%M:%S')
            fix_info['local_time'] = datetime.now().strftime('%H:%M:%S')
    except Exception:
        pass

# Parse GSA (GNSS DOP and Active Satellites)
def parse_gsa(fields):
    try:
        fix_info['pdop'] = fields[15]
        fix_info['hdop'] = fields[16]
        fix_info['vdop'] = fields[17].split('*')[0]
    except IndexError:
        pass

def display(stdscr, ser):
    curses.curs_set(0)
    stdscr.nodelay(True)

    while True:
        try:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if not line.startswith('$'):
                continue

            fields = line.split(',')
            prefix = line[0:3]
            system = SYSTEM_LABELS.get(prefix, None)

            if 'GSV' in line:
                sats = parse_gsv(fields, system)
                if system and sats:
                    satellite_data[system] += sats
                    # Keep latest ~16 sats only
                    satellite_data[system] = satellite_data[system][-16:]

            elif 'GGA' in line:
                parse_gga(fields)

            elif 'GSA' in line:
                parse_gsa(fields)

            # Update screen
            stdscr.erase()
            stdscr.addstr(0, 2, "GNSS Monitor", curses.A_BOLD | curses.A_UNDERLINE)

            row = 2
            for sys_name in satellite_data:
                stdscr.addstr(row, 2, f"{sys_name} Satellites:", curses.A_BOLD)
                row += 1
                for prn, snr in satellite_data[sys_name]:
                    stdscr.addstr(row, 4, f"PRN: {prn: <4}  SNR: {snr: >3} dBHz")
                    row += 1
                row += 1

            # Display fix info
            stdscr.addstr(row, 2, "Time Info:", curses.A_BOLD)
            row += 1
            stdscr.addstr(row, 4, f"UTC Time:   {fix_info.get('utc_time', '')}")
            row += 1
            stdscr.addstr(row, 4, f"Local Time: {fix_info.get('local_time', '')}")
            row += 2

            stdscr.addstr(row, 2, "Fix Accuracy:", curses.A_BOLD)
            row += 1
            stdscr.addstr(row, 4, f"PDOP: {fix_info.get('pdop', '')}  HDOP: {fix_info.get('hdop', '')}  VDOP: {fix_info.get('vdop', '')}")

            stdscr.refresh()
            time.sleep(0.1)

        except KeyboardInterrupt:
            break
        except Exception as e:
            stdscr.addstr(0, 2, f"Error: {e}")
            stdscr.refresh()
            time.sleep(1)

def main():
    port = '/dev/ttyUSB0'  # Update if your device uses a different port
    baudrate = 115200
    try:
        with serial.Serial(port, baudrate, timeout=1) as ser:
            curses.wrapper(display, ser)
    except serial.SerialException as e:
        print(f"Serial error: {e}")

if __name__ == "__main__":
    main()
