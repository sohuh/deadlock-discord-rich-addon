"""
Deadlock Discord Rich Presence
A system tray application that updates Discord status when playing Deadlock
Now with HERO DETECTION!
"""

import time
import psutil
from pypresence import Presence
import pystray
from PIL import Image, ImageDraw
from threading import Thread
import sys
import os
import re
from pathlib import Path

# Configuration
CLIENT_ID = '1469933400633639003'  # Replace with your Discord Client ID
DEADLOCK_PROCESS = 'project8.exe'  # Deadlock's process name
UPDATE_INTERVAL = 15  # Seconds between updates
ENABLE_HERO_DETECTION = True  # Set to False to disable hero detection

# Hero name mapping (internal name -> display name)
HERO_NAMES = {
    'hero_abrams': 'Abrams',
    'hero_bebop': 'Bebop',
    'hero_dynamo': 'Dynamo',
    'hero_grey_talon': 'Grey Talon',
    'hero_haze': 'Haze',
    'hero_infernus': 'Infernus',
    'hero_ivy': 'Ivy',
    'hero_kelvin': 'Kelvin',
    'hero_lady_geist': 'Lady Geist',
    'hero_lash': 'Lash',
    'hero_mcginnis': 'McGinnis',
    'hero_mirage': 'Mirage',
    'hero_mo_krill': 'Mo & Krill',
    'hero_paradox': 'Paradox',
    'hero_pocket': 'Pocket',
    'hero_seven': 'Seven',
    'hero_shiv': 'Shiv',
    'hero_synth': 'Vindicta',
    'hero_viscous': 'Viscous',
    'hero_warden': 'Warden',
    'hero_wraith': 'Wraith',
    'hero_yamato': 'Yamato',
    # Add more heroes as they're released
    'hero_gigawatt': 'Seven',  # Alternate name
    'hero_tengu': 'Ivy',  # Alternate name
}

