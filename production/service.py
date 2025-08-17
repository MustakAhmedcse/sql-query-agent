import multiprocessing
import sys
import os

# ---------- Force venv activation BEFORE any other imports ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_DIR = os.path.join(BASE_DIR, ".venv")

# Ensure we're using the venv Python executable
venv_python = os.path.join(VENV_DIR, "Scripts", "python.exe")
current_python = sys.executable

# If we're not running from venv Python, restart with venv Python
if os.path.normpath(current_python).lower() != os.path.normpath(venv_python).lower():
    import subprocess
    # Re-execute this script with the venv Python
    exit_code = subprocess.call([venv_python] + sys.argv)
    sys.exit(exit_code)

# Add venv to Python path for proper module loading
venv_site_packages = os.path.join(VENV_DIR, "Lib", "site-packages")
if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

# Set environment variables for venv
os.environ['VIRTUAL_ENV'] = VENV_DIR
if 'PYTHONHOME' in os.environ:
    del os.environ['PYTHONHOME']

# Now import Windows service modules
import subprocess
import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import time
import threading
import shutil
from logging.handlers import RotatingFileHandler
import logging

class SQLQueryAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "SQLQueryAgent"
    _svc_display_name_ = "SQL Query Agent Service"
    _svc_description_ = "AI-powered SQL generation service for BL Commission reports"
    
    # Specify the Python executable to use
    _exe_name_ = os.path.join(VENV_DIR, "Scripts", "python.exe")
    _exe_args_ = '"{}"'.format(os.path.abspath(__file__))
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.process = None
        self.app_dir = BASE_DIR
        self._setup_service_logging()

    # ---------- Logging to file for the service wrapper ----------
    def _setup_service_logging(self):
        try:
            os.makedirs(os.path.join(self.app_dir, "logs"), exist_ok=True)
            log_path = os.path.join(self.app_dir, "logs", "service-wrapper.log")
            self.logger = logging.getLogger("sqlqueryagent.service")
            self.logger.setLevel(logging.INFO)
            if not self.logger.handlers:
                handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
                fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
                handler.setFormatter(fmt)
                self.logger.addHandler(handler)
        except Exception as e:
            servicemanager.LogErrorMsg(f"Failed to set up service logging: {e}")
            self.logger = None

    def _log(self, level, msg):
        try:
            if self.logger:
                getattr(self.logger, level)(msg)
        except Exception:
            pass
        if level == "error":
            servicemanager.LogErrorMsg(msg)
        elif level == "info":
            servicemanager.LogInfoMsg(msg)

    # ---------- Child process starter in background ----------
    def _start_uvicorn(self):
        try:
            os.chdir(self.app_dir)
            sys.path.append(os.path.join(self.app_dir, 'production', 'config'))
            os.environ['PYTHONIOENCODING'] = 'utf-8'

            # Ensure logging config exists
            logging_config = os.path.join(self.app_dir, 'logging.conf')
            if not os.path.exists(logging_config):
                source_config = os.path.join(self.app_dir, 'production', 'config', 'logging.conf')
                if os.path.exists(source_config):
                    shutil.copy2(source_config, logging_config)

            # Use venv's python for uvicorn
            venv_python = os.path.join(self.app_dir, '.venv', 'Scripts', 'python.exe')
            if not os.path.exists(venv_python):
                raise FileNotFoundError(f"Virtualenv python not found at: {venv_python}")

            uvicorn_cmd = [
                venv_python, '-m', 'uvicorn',
                'web.app:app',
                '--host', '0.0.0.0',
                '--port', '8000',
                '--workers', str(min(multiprocessing.cpu_count() * 2 + 1, 4)),
                '--log-config', os.path.join(self.app_dir, 'logging.conf')
            ]

            # Redirect child logs to file
            os.makedirs(os.path.join(self.app_dir, "logs"), exist_ok=True)
            child_log_path = os.path.join(self.app_dir, "logs", "uvicorn-service.log")
            child_log = open(child_log_path, "a", encoding="utf-8", buffering=1)

            self._log("info", f"Starting Uvicorn: {' '.join(uvicorn_cmd)}")
            self.process = subprocess.Popen(
                uvicorn_cmd,
                stdout=child_log,
                stderr=child_log,
                cwd=self.app_dir,
                env=os.environ.copy(),
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
            )

            start_time = time.time()
            while True:
                if win32event.WaitForSingleObject(self.hWaitStop, 100) == win32event.WAIT_OBJECT_0:
                    break
                ret = self.process.poll()
                if ret is not None:
                    self._log("error", f"Uvicorn exited early with code {ret}. See {child_log_path} for details.")
                    break
                if time.time() - start_time > 10:
                    time.sleep(1)
                else:
                    time.sleep(0.2)

            if self.process and self.process.poll() is None:
                self.process.wait()

        except Exception as e:
            self._log("error", f"Error in Uvicorn process: {e}")

    # ---------- Service control handlers ----------
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING, waitHint=20000)
        win32event.SetEvent(self.hWaitStop)

        if self.process:
            try:
                self._log("info", "Stopping Uvicorn process...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self._log("info", "Uvicorn did not exit in time; killing...")
                    self.process.kill()
                    self.process.wait()
                self._log("info", "Service stopped successfully.")
            except Exception as e:
                self._log("error", f"Error stopping service: {e}")

        self.ReportServiceStatus(win32service.SERVICE_STOPPED)

    def SvcDoRun(self):
        self._log("info", "Service starting...")
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING, waitHint=60000)
        t = threading.Thread(target=self._start_uvicorn, daemon=True)
        t.start()
        self.ReportServiceStatus(win32service.SERVICE_RUNNING)
        self._log("info", "Service reported as RUNNING.")
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(SQLQueryAgentService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(SQLQueryAgentService)
