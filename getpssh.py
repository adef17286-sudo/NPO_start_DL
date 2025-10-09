#!/usr/bin/env python3

import subprocess
import re
import requests
from pathlib import Path
import os
import sys
import traceback

from pywidevine.cdm import Cdm
from pywidevine.device import Device
from pywidevine.pssh import PSSH


def run_npo_get_output(link):
    try:
        p = subprocess.run([sys.executable, 'NPO.py', link],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True)
        return p.stdout or "", p.stderr or "", p.returncode
    except Exception as e:
        print("[!] Failed to run NPO.py:", e)
        return "", str(e), 1


def extract_mpd_url(text):
    m = re.search(r'(https?://[^\s\'"]+?\.mpd(?:[^\s\'"]*)?)', text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def extract_drm_token(text):
    match = re.search(r'DRM Token:\s*([A-Za-z0-9_\-\.=]+)', text)
    if match:
        return match.group(1).strip()
    return None


def download_mpd(mpd_url, out_path="manifest.mpd"):
    try:
        r = requests.get(mpd_url, timeout=20)
        r.raise_for_status()
        Path(out_path).write_text(r.text, encoding='utf-8', errors='ignore')
        return out_path
    except requests.RequestException as e:
        print("[!] Failed to download MPD:", e)
        return None


def extract_pssh_blocks_from_mpd(path, max_len=200):
    text = Path(path).read_text(encoding='utf-8', errors='ignore')
    pattern = re.compile(r"<cenc:pssh>(.*?)</cenc:pssh>", re.DOTALL | re.IGNORECASE)
    found = pattern.findall(text)
    short = [f.strip() for f in found if len(f.strip()) <= max_len]
    return short


def to_hex(val):
    if isinstance(val, bytes):
        return val.hex()
    elif isinstance(val, str):
        return val
    else:
        return str(val)


def kid_to_nodash_hex(kid_val):
    if isinstance(kid_val, bytes):
        return kid_val.hex()
    if isinstance(kid_val, str):
        return kid_val.replace("-", "").lower()
    return str(kid_val)


def process_pssh_with_pywidevine(pssh_b64, provision_path, license_url):
    try:
        pssh = PSSH(pssh_b64)
        device = Device.load(provision_path)
        cdm = Cdm.from_device(device)
        session_id = cdm.open()

        challenge = cdm.get_license_challenge(session_id, pssh)

        headers = {'Content-Type': 'application/octet-stream'}
        resp = requests.post(license_url, data=challenge, headers=headers, timeout=30)
        resp.raise_for_status()

        cdm.parse_license(session_id, resp.content)

        keys = cdm.get_keys(session_id)
        if not keys:
            print("[!] No keys returned.")
            cdm.close(session_id)
            return []

        keypairs = []
        for key in keys:
            kid_raw = kid_to_nodash_hex(key.kid).lower()
            key_hex = to_hex(key.key).lower()
            kid_raw = kid_raw.replace("-", "")
            output = f"{kid_raw}:{key_hex}"
            if len(output) < 70:
                print(output)
                keypairs.append(output)

        cdm.close(session_id)
        return keypairs

    except Exception:
        traceback.print_exc()
        return []


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <link>")
        sys.exit(1)

    link = sys.argv[1]
    provision_path = "motorola_moto.wvd"
    if not Path(provision_path).is_file():
        print(f"[!] Provisioning file '{provision_path}' not found.")
        sys.exit(1)

    out, err, code = run_npo_get_output(link)
    if code != 0:
        print("[!] NPO.py exited with code", code)
        sys.exit(1)

    combined = out + "\n" + err
    mpd_url = extract_mpd_url(combined)
    if not mpd_url:
        print("[!] Could not find .mpd URL in output.")
        sys.exit(1)

    drm_token = extract_drm_token(combined)
    if not drm_token:
        print("[!] Could not find DRM token.")
        sys.exit(1)

    license_url = f"https://npo-drm-gateway.samgcloud.nepworldwide.nl/authentication?custom_data={drm_token}"

    mpd_file = download_mpd(mpd_url)
    if not mpd_file:
        sys.exit(1)

    psshs = extract_pssh_blocks_from_mpd(mpd_file, max_len=200)

    try:
        os.remove(mpd_file)
    except Exception:
        pass

    if not psshs:
        print("[!] No suitable PSSH blocks found.")
        sys.exit(1)

    all_keypairs = []
    for pssh in psshs:
        p_clean = "".join(pssh.split())
        keys = process_pssh_with_pywidevine(p_clean, provision_path, license_url)
        if not keys:
            sys.exit(1)
        all_keypairs.extend(keys)

    # Build command for N_m3u8dl-re
    cmd = ["N_m3u8dl-re", mpd_url]
    for keypair in all_keypairs:
        cmd += ["--key", keypair]

    # Append fixed options
    cmd += ["-sv", "best", "-sa", "best", "-M", "mkv"]

    print("\n[+] Running command:")
    print(" ".join(cmd))

    # Run the command
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print("[!] N_m3u8dl-re failed:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
