def get_config_term(brand):
    """Global konfigürasyon moduna geçiş komutu."""
    return "configure terminal" if brand == "Ruijie" else "conf t"

def get_interface_name(brand, port):
    """Markaya göre interface ismini (GigabitEthernet, port1.0 vb.) döndürür."""
    if brand == "Cisco":
        return f"interface GigabitEthernet 1/0/{port}"
    elif brand == "Allied Telesis":
        return f"interface port1.0.{port}"
    else:  # Ruijie ve varsayılan
        return f"interface GigabitEthernet 0/{port}"

def build_create_vlan_cmds(brand, vlan_id, vlan_name=None, ip=None, mask=None):
    """VLAN oluşturma ve opsiyonel olarak IP atama komutlarını derler."""
    cmds = [get_config_term(brand), f"vlan {vlan_id}"]
    if vlan_name:
        cmds.append(f"name {vlan_name}")
        
    # Eğer IP ve Mask girildiyse, VLAN'ı oluşturduktan sonra Interface'ine girip IP ata
    if ip and mask:
        cmds.append(f"interface vlan {vlan_id}")
        cmds.append(f"ip address {ip} {mask}")
        cmds.append("no shutdown")
        
    cmds.append("end")
    return cmds

def build_assign_vlan_cmds(brand, ports, vlan_id, mode):
    """Seçili portlara Access veya Trunk VLAN atama komutlarını derler."""
    cmds = [get_config_term(brand)]
    for p in ports:
        cmds.append(get_interface_name(brand, p))
        if mode == "Access":
            cmds.append("switchport mode access")
            cmds.append(f"switchport access vlan {vlan_id}")
        else:
            cmds.append("switchport mode trunk")
            cmds.append(f"switchport trunk allowed vlan {vlan_id}")
    cmds.append("end")
    return cmds

def build_stp_cmds(brand, ports, stp_mode):
    """Portfast veya BPDU Guard komutlarını derler."""
    cmds = [get_config_term(brand)]
    for p in ports:
        cmds.append(get_interface_name(brand, p))
        if stp_mode == "portfast":
            if brand == "Allied Telesis": cmds.append("spanning-tree edgeport")
            else: cmds.append("spanning-tree portfast")
        elif stp_mode == "bpduguard":
            if brand == "Allied Telesis": cmds.append("spanning-tree bpdu-guard enable")
            else: cmds.append("spanning-tree bpduguard enable")
    cmds.append("end")
    return cmds

def build_management_ip_cmds(brand, vid, ip, mask, port=None):
    """Management VLAN'ına IP atama ve opsiyonel port atama komutlarını derler."""
    cmds = [get_config_term(brand), f"interface vlan {vid}", f"ip address {ip} {mask}", "no shutdown"]
    
    # Eğer belirli bir port seçildiyse, portun içine girip vlan'ı ata
    if port and str(port).isdigit():
        cmds.append("exit")
        cmds.append(get_interface_name(brand, port))
        cmds.append("switchport mode access")
        cmds.append(f"switchport access vlan {vid}")
        
    cmds.append("end")
    return cmds

def build_port_control_cmds(brand, ports, state):
    """Portu açma (no shutdown) veya kapatma (shutdown) komutlarını derler."""
    cmds = [get_config_term(brand)]
    for p in ports:
        cmds.append(get_interface_name(brand, p))
        cmds.append(state)
    cmds.append("end")
    return cmds

def build_default_port_cmds(brand, ports):
    """Portu fabrika ayarlarına sıfırlama komutlarını derler."""
    cmds = [get_config_term(brand)]
    for p in ports:
        if brand == "Cisco": cmds.append(f"default interface GigabitEthernet 1/0/{p}")
        elif brand == "Allied Telesis": cmds.append(f"default interface port1.0.{p}")
        else: cmds.append(f"default interface GigabitEthernet 0/{p}")
    cmds.append("end")
    return cmds