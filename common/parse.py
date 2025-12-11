

from datetime import datetime, timezone
from . import Response
from . import log


def show_switches(data: dict):
    """
    Parses show switches output
    :returns dictionary of ManagedDevice objects by switch IP
    """
    switch_dict = {}
    for dev in data.get('All Switches', {}):
        switch_dict[dev['IP Address']] = dev

    return switch_dict


def show_image_version(data):
    """Parse return from show image version command
    """
    data = data.get('_data', [])[0].split('\n')
    img_dict = {}
    _part = 'err'
    for line in data:
        if line.startswith("Partition"):
            if '0:0' in line:
                _part = '0:0'
            elif '0:1' in line:
                _part = '0:1'
            if 'Default boot' in line:
                img_dict['default_boot'] = f"0:{line.split(':')[2].replace(' **Default boot**', '')}"
            continue
        if line.startswith('Software Version'):
            img_dict[f"version {_part}"] = line.split(':')[-1].replace('ArubaOS ', '').split('(')[0].strip()
            # img_dict[f"version {_part}"] = img_dict[f"version {_part}"].split(' (Digitally')[0]
        if line.startswith('Build num'):
            img_dict[f"version {_part}"] += f"_{line.split(':')[-1].strip()}"

    return img_dict


def show_web_server_profile(data: Response) -> dict:
    """Get Portal Certificate Name from output of show web-server profile

    Args:
        data (dict): Output of "show web-server profile" on Aruba Controller

    Returns:
        dict: Clean Return data from output of command
    """
    data = data.json()
    key = data.get("Web Server Configuration", list(data.keys())[0])
    if "Error" in key:
        try:
            log.error(key.split("(")[1].split(")")[0])
        except Exception:
            log.error(key)

    data = data.get(key)
    # cert_name = [z for y in data for z in y.values() if "Captive Portal Certificate" in y.values()][-1]

    _ret = {_dict.get("Parameter", "error"): _dict.get("Value", "error") for _dict in data}
    if "error" in _ret:
        log.error("Error During Parsing of show web-server profile output")
        return {}
    else:
        return _ret


def show_crypto_pki_servercert(data: Response) -> dict:
    this = iter(data.json().get("_data"))
    _ret = {}
    for line in this:
        if line.startswith("Not After :"):
            expire_date = line.replace("Not After : ", "")
            expire_date = expire_date.split()
            if expire_date:
                expire_date[1] = f"{int(expire_date[1]):02}"
                expire_date = " ".join(expire_date)
                naive = datetime.strptime(expire_date, '%b %d %H:%M:%S %Y %Z')
                aware = datetime(naive.year, naive.month, naive.day, naive.hour, naive.minute, naive.second, tzinfo=timezone.utc)
                _ret["cert_exp_date"] = aware

        elif line.startswith("Subject: CN="):
            _ret["cert_cn"] = line.split("Subject: CN=")[-1]

        elif "CA Issuers - URI:" in line:
            _ret["cert_ca_issuers_uri"] = line.replace("CA Issuers - URI:", "")

        elif "Subject Alternative Name:" in line:
            try:
                san_line = next(this)
                san_line = san_line.split(",")
                san = {"dns": [], "ip": []}
                _ = [san[y.split(":")[0].strip().lower()].append(y.split(":")[1]) for y in san_line]
                _ret["cert_san"] = san
            except Exception as e:
                log.warning(f"Unable to Parse SAN from show crypto pki ServerCert output\n{e}")

    return _ret