class DeadlockRPC:
    def __init__(self):
        self.rpc = None
        self.running = False
        self.game_start_time = None
        self.was_playing = False
        self.icon = None
        self.current_hero = None
        self.steam_userdata_path = self.find_steam_userdata()
        
    def find_steam_userdata(self):
        """Find Steam userdata folder for Deadlock"""
        possible_paths = [
            Path(os.path.expandvars(r'%ProgramFiles(x86)%\Steam\userdata')),
            Path(os.path.expandvars(r'%ProgramFiles%\Steam\userdata')),
            Path.home() / '.steam' / 'steam' / 'userdata',  # Linux
        ]
        
        for base_path in possible_paths:
            if base_path.exists():
                # Look for Deadlock's app ID (1422450) in any user folder
                for user_folder in base_path.iterdir():
                    if user_folder.is_dir():
                        deadlock_path = user_folder / '1422450' / 'remote'
                        if deadlock_path.exists():
                            return deadlock_path
        return None
    
    def detect_hero_from_logs(self):
        """
        Detect current hero from various sources
        Method 1: Check recent console log if available
        Method 2: Parse config files
        """
        if not ENABLE_HERO_DETECTION or not self.steam_userdata_path:
            return None
        
        hero = None
        
        # Try to read from console log if it exists
        console_log_paths = [
            Path(os.path.expandvars(r'%ProgramFiles(x86)%\Steam\steamapps\common\Deadlock\game\citadel\console.log')),
            Path(os.path.expandvars(r'%ProgramFiles%\Steam\steamapps\common\Deadlock\game\citadel\console.log')),
        ]
        
        for log_path in console_log_paths:
            if log_path.exists():
                try:
                    # Read last 5000 characters of log file
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(0, 2)  # Go to end
                        file_size = f.tell()
                        f.seek(max(0, file_size - 5000))
                        content = f.read()
                        
                        # Look for hero selection patterns
                        # Pattern: "selecthero hero_xxx" or similar
                        hero_patterns = [
                            r'selecthero\s+(hero_\w+)',
                            r'Playing as:\s+(hero_\w+)',
                            r'Selected hero:\s+(hero_\w+)',
                        ]
                        
                        for pattern in hero_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            if matches:
                                hero = matches[-1].lower()  # Get the most recent match
                                break
                        
                        if hero:
                            break
                except Exception as e:
                    print(f"Could not read console log: {e}")
        
        # If found a hero, return the display name
        if hero and hero in HERO_NAMES:
            return HERO_NAMES[hero]
        
        return None
        
    def create_icon_image(self):
        """Create a simple icon for the system tray"""
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='black')
        dc = ImageDraw.Draw(image)
        dc.rectangle([0, 0, width, height], fill='#2B2D31')
        dc.ellipse([16, 16, 48, 48], fill='#5865F2')
        return image
    
    def is_deadlock_running(self):
        """Check if Deadlock is currently running"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'].lower() == DEADLOCK_PROCESS.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    
    def connect_rpc(self):
        """Connect to Discord RPC"""
        try:
            if self.rpc is None:
                self.rpc = Presence(CLIENT_ID)
                self.rpc.connect()
                print("✓ Connected to Discord!")
                return True
        except Exception as e:
            print(f"✗ Failed to connect to Discord: {e}")
            self.rpc = None
            return False
    
    def update_presence(self):
        """Main loop to update Discord presence"""
        self.running = True
        
        while self.running:
            try:
                is_playing = self.is_deadlock_running()
                
                if is_playing and not self.was_playing:
                    # Game just started
                    if self.connect_rpc():
                        self.game_start_time = time.time()
                        hero = self.detect_hero_from_logs()
                        self.current_hero = hero
                        
                        # Build the Discord presence
                        details = "Playing Deadlock"
                        state = "In Game"
                        
                        if hero:
                            state = f"Playing {hero}"
                        
                        self.rpc.update(
                            state=state,
                            details=details,
                            large_image="deadlock_logo",
                            large_text="Deadlock",
                            start=int(self.game_start_time)
                        )
                        print(f"✓ Updated Discord: {details} - {state}")
                    self.was_playing = True
                    
                elif not is_playing and self.was_playing:
                    # Game just stopped
                    if self.rpc:
                        try:
                            self.rpc.clear()
                            print("✓ Cleared Discord presence")
                        except:
                            pass
                    self.game_start_time = None
                    self.current_hero = None
                    self.was_playing = False
                    
                elif is_playing and self.was_playing:
                    # Game is still running
                    # Check if hero changed (for respawn or hero swap in sandbox)
                    new_hero = self.detect_hero_from_logs()
                    
                    if new_hero != self.current_hero:
                        self.current_hero = new_hero
                        print(f"✓ Hero changed to: {new_hero}")
                    
                    # Keep presence alive with current info
                    if self.rpc and self.game_start_time:
                        try:
                            details = "Playing Deadlock"
                            state = "In Game"
                            
                            if self.current_hero:
                                state = f"Playing {self.current_hero}"
                            
                            self.rpc.update(
                                state=state,
                                details=details,
                                large_image="deadlock_logo",
                                large_text="Deadlock",
                                start=int(self.game_start_time)
                            )
                        except:
                            # Connection lost, try to reconnect
                            self.rpc = None
                            self.connect_rpc()
                
                time.sleep(UPDATE_INTERVAL)
                
            except Exception as e:
                print(f"✗ Error in update loop: {e}")
                time.sleep(UPDATE_INTERVAL)
    
    def on_quit(self, icon, item):
        """Handle quit action from system tray"""
        print("Shutting down...")
        self.running = False
        if self.rpc:
            try:
                self.rpc.close()
            except:
                pass
        icon.stop()
        sys.exit(0)
    
    def run(self):
        """Start the application"""
        print("=" * 50)
        print("Deadlock Discord Rich Presence with Hero Detection")
        print("=" * 50)
        print(f"Client ID: {CLIENT_ID}")
        print(f"Watching for: {DEADLOCK_PROCESS}")
        print(f"Hero Detection: {'Enabled' if ENABLE_HERO_DETECTION else 'Disabled'}")
        print("")
        print("For hero detection to work:")
        print("1. Add '-condebug' to Deadlock launch options")
        print("2. Press F7 in-game and enable console")
        print("")
        print("Minimize this window - the app runs in your system tray")
        print("Right-click the tray icon to quit")
        print("=" * 50)
        
        # Start the RPC update thread
        rpc_thread = Thread(target=self.update_presence, daemon=True)
        rpc_thread.start()
        
        # Create system tray icon
        image = self.create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Deadlock Discord RPC", lambda: None, enabled=False),
            pystray.MenuItem("Quit", self.on_quit)
        )
        
        self.icon = pystray.Icon("deadlock_rpc", image, "Deadlock Discord RPC", menu)
        self.icon.run()

if __name__ == "__main__":
    app = DeadlockRPC()
    app.run()
