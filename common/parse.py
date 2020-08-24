

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
