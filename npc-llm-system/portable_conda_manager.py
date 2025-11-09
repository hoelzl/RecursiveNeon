"""
Portable Conda Manager - Helper for using bundled micromamba

This allows your application to optionally use the bundled micromamba
for advanced features like:
- Installing additional packages at runtime
- Creating custom environments
- Downloading models via conda channels
"""

import subprocess
import os
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class PortableCondaManager:
    """
    Manages the bundled micromamba installation
    
    This is optional - the main application works without it.
    Use this for advanced features only.
    """
    
    def __init__(self, app_dir: Optional[Path] = None):
        """
        Initialize the portable conda manager
        
        Args:
            app_dir: Application directory (auto-detected if None)
        """
        if app_dir is None:
            # Auto-detect from script location
            app_dir = Path(__file__).parent
        
        self.app_dir = Path(app_dir)
        self.conda_dir = self.app_dir / "portable_conda"
        self.micromamba_exe = self.conda_dir / "Library" / "bin" / "micromamba.exe"
        self.envs_dir = self.conda_dir / "envs"
        
        # Set environment variables for micromamba
        self.env = os.environ.copy()
        self.env["MAMBA_ROOT_PREFIX"] = str(self.conda_dir)
        
    def is_available(self) -> bool:
        """Check if micromamba is bundled and available"""
        return self.micromamba_exe.exists()
    
    def get_version(self) -> Optional[str]:
        """Get micromamba version"""
        if not self.is_available():
            return None
        
        try:
            result = subprocess.run(
                [str(self.micromamba_exe), "--version"],
                capture_output=True,
                text=True,
                env=self.env
            )
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to get micromamba version: {e}")
            return None
    
    def list_environments(self) -> List[str]:
        """List available conda environments"""
        if not self.is_available():
            return []
        
        try:
            result = subprocess.run(
                [str(self.micromamba_exe), "env", "list"],
                capture_output=True,
                text=True,
                env=self.env
            )
            
            # Parse output
            envs = []
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if parts:
                        envs.append(parts[0])
            
            return envs
        except Exception as e:
            logger.error(f"Failed to list environments: {e}")
            return []
    
    def create_environment(
        self,
        name: str,
        python_version: str = "3.11",
        packages: Optional[List[str]] = None
    ) -> bool:
        """
        Create a new conda environment
        
        Args:
            name: Environment name
            python_version: Python version to install
            packages: Additional packages to install
            
        Returns:
            True if successful
        """
        if not self.is_available():
            logger.error("Micromamba not available")
            return False
        
        try:
            cmd = [
                str(self.micromamba_exe),
                "create",
                "-n", name,
                f"python={python_version}",
                "-y"
            ]
            
            if packages:
                cmd.extend(packages)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env
            )
            
            if result.returncode == 0:
                logger.info(f"Created environment: {name}")
                return True
            else:
                logger.error(f"Failed to create environment: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating environment: {e}")
            return False
    
    def install_package(
        self,
        package: str,
        environment: str = "base",
        channel: str = "conda-forge"
    ) -> bool:
        """
        Install a package in an environment
        
        Args:
            package: Package name (e.g., 'numpy', 'pandas')
            environment: Environment name
            channel: Conda channel
            
        Returns:
            True if successful
        """
        if not self.is_available():
            logger.error("Micromamba not available")
            return False
        
        try:
            cmd = [
                str(self.micromamba_exe),
                "install",
                "-n", environment,
                "-c", channel,
                package,
                "-y"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env
            )
            
            if result.returncode == 0:
                logger.info(f"Installed {package} in {environment}")
                return True
            else:
                logger.error(f"Failed to install package: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing package: {e}")
            return False
    
    def run_command_in_env(
        self,
        environment: str,
        command: List[str]
    ) -> Optional[str]:
        """
        Run a command in a conda environment
        
        Args:
            environment: Environment name
            command: Command and arguments as list
            
        Returns:
            Command output or None if failed
        """
        if not self.is_available():
            logger.error("Micromamba not available")
            return None
        
        try:
            cmd = [
                str(self.micromamba_exe),
                "run",
                "-n", environment
            ] + command
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self.env
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Command failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error running command: {e}")
            return None


# Example usage functions

def example_basic_usage():
    """Example: Check if micromamba is available"""
    manager = PortableCondaManager()
    
    if manager.is_available():
        print(f"✅ Micromamba available: {manager.get_version()}")
        print(f"Environments: {manager.list_environments()}")
    else:
        print("❌ Micromamba not bundled (application works without it)")


def example_create_custom_env():
    """Example: Create a custom environment for plugins"""
    manager = PortableCondaManager()
    
    if not manager.is_available():
        print("Micromamba not available")
        return
    
    # Create environment with additional packages
    print("Creating custom environment...")
    success = manager.create_environment(
        name="plugins",
        python_version="3.11",
        packages=["requests", "beautifulsoup4"]
    )
    
    if success:
        print("✅ Environment created!")
    else:
        print("❌ Failed to create environment")


def example_install_package():
    """Example: Install a package at runtime"""
    manager = PortableCondaManager()
    
    if not manager.is_available():
        print("Micromamba not available")
        return
    
    # Install a package for voice synthesis
    print("Installing TTS package...")
    success = manager.install_package(
        package="TTS",
        environment="base",
        channel="conda-forge"
    )
    
    if success:
        print("✅ Package installed!")
    else:
        print("❌ Installation failed")


def example_model_downloader():
    """Example: Use conda to download models"""
    manager = PortableCondaManager()
    
    if not manager.is_available():
        print("Using fallback download method...")
        return
    
    # Create environment for model management
    manager.create_environment(
        name="models",
        packages=["huggingface_hub"]
    )
    
    # Download model using huggingface-cli
    output = manager.run_command_in_env(
        environment="models",
        command=[
            "huggingface-cli",
            "download",
            "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
            "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            "--local-dir", "models"
        ]
    )
    
    if output:
        print("✅ Model downloaded!")
    else:
        print("❌ Download failed")


if __name__ == "__main__":
    # Test the manager
    example_basic_usage()
