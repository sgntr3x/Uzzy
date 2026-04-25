import json
import os

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

def get_interface_name(brand, port):
    """Markaya göre interface ismini JSON'dan çeker (GigabitEthernet, port1.0 vb.)."""
    template = COMMANDS.get(brand, {}).get("interface", "interface GigabitEthernet 0/{port}")
    return template.format(port=port)

def build_create_vlan_cmds(brand, vlan_id, vlan_name=None, ip=None, mask=None):
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

def build_assign_vlan_cmds(brand, ports, vlan_id, mode):
    """Seçili portlara Access veya Trunk VLAN atama komutlarını JSON üzerinden derler."""
    brand_cmds = COMMANDS.get(brand, {})
    assign_cmds = brand_cmds.get("vlan_assign", {})
    
    cmds = [get_config_term(brand)]
    for p in ports:
        cmds.append(get_interface_name(brand, p))
        if mode == "Access":
            cmds.append(assign_cmds.get("access_mode", "switchport mode access"))
            cmds.append(assign_cmds.get("access_vlan", "switchport access vlan {vlan_id}").format(vlan_id=vlan_id))
        else:
            cmds.append(assign_cmds.get("trunk_mode", "switchport mode trunk"))
            cmds.append(assign_cmds.get("trunk_vlan", "switchport trunk allowed vlan {vlan_id}").format(vlan_id=vlan_id))
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds

def build_stp_cmds(brand, ports, stp_mode):
    """Portfast veya BPDU Guard komutlarını JSON üzerinden derler."""
    brand_cmds = COMMANDS.get(brand, {})
    stp_cmds = brand_cmds.get("stp", {})
    
    cmds = [get_config_term(brand)]
    for p in ports:
        cmds.append(get_interface_name(brand, p))
        if stp_mode == "portfast":
            cmds.append(stp_cmds.get("portfast", "spanning-tree portfast"))
        elif stp_mode == "bpduguard":
            cmds.append(stp_cmds.get("bpduguard", "spanning-tree bpduguard enable"))
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds

def build_management_ip_cmds(brand, vid, ip, mask, port=None):
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
        cmds.append(get_interface_name(brand, port))
        cmds.append(assign_cmds.get("access_mode", "switchport mode access"))
        cmds.append(assign_cmds.get("access_vlan", "switchport access vlan {vlan_id}").format(vlan_id=vid))
        
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds

def build_port_control_cmds(brand, ports, state):
    """Portu açma veya kapatma komutlarını JSON üzerinden derler."""
    brand_cmds = COMMANDS.get(brand, {})
    cmds = [get_config_term(brand)]
    for p in ports:
        cmds.append(get_interface_name(brand, p))
        cmds.append(state)
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds

def build_default_port_cmds(brand, ports):
    """Portu fabrika ayarlarına sıfırlama komutlarını JSON üzerinden derler."""
    brand_cmds = COMMANDS.get(brand, {})
    cmds = [get_config_term(brand)]
    for p in ports:
        template = brand_cmds.get("default_interface", "default interface GigabitEthernet 0/{port}")
        cmds.append(template.format(port=p))
    cmds.append(brand_cmds.get("end_command", "end"))
    return cmds