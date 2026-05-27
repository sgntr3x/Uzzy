import json
import os
import re

JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "commands.json")

try:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        COMMANDS = json.load(f)
except FileNotFoundError:
    print(f"Hata: {JSON_PATH} bulunamadı!")
    COMMANDS = {}
except Exception as e:
    print(f"JSON Okuma Hatası: {e}")
    COMMANDS = {}

def get_config_term(brand):
    """Global konfigürasyon moduna geçiş komutunu JSON'dan çeker."""
    return COMMANDS.get(brand, {}).get("global_config", "conf t")

def group_ports(ports):
    """Ardışık portları gruplayarak range formatına çevirir. (Örn: [1,2,3,5] -> ['1-3', '5'])"""
    if not ports:
        return []
    sorted_ports = sorted(list(set([int(p) for p in ports])))
    ranges = []
    start = sorted_ports[0]
    end = sorted_ports[0]
    
    for p in sorted_ports[1:]:
        if p == end + 1:
            end = p
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = p
            end = p
            
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
        
    return ranges

def get_interface_name(brand, port, is_range=False):
    """Markaya göre interface ismini JSON'dan çeker (GigabitEthernet, port1.0 vb.)."""
    brand_cmds = COMMANDS.get(brand, {})
    if is_range:
        template = brand_cmds.get("interface_range", brand_cmds.get("interface", "interface GigabitEthernet 0/{port}"))
    else:
        template = brand_cmds.get("interface", "interface GigabitEthernet 0/{port}")
    return template.format(port=port)

def get_interface_names(brand, ports, port_mapping=None):
    """Port_mapping varsa gerçek isimleri döner, yoksa varsayılan JSON yapılandırmasını dener."""
    brand_cmds = COMMANDS.get(brand, {})
    res = []
    if port_mapping and any(p in port_mapping for p in ports):
        valid_ports = sorted([p for p in ports if p in port_mapping])
        if valid_ports:
            # İsimleri akıllı gruplama (Örn: Gi1/0/1, Gi1/0/2, Gi1/0/3 -> Gi1/0/1-3)
            groups = {}
            for p in valid_ports:
                name = port_mapping[p]
                match = re.match(r'^(.*?)(\d+)$', name)
                if match:
                    prefix, num = match.groups()
                    if prefix not in groups:
                        groups[prefix] = []
                    groups[prefix].append(int(num))
                else:
                    groups[name] = []
                    
            for prefix, nums in groups.items():
                if not nums:
                    res.append(f"interface {prefix}")
                    continue
                    
                nums = sorted(list(set(nums)))
                ranges = []
                start = end = nums[0]
                for n in nums[1:]:
                    if n == end + 1: end = n
                    else:
                        ranges.append(str(start) if start == end else f"{start}-{end}")
                        start = end = n
                ranges.append(str(start) if start == end else f"{start}-{end}")
                
                for r in ranges:
                    is_range = "-" in r
                    if is_range:
                        res.append(f"interface range {prefix}{r}")
                    else:
                        res.append(f"interface {prefix}{r}")
            return res
            
    # Mapping yoksa eski usul range ve varsayılan isim gruplaması yap
    port_ranges = group_ports(ports)
    for pr in port_ranges:
        is_range = "-" in pr
        template = brand_cmds.get("interface_range" if is_range else "interface", "interface GigabitEthernet 0/{port}")
        res.append(template.format(port=pr))
    return res

def build_create_vlan_cmds(brand, vlan_id, vlan_name=None, ip=None, mask=None, port_mapping=None):
    """VLAN oluşturma ve opsiyonel olarak IP atama komutlarını JSON üzerinden derler."""
    brand_cmds = COMMANDS.get(brand, {})
    vlan_cmds = brand_cmds.get("vlan_create", {})
    
    cmds = [get_config_term(brand), vlan_cmds.get("create", "vlan {vlan_id}").format(vlan_id=vlan_id)]
    if vlan_name:
        cmds.append(vlan_cmds.get("name", "name {vlan_name}").format(vlan_name=vlan_name))
        
    if ip and mask:
        cmds.append(vlan_cmds.get("interface", "interface vlan {vlan_id}").format(vlan_id=vlan_id))
        cmds.append(vlan_cmds.get("ip_address", "ip address {ip} {mask}").format(ip=ip, mask=mask))
        cmds.append(vlan_cmds.get("no_shutdown", "no shutdown"))
        
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds

