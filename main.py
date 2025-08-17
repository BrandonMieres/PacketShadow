#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PacketShadow - Network Device Scanner
Advanced Network Reconnaissance Tool
Versión: 2.2
"""

import os
import sys
import ipaddress
import subprocess
import platform
import time
import getpass

# Variables globales para módulos que se importarán después de configurar el entorno
Colors = None
loading_animation = None
OUIDatabase = None
NetworkScanner = None
deauth_device = None

def print_colored(message, color_code="37"):
    """Imprime mensajes con colores básicos sin depender de colorama"""
    print(f"\033[{color_code}m{message}\033[0m")

def check_admin_privileges():
    """Verifica si el programa se ejecuta con privilegios de administrador"""
    try:
        if os.name == 'nt':  # Windows
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:  # Linux/Mac
            return os.geteuid() == 0
    except:
        return False

def wait_for_user_input(message="Presiona Enter para continuar..."):
    """Espera entrada del usuario para evitar que se cierre la ventana"""
    try:
        input(f"\n{message}")
    except (KeyboardInterrupt, EOFError):
        pass

def relaunch_as_admin():
    """Relanza el programa con privilegios de administrador manteniendo la ventana"""
    try:
        if os.name == 'nt':  # Windows
            import ctypes
            
            print_colored("🔄 Relanzando como administrador...", "36")
            print_colored("⚠️  Se abrirá una ventana de UAC - acepta los permisos", "33")
            print_colored("📝 La aplicación continuará en una nueva ventana con permisos", "33")
            
            # Preparar argumentos
            args = " ".join([f'"{arg}"' if " " in arg else arg for arg in sys.argv])
            
            # Intentar relanzar como admin
            result = ctypes.windll.shell32.ShellExecuteW(
                None,           # hwnd
                "runas",        # lpVerb
                sys.executable, # lpFile  
                args,           # lpParameters
                None,           # lpDirectory
                1               # nShowCmd (SW_SHOWNORMAL)
            )
            
            if result > 32:  # Éxito
                print_colored("✅ Relanzando con permisos de administrador...", "32")
                time.sleep(2)
                return True
            else:
                print_colored("❌ No se pudo obtener permisos de administrador", "31")
                return False
                
        else:  # Linux/Mac
            print_colored("🔄 Relanzando con sudo...", "36")
            result = subprocess.run(['sudo', sys.executable] + sys.argv)
            return result.returncode == 0
            
    except Exception as e:
        print_colored(f"⚠️ Error al intentar relanzar como administrador: {e}", "31")
        return False

def handle_admin_permissions():
    """Maneja la verificación y solicitud de permisos de administrador"""
    if not check_admin_privileges():
        clear_screen()
        print_colored("╔" + "═" * 60 + "╗", "31")
        print_colored("║" + " " * 22 + "ERROR DE PERMISOS" + " " * 21 + "║", "31")
        print_colored("║" + " " * 60 + "║", "31")
        print_colored("║  Este programa REQUIERE ejecutarse como administrador      ║", "31")
        print_colored("║  para poder realizar escaneos de red correctamente.        ║", "31")
        print_colored("║" + " " * 60 + "║", "31")
        print_colored("║  En Windows: Aparecerá una ventana UAC                     ║", "33")
        print_colored("║  En Linux/Mac: Se solicitará contraseña sudo               ║", "33")
        print_colored("╚" + "═" * 60 + "╝", "31")
        
        print_colored("\n🤔 ¿Qué deseas hacer?", "36")
        print_colored("[1] 🚀 Relanzar como administrador", "32")
        print_colored("[2] ❌ Salir del programa", "31")
        
        while True:
            try:
                choice = input("\nSelecciona una opción (1-2): ").strip()
                
                if choice == "1":
                    print_colored("\n🔄 Intentando obtener permisos de administrador...", "36")
                    if relaunch_as_admin():
                        print_colored("✅ El programa se está relanzando con permisos", "32")
                        print_colored("⏳ Esta ventana se cerrará automáticamente...", "36")
                        time.sleep(2)  # Breve pausa para que el usuario lea el mensaje
                        sys.exit(0)
                    else:
                        print_colored("❌ No se pudieron obtener permisos de administrador", "31")
                        print_colored("💡 El programa no puede funcionar sin estos permisos", "33")
                        wait_for_user_input("Presiona Enter para salir...")
                        sys.exit(1)
                        
                elif choice == "2":
                    print_colored("👋 Saliendo del programa...", "31")
                    wait_for_user_input("Presiona Enter para salir...")
                    sys.exit(0)
                    
                else:
                    print_colored("❌ Opción inválida. Usa 1 o 2", "31")
                    
            except (KeyboardInterrupt, EOFError):
                print_colored("\n👋 Saliendo del programa...", "31")
                sys.exit(0)
    
    return True

def get_venv_paths():
    """Obtiene las rutas del entorno virtual según el SO"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    venv_dir = os.path.join(script_dir, "venv")
    
    if platform.system() in ["Linux", "Darwin"]:
        python_bin = os.path.join(venv_dir, "bin", "python")
        pip_bin = os.path.join(venv_dir, "bin", "pip")
    else:  # Windows
        python_bin = os.path.join(venv_dir, "Scripts", "python.exe")
        pip_bin = os.path.join(venv_dir, "Scripts", "pip.exe")
    
    return venv_dir, python_bin, pip_bin

def is_running_in_venv():
    """Verifica si estamos ejecutando desde el entorno virtual"""
    venv_dir, python_bin, _ = get_venv_paths()
    current_python = os.path.normpath(sys.executable).lower()
    venv_path = os.path.normpath(venv_dir).lower()
    return current_python.startswith(venv_path)

def create_virtual_environment():
    """Crea un entorno virtual si no existe"""
    venv_dir, python_bin, pip_bin = get_venv_paths()
    
    if os.path.exists(venv_dir) and os.path.exists(python_bin):
        print_colored("✅ Entorno virtual ya existe.", "32")
        return True
    
    print_colored("🔧 Creando entorno virtual...", "33")
    
    try:
        # Limpiar entorno anterior si existe pero está incompleto
        if os.path.exists(venv_dir):
            import shutil
            shutil.rmtree(venv_dir)
        
        # Crear nuevo entorno virtual
        result = subprocess.run([sys.executable, "-m", "venv", venv_dir], 
                              capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(python_bin):
            print_colored("✅ Entorno virtual creado exitosamente.", "32")
            
            # Actualizar pip en el nuevo entorno
            print_colored("🔄 Actualizando pip...", "33")
            subprocess.run([python_bin, "-m", "pip", "install", "--upgrade", "pip", "--no-cache-dir"], 
                         capture_output=True, timeout=60)
            
            return True
        else:
            print_colored(f"⚠️ Error creando entorno virtual: {result.stderr}", "31")
            return False
            
    except subprocess.TimeoutExpired:
        print_colored("⏰ Timeout creando entorno virtual.", "31")
        return False
    except Exception as e:
        print_colored(f"⚠️ Error inesperado creando venv: {e}", "31")
        return False

def install_dependencies():
    """Instala las dependencias necesarias para PacketShadow"""
    venv_dir, python_bin, pip_bin = get_venv_paths()
    
    # Lista de dependencias específicas para PacketShadow
    dependencies = [
        "scapy==2.5.0",
        "colorama==0.4.6", 
        "requests==2.31.0",
        "setuptools==70.0.0"
    ]
    
    print_colored("📦 Instalando dependencias de PacketShadow...", "36")
    
    success_count = 0
    total_deps = len(dependencies)
    
    for dep in dependencies:
        print_colored(f"📥 Instalando {dep}...", "33")
        
        try:
            result = subprocess.run([pip_bin, "install", "--no-cache-dir", dep], 
                                  capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0 or "already satisfied" in result.stdout.lower():
                print_colored(f"✅ {dep} instalado correctamente.", "32")
                success_count += 1
            else:
                print_colored(f"⚠️ Problema instalando {dep}: {result.stderr[:100]}", "33")
                # Intentar sin versión específica
                base_dep = dep.split("==")[0]
                retry_result = subprocess.run([pip_bin, "install", "--no-cache-dir", base_dep], 
                                            capture_output=True, text=True, timeout=120)
                if retry_result.returncode == 0:
                    print_colored(f"✅ {base_dep} instalado sin versión específica.", "32")
                    success_count += 1
                    
        except subprocess.TimeoutExpired:
            print_colored(f"⏰ Timeout instalando {dep}.", "33")
        except Exception as e:
            print_colored(f"⚠️ Error instalando {dep}: {e}", "31")
    
    # Instalar requirements.txt si existe
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if os.path.exists(req_file):
        print_colored("📜 Instalando desde requirements.txt...", "33")
        try:
            subprocess.run([pip_bin, "install", "-r", req_file, "--no-cache-dir"], 
                         capture_output=True, timeout=180)
        except:
            pass
    
    success_rate = (success_count / total_deps) * 100
    print_colored(f"📊 Dependencias instaladas: {success_count}/{total_deps} ({success_rate:.1f}%)", "36")
    
    return success_count >= total_deps * 0.75  # 75% mínimo de éxito

def verify_dependencies():
    """Verifica que las dependencias críticas estén disponibles"""
    critical_modules = ["scapy", "colorama"]
    
    for module in critical_modules:
        try:
            __import__(module)
        except ImportError:
            return False
    return True

def setup_environment():
    """Configura el entorno completo para PacketShadow"""
    print_colored("🚀 Configurando entorno para PacketShadow...", "36")
    
    # Verificar estructura de directorios
    required_dirs = ["modules", "OUI"]
    missing_dirs = []
    for dir_name in required_dirs:
        if not os.path.exists(dir_name):
            missing_dirs.append(dir_name)
    
    if missing_dirs:
        print_colored(f"⚠️ Directorios requeridos no encontrados: {', '.join(missing_dirs)}", "31")
        print_colored("💡 Asegúrate de ejecutar el programa desde el directorio correcto", "33")
        wait_for_user_input()
        return False
    
    # Crear entorno virtual si no existe
    if not create_virtual_environment():
        print_colored("⚠️ No se pudo crear el entorno virtual.", "31")
        print_colored("💡 Continuando con el entorno actual...", "33")
    
    # Si no estamos ejecutando desde el venv, instalamos dependencias y relanzamos
    if not is_running_in_venv():
        if not install_dependencies():
            print_colored("⚠️ Algunas dependencias pueden no haberse instalado correctamente.", "33")
        
        # Relanzar desde el venv SOLO si no tenemos el marcador Y si no hay errores críticos
        if "venv_restart_marker" not in sys.argv:
            venv_dir, python_bin, pip_bin = get_venv_paths()
            
            # Verificar que el python del venv existe antes de intentar relanzar
            if not os.path.exists(python_bin):
                print_colored("⚠️ No se encontró el ejecutable de Python en el venv.", "31")
                print_colored("💡 Continuando con el entorno actual...", "33")
                return True
            
            print_colored(f"🔄 Relanzando desde el entorno virtual...", "36")
            print_colored("⏳ El programa continuará automáticamente...", "33")
            time.sleep(2)
            
            try:
                # Usar subprocess en lugar de os.execv para mejor manejo de errores
                result = subprocess.run([python_bin] + sys.argv + ["venv_restart_marker"], 
                                      cwd=os.getcwd())
                
                # Si llegamos aquí, el proceso hijo terminó
                sys.exit(result.returncode)
                
            except FileNotFoundError:
                print_colored(f"⚠️ No se pudo encontrar el ejecutable: {python_bin}", "31")
                print_colored("💡 Continuando con el entorno actual...", "33")
            except Exception as e:
                print_colored(f"⚠️ Error al relanzar desde venv: {e}", "31")
                print_colored("💡 Continuando con el entorno actual...", "33")
    
    # Verificar dependencias críticas
    if not verify_dependencies():
        print_colored("⚠️ Algunas dependencias críticas no están disponibles.", "33")
        print_colored("💡 El programa puede no funcionar correctamente.", "33")
        wait_for_user_input("Presiona Enter para continuar de todos modos...")
    
    print_colored("✅ Entorno configurado correctamente.", "32")
    time.sleep(1)
    return True

def clear_screen():
    """Limpia la pantalla"""
    os.system('clear' if os.name == 'posix' else 'cls')
    time.sleep(0.1)

def get_system_prompt():
    """Obtiene el prompt personalizado con usuario y sistema"""
    try:
        username = getpass.getuser()
        if not username or username.strip() == "":
            username = "anonymous"
    except:
        username = "anonymous"
    
    try:
        system = platform.system().lower()
        system_map = {
            'windows': 'windows',
            'linux': 'linux', 
            'darwin': 'macos',
            'freebsd': 'freebsd',
            'openbsd': 'openbsd'
        }
        system_name = system_map.get(system, 'unknown')
        if system_name == 'unknown' or not system_name:
            system_name = "anonymous"
    except:
        system_name = "anonymous"
    
    return f"\033[96m{username}@{system_name}:~$\033[0m "

def get_colors():
    """Obtiene la clase Colors o devuelve un fallback"""
    global Colors
    if Colors is not None:
        return Colors
    else:
        class ColorsClass:
            BRIGHT_RED = "\033[91m"
            BRIGHT_CYAN = "\033[96m"
            BRIGHT_YELLOW = "\033[93m"
            BRIGHT_GREEN = "\033[92m"
            WHITE = "\033[97m"
            RESET = "\033[0m"
        return ColorsClass

def print_banner():
    """Muestra el banner del programa"""
    Colors = get_colors()
    
    banner = f"""
{Colors.BRIGHT_RED}
   ██████   █████   ██████ ██   ██ ███████ ████████ ███████ ██   ██  █████  ██████   ██████  ██     ██
   ██   ██ ██   ██ ██      ██  ██  ██         ██    ██      ██   ██ ██   ██ ██   ██ ██    ██ ██     ██
   ██████  ███████ ██      █████   █████      ██    ███████ ███████ ███████ ██   ██ ██    ██ ██  █  ██
   ██      ██   ██ ██      ██  ██  ██         ██         ██ ██   ██ ██   ██ ██   ██ ██    ██ ██ ███ ██
   ██      ██   ██  ██████ ██   ██ ███████    ██    ███████ ██   ██ ██   ██ ██████   ██████   ███ ███ 
{Colors.RESET}
{Colors.BRIGHT_CYAN}                        ╔══════════════════════════════════════╗
                        ║        Advanced Network Scanner      ║
                        ║         by DarK v0.1                 ║
                        ╚══════════════════════════════════════╝{Colors.RESET}
{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} {Colors.WHITE}Network Reconnaissance & Device Identification Tool{Colors.RESET}
{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} {Colors.WHITE}Enterprise Grade Penetration Testing Suite{Colors.RESET}
{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} {Colors.WHITE}IEEE OUI Database Integration{Colors.RESET}
{Colors.BRIGHT_YELLOW}[+]{Colors.RESET} {Colors.WHITE}Manual Network Configuration{Colors.RESET}
"""
    print(banner)

def show_menu():
    """Muestra el menú principal"""
    Colors = get_colors()
    
    menu = f"""
{Colors.BRIGHT_CYAN}╔═══════════════════════════════════════════════╗
║              MENÚ PRINCIPAL                   ║
╚═══════════════════════════════════════════════╝{Colors.RESET}

{Colors.BRIGHT_GREEN}[1]{Colors.RESET} {Colors.WHITE}🎯 Escanear rango personalizado{Colors.RESET}
{Colors.BRIGHT_GREEN}[2]{Colors.RESET} {Colors.WHITE}🖥️ Escanear IP específica{Colors.RESET}
{Colors.BRIGHT_GREEN}[3]{Colors.RESET} {Colors.WHITE}📋 Ver últimos resultados{Colors.RESET}
{Colors.BRIGHT_GREEN}[4]{Colors.RESET} {Colors.WHITE}🔄 Actualizar base de datos OUI{Colors.RESET}
{Colors.BRIGHT_GREEN}[5]{Colors.RESET} {Colors.WHITE}ℹ️ Información del sistema{Colors.RESET}
{Colors.BRIGHT_RED}[0]{Colors.RESET} {Colors.WHITE}⚠ Salir{Colors.RESET}

{Colors.BRIGHT_YELLOW}┌──────────────────────────────────────────────────────┐
│  💡 Tip: Especifica manualmente el rango de          │
│  red que quieres escanear (ej: 192.168.1.0/24)       │
└──────────────────────────────────────────────────────┘{Colors.RESET}
"""
    print(menu)

def show_system_info():
    """Muestra información del sistema y configuración"""
    Colors = get_colors()
    
    print(f"\n{Colors.BRIGHT_CYAN}╔═══════════════════════════════════════════════╗")
    print(f"║           INFORMACIÓN SISTEMA         ║")
    print(f"╚═══════════════════════════════════════════════╝{Colors.RESET}")
    
    # Información del sistema
    print(f"\n{Colors.BRIGHT_GREEN}[+]{Colors.RESET} {Colors.WHITE}Sistema Operativo:{Colors.RESET}")
    print(f"  {Colors.BRIGHT_CYAN}▶{Colors.RESET} OS: {Colors.BRIGHT_YELLOW}{platform.system()}{Colors.RESET}")
    print(f"  {Colors.BRIGHT_CYAN}▶{Colors.RESET} Versión: {Colors.BRIGHT_YELLOW}{platform.version()}{Colors.RESET}")
    print(f"  {Colors.BRIGHT_CYAN}▶{Colors.RESET} Arquitectura: {Colors.BRIGHT_YELLOW}{platform.architecture()[0]}{Colors.RESET}")
    
    # Información de Python
    print(f"\n{Colors.BRIGHT_GREEN}[+]{Colors.RESET} {Colors.WHITE}Entorno Python:{Colors.RESET}")
    print(f"  {Colors.BRIGHT_CYAN}▶{Colors.RESET} Versión: {Colors.BRIGHT_YELLOW}{platform.python_version()}{Colors.RESET}")
    print(f"  {Colors.BRIGHT_CYAN}▶{Colors.RESET} Ejecutable: {Colors.BRIGHT_YELLOW}{sys.executable}{Colors.RESET}")
    print(f"  {Colors.BRIGHT_CYAN}▶{Colors.RESET} Entorno virtual: {Colors.BRIGHT_GREEN if is_running_in_venv() else Colors.BRIGHT_RED}{'✓ Activo' if is_running_in_venv() else '✗ No activo'}{Colors.RESET}")
    
    # Información del proyecto
    print(f"\n{Colors.BRIGHT_GREEN}[+]{Colors.RESET} {Colors.WHITE}Configuración PacketShadow:{Colors.RESET}")
    print(f"  {Colors.BRIGHT_CYAN}▶{Colors.RESET} Directorio actual: {Colors.BRIGHT_YELLOW}{os.getcwd()}{Colors.RESET}")
    print(f"  {Colors.BRIGHT_CYAN}▶{Colors.RESET} Archivo OUI: {Colors.BRIGHT_YELLOW}{'✓ Encontrado' if os.path.exists('OUI/ieee-oui.txt') else '✗ No encontrado'}{Colors.RESET}")
    
    # Verificar permisos de administrador
    is_admin = check_admin_privileges()
    print(f"  {Colors.BRIGHT_CYAN}▶{Colors.RESET} Permisos admin: {Colors.BRIGHT_GREEN if is_admin else Colors.BRIGHT_RED}{'✓ Sí' if is_admin else '✗ No'}{Colors.RESET}")
    
    # Verificar dependencias críticas
    print(f"\n{Colors.BRIGHT_GREEN}[+]{Colors.RESET} {Colors.WHITE}Dependencias Críticas:{Colors.RESET}")
    critical_deps = ["scapy", "colorama", "requests"]
    for dep in critical_deps:
        try:
            __import__(dep)
            status = f"{Colors.BRIGHT_GREEN}✓ Disponible"
        except ImportError:
            status = f"{Colors.BRIGHT_RED}✗ No disponible"
        print(f"  {Colors.BRIGHT_CYAN}▶{Colors.RESET} {dep}: {status}{Colors.RESET}")

def load_modules():
    """Carga los módulos necesarios después de configurar el entorno"""
    global Colors, loading_animation, OUIDatabase, NetworkScanner, deauth_device
    
    try:
        from modules.red import Colors, loading_animation, OUIDatabase, NetworkScanner
        from modules.authattack import deauth_device
        return True
    except ImportError as e:
        print_colored(f"⚠️ Error importando módulos: {e}", "31")
        print_colored("💡 Verifica que los archivos modules/red.py y modules/authattack.py existan", "33")
        return False

def main():
    """Función principal del programa"""
    try:
        # Configurar codificación de consola para Windows
        if os.name == 'nt':
            try:
                # Intentar configurar UTF-8
                os.system('chcp 65001 > nul 2>&1')
            except:
                pass
        
        # Remover marcador de reinicio si existe
        if "venv_restart_marker" in sys.argv:
            sys.argv.remove("venv_restart_marker")
        
        # Verificar y manejar permisos de administrador
        has_admin = handle_admin_permissions()
        
        # Si llegamos aquí, tenemos permisos de administrador
        # Configurar entorno (venv y dependencias)
        if not setup_environment():
            print_colored("⚠️ Error configurando el entorno.", "31")
            wait_for_user_input("Presiona Enter para salir...")
            sys.exit(1)
        
        # Cargar módulos después de configurar el entorno
        if not load_modules():
            print_colored("⚠️ No se pudieron cargar los módulos necesarios.", "31")
            print_colored("💡 Verifica que las dependencias estén instaladas correctamente", "33")
            print_colored("⚠️ Continuando en modo degradado...", "33")
            wait_for_user_input("Presiona Enter para continuar...")
        
        # Limpiar pantalla y mostrar banner
        clear_screen()
        print_banner()
        
        # Solo continuar si se pudieron cargar los módulos básicos
        if Colors is None:
            print_colored("❌ No se pueden cargar los módulos necesarios para el funcionamiento.", "31")
            print_colored("💡 Verifica la estructura del proyecto y las dependencias", "33")
            wait_for_user_input("Presiona Enter para salir...")
            return
        
        # Inicializar base de datos OUI
        loading_animation("Cargando base de datos OUI")
        oui_db = OUIDatabase("OUI/ieee-oui.txt")
        
        # Verificar que se cargó correctamente
        if not oui_db.oui_dict:
            print_colored("⚠️ No se pudo cargar la base de datos OUI", "31")
            print_colored("💡 Verifica que el archivo OUI/ieee-oui.txt existe y tiene el formato correcto", "33")
            wait_for_user_input("Presiona Enter para continuar sin OUI...")
        
        # Inicializar escáner
        scanner = NetworkScanner(oui_db)
        
        # Loop principal del menú
        while True:
            show_menu()
            
            try:
                choice = input(get_system_prompt()).strip()
                
                if choice == '0':
                    print_colored("\n⚠️ Saliendo de PacketShadow...", "31")
                    print_colored("  ╔═══════════════════════════════════════════╗", "36")
                    print_colored("  ║     ¡Gracias por usar PacketShadow!  ║", "36")
                    print_colored("  ║        Happy Hacking! 🚀             ║", "36")
                    print_colored("  ╚═══════════════════════════════════════════╝", "36")
                    wait_for_user_input("Presiona Enter para salir...")
                    break
                
                elif choice == '1':
                    # Escanear rango personalizado
                    network_range = input("\nIngresa el rango de red (formato CIDR): ").strip()
                    
                    if network_range:
                        try:
                            net = ipaddress.IPv4Network(network_range, strict=False)
                            hosts_count = net.num_addresses - 2
                            
                            print_colored(f"✓ Formato válido: {network_range}", "32")
                            print_colored(f"Hosts a escanear: {hosts_count}", "36")
                            
                            if hosts_count > 1000:
                                print_colored("⚠️ Red muy grande - Este escaneo puede tardar mucho tiempo", "33")
                                confirm = input("¿Continuar? (y/N): ").lower()
                                if confirm not in ['y', 'yes', 's', 'si']:
                                    print_colored("Escaneo cancelado", "36")
                                    continue
                            
                            scanner.scan_network_range(network_range)
                            scanner.display_results()
                            
                            # Preguntar si desea desconectar dispositivos
                            confirm_deauth = input("\n¿Quieres desconectar algún dispositivo? (s/N): ").lower()
                            if confirm_deauth in ['s', 'si', 'y', 'yes']:
                                target_ips_input = input("Ingresa las IPs de los dispositivos a desconectar (separadas por comas): ").strip()
                                target_ips = [ip.strip() for ip in target_ips_input.split(',') if ip.strip()]
                                if target_ips:
                                    interface = input("Ingresa la interfaz de red (e.g., wlan0 o Wi-Fi): ").strip()
                                    deauth_device(target_ips, interface, scanner)
                                else:
                                    print_colored("⚠️ No se especificaron IPs válidas", "31")
                                    
                        except ValueError as e:
                            print_colored(f"⚠️ Formato de red inválido: {e}", "31")
                    else:
                        print_colored("⚠️ No se especificó ningún rango", "31")
                
                elif choice == '2':
                    # Escanear IP específica
                    ip = input("Ingresa la IP a escanear: ").strip()
                    
                    if ip:
                        try:
                            ipaddress.IPv4Address(ip)
                            print_colored(f"\nEscaneando {ip}...", "36")
                            
                            result = scanner.scan_host(ipaddress.IPv4Address(ip))
                            if result:
                                scanner.active_hosts = [result]
                                scanner.display_results()
                                
                                # Preguntar si desea desconectar el dispositivo
                                confirm_deauth = input("\n¿Quieres desconectar este dispositivo? (s/N): ").lower()
                                if confirm_deauth in ['s', 'si', 'y', 'yes']:
                                    interface = input("Ingresa la interfaz de red (e.g., wlan0 o Wi-Fi): ").strip()
                                    deauth_device([ip], interface, scanner)
                            else:
                                print_colored(f"⚠️ Host {ip} no está activo o no es accesible", "31")
                                
                        except ValueError:
                            print_colored("⚠️ Formato de IP inválido", "31")
                    else:
                        print_colored("⚠️ No se especificó ninguna IP", "31")
                
                elif choice == '3':
                    # Ver últimos resultados
                    if scanner.active_hosts:
                        print_colored("\nMostrando últimos resultados...", "36")
                        scanner.display_results()
                        
                        # Preguntar si desea desconectar dispositivos
                        confirm_deauth = input("\n¿Quieres desconectar algún dispositivo? (s/N): ").lower()
                        if confirm_deauth in ['s', 'si', 'y', 'yes']:
                            target_ips_input = input("Ingresa las IPs de los dispositivos a desconectar (separadas por comas): ").strip()
                            target_ips = [ip.strip() for ip in target_ips_input.split(',') if ip.strip()]
                            if target_ips:
                                interface = input("Ingresa la interfaz de red (e.g., wlan0 o Wi-Fi): ").strip()
                                deauth_device(target_ips, interface, scanner)
                            else:
                                print_colored("⚠️ No se especificaron IPs válidas", "31")
                    else:
                        print_colored("\n⚠️ No hay resultados previos", "31")
                        print_colored("💡 Realiza un escaneo primero usando las opciones 1 o 2", "33")
                
                elif choice == '4':
                    # Actualizar base de datos OUI
                    print_colored("\nRecargando base de datos OUI...", "36")
                    loading_animation("Actualizando base de datos OUI", 1)
                    
                    oui_db = OUIDatabase("OUI/ieee-oui.txt")
                    scanner.oui_db = oui_db
                    
                    if oui_db.oui_dict:
                        print_colored("✅ Base de datos actualizada correctamente", "32")
                    else:
                        print_colored("⚠️ Error al actualizar la base de datos", "31")
                
                elif choice == '5':
                    # Información del sistema
                    show_system_info()
                
                elif choice.lower() in ['help', 'h', '?', 'ayuda']:
                    print_colored("\n💡 Comandos disponibles:", "36")
                    print_colored("  1 - Escanear rango de red personalizado", "37")
                    print_colored("  2 - Escanear IP específica", "37")
                    print_colored("  3 - Ver últimos resultados", "37")
                    print_colored("  4 - Actualizar base de datos OUI", "37")
                    print_colored("  5 - Información del sistema", "37")
                    print_colored("  0 - Salir", "37")
                
                else:
                    print_colored(f"\n⚠️ Opción no válida: '{choice}'", "31")
                    print_colored("💡 Usa números del 0-5 o 'help' para ayuda", "33")
                
                # Pausa antes de volver al menú (excepto al salir)
                if choice != '0':
                    wait_for_user_input("\nPresiona Enter para volver al menú principal...")
                    clear_screen()
                    print_banner()
            
            except KeyboardInterrupt:
                print_colored("\n\n⚠️ Interrumpido por el usuario (Ctrl+C)", "31")
                print_colored("💡 Saliendo de forma segura...", "33")
                wait_for_user_input("Presiona Enter para salir...")
                break
                
            except EOFError:
                print_colored("\n\n⚠️ Entrada terminada inesperadamente", "31")
                wait_for_user_input("Presiona Enter para salir...")
                break
                
            except Exception as e:
                print_colored(f"\n⚠️ Error inesperado: {e}", "31")
                print_colored("💡 Continuando...", "33")
                wait_for_user_input("Presiona Enter para continuar...")
    
    except Exception as e:
        print_colored(f"⚠️ Error crítico: {e}", "31")
        wait_for_user_input("Presiona Enter para salir...")
        sys.exit(1)

if __name__ == "__main__":
    main()
