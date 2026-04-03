import os
import platform
import multiprocessing
import socket
import json
from typing import Dict, Any

class DeviceAwareness:
    """
    Analyzes local device constraints to determine operational edge cases
    and classify the node type (Compute vs Signal).
    """

    @staticmethod
    def get_system_constraints() -> Dict[str, Any]:
        """Collects hardware and OS metrics using standard libraries."""
        try:
            cpu_count = multiprocessing.cpu_count()
        except:
            cpu_count = 1

        # Memory estimation (may require OS-specific commands if psutil is missing)
        mem_gb = 0
        if platform.system() == "Windows":
            try:
                # Use wmic for Windows
                from subprocess import check_output
                out = check_output(['wmic', 'computersystem', 'get', 'TotalPhysicalMemory']).decode()
                mem_gb = int(out.split()[1]) / (1024**3)
            except:
                mem_gb = 4 # Default fallback
        else:
            try:
                # Use /proc/meminfo for Linux
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        if "MemTotal" in line:
                            mem_gb = int(line.split()[1]) / (1024*1024)
                            break
            except:
                mem_gb = 4

        return {
            "os": platform.system(),
            "arch": platform.machine(),
            "cpus": cpu_count,
            "ram_gb": round(mem_gb, 2),
            "hostname": socket.gethostname()
        }

    @staticmethod
    def classify_device() -> Dict[str, Any]:
        """
        Classifies the device based on constraints.
        BCIs/Embedded are marked as 'EDGE_SIGNAL'.
        PCs/Servers are marked as 'COMPUTE_NODE'.
        """
        stats = DeviceAwareness.get_system_constraints()
        
        # Heuristic for Edge Signal (e.g., Raspberry Pi Zero, Microcontrollers, BCIs)
        # Typically < 2 CPUs and < 2GB RAM
        is_edge = stats['cpus'] <= 2 and stats['ram_gb'] < 2.5
        
        classification = "EDGE_SIGNAL" if is_edge else "COMPUTE_NODE"
        
        # P2P Connectivity Check (True/False Probe)
        p2p_capable = False
        try:
            # Check if we can open a local socket listener (basic P2P capability check)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            # Try to bind to a random high port
            s.bind(('', 0))
            p2p_capable = True
            s.close()
        except:
            p2p_capable = False

        return {
            "type": classification,
            "p2p_status": p2p_capable,
            "metrics": stats,
            "difficulty_multiplier": 0.5 if is_edge else 1.0,
            "max_difficulty_clamp": 3 if is_edge else 6
        }

    @staticmethod
    def get_edge_case_config() -> Dict[str, Any]:
        """Returns dynamic overrides for config/settings.json."""
        device = DeviceAwareness.classify_device()
        
        return {
            "base_difficulty": 1 if device["type"] == "EDGE_SIGNAL" else 2,
            "max_difficulty_clamp": device["max_difficulty_clamp"],
            "is_p2p_ready": device["p2p_status"],
            "device_signature": f"{device['type']}_{device['metrics']['arch']}"
        }

if __name__ == "__main__":
    # Self-test
    print(json.dumps(DeviceAwareness.classify_device(), indent=2))
