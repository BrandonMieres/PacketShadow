#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Funcionalidades de escaneo de red e identificación de dispositivos
"""

import subprocess
import threading
import time
import ipaddress
import re
import os
import sys
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

# Colores para la terminal
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BRIGHT_RED = '\033[1;91m'
    BRIGHT_GREEN = '\033[1;92m'
    BRIGHT_YELLOW = '\033[1;93m'
    BRIGHT_BLUE = '\033[1;94m'
    BRIGHT_MAGENTA = '\033[1;95m'
    BRIGHT_CYAN = '\033[1;96m'
    BRIGHT_WHITE = '\033[1;97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

def loading_animation(text, duration=2):
    """Animación de carga"""
    chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        print(f"\r{Colors.BRIGHT_CYAN}[{chars[i]}]{Colors.RESET} {Colors.WHITE}{text}{Colors.RESET}", end="", flush=True)
        i = (i + 1) % len(chars)
        time.sleep(0.1)
    print(f"\r{Colors.BRIGHT_GREEN}[✓]{Colors.RESET} {Colors.WHITE}{text} - Completado{Colors.RESET}")

class OUIDatabase:
    """Clase para manejar la base de datos OUI"""
    
    def __init__(self, oui_file="OUI/ieee-oui.txt"):
        self.oui_file = oui_file
        self.oui_dict = {}
        self.load_oui_database()
    
    def load_oui_database(self):
        """Carga la base de datos OUI desde el archivo"""
        try:
            if not os.path.exists(self.oui_file):
                print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Archivo OUI no encontrado: {self.oui_file}{Colors.RESET}")
                print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Asegúrate de que el archivo ieee-oui.txt esté en la carpeta OUI{Colors.RESET}")
                return
            
            print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Cargando base de datos OUI...{Colors.RESET}")
            
            with open(self.oui_file, 'r', encoding='utf-8', errors='ignore') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    
                    # Ignorar líneas vacías o comentarios
                    if not line or line.startswith('#'):
                        continue
                    
                    # Buscar el patrón específico: XX:XX:XX   (hex)		Manufacturer
                    if '(hex)' in line:
                        try:
                            # Dividir por "(hex)"
                            parts = line.split('(hex)', 1)
                            if len(parts) == 2:
                                oui_part = parts[0].strip()
                                manufacturer_part = parts[1].strip()
                                
                                # El OUI debería ser algo como "XX:XX:XX" o "XX-XX-XX"
                                # Normalizar el formato del OUI
                                oui_clean = oui_part.replace(':', '').replace('-', '').replace(' ', '').upper()
                                
                                # Verificar que el OUI tenga 6 caracteres hexadecimales
                                if len(oui_clean) >= 6 and all(c in '0123456789ABCDEF' for c in oui_clean[:6]):
                                    oui_prefix = oui_clean[:6]
                                    
                                    # Limpiar el nombre del fabricante
                                    if manufacturer_part:
                                        self.oui_dict[oui_prefix] = manufacturer_part
                        
                        except Exception as e:
                            # Continuar con la siguiente línea si hay error
                            continue
            
            print(f"{Colors.BRIGHT_GREEN}[✓]{Colors.RESET} {Colors.WHITE}Base de datos OUI cargada: {len(self.oui_dict)} fabricantes{Colors.RESET}")
            
            # Mostrar algunos ejemplos para verificación
            if len(self.oui_dict) > 0:
                print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Ejemplos cargados:{Colors.RESET}")
                count = 0
                for oui, manufacturer in list(self.oui_dict.items())[:3]:
                    formatted_oui = f"{oui[:2]}:{oui[2:4]}:{oui[4:6]}"
                    print(f"  {Colors.BRIGHT_YELLOW}{formatted_oui}{Colors.RESET} -> {Colors.WHITE}{manufacturer[:40]}{Colors.RESET}")
                    count += 1
            
        except Exception as e:
            print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Error cargando OUI: {e}{Colors.RESET}")
            self.oui_dict = {}
    
    def get_manufacturer(self, mac_address):
        """Obtiene el fabricante basado en la dirección MAC"""
        if not mac_address or mac_address == "No disponible":
            return "MAC no disponible"
        
        try:
            # Limpiar y obtener OUI (primeros 6 caracteres hex)
            oui = mac_address.replace(':', '').replace('-', '').replace(' ', '').upper()[:6]
            
            if len(oui) == 6 and all(c in '0123456789ABCDEF' for c in oui):
                manufacturer = self.oui_dict.get(oui, "Fabricante desconocido")
                return manufacturer
            else:
                return "MAC inválida"
        except Exception as e:
            return "Error procesando MAC"

class NetworkScanner:
    """Escáner de red principal"""
    
    def __init__(self, oui_db):
        self.oui_db = oui_db
        self.active_hosts = []
    
    def ping_host(self, ip):
        """Hace ping a una IP específica"""
        try:
            # Ping silencioso multiplataforma
            if os.name == 'nt':  # Windows
                result = subprocess.run(['ping', '-n', '1', '-w', '1000', str(ip)], 
                                      capture_output=True, text=True, timeout=2)
            else:  # Linux/Mac
                result = subprocess.run(['ping', '-c', '1', '-W', '1', str(ip)], 
                                      capture_output=True, text=True, timeout=2)
            
            return result.returncode == 0
        except:
            return False
    
    def get_mac_address(self, ip):
        """Obtiene la dirección MAC usando ARP"""
        try:
            if os.name == 'nt':  # Windows
                # Primero hacer ping para llenar tabla ARP
                subprocess.run(['ping', '-n', '1', '-w', '1000', str(ip)], 
                             capture_output=True, text=True, timeout=2)
                
                result = subprocess.run(['arp', '-a', str(ip)], capture_output=True, text=True, timeout=3)
                output = result.stdout
                
                # Buscar patrón MAC en Windows
                mac_patterns = [
                    r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',
                    r'([0-9A-Fa-f]{2}-){5}([0-9A-Fa-f]{2})'
                ]
                
                for pattern in mac_patterns:
                    match = re.search(pattern, output)
                    if match:
                        return match.group(0).upper().replace('-', ':')
                        
            else:  # Linux/Mac
                # Primero hacer ping para llenar tabla ARP
                subprocess.run(['ping', '-c', '1', '-W', '1', str(ip)], 
                             capture_output=True, text=True, timeout=2)
                
                result = subprocess.run(['arp', '-n', str(ip)], capture_output=True, text=True, timeout=3)
                output = result.stdout
                
                # Buscar patrón MAC en Linux/Mac
                for line in output.split('\n'):
                    if str(ip) in line:
                        mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', line)
                        if mac_match:
                            return mac_match.group(0).upper().replace('-', ':')
        except:
            pass
        return None
    
    def get_hostname(self, ip):
        """Intenta obtener el hostname del dispositivo"""
        try:
            import socket
            hostname = socket.gethostbyaddr(str(ip))[0]
            return hostname
        except:
            return "N/A"
    
    def scan_host(self, ip):
        """Escanea un host individual"""
        if self.ping_host(ip):
            mac = self.get_mac_address(ip)
            manufacturer = self.oui_db.get_manufacturer(mac) if mac else "N/A"
            hostname = self.get_hostname(ip)
            
            return {
                'ip': str(ip),
                'mac': mac or "No disponible",
                'manufacturer': manufacturer,
                'hostname': hostname,
                'status': 'Activo'
            }
        return None
    
    def scan_network_range(self, network_range, max_workers=50):
        """Escanea un rango de red completo"""
        print(f"\n{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} {Colors.WHITE}Iniciando escaneo de red: {network_range}{Colors.RESET}")
        
        try:
            network = ipaddress.IPv4Network(network_range, strict=False)
            hosts_list = list(network.hosts())
            total_hosts = len(hosts_list)
            
            if total_hosts > 254:
                print(f"{Colors.BRIGHT_YELLOW}[!]{Colors.RESET} {Colors.WHITE}Red muy grande ({total_hosts} hosts). Esto puede tardar varios minutos...{Colors.RESET}")
                
                # Preguntar si quiere continuar con redes grandes
                confirm = input(f"{Colors.BRIGHT_YELLOW}¿Continuar con el escaneo? (y/N): {Colors.RESET}").lower()
                if confirm not in ['y', 'yes', 's', 'si']:
                    print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Escaneo cancelado{Colors.RESET}")
                    return []
            
            print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Escaneando {total_hosts} hosts con {max_workers} hilos...{Colors.RESET}")
            
            # Inicializar contadores
            scanned = 0
            active_hosts = []
            start_time = time.time()
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Enviar trabajos
                future_to_ip = {executor.submit(self.scan_host, ip): ip for ip in hosts_list}
                
                # Recoger resultados
                for future in as_completed(future_to_ip):
                    scanned += 1
                    result = future.result()
                    
                    if result:
                        active_hosts.append(result)
                        print(f"\r{Colors.BRIGHT_GREEN}[+] Host encontrado:{Colors.RESET} {Colors.WHITE}{result['ip']}{Colors.RESET} {Colors.BRIGHT_CYAN}[{result['mac']}]{Colors.RESET} {Colors.BRIGHT_YELLOW}({result['manufacturer'][:30]}){Colors.RESET}")
                    
                    # Mostrar progreso cada 10 hosts o al final
                    if scanned % 10 == 0 or scanned == total_hosts:
                        progress = (scanned / total_hosts) * 100
                        elapsed = time.time() - start_time
                        rate = scanned / elapsed if elapsed > 0 else 0
                        print(f"\r{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} Progreso: {Colors.BRIGHT_CYAN}{progress:.1f}%{Colors.RESET} ({scanned}/{total_hosts}) - {Colors.WHITE}{rate:.1f} hosts/s{Colors.RESET}", end="", flush=True)
            
            elapsed_total = time.time() - start_time
            print(f"\n\n{Colors.BRIGHT_GREEN}[✓]{Colors.RESET} {Colors.WHITE}Escaneo completado en {elapsed_total:.2f}s. Hosts activos: {len(active_hosts)}/{total_hosts}{Colors.RESET}")
            self.active_hosts = active_hosts
            return active_hosts
            
        except ValueError as e:
            print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Formato de red inválido: {e}{Colors.RESET}")
            return []
        except Exception as e:
            print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Error en el escaneo: {e}{Colors.RESET}")
            return []
    
    def display_results(self):
        """Muestra los resultados del escaneo en formato tabla"""
        if not self.active_hosts:
            print(f"\n{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}No se encontraron hosts activos{Colors.RESET}")
            return
        
        print(f"\n{Colors.BRIGHT_CYAN}╔═══════════════════════════════════════════════════════════════════════════════════════════════════════╗")
        print(f"║                                       DISPOSITIVOS DETECTADOS                                         ║")
        print(f"╚═══════════════════════════════════════════════════════════════════════════════════════════════════════╝{Colors.RESET}")
        
        # Header de la tabla
        print(f"{Colors.BOLD}{Colors.WHITE}{'#':<3} {'IP Address':<15} {'MAC Address':<18} {'Hostname':<20} {'Fabricante':<30} {'Estado'}{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'─' * 3} {'─' * 15} {'─' * 18} {'─' * 20} {'─' * 30} {'─' * 8}{Colors.RESET}")
        
        # Datos de la tabla
        for i, host in enumerate(self.active_hosts, 1):
            ip_color = Colors.BRIGHT_GREEN
            mac_color = Colors.BRIGHT_YELLOW if host['mac'] != "No disponible" else Colors.RED
            hostname_color = Colors.BRIGHT_MAGENTA if host['hostname'] != "N/A" else Colors.WHITE
            manufacturer_color = Colors.WHITE if host['manufacturer'] != "Fabricante desconocido" else Colors.YELLOW
            status_color = Colors.BRIGHT_GREEN
            
            # Truncar textos largos
            hostname_display = host['hostname'][:18] + ".." if len(host['hostname']) > 20 else host['hostname']
            manufacturer_display = host['manufacturer'][:28] + ".." if len(host['manufacturer']) > 30 else host['manufacturer']
            
            print(f"{Colors.BRIGHT_BLUE}{i:<3}{Colors.RESET} "
                  f"{ip_color}{host['ip']:<15}{Colors.RESET} "
                  f"{mac_color}{host['mac']:<18}{Colors.RESET} "
                  f"{hostname_color}{hostname_display:<20}{Colors.RESET} "
                  f"{manufacturer_color}{manufacturer_display:<30}{Colors.RESET} "
                  f"{status_color}{host['status']}{Colors.RESET}")
        
        # Estadísticas
        unique_manufacturers = len(set(host['manufacturer'] for host in self.active_hosts if host['manufacturer'] != "Fabricante desconocido"))
        devices_with_mac = len([host for host in self.active_hosts if host['mac'] != "No disponible"])
        devices_with_hostname = len([host for host in self.active_hosts if host['hostname'] != "N/A"])
        
        print(f"\n{Colors.BRIGHT_GREEN}[✓]{Colors.RESET} {Colors.WHITE}Estadísticas del escaneo:{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}►{Colors.RESET} Total de dispositivos: {Colors.BRIGHT_GREEN}{len(self.active_hosts)}{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}►{Colors.RESET} Dispositivos con MAC: {Colors.BRIGHT_YELLOW}{devices_with_mac}{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}►{Colors.RESET} Dispositivos con hostname: {Colors.BRIGHT_MAGENTA}{devices_with_hostname}{Colors.RESET}")
        print(f"  {Colors.BRIGHT_CYAN}►{Colors.RESET} Fabricantes únicos: {Colors.BRIGHT_WHITE}{unique_manufacturers}{Colors.RESET}")