def build_assign_vlan_cmds(brand, ports, vlan_id, mode, port_mapping=None):
    """Seçili portlara Access veya Trunk VLAN atama komutlarını JSON üzerinden derler."""
    brand_cmds = COMMANDS.get(brand, {})
    assign_cmds = brand_cmds.get("vlan_assign", {})
    
    cmds = [get_config_term(brand)]
    interfaces = get_interface_names(brand, ports, port_mapping)
    for iface in interfaces:
        cmds.append(iface)
        if mode == "Access":
            cmds.append(assign_cmds.get("access_mode", "switchport mode access"))
            cmds.append(assign_cmds.get("access_vlan", "switchport access vlan {vlan_id}").format(vlan_id=vlan_id))
        else:
            cmds.append(assign_cmds.get("trunk_mode", "switchport mode trunk"))
            cmds.append(assign_cmds.get("trunk_vlan", "switchport trunk allowed vlan {vlan_id}").format(vlan_id=vlan_id))
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds

def build_stp_cmds(brand, ports, stp_mode, port_mapping=None):
    """Portfast veya BPDU Guard komutlarını JSON üzerinden derler."""
    brand_cmds = COMMANDS.get(brand, {})
    stp_cmds = brand_cmds.get("stp", {})
    
    cmds = [get_config_term(brand)]
    interfaces = get_interface_names(brand, ports, port_mapping)
    for iface in interfaces:
        cmds.append(iface)
        if stp_mode == "portfast":
            cmds.append(stp_cmds.get("portfast", "spanning-tree portfast"))
        elif stp_mode == "bpduguard":
            cmds.append(stp_cmds.get("bpduguard", "spanning-tree bpduguard enable"))
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds

def build_management_ip_cmds(brand, vid, ip, mask, port=None, port_mapping=None):
    """Management VLAN'ına IP atama ve opsiyonel port atama komutlarını JSON üzerinden derler."""
    brand_cmds = COMMANDS.get(brand, {})
    vlan_cmds = brand_cmds.get("vlan_create", {})
    assign_cmds = brand_cmds.get("vlan_assign", {})
    
    cmds = [
        get_config_term(brand),
        vlan_cmds.get("interface", "interface vlan {vlan_id}").format(vlan_id=vid),
        vlan_cmds.get("ip_address", "ip address {ip} {mask}").format(ip=ip, mask=mask),
        vlan_cmds.get("no_shutdown", "no shutdown")
    ]
    
    if port and str(port).isdigit():
        cmds.append(brand_cmds.get("exit_command", "exit"))
        if port_mapping and int(port) in port_mapping:
            cmds.append(f"interface {port_mapping[int(port)]}")
        else:
            cmds.append(get_interface_name(brand, port))
        cmds.append(assign_cmds.get("access_mode", "switchport mode access"))
        cmds.append(assign_cmds.get("access_vlan", "switchport access vlan {vlan_id}").format(vlan_id=vid))
        
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds

def build_port_control_cmds(brand, ports, state, port_mapping=None):
    """Portu açma veya kapatma komutlarını JSON üzerinden derler."""
    brand_cmds = COMMANDS.get(brand, {})
    cmds = [get_config_term(brand)]
    interfaces = get_interface_names(brand, ports, port_mapping)
    for iface in interfaces:
        cmds.append(iface)
        cmds.append(state)
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds

def build_default_port_cmds(brand, ports, port_mapping=None):
    """Portu fabrika ayarlarına sıfırlama komutlarını JSON üzerinden derler."""
    brand_cmds = COMMANDS.get(brand, {})
    cmds = [get_config_term(brand)]
    if port_mapping and any(p in port_mapping for p in ports):
        valid_ports = [p for p in ports if p in port_mapping]
        for p in valid_ports:
            cmds.append(f"default interface {port_mapping[p]}")
    else:
        port_ranges = group_ports(ports)
        for pr in port_ranges:
            is_range = "-" in pr
            template = brand_cmds.get("default_interface_range" if is_range else "default_interface", "default interface GigabitEthernet 0/{port}")
            cmds.append(template.format(port=pr))
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds

def build_poe_cmds(brand, ports, state, port_mapping=None):
    """PoE'yi açma (enable) veya kapatma (disable) komutlarını derler."""
    brand_cmds = COMMANDS.get(brand, {})
    poe_cmds = brand_cmds.get("poe", {})
    cmds = [get_config_term(brand)]
    interfaces = get_interface_names(brand, ports, port_mapping)
    for iface in interfaces:
        cmds.append(iface)
        if state == "enable":
            cmds.append(poe_cmds.get("enable", "power inline auto"))
        else:
            cmds.append(poe_cmds.get("disable", "power inline never"))
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